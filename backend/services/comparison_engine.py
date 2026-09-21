"""Diff-Driven ROI Comparison Pipeline Orchestrator.

Orchestrates full comparison flow:
  1. Title-block OCR signature matching for page pairing
  2. Memory-efficient PDF page rasterization with dynamic DPI
  3. Diff-Driven ROI Patch audit via services.classify.compare_drawing_pages
  4. Database persistence, caching, and annotated export generation
"""
import os
import traceback
import logging
from typing import Callable, Optional

import cv2
import numpy as np

from services.classify import compare_drawing_pages
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

logger = logging.getLogger(__name__)


# DPI computation constants (mirrored from pdf_pages)
BASE_DPI = float(os.getenv("BASE_DPI", "200.0"))
MAX_WIDTH_FOR_BASE_DPI = float(os.getenv("MAX_WIDTH_FOR_BASE_DPI", "24.0"))
MAX_DPI = float(os.getenv("MAX_DPI", "200.0"))
MIN_DPI = float(os.getenv("MIN_DPI", "72.0"))

# Maximum pages to process per comparison (prevent runaway processing on huge docs)
MAX_PAGES_PER_COMPARISON = int(os.getenv("MAX_PAGES_PER_COMPARISON", "20"))


def _encode_annotated_source(image: np.ndarray) -> bytes:
    """Encode the rendered page image for annotated export storage."""
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError("Could not encode annotated export source image")
    return encoded.tobytes()


def _compute_pair_dpi(old_page_info: dict, new_page_info: dict) -> float:
    """Compute render DPI for a matched page pair based on physical dimensions."""
    max_width_in = max(old_page_info["width_in"], new_page_info["width_in"])
    if max_width_in <= MAX_WIDTH_FOR_BASE_DPI:
        return BASE_DPI
    computed_dpi = BASE_DPI * (MAX_WIDTH_FOR_BASE_DPI / max_width_in)
    return max(MIN_DPI, min(MAX_DPI, computed_dpi))


def compare_page_pair(
    old_img: np.ndarray,
    new_img: np.ndarray,
    render_dpi: float = None,
    page_size_pts: tuple = None,
) -> dict:
    """Compare one matched page pair using the Diff-Driven ROI Patch architecture.

    Args:
        old_img: BGR ndarray of the old drawing page.
        new_img: BGR ndarray of the new drawing page.
        render_dpi: DPI used to render the images (informational).
        page_size_pts: (width_pts, height_pts) of the page in PDF points.

    Returns:
        Page report dict ready for save_report_page(), plus '_comparison_image' key.
    """
    logger.info("[pipeline] Running Diff-Driven ROI Patch comparison architecture...")
    vlm_result = compare_drawing_pages(old_img, new_img)
    changes = vlm_result.get("changes", [])
    overall_summary = vlm_result.get("summary", "")
    aligned_img = vlm_result.get("_aligned_image", new_img)

    result = build_report(
        changes=changes,
        overall_summary=overall_summary,
        render_dpi=render_dpi,
        page_size_pts=page_size_pts,
        pipeline_version="diff_roi_v2",
    )
    # Store aligned image for annotated export rendering
    result["_comparison_image"] = aligned_img
    return result


