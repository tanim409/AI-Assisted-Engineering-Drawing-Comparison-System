"""
Unit tests for DPI consistency and multi-page alignment.
Run with: python -m pytest tests/ -v
"""
import os
import sys
import tempfile
import numpy as np
import cv2
import fitz  # PyMuPDF

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.pdf_pages import (
    _get_page_physical_size,
    _compute_common_dpi,
    render_pdf_pair_at_common_dpi,
    BASE_DPI,
    MAX_WIDTH_FOR_BASE_DPI,
    PAGE_SIZE_MISMATCH_THRESHOLD,
)
from services.page_matcher import (
    PageSignature,
    PageMatch,
    _normalize_text,
    _crop_title_block,
    match_pages,
    get_match_summary,
    MIN_TITLE_MATCH_SCORE,
)


def create_test_pdf(path: str, page_size_inches: tuple, num_pages: int = 1, title_text: str = ""):
    """Create a test PDF with specified page size and optional title block text."""
    doc = fitz.open()
    width_pts = page_size_inches[0] * 72
    height_pts = page_size_inches[1] * 72

    for i in range(num_pages):
        page = doc.new_page(width=width_pts, height=height_pts)
        if title_text:
            # Add text in title block region (bottom-right)
            x = width_pts * 0.7
            y = height_pts * 0.9
            page.insert_text((x, y), title_text, fontsize=12)
    doc.save(path)
    doc.close()


def test_dpi_consistency_same_page_size():
    """Two PDFs with same physical page size should render at same DPI."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_pdf = os.path.join(tmpdir, "old.pdf")
        new_pdf = os.path.join(tmpdir, "new.pdf")

        # Both A1 size (23.39 x 33.11 inches)
        create_test_pdf(old_pdf, (23.39, 33.11), num_pages=1, title_text="DRAWING TITLE REV A")
        create_test_pdf(new_pdf, (23.39, 33.11), num_pages=1, title_text="DRAWING TITLE REV B")

        with open(old_pdf, "rb") as f:
            old_bytes = f.read()
        with open(new_pdf, "rb") as f:
            new_bytes = f.read()

        old_pages, new_pages, common_dpi, size_mismatch, _ = render_pdf_pair_at_common_dpi(old_bytes, new_bytes)

        assert len(old_pages) == 1
        assert len(new_pages) == 1
        assert old_pages[0]["render_dpi"] == new_pages[0]["render_dpi"] == common_dpi
        assert not size_mismatch
        print(f"  Same size test: common_dpi={common_dpi:.1f}, size_mismatch={size_mismatch}")


def test_dpi_consistency_different_page_size():
    """Two PDFs with different physical page sizes should render at same DPI (based on larger)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_pdf = os.path.join(tmpdir, "old.pdf")
        new_pdf = os.path.join(tmpdir, "new.pdf")

        # Old: A3 (11.69 x 16.54), New: A1 (23.39 x 33.11)
        create_test_pdf(old_pdf, (11.69, 16.54), num_pages=1, title_text="DRAWING TITLE REV A")
        create_test_pdf(new_pdf, (23.39, 33.11), num_pages=1, title_text="DRAWING TITLE REV B")

        with open(old_pdf, "rb") as f:
            old_bytes = f.read()
        with open(new_pdf, "rb") as f:
            new_bytes = f.read()

        old_pages, new_pages, common_dpi, size_mismatch, mismatch_details = render_pdf_pair_at_common_dpi(old_bytes, new_bytes)

        assert len(old_pages) == 1
        assert len(new_pages) == 1
        # Both should use the SAME DPI
        assert old_pages[0]["render_dpi"] == new_pages[0]["render_dpi"] == common_dpi
        # Size mismatch should be detected (A3 vs A1 is > 5% diff)
        assert size_mismatch is True
        assert mismatch_details is not None
        assert "old_page_size_in" in mismatch_details
        assert "new_page_size_in" in mismatch_details
        print(f"  Different size test: common_dpi={common_dpi:.1f}, size_mismatch={size_mismatch}")
        print(f"  Mismatch details: {mismatch_details}")


