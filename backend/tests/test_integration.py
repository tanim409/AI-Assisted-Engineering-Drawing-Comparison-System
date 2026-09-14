"""Integration test for the full pipeline: upload -> compare -> save -> retrieve."""
import sys
import os
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz
import numpy as np
import cv2

from services.pdf_pages import render_pdf_pair_at_common_dpi, image_bytes_to_array
from services.page_matcher import match_pages, get_match_summary
from services.Preprocess import preprocess_pipeline, load_image_from_bytes
from services.report_data import init_report, save_report_page, complete_report, get_report, get_full_report
from model.report_db import init_db


def create_test_pdf_bytes(page_size_inches: tuple, num_pages: int = 1, title_text: str = "") -> bytes:
    """Create a test PDF and return as bytes."""
    doc = fitz.open()
    width_pts = page_size_inches[0] * 72
    height_pts = page_size_inches[1] * 72

    for i in range(num_pages):
        page = doc.new_page(width=width_pts, height=height_pts)
        if title_text:
            x = width_pts * 0.7
            y = height_pts * 0.9
            page.insert_text((x, y), title_text, fontsize=12)
    
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_test_image_bytes(title_text: str = "") -> bytes:
    """Create a test image and return as bytes."""
    img = np.zeros((1000, 800), dtype=np.uint8)
    if title_text:
        cv2.putText(img, title_text, (550, 950), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 255, 2)
    _, encoded = cv2.imencode('.png', img)
    return encoded.tobytes()


def test_full_pipeline_pdf():
    """Test PDF comparison -> save -> retrieve full report -> flat changes for QA."""
    print("Testing PDF pipeline...")
    
    # Create test PDFs
    old_bytes = create_test_pdf_bytes((22, 34), num_pages=2, title_text="SHEET 1 REV A")
    new_bytes = create_test_pdf_bytes((22, 34), num_pages=2, title_text="SHEET 1 REV B")
    
    # Render at common DPI
    old_pages, new_pages, common_dpi, size_mismatch, mismatch_details = render_pdf_pair_at_common_dpi(old_bytes, new_bytes)
    print(f"  Rendered: {len(old_pages)} old pages, {len(new_pages)} new pages at {common_dpi:.1f} DPI")
    
    # Preprocess
    old_gray_pages = [preprocess_pipeline(p["image"])["gray"] for p in old_pages]
    new_gray_pages = [preprocess_pipeline(p["image"])["gray"] for p in new_pages]
    
    # Match pages
    old_page_numbers = [p["page_number"] for p in old_pages]
    new_page_numbers = [p["page_number"] for p in new_pages]
    page_matches = match_pages(old_gray_pages, new_gray_pages, old_page_numbers, new_page_numbers)
    match_summary = get_match_summary(page_matches)
    print(f"  Matched: {match_summary['total_pages_matched']}, added: {match_summary['pages_added']}, removed: {match_summary['pages_removed']}")
    
    # Build page reports
    page_reports = []
    for match in page_matches:
        if match.old_page_idx is not None and match.new_page_idx is not None:
            # For simplicity, just create a mock page report with minimal fields
            page_report = {
                "page_number": match.old_page_number,
                "matched_new_page_number": match.new_page_number,
                "page_status": "matched",
                "page_match_method": match.match_method,
                "page_match_score": match.match_score,
                "comparison_mode": "normal",
                "redesign_detected": False,
                "alignment": {"match_count": 100, "inlier_count": 95, "confidence": 0.95},
                "alignment_error": None,
                "render_dpi": common_dpi,
                "page_size_pts": {"width": 1584.0, "height": 2448.0},
                "page_size_mismatch": size_mismatch,
                "page_size_mismatch_details": mismatch_details if size_mismatch else None,
                "overall_similarity": 0.98,
                "overall_summary": "Test summary",
                "changes": [{"bbox": {"x": 10, "y": 10, "w": 100, "h": 50}, "category": "dimension_change", "old_text": "100mm", "new_text": "120mm"}],
            }
            page_reports.append(page_report)
    
    # Save
    import uuid
    report_id = str(uuid.uuid4())
    content_hash = "test_hash_" + report_id  # dummy for test
    init_report(report_id, len(page_reports), page_reports[0].get("page_matching"), 
                None, False, None, content_hash)
    for page in page_reports:
        save_report_page(report_id, page)
    complete_report(report_id, len(page_reports), page_reports[0].get("page_matching"), 
                    None, False, None)
    print(f"  Saved report: {report_id}")
    
    # Retrieve flat changes (for QA)
    flat_changes = get_report(report_id)
    print(f"  Flat changes retrieved: {len(flat_changes)} changes")
    assert len(flat_changes) == 2  # 2 pages * 1 change each
    
    # Retrieve full structured report
    full_report = get_full_report(report_id)
    print(f"  Full report retrieved: {full_report['report_id']}")
    assert full_report["total_pages"] == 2
    assert len(full_report["pages"]) == 2
    assert full_report["pages"][0]["page_status"] == "matched"
    for change in full_report["pages"][0]["changes"]:
        change.pop("review", None)
    assert full_report["pages"][0]["changes"] == page_reports[0]["changes"]
    print("  PDF pipeline test passed!")