def run_comparison(
    old_bytes: bytes,
    new_bytes: bytes,
    result_id: str,
    on_progress: Optional[Callable[[str], None]] = None,
    resume: bool = False,
    owner_user_id: int = 1,
) -> dict:
    """Run the full hybrid comparison pipeline on two uploaded files.

    Persists the report under `result_id`. Returns the full document report.
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

    # Detect file types
    old_is_pdf = is_pdf_bytes(old_bytes)
    new_is_pdf = is_pdf_bytes(new_bytes)

    # ── Single image comparison (non-PDF) ────────────────────────────────────
    if not old_is_pdf and not new_is_pdf:
        try:
            _report("Decoding images")
            def _decode_bytes(b: bytes) -> np.ndarray:
                nparr = np.frombuffer(b, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is None:
                    raise ValueError("Could not decode image bytes")
                return img

            old_img = _decode_bytes(old_bytes)
            new_img = _decode_bytes(new_bytes)

            _report("Running VLM comparison")
            page_report = compare_page_pair(old_img, new_img)
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
                comparison_image if comparison_image is not None else new_img
            )

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

    # ── PDF comparison — three-pass memory-efficient flow ────────────────────
    try:
        # Pass 1: Get page metadata
        old_meta = pdf_bytes_get_page_metadata(old_bytes)
        new_meta = pdf_bytes_get_page_metadata(new_bytes)

        if not old_meta or not new_meta:
            raise ValueError("One or both PDFs have no pages")

        # Pass 1b: Title-block crops for page matching
        _report("Rendering title-block crops")
        old_crops = pdf_bytes_render_title_block_crops(old_bytes)
        new_crops = pdf_bytes_render_title_block_crops(new_bytes)

        # Pass 2: OCR signatures → match pages
        _report("Matching pages")
        old_sigs = extract_signatures_from_crops(old_crops)
        new_sigs = extract_signatures_from_crops(new_crops)
        page_matches = match_pages_from_signatures(old_sigs, new_sigs)
        match_summary = get_match_summary(page_matches)

        # Enforce max pages limit to prevent runaway processing
        total_pages = len(page_matches)
        if total_pages > MAX_PAGES_PER_COMPARISON:
            raise ValueError(
                f"Document comparison involves {total_pages} total pages, which exceeds the limit of "
                f"{MAX_PAGES_PER_COMPARISON}. Please split into smaller comparisons or increase "
                f"MAX_PAGES_PER_COMPARISON environment variable."
            )

        # Checkpoint map for resume
        completed_keys = set()
        if resume:
            for row in get_page_status_map(report_id):
                if row["page_number"] is not None:
                    if row["page_status"] != "failed":
                        completed_keys.add(("old", row["page_number"]))
                elif row["page_status"] != "failed":
                    completed_keys.add(("new", row["matched_new_page_number"]))

        page_reports = []

        if not resume:
            report_id = init_report(
                report_id, total_pages=len(page_matches), page_matching=match_summary,
                common_render_dpi=None, page_size_mismatch=False,
                page_size_mismatch_details=None, content_hash=content_hash,
                owner_user_id=owner_user_id
            ) or report_id

        matched_total = sum(
            1 for m in page_matches
            if m.old_page_idx is not None and m.new_page_idx is not None
        )
        matched_done = sum(
            1 for m in page_matches
            if m.old_page_idx is not None and m.new_page_idx is not None
            and resume and ("old", m.old_page_number) in completed_keys
        )

        # Pass 3: Process each page
        for match in page_matches:
            if match.old_page_idx is not None and match.new_page_idx is not None:
                # Matched pair
                if resume and ("old", match.old_page_number) in completed_keys:
                    _report(f"Skipping page {match.old_page_number} (already complete)")
                    continue
                matched_done += 1
                _report(f"Comparing page {matched_done} of {matched_total}")

                old_page_info = old_meta[match.old_page_idx]
                new_page_info = new_meta[match.new_page_idx]
                pair_dpi = _compute_pair_dpi(old_page_info, new_page_info)

                try:
                    old_page_full = pdf_bytes_render_single_page(old_bytes, old_page_info["page_number"], pair_dpi)
                    new_page_full = pdf_bytes_render_single_page(new_bytes, new_page_info["page_number"], pair_dpi)

                    old_img = old_page_full["image"]
                    new_img = new_page_full["image"]

                    page_report = compare_page_pair(
                        old_img, new_img,
                        render_dpi=pair_dpi,
                        page_size_pts=(old_page_full["width_pts"], old_page_full["height_pts"]),
                    )
                    comparison_image = page_report.pop("_comparison_image", None)
                    page_report["annotated_source_png"] = _encode_annotated_source(
                        comparison_image if comparison_image is not None else new_img
                    )

                except Exception as e:
                    logger.error(f"Page comparison failed: {e}", exc_info=True)
                    page_report = {
                        "page_number": match.old_page_number,
                        "matched_new_page_number": match.new_page_number,
                        "page_status": "failed",
                        "page_match_method": match.match_method,
                        "page_match_score": round(match.match_score, 1) if match.match_score else None,
                        "changes": [],
                        "total_changes": 0,
                        "render_dpi": None,
                        "pipeline_version": "diff_roi_v2",
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

                if resume:
                    delete_failed_page_result(report_id, match.old_page_number)
                save_report_page(report_id, page_report)
                page_reports.append(page_report)

                del old_page_full, new_page_full, old_img, new_img

            elif match.old_page_idx is not None and match.new_page_idx is None:
                # Page removed
                if resume and ("old", match.old_page_number) in completed_keys:
                    continue
                old_page_info = old_meta[match.old_page_idx]
                page_report = {
                    "page_number": match.old_page_number,
                    "page_status": "removed",
                    "page_match_method": match.match_method,
                    "changes": [],
                    "total_changes": 0,
                    "render_dpi": None,
                    "pipeline_version": "diff_roi_v2",
                    "page_size_pts": {
                        "width": round(old_page_info["width_pts"], 1),
                        "height": round(old_page_info["height_pts"], 1),
                    },
                }
                save_report_page(report_id, page_report)
                page_reports.append(page_report)

            elif match.old_page_idx is None and match.new_page_idx is not None:
                # Page added
                if resume and ("new", match.new_page_number) in completed_keys:
                    continue
                new_page_info = new_meta[match.new_page_idx]
                pair_dpi = _compute_pair_dpi(new_page_info, new_page_info)
                try:
                    added_page_full = pdf_bytes_render_single_page(new_bytes, new_page_info["page_number"], pair_dpi)
                    page_report = {
                        "page_number": None,
                        "matched_new_page_number": match.new_page_number,
                        "page_status": "added",
                        "page_match_method": match.match_method,
                        "changes": [],
                        "total_changes": 0,
                        "render_dpi": pair_dpi,
                        "pipeline_version": "diff_roi_v2",
                        "page_size_pts": {
                            "width": round(new_page_info["width_pts"], 1),
                            "height": round(new_page_info["height_pts"], 1),
                        },
                        "annotated_source_png": _encode_annotated_source(added_page_full["image"]),
                    }
                except Exception as e:
                    logger.error(f"Page comparison failed: {e}", exc_info=True)
                    page_report = {
                        "page_number": None,
                        "matched_new_page_number": match.new_page_number,
                        "page_status": "failed",
                        "page_match_method": match.match_method,
                        "page_match_score": round(match.match_score, 1) if match.match_score else None,
                        "changes": [],
                        "total_changes": 0,
                        "render_dpi": None,
                        "pipeline_version": "diff_roi_v2",
                        "alignment_error": f"Added page processing failed: {e}",
                    }
                if resume:
                    delete_failed_page_result(report_id, matched_new_page_number=match.new_page_number)
                save_report_page(report_id, page_report)
                page_reports.append(page_report)

        if resume:
            stored = get_full_report(report_id)
            document_report = {
                "report_id": report_id,
                "pages": stored["pages"] if stored else page_reports,
                "total_pages": len(stored["pages"]) if stored else len(page_reports),
                "page_count_warning": None,
                "page_matching": match_summary,
                "common_render_dpi": None,
            }
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

        overall_summary = " ".join(
            [p.get("overall_summary", "") for p in page_reports if p.get("overall_summary")]
        ).strip()
        page_sims = [p.get("overall_similarity") for p in page_reports if p.get("overall_similarity") is not None]
        overall_sim = round(sum(page_sims) / len(page_sims), 3) if page_sims else 1.0

        document_report = {
            "report_id": result_id,
            "pages": page_reports,
            "total_pages": len(page_reports),
            "page_count_warning": None,
            "page_matching": match_summary,
            "common_render_dpi": None,
            "overall_summary": overall_summary or "Comparison completed.",
            "overall_similarity": overall_sim,
        }

        complete_report(report_id, len(page_reports), match_summary, None, False, None)
        if report_id != result_id:
            rename_report(report_id, result_id)

        return document_report

    except Exception as e:
        fail_report(report_id)
        if report_id != result_id:
            delete_report(report_id)
        raise
