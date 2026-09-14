"""Shared comparison pipeline.

Extracted from router/drawings.py so that both the standalone POST /compare
endpoint and the drawing-scoped revision comparison run exactly the same
pipeline. Persistence of the produced report is keyed by `result_id`:
- standalone /compare passes a fresh uuid (report_id, as before)
- drawing comparisons pass the comparison_id

Heavy steps (LLM classification, OCR) are module-level imports so tests can
patch them in this namespace.
"""
import os
import traceback
from typing import Callable, Optional

import cv2
import numpy as np

from services.Preprocess import preprocess_pipeline
from services.align import align_image, AlignmentError
from services.classify import llm_classify_batch
from services.diff import (
    compute_diff_mask, extract_change_regions, crop_region,
    extract_paired_crops, make_grid_regions, redesign_metrics, is_redesign,
)
from services.pdf_pages import (
    is_pdf_bytes,
    pdf_bytes_get_page_metadata,
    pdf_bytes_render_title_block_crops,
    pdf_bytes_render_single_page,
)
from services.page_matcher import (
    get_match_summary,
    extract_signatures_from_crops,
    match_pages_from_signatures,
)
from services.report import build_report
from services.report_data import (
    reserve_report, wait_for_report, init_report, save_report_page,
    complete_report, fail_report, _compute_content_hash,
    get_full_report, get_full_report_by_hash, get_page_status_map,
    delete_failed_page_result, get_annotated_export_pages,
    rename_report, copy_report_rows, delete_report,
)
from model.db import connect


VISUAL_CHANGE_THRESHOLD = float(os.getenv("VISUAL_CHANGE_THRESHOLD", "8.0"))

# DPI computation constants (mirrored from pdf_pages)
BASE_DPI = float(os.getenv("BASE_DPI", "200.0"))
MAX_WIDTH_FOR_BASE_DPI = float(os.getenv("MAX_WIDTH_FOR_BASE_DPI", "24.0"))
MAX_DPI = float(os.getenv("MAX_DPI", "400.0"))
MIN_DPI = float(os.getenv("MIN_DPI", "72.0"))
PAGE_SIZE_MISMATCH_THRESHOLD = float(os.getenv("PAGE_SIZE_MISMATCH_THRESHOLD", "0.05"))


def _encode_annotated_source(gray_image: np.ndarray) -> bytes:
    """Persist the already-rendered NEW page used by comparison for export."""
    if gray_image.ndim == 2:
        image = cv2.cvtColor(gray_image, cv2.COLOR_GRAY2BGR)
    else:
        image = gray_image
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError("Could not encode annotated export source image")
    return encoded.tobytes()


def _compute_pair_dpi(old_page_info: dict, new_page_info: dict) -> float:
    """Compute DPI for a matched pair based on the larger physical width of the two pages.
    Uses base DPI for pages up to MAX_WIDTH_FOR_BASE_DPI, scales down for larger pages.
    """
    max_width_in = max(old_page_info["width_in"], new_page_info["width_in"])
    
    if max_width_in <= MAX_WIDTH_FOR_BASE_DPI:
        return BASE_DPI
    
    computed_dpi = BASE_DPI * (MAX_WIDTH_FOR_BASE_DPI / max_width_in)
    return max(MIN_DPI, min(MAX_DPI, computed_dpi))


def _check_page_size_mismatch(old_page: dict, new_page: dict) -> tuple[bool, dict]:
    """Check if two pages have significantly different physical sizes."""
    old_w, old_h = old_page["width_in"], old_page["height_in"]
    new_w, new_h = new_page["width_in"], new_page["height_in"]
    width_diff = abs(old_w - new_w) / max(old_w, new_w)
    height_diff = abs(old_h - new_h) / max(old_h, new_h)
    if width_diff > PAGE_SIZE_MISMATCH_THRESHOLD or height_diff > PAGE_SIZE_MISMATCH_THRESHOLD:
        return True, {
            "old_page_size_in": {"width": round(old_w, 2), "height": round(old_h, 2)},
            "new_page_size_in": {"width": round(new_w, 2), "height": round(new_h, 2)},
            "width_diff_pct": round(width_diff * 100, 1),
            "height_diff_pct": round(height_diff * 100, 1),
        }
    return False, {}


def _transform_bbox_to_raw_new(region: dict, H: np.ndarray, raw_new_shape: tuple) -> Optional[dict]:
    """Map region bounding box from warped/old coordinate space back to original raw new image space using homography H."""
    if H is None:
        return None
    x, y, w, h = region["x"], region["y"], region["w"], region["h"]
    pts = np.float32([
        [x, y],
        [x + w, y],
        [x + w, y + h],
        [x, y + h]
    ]).reshape(-1, 1, 2)
    try:
        pts_new = cv2.perspectiveTransform(pts, H)
        xs = pts_new[:, 0, 0]
        ys = pts_new[:, 0, 1]

        raw_h, raw_w = raw_new_shape[:2]
        min_x = max(0.0, min(float(raw_w), float(np.min(xs))))
        min_y = max(0.0, min(float(raw_h), float(np.min(ys))))
        max_x = max(0.0, min(float(raw_w), float(np.max(xs))))
        max_y = max(0.0, min(float(raw_h), float(np.max(ys))))

        new_w = max(1.0, max_x - min_x)
        new_h = max(1.0, max_y - min_y)

        return {
            "bbox_new": {"x": round(min_x, 2), "y": round(min_y, 2), "w": round(new_w, 2), "h": round(new_h, 2)},
            "bbox_percent_new": {
                "x": round(min_x / raw_w * 100, 4),
                "y": round(min_y / raw_h * 100, 4),
                "w": round(new_w / raw_w * 100, 4),
                "h": round(new_h / raw_h * 100, 4),
            }
        }
    except Exception:
        return None


def compare_single_page(old_source, new_source, render_dpi=None, page_size_pts=None, page_size_mismatch=False, page_mismatch_details=None) -> dict:
    """old_source/new_source: grayscale ndarray (already preprocessed)."""
    old_gray = old_source
    new_gray = new_source

    # For single-page (non-PDF) or already-aligned pages, resize new to match old dimensions
    new_resized = cv2.resize(new_gray, (old_gray.shape[1], old_gray.shape[0]))

    alignment_error = None
    H_matrix = None
    try:
        alignment_result = align_image(old_gray, new_gray)
        H_matrix = alignment_result.get("H")
        wrapped_new_image = alignment_result['warped_new']
        diff_result = compute_diff_mask(old_gray, wrapped_new_image)
        page_regions = extract_change_regions(diff_result["mask"])
        metrics = redesign_metrics(diff_result["mask"], diff_result["similarity_score"],
                                    alignment_result, page_regions)
        redesign_detected = is_redesign(metrics)
    except AlignmentError as e:
        alignment_error = str(e)
        alignment_result = {"match_count": 0, "inlier_count": 0, "confidence": 0.0}
        diff_result = compute_diff_mask(old_gray, new_resized)
        page_regions = extract_change_regions(diff_result["mask"])
        metrics = redesign_metrics(diff_result["mask"], diff_result["similarity_score"],
                                    alignment_result, page_regions)
        redesign_detected = True

    if redesign_detected:
        comparison_mode = "tiled"
        comparison_new_image = new_resized
        # Extract tight diff contours across the page mask instead of rendering rigid tile boundaries
        regions = extract_change_regions(diff_result["mask"])
        if not regions:
            # Fallback to coarse grid if contour extraction finds no connected components
            regions = make_grid_regions(old_gray.shape, rows=8, cols=8)
        print(f"[pipeline] Redesign detected, mode=tiled, {len(regions)} initial regions")
    else:
        comparison_mode = "normal"
        regions = page_regions
        comparison_new_image = wrapped_new_image
        print(f"[pipeline] Normal alignment, {len(regions)} initial regions")

    regions_data = []
    candidate_regions = []
    image_height, image_width = old_gray.shape[:2]
    for region in regions:
        old_crop = crop_region(old_gray, region)
        new_crop = crop_region(comparison_new_image, region)

        visual_delta = cv2.absdiff(old_crop, new_crop)
        visual_change = (
            float(np.mean(visual_delta)) > VISUAL_CHANGE_THRESHOLD
            or int(np.count_nonzero(visual_delta > 25)) > 12
            or float(np.max(visual_delta)) > 50.0
        )
        if comparison_mode == "tiled" and not visual_change:
            continue

        candidate_regions.append(region)

        bbox_percent_a = {
            "x": round(region["x"] / image_width * 100, 4),
            "y": round(region["y"] / image_height * 100, 4),
            "w": round(region["w"] / image_width * 100, 4),
            "h": round(region["h"] / image_height * 100, 4),
        }

        transformed = _transform_bbox_to_raw_new(region, H_matrix, new_gray.shape)
        bbox_percent_b = transformed["bbox_percent_new"] if transformed else bbox_percent_a

        regions_data.append({
            "bbox": {"x": region["x"], "y": region["y"], "w": region["w"], "h": region["h"]},
            "bbox_percent": bbox_percent_a,
            "bbox_percent_new": bbox_percent_b,
            "area_px": region["area"],
            "old_text": "",
            "new_text": "",
            "ocr_confidence": {"old": 0.0, "new": 0.0},
            "classification": {"category": "note_or_annotation_change", "confidence": 0.7},
            "rule_based_classification": {"category": "note_or_annotation_change", "confidence": 0.7},
        })

    # Extract side-by-side patch images with contextual padding for VLM
    patch_images = extract_paired_crops(old_gray, comparison_new_image, candidate_regions)

    print(f"[pipeline] {len(candidate_regions)} candidate regions passed visual_change filter, calling LLM classify...")
    batch = llm_classify_batch(regions_data, patch_images=patch_images)
    print(f"[pipeline] LLM classify returned {len(batch.get('results', {}))} results")
    for region_index, region_data in enumerate(regions_data):
        llm_result = batch["results"].get(region_index, {})
        category = llm_result.get("category", "note_or_annotation_change")
        description = llm_result.get("description", "")
        
        region_data["classification"] = {
            "category": category,
            "confidence": llm_result.get("confidence", 0.85)
        }
        region_data["llm_classification"] = llm_result
        region_data["verification"] = {"verified": True, "reason": None}
        
        # Populate old_text / new_text from VLM explicit fields or parsed description
        if llm_result.get("old_value") or llm_result.get("new_value"):
            region_data["old_text"] = str(llm_result.get("old_value", ""))
            region_data["new_text"] = str(llm_result.get("new_value", ""))
        elif "from" in description.lower() and "to" in description.lower():
            try:
                parts = description.lower().split("from", 1)[1].split("to", 1)
                region_data["old_text"] = parts[0].strip(" '\".,")
                region_data["new_text"] = parts[1].strip(" '\".,")
            except Exception:
                pass

    result = build_report(regions_data, alignment_result, diff_result['similarity_score'],
                         comparison_mode=comparison_mode, redesign_detected=redesign_detected,
                         redesign_metrics=metrics, alignment_error=alignment_error,
                         overall_summary=batch.get("overall_summary", "Comparison complete."),
                         render_dpi=render_dpi, page_size_pts=page_size_pts,
                         page_size_mismatch=page_size_mismatch, page_mismatch_details=page_mismatch_details)
    result["_comparison_image"] = comparison_new_image
    return result



def _preprocess_to_gray(source) -> np.ndarray:
    """Preprocess image bytes or BGR array to grayscale."""
    pre = preprocess_pipeline(source)
    return pre['gray']


def run_comparison(
    old_bytes: bytes,
    new_bytes: bytes,
    result_id: str,
    on_progress: Optional[Callable[[str], None]] = None,
    resume: bool = False,
    owner_user_id: int = 1,
) -> dict:
    """Run the full comparison pipeline on two uploaded files and persist the
    report under `result_id` (report_id for standalone /compare, comparison_id
    for drawing-scoped comparisons). Returns the full document report.
    """

    def _report(message: str) -> None:
        if on_progress is not None:
            on_progress(message)

    if not resume:
        content_hash = _compute_content_hash(old_bytes, new_bytes)
        existing = get_full_report_by_hash(content_hash, owner_user_id=owner_user_id)
        if existing:
            copy_report_rows(existing["report_id"], result_id)
            existing_report = dict(existing)
            existing_report["report_id"] = result_id
            return existing_report

        reserve_result = reserve_report(old_bytes, new_bytes, owner_user_id=owner_user_id)
        if reserve_result is None:
            with connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT report_id FROM reports WHERE owner_user_id = %s AND content_hash = %s AND status IN ('pending', 'complete') ORDER BY created_at DESC LIMIT 1",
                        (owner_user_id, content_hash)
                    )
                    row = cursor.fetchone()
            if row:
                if wait_for_report(row["report_id"], owner_user_id=owner_user_id):
                    completed = get_full_report_by_hash(content_hash, owner_user_id=owner_user_id)
                    if completed:
                        copy_report_rows(completed["report_id"], result_id)
                        completed_report = dict(completed)
                        completed_report["report_id"] = result_id
                        return completed_report
                
                # If we get here, the existing report was failed or timed out.
                # Delete it so we can start a fresh one without hitting UNIQUE KEY conflicts.
                delete_report(row["report_id"], owner_user_id=owner_user_id)

            report_id = result_id
        else:
            reserved_id, outcome = reserve_result
            if outcome == "complete":
                copy_report_rows(reserved_id, result_id)
                completed = get_full_report(reserved_id, owner_user_id=owner_user_id)
                completed_report = dict(completed)
                completed_report["report_id"] = result_id
                return completed_report
            elif outcome == "resume":
                resume = True
                report_id = reserved_id
            else:
                report_id = reserved_id
    else:
        content_hash = _compute_content_hash(old_bytes, new_bytes)
        report_id = result_id

    # Detect type once from filename/content
    old_is_pdf = is_pdf_bytes(old_bytes)
    new_is_pdf = is_pdf_bytes(new_bytes)

    # Single image comparison (non-PDF)
    if not old_is_pdf and not new_is_pdf:
        try:
            _report("Preprocessing images")
            old_gray = _preprocess_to_gray(old_bytes)
            new_gray = _preprocess_to_gray(new_bytes)
            _report("Comparing pages")
            page_report = compare_single_page(old_gray, new_gray)
            comparison_image = page_report.pop("_comparison_image", None)
            page_report["page_number"] = 1
            page_report["page_status"] = "matched"
            page_report["page_match_method"] = "single_image"
            page_report["page_match_score"] = 100.0
            page_report["page_matching"] = get_match_summary([type('Match', (), {
                'old_page_idx': 0, 'new_page_idx': 0, 'match_method': 'single_image',
                'match_score': 100, 'old_page_number': 1, 'new_page_number': 1
            })()])
            page_report["common_render_dpi"] = None
            page_report["annotated_source_png"] = _encode_annotated_source(
                comparison_image if comparison_image is not None else new_gray
            )

            # Initialize and complete in one go for single image
            init_report(report_id, 1, page_report["page_matching"], None, False, None, content_hash, owner_user_id)
            save_report_page(report_id, page_report)
            complete_report(report_id, 1, page_report["page_matching"], None, False, None)
            if report_id != result_id:
                rename_report(report_id, result_id)

            return {
                "report_id": result_id,
                "pages": [page_report],
                "total_pages": 1,
                "page_count_warning": None,
                "page_matching": page_report["page_matching"],
                "common_render_dpi": None,
                "overall_summary": page_report.get("overall_summary", "Comparison completed."),
            }
        except Exception as e:
            fail_report(report_id)
            if report_id != result_id:
                delete_report(report_id)
            raise

    # PDF comparison - three-pass memory-efficient flow
    try:
        # Pass 1: Get page metadata (physical sizes) for both documents
        old_meta = pdf_bytes_get_page_metadata(old_bytes)
        new_meta = pdf_bytes_get_page_metadata(new_bytes)

        if not old_meta or not new_meta:
            raise ValueError("One or both PDFs have no pages")

        # Pass 1b: Render title-block crops at low DPI for all pages (cheap, small images)
        _report("Rendering title-block crops")
        old_crops = pdf_bytes_render_title_block_crops(old_bytes)
        new_crops = pdf_bytes_render_title_block_crops(new_bytes)

        # Pass 2: Extract OCR signatures from crops and match pages
        _report("Matching pages")
        old_sigs = extract_signatures_from_crops(old_crops)
        new_sigs = extract_signatures_from_crops(new_crops)
        page_matches = match_pages_from_signatures(old_sigs, new_sigs)
        match_summary = get_match_summary(page_matches)

        # Checkpoint map for resume: pages already complete are skipped,
        # 'failed'/missing pages are reprocessed below.
        completed_keys = set()
        if resume:
            for row in get_page_status_map(report_id):
                if row["page_number"] is not None:
                    if row["page_status"] != "failed":
                        completed_keys.add(("old", row["page_number"]))
                elif row["page_status"] != "failed":
                    completed_keys.add(("new", row["matched_new_page_number"]))

        # Pass 3: Compare matched pairs one at a time
        page_reports = []

        # Initialize report with document-level metadata (already exists on resume)
        if not resume:
            report_id = init_report(report_id, total_pages=len(page_matches), page_matching=match_summary,
                        common_render_dpi=None, page_size_mismatch=False, page_size_mismatch_details=None, content_hash=content_hash, owner_user_id=owner_user_id) or report_id

        matched_total = sum(
            1 for match in page_matches
            if match.old_page_idx is not None and match.new_page_idx is not None
        )
        matched_done = sum(
            1 for match in page_matches
            if match.old_page_idx is not None and match.new_page_idx is not None
            and resume and ("old", match.old_page_number) in completed_keys
        )
        for match in page_matches:
            if match.old_page_idx is not None and match.new_page_idx is not None:
                if resume and ("old", match.old_page_number) in completed_keys:
                    _report(f"Skipping page {match.old_page_number} (already complete)")
                    continue
                matched_done += 1
                _report(f"Comparing page {matched_done} of {matched_total}")
                # Matched pair - render full pages at appropriate DPI and compare
                old_page_info = old_meta[match.old_page_idx]
                new_page_info = new_meta[match.new_page_idx]

                # Compute DPI for this specific pair based on their physical sizes
                pair_dpi = _compute_pair_dpi(old_page_info, new_page_info)

                try:
                    # Render full pages for this pair only
                    old_page_full = pdf_bytes_render_single_page(old_bytes, old_page_info["page_number"], pair_dpi)
                    new_page_full = pdf_bytes_render_single_page(new_bytes, new_page_info["page_number"], pair_dpi)

                    # Preprocess to grayscale
                    old_gray = _preprocess_to_gray(old_page_full["image"])
                    new_gray = _preprocess_to_gray(new_page_full["image"])

                    # Check for page size mismatch for this pair
                    size_mismatch, mismatch_details = _check_page_size_mismatch(old_page_full, new_page_full)

                    # Compare
                    page_report = compare_single_page(
                        old_gray, new_gray,
                        render_dpi=pair_dpi,
                        page_size_pts=(old_page_full["width_pts"], old_page_full["height_pts"]),
                        page_size_mismatch=size_mismatch,
                        page_mismatch_details=mismatch_details if size_mismatch else None
                    )
                    # Persist the corrected image variant the coordinates were
                    # measured against (aligned/warped or resized) — NOT the
                    # raw new page, or annotated boxes would be misplaced.
                    comparison_image = page_report.pop("_comparison_image", None)
                    page_report["annotated_source_png"] = _encode_annotated_source(
                        comparison_image if comparison_image is not None else new_gray
                    )
                except Exception as e:
                    # Page-specific failure: checkpoint this page as 'failed'
                    # with the error captured, and continue with the rest.
                    traceback.print_exc()
                    page_report = {
                        "page_number": match.old_page_number,
                        "matched_new_page_number": match.new_page_number,
                        "page_status": "failed",
                        "page_match_method": match.match_method,
                        "page_match_score": round(match.match_score, 1) if match.match_score else None,
                        "changes": [],
                        "total_changes": 0,
                        "render_dpi": None,
                        "page_size_mismatch": False,
                        "alignment_error": f"Page comparison failed: {e}",
                    }
                    if resume:
                        delete_failed_page_result(report_id, match.old_page_number)
                    save_report_page(report_id, page_report)
                    page_reports.append(page_report)
                    continue

                page_report["page_number"] = match.old_page_number
                page_report["matched_new_page_number"] = match.new_page_number
                page_report["page_match_method"] = match.match_method
                page_report["page_match_score"] = round(match.match_score, 1) if match.match_score else None
                page_report["page_status"] = "matched"

                # Replace a failed checkpoint for this page, if any, then save
                # immediately (streaming persistence)
                if resume:
                    delete_failed_page_result(report_id, match.old_page_number)
                save_report_page(report_id, page_report)
                page_reports.append(page_report)

                # Explicitly release full-page images
                del old_page_full, new_page_full, old_gray, new_gray

            elif match.old_page_idx is not None and match.new_page_idx is None:
                if resume and ("old", match.old_page_number) in completed_keys:
                    continue
                # Page removed - no full-page render needed
                old_page_info = old_meta[match.old_page_idx]
                page_report = {
                    "page_number": match.old_page_number,
                    "page_status": "removed",
                    "page_match_method": match.match_method,
                    "changes": [],
                    "total_changes": 0,
                    "render_dpi": None,
                    "page_size_pts": {
                        "width": round(old_page_info["width_pts"], 1),
                        "height": round(old_page_info["height_pts"], 1),
                    },
                    "page_size_mismatch": False,
                }
                save_report_page(report_id, page_report)
                page_reports.append(page_report)

            elif match.old_page_idx is None and match.new_page_idx is not None:
                if resume and ("new", match.new_page_number) in completed_keys:
                    continue
                # Page added - no full-page render needed
                new_page_info = new_meta[match.new_page_idx]
                # Added pages have no matched counterpart, so pair_dpi may be
                # undefined if NO pages matched at all. Derive the resolution
                # from the new page itself — this branch never depends on the
                # matched-page code path having run first.
                pair_dpi = _compute_pair_dpi(new_page_info, new_page_info)
                try:
                    # Render the new page for added pages so we have it for annotation
                    added_page_full = pdf_bytes_render_single_page(new_bytes, new_page_info["page_number"], pair_dpi)
                    page_report = {
                        "page_number": None,
                        "matched_new_page_number": match.new_page_number,
                        "page_status": "added",
                        "page_match_method": match.match_method,
                        "changes": [],
                        "total_changes": 0,
                        "render_dpi": pair_dpi,
                        "page_size_pts": {
                            "width": round(new_page_info["width_pts"], 1),
                            "height": round(new_page_info["height_pts"], 1),
                        },
                        "page_size_mismatch": False,
                        "annotated_source_png": _encode_annotated_source(added_page_full["image"]),
                    }
                except Exception as e:
                    # Page-specific failure: checkpoint this page as 'failed'
                    # with the error captured, and continue with the rest.
                    traceback.print_exc()
                    page_report = {
                        "page_number": None,
                        "matched_new_page_number": match.new_page_number,
                        "page_status": "failed",
                        "page_match_method": match.match_method,
                        "page_match_score": round(match.match_score, 1) if match.match_score else None,
                        "changes": [],
                        "total_changes": 0,
                        "render_dpi": None,
                        "page_size_mismatch": False,
                        "alignment_error": f"Added page processing failed: {e}",
                    }
                # Replace a failed checkpoint for this page, if any, before saving
                if resume:
                    delete_failed_page_result(report_id, matched_new_page_number=match.new_page_number)
                save_report_page(report_id, page_report)
                page_reports.append(page_report)

        if resume:
            # Assemble the final report from ALL stored pages (previous
            # attempt + this one) in page order — identical to a single-pass
            # result once no 'failed' checkpoints remain.
            stored = get_full_report(report_id)
            document_report = {
                "report_id": report_id,
                "pages": stored["pages"] if stored else page_reports,
                "total_pages": len(stored["pages"]) if stored else len(page_reports),
                "page_count_warning": None,
                "page_matching": match_summary,
                "common_render_dpi": None,  # Per-pair DPI
            }
            # Re-attach stored page renders so the returned shape matches a
            # fresh run's document report.
            stored_pngs = {
                (p["page_number"], p["matched_new_page_number"]): p["annotated_source_png"]
                for p in get_annotated_export_pages(report_id)
            }
            for p in document_report["pages"]:
                png = stored_pngs.get((p["page_number"], p["matched_new_page_number"]))
                if png:
                    p["annotated_source_png"] = png
            complete_report(report_id, document_report["total_pages"], match_summary, None, False, None)
            if report_id != result_id:
                rename_report(report_id, result_id)
            document_report["report_id"] = result_id
            return document_report

        overall_summary = " ".join([p.get("overall_summary", "") for p in page_reports if p.get("overall_summary")]).strip()
        document_report = {
            "report_id": result_id,
            "pages": page_reports,
            "total_pages": len(page_reports),
            "page_count_warning": None,
            "page_matching": match_summary,
            "common_render_dpi": None,  # Per-pair DPI
            "overall_summary": overall_summary or "Comparison completed.",
        }

        # Mark report as complete
        complete_report(report_id, len(page_reports), match_summary, None, False, None)
        # Relabel the reservation rows to the caller's result id
        if report_id != result_id:
            rename_report(report_id, result_id)

        return document_report

    except Exception as e:
        # Mark as failed on error. A run that failed BEFORE any page results
        # exist (e.g. unreadable files, matching failure) worked under its
        # reservation id — delete that placeholder so its content hash is
        # freed and the next attempt can reserve again.
        fail_report(report_id)
        if report_id != result_id:
            delete_report(report_id)
        raise