def test_full_pipeline_image():
    """Test single image comparison -> save -> retrieve."""
    print("Testing single image pipeline...")
    
    # Create test images
    old_bytes = create_test_image_bytes("SHEET 1 REV A")
    new_bytes = create_test_image_bytes("SHEET 1 REV B")
    
    # Preprocess
    old_gray = preprocess_pipeline(old_bytes)["gray"]
    new_gray = preprocess_pipeline(new_bytes)["gray"]
    
    # Build page report
    page_report = {
        "page_number": 1,
        "page_status": "matched",
        "page_match_method": "single_image",
        "page_match_score": 100.0,
        "comparison_mode": "normal",
        "redesign_detected": False,
        "alignment": {"match_count": 100, "inlier_count": 95, "confidence": 0.95},
        "alignment_error": None,
        "render_dpi": None,
        "page_size_pts": {"width": 800.0, "height": 1000.0},
        "page_size_mismatch": False,
        "page_size_mismatch_details": None,
        "overall_similarity": 0.98,
        "overall_summary": "Test summary",
        "changes": [{"bbox": {"x": 10, "y": 10, "w": 100, "h": 50}, "category": "addition", "old_text": "", "new_text": "NEW NOTE"}],
    }
    page_report["page_matching"] = get_match_summary([type('Match', (), {
        'old_page_idx': 0, 'new_page_idx': 0, 'match_method': 'single_image',
        'match_score': 100, 'old_page_number': 1, 'new_page_number': 1
    })()])
    page_report["common_render_dpi"] = None
    
    # Save
    import uuid
    report_id = str(uuid.uuid4())
    content_hash = "test_hash_" + report_id  # dummy for test
    init_report(report_id, 1, page_report.get("page_matching"), 
                None, False, None, content_hash)
    save_report_page(report_id, page_report)
    complete_report(report_id, 1, page_report.get("page_matching"), 
                    None, False, None)
    print(f"  Saved report: {report_id}")
    
    # Retrieve flat changes (for QA)
    flat_changes = get_report(report_id)
    print(f"  Flat changes retrieved: {len(flat_changes)} changes")
    assert len(flat_changes) == 1
    
    # Retrieve full structured report
    full_report = get_full_report(report_id)
    print(f"  Full report retrieved: {full_report['report_id']}")
    assert full_report["total_pages"] == 1
    assert len(full_report["pages"]) == 1
    assert full_report["pages"][0]["page_status"] == "matched"
    print("  Single image pipeline test passed!")


if __name__ == "__main__":
    init_db()
    test_full_pipeline_pdf()
    test_full_pipeline_image()
    print("\nAll integration tests passed!")