def test_dpi_consistency_multi_page():
    """Multi-page PDFs should all render at the same common DPI."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_pdf = os.path.join(tmpdir, "old.pdf")
        new_pdf = os.path.join(tmpdir, "new.pdf")

        create_test_pdf(old_pdf, (22, 34), num_pages=3, title_text="SHEET 1 REV A")
        create_test_pdf(new_pdf, (22, 34), num_pages=3, title_text="SHEET 1 REV B")

        with open(old_pdf, "rb") as f:
            old_bytes = f.read()
        with open(new_pdf, "rb") as f:
            new_bytes = f.read()

        old_pages, new_pages, common_dpi, size_mismatch, _ = render_pdf_pair_at_common_dpi(old_bytes, new_bytes)

        assert len(old_pages) == 3
        assert len(new_pages) == 3
        # All pages should have the same render_dpi
        for p in old_pages + new_pages:
            assert p["render_dpi"] == common_dpi
        assert not size_mismatch
        print(f"  Multi-page test: common_dpi={common_dpi:.1f}, all pages consistent")


def test_page_matching_same_order():
    """3 old pages, 3 new pages, same order -> all match with title_block method."""
    # Create mock page images with title block text (grayscale for OCR)
    old_pages = []
    new_pages = []
    old_page_numbers = [1, 2, 3]
    new_page_numbers = [1, 2, 3]

    for i in range(3):
        # Create a simple page image with title block text
        old_img = np.zeros((1000, 800), dtype=np.uint8)
        new_img = np.zeros((1000, 800), dtype=np.uint8)
        # Add text in title block region (bottom-right)
        cv2.putText(old_img, f"SHEET {i+1} REV A", (550, 950), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 255, 2)
        cv2.putText(new_img, f"SHEET {i+1} REV B", (550, 950), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 255, 2)
        old_pages.append(old_img)
        new_pages.append(new_img)

    matches = match_pages(old_pages, new_pages, old_page_numbers, new_page_numbers)
    summary = get_match_summary(matches)

    assert summary["total_pages_matched"] == 3
    assert summary["pages_added"] == 0
    assert summary["pages_removed"] == 0
    assert summary["title_block_matches"] == 3
    assert summary["positional_fallback_matches"] == 0
    print(f"  Same order test: {summary}")


def test_page_matching_page_removed():
    """Old has 3 pages, new has 2 (page 2 removed) -> page 2 reports as removed, 1&3 matched."""
    old_pages = []
    new_pages = []
    old_page_numbers = [1, 2, 3]
    new_page_numbers = [1, 3]  # Page 2 removed

    for i, num in enumerate([1, 2, 3]):
        old_img = np.zeros((1000, 800), dtype=np.uint8)
        cv2.putText(old_img, f"SHEET {num} REV A", (550, 950), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 255, 2)
        old_pages.append(old_img)

    for i, num in enumerate([1, 3]):
        new_img = np.zeros((1000, 800), dtype=np.uint8)
        cv2.putText(new_img, f"SHEET {num} REV B", (550, 950), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 255, 2)
        new_pages.append(new_img)

    matches = match_pages(old_pages, new_pages, old_page_numbers, new_page_numbers)
    summary = get_match_summary(matches)

    assert summary["total_pages_matched"] == 2
    assert summary["pages_added"] == 0
    assert summary["pages_removed"] == 1
    assert summary["title_block_matches"] == 2
    # Check that removed page is page 2
    removed = [m for m in matches if m.old_page_idx is not None and m.new_page_idx is None]
    assert len(removed) == 1
    assert removed[0].old_page_number == 2
    print(f"  Page removed test: {summary}")


def test_page_matching_reordered():
    """Old order A,B,C -> new order C,A,B -> all 3 correctly matched via title block."""
    old_pages = []
    new_pages = []
    # Use sheet numbers as page numbers to track content
    old_page_numbers = [1, 2, 3]
    new_page_numbers = [3, 1, 2]  # New PDF has pages in order: Sheet 3, Sheet 1, Sheet 2

    # Old: Sheet 1, Sheet 2, Sheet 3
    for sheet_num in [1, 2, 3]:
        old_img = np.zeros((1000, 800), dtype=np.uint8)
        cv2.putText(old_img, f"SHEET {sheet_num} REV A", (550, 950), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 255, 2)
        old_pages.append(old_img)

    # New: Sheet 3, Sheet 1, Sheet 2 (reordered)
    for sheet_num in [3, 1, 2]:
        new_img = np.zeros((1000, 800), dtype=np.uint8)
        cv2.putText(new_img, f"SHEET {sheet_num} REV B", (550, 950), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 255, 2)
        new_pages.append(new_img)

    matches = match_pages(old_pages, new_pages, old_page_numbers, new_page_numbers)
    summary = get_match_summary(matches)

    assert summary["total_pages_matched"] == 3
    assert summary["pages_added"] == 0
    assert summary["pages_removed"] == 0
    assert summary["title_block_matches"] == 3
    # Verify correct pairing: content-based matching should pair by sheet number
    matched = [m for m in matches if m.old_page_idx is not None and m.new_page_idx is not None]
    assert len(matched) == 3
    # Check each old page matched to correct new page by sheet number (content)
    for m in matched:
        old_sheet = m.old_page_number  # 1, 2, 3
        new_sheet = m.new_page_number  # Should match old_sheet (3, 1, 2)
        assert old_sheet == new_sheet, f"Expected old {old_sheet} to match new {old_sheet}, got new {new_sheet}"
    print(f"  Reordered test: {summary}")


def test_page_matching_empty_title_fallback():
    """Pages with empty title block should fall back to positional matching."""
    old_pages = []
    new_pages = []
    old_page_numbers = [1, 2]
    new_page_numbers = [1, 2]

    # Page 1: valid title block
    old_img1 = np.zeros((1000, 800), dtype=np.uint8)
    new_img1 = np.zeros((1000, 800), dtype=np.uint8)
    cv2.putText(old_img1, "SHEET 1 REV A", (550, 950), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 255, 2)
    cv2.putText(new_img1, "SHEET 1 REV B", (550, 950), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 255, 2)

    # Page 2: NO title block text (blank)
    old_img2 = np.zeros((1000, 800), dtype=np.uint8)
    new_img2 = np.zeros((1000, 800), dtype=np.uint8)
    # No text added

    old_pages = [old_img1, old_img2]
    new_pages = [new_img1, new_img2]

    matches = match_pages(old_pages, new_pages, old_page_numbers, new_page_numbers)
    summary = get_match_summary(matches)

    assert summary["total_pages_matched"] == 2
    assert summary["pages_added"] == 0
    assert summary["pages_removed"] == 0
    print(f"  Empty title fallback test: {summary}")


def test_normalize_text():
    """Test text normalization for fuzzy matching."""
    assert _normalize_text("  Hello   World!  ") == "hello world"
    assert _normalize_text("DRAWING-NO. 123") == "drawing no 123"
    assert _normalize_text("") == ""
    assert _normalize_text("REV\tA\nB") == "rev a b"
    print("  normalize_text tests passed")


def test_crop_title_block():
    """Test title block cropping."""
    img = np.zeros((1000, 800, 3), dtype=np.uint8)
    crop = _crop_title_block(img)
    # Default region: x=0.65*800=520, y=0.85*1000=850, w=0.35*800=280, h=0.15*1000=150
    assert crop.shape == (150, 280, 3)
    print("  crop_title_block test passed")


if __name__ == "__main__":
    print("Running DPI consistency tests...")
    test_dpi_consistency_same_page_size()
    test_dpi_consistency_different_page_size()
    test_dpi_consistency_multi_page()

    print("\nRunning page matching tests...")
    test_normalize_text()
    test_crop_title_block()
    test_page_matching_same_order()
    test_page_matching_page_removed()
    test_page_matching_reordered()
    test_page_matching_empty_title_fallback()

    print("\nAll tests passed!")