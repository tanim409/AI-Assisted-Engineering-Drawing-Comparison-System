"""
Renders PDF pages to OpenCV BGR images in memory with consistent physical scale.
Uses PyMuPDF (fitz) — no poppler system dependency, unlike pdf2image.

DPI Consistency Strategy:
- Each PDF page has a physical size in points (1 pt = 1/72 inch).
- For a given comparison (old vs new), we compute a DPI per matched pair based on
  the larger physical width of the two pages.
- Both old and new pages are rendered at the SAME DPI so that 1 inch in the
  physical drawing = same pixel count in both rendered images.
- For pages up to MAX_WIDTH_FOR_BASE_DPI (default 24"), use BASE_DPI (default 200).
- For larger pages, scale DPI down proportionally to keep pixel dimensions reasonable.
- This ensures VISUAL_CHANGE_THRESHOLD and region sizes correspond to real
  physical dimensions, not arbitrary pixel scales.
"""
from typing import List, Tuple, Optional
import os
import logging

import cv2
import fitz  # PyMuPDF
import numpy as np

logger = logging.getLogger(__name__)

# DPI computation constants
# Base DPI for normal-sized pages
BASE_DPI = float(os.getenv("BASE_DPI", "200.0"))
# Maximum page width (inches) before we start reducing DPI
MAX_WIDTH_FOR_BASE_DPI = float(os.getenv("MAX_WIDTH_FOR_BASE_DPI", "24.0"))
# Maximum DPI cap — capped to prevent OOM on very small drawings
# (A0 at 400 DPI = ~9000x12000 px ≈ 324MB per image)
MAX_DPI = float(os.getenv("MAX_DPI", "200.0"))
# Minimum DPI floor
MIN_DPI = float(os.getenv("MIN_DPI", "72.0"))

# Threshold for page size mismatch warning (fractional difference)
PAGE_SIZE_MISMATCH_THRESHOLD = float(os.getenv("PAGE_SIZE_MISMATCH_THRESHOLD", "0.05"))

# Title block region as fractions of page dimensions (x, y, w, h)
# Default: bottom-right quadrant (most common for engineering drawings)
TITLE_BLOCK_X_PCT = float(os.getenv("TITLE_BLOCK_X_PCT", "0.65"))
TITLE_BLOCK_Y_PCT = float(os.getenv("TITLE_BLOCK_Y_PCT", "0.85"))
TITLE_BLOCK_W_PCT = float(os.getenv("TITLE_BLOCK_W_PCT", "0.35"))
TITLE_BLOCK_H_PCT = float(os.getenv("TITLE_BLOCK_H_PCT", "0.15"))

# Low DPI for title-block crops (cheap, small images)
TITLE_BLOCK_DPI = int(os.getenv("TITLE_BLOCK_DPI", "72"))


def is_pdf_filename(filename: str) -> bool:
    """Check if filename indicates a PDF."""
    return filename.lower().endswith(".pdf")


def is_pdf_bytes(data: bytes) -> bool:
    """Check if bytes start with PDF magic number."""
    return data[:5] == b"%PDF-"


def _get_page_physical_size(page: fitz.Page) -> Tuple[float, float]:
    """Return page physical size in inches (width, height)."""
    rect = page.rect
    width_in = rect.width / 72.0
    height_in = rect.height / 72.0
    return width_in, height_in



def _compute_pair_dpi(old_page_info: dict, new_page_info: dict) -> float:
    """
    Compute DPI for a matched pair based on the larger physical width of the two pages.
    Uses base DPI for pages up to MAX_WIDTH_FOR_BASE_DPI, scales down for larger pages.
    """
    max_width_in = max(old_page_info["width_in"], new_page_info["width_in"])
    
    if max_width_in <= MAX_WIDTH_FOR_BASE_DPI:
        # Normal-sized pages: use base DPI
        return BASE_DPI
    
    # Large pages: scale DPI down to keep pixel dimensions reasonable
    computed_dpi = BASE_DPI * (MAX_WIDTH_FOR_BASE_DPI / max_width_in)
    return max(MIN_DPI, min(MAX_DPI, computed_dpi))


def _compute_common_dpi(old_pages_info: List[dict], new_pages_info: List[dict]) -> float:
    """
    Compute a single DPI to use for ALL pages in this comparison (legacy function).
    Based on the largest physical width across both documents.
    """
    all_widths = [info["width_in"] for info in old_pages_info] + [info["width_in"] for info in new_pages_info]
    if not all_widths:
        return BASE_DPI  # fallback
    max_width_in = max(all_widths)
    
    if max_width_in <= MAX_WIDTH_FOR_BASE_DPI:
        return BASE_DPI
    
    computed_dpi = BASE_DPI * (MAX_WIDTH_FOR_BASE_DPI / max_width_in)
    return max(MIN_DPI, min(MAX_DPI, computed_dpi))


def _extract_page_metadata(doc: fitz.Document) -> List[dict]:
    """Extract physical metadata from all pages of an open PDF document."""
    pages_info = []
    for page_num, page in enumerate(doc):
        width_in, height_in = _get_page_physical_size(page)
        pages_info.append({
            "page_number": page_num + 1,
            "width_in": width_in,
            "height_in": height_in,
            "width_pts": page.rect.width,
            "height_pts": page.rect.height,
        })
    return pages_info


def crop_title_block(image: np.ndarray, title_block: Optional[dict] = None) -> np.ndarray:
    """Crop the title block region from a page image.

    pdf_pages.py owns the title-block region constants and this crop function
    (single source of truth) because it does all PDF rendering. Other modules
    (e.g. page_matcher.py) must import from here instead of redefining them.
    """
    h, w = image.shape[:2]
    title_block = title_block or {}
    x = int(w * title_block.get("x_pct", TITLE_BLOCK_X_PCT))
    y = int(h * title_block.get("y_pct", TITLE_BLOCK_Y_PCT))
    cw = int(w * title_block.get("w_pct", TITLE_BLOCK_W_PCT))
    ch = int(h * title_block.get("h_pct", TITLE_BLOCK_H_PCT))
    x = max(0, min(x, w - 1))
    y = max(0, min(y, h - 1))
    cw = max(1, min(cw, w - x))
    ch = max(1, min(ch, h - y))
    return image[y:y+ch, x:x+cw]


# Backward-compatible alias (internal callers used this name).
_crop_title_block_region = crop_title_block


def pdf_bytes_get_page_metadata(pdf_bytes: bytes) -> List[dict]:
    """
    Extract physical metadata for all pages without rendering full images.
    Returns list of dicts with page_number, width_in, height_in, width_pts, height_pts.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        return _extract_page_metadata(doc)
    finally:
        doc.close()


def pdf_bytes_render_title_block_crops(
    pdf_bytes: bytes, dpi: int = TITLE_BLOCK_DPI, title_block: Optional[dict] = None,
) -> List[dict]:
    """
    Render ONLY the title-block region of each page at low DPI for OCR-based matching.
    Returns list of dicts: {
        "page_number": int,
        "crop": np.ndarray (BGR, small),
        "width_in": float,
        "height_in": float,
        "width_pts": float,
        "height_pts": float,
    }
    Memory efficient: only small crops are held, not full pages.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        pages_info = _extract_page_metadata(doc)
        if not pages_info:
            raise ValueError("PDF has no pages")

        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        results = []
        for info in pages_info:
            page = doc[info["page_number"] - 1]
            # Render full page at low DPI first
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            full_img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 3:
                full_img = cv2.cvtColor(full_img, cv2.COLOR_RGB2BGR)
            # Crop title block
            crop = _crop_title_block_region(full_img, title_block)
            results.append({
                "page_number": info["page_number"],
                "crop": crop,
                "width_in": info["width_in"],
                "height_in": info["height_in"],
                "width_pts": info["width_pts"],
                "height_pts": info["height_pts"],
            })
        return results
    finally:
        doc.close()


def pdf_bytes_render_single_page(pdf_bytes: bytes, page_number: int, dpi: float) -> dict:
    """
    Render a single page at full resolution (given DPI).
    Returns dict with image, metadata, and render_dpi.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        if page_number < 1 or page_number > len(doc):
            raise ValueError(f"Page number {page_number} out of range (1-{len(doc)})")
        page = doc[page_number - 1]
        width_in, height_in = _get_page_physical_size(page)
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        return {
            "image": img,
            "page_number": page_number,
            "width_in": width_in,
            "height_in": height_in,
            "width_pts": page.rect.width,
            "height_pts": page.rect.height,
            "render_dpi": dpi,
        }
    finally:
        doc.close()


def _render_pages_at_dpi(doc: fitz.Document, pages_info: List[dict], dpi: float) -> List[dict]:
    """Render all pages at the given DPI from an already-open document."""
    results = []
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    for info in pages_info:
        page = doc[info["page_number"] - 1]
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        results.append({
            "image": img,
            "width_in": info["width_in"],
            "height_in": info["height_in"],
            "width_pts": info["width_pts"],
            "height_pts": info["height_pts"],
            "render_dpi": dpi,
            "page_number": info["page_number"],
        })
    return results


def pdf_bytes_to_images_with_meta(pdf_bytes: bytes, dpi: Optional[float] = None) -> List[dict]:
    """
    Render every page of a PDF (from bytes) to a BGR ndarray with metadata.
    Returns list of dicts: {
        "image": np.ndarray (BGR),
        "width_in": float,
        "height_in": float,
        "width_pts": float,
        "height_pts": float,
        "render_dpi": float,
        "page_number": int (1-based)
    }
    If dpi is provided, use it for all pages and render immediately.
    Otherwise, return metadata only (for DPI computation phase).
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        pages_info = _extract_page_metadata(doc)
        if not pages_info:
            raise ValueError("PDF has no pages")

        if dpi is not None:
            return _render_pages_at_dpi(doc, pages_info, dpi)

        # Return metadata only (no images) for DPI computation phase
        return [{
            "width_in": info["width_in"],
            "height_in": info["height_in"],
            "width_pts": info["width_pts"],
            "height_pts": info["height_pts"],
            "page_number": info["page_number"],
            "render_dpi": None,
            "image": None,
        } for info in pages_info]
    finally:
        doc.close()


def render_pdf_pair_at_common_dpi(old_pdf_bytes: bytes, new_pdf_bytes: bytes) -> Tuple[List[dict], List[dict], float, bool, dict]:
    """
    Render both PDFs at a common DPI computed from their physical page sizes.
    Single-pass per PDF: opens each PDF once, extracts metadata and renders all pages.
    Returns: (old_pages, new_pages, common_dpi, size_mismatch, mismatch_details)
    """
    # Phase 1: Open both PDFs once, get metadata and render all pages at computed DPI
    old_doc = fitz.open(stream=old_pdf_bytes, filetype="pdf")
    new_doc = fitz.open(stream=new_pdf_bytes, filetype="pdf")
    
    try:
        # Extract metadata from both
        old_pages_info = _extract_page_metadata(old_doc)
        new_pages_info = _extract_page_metadata(new_doc)
        
        if not old_pages_info or not new_pages_info:
            raise ValueError("One or both PDFs have no pages")
        
        # Compute common DPI
        common_dpi = _compute_common_dpi(old_pages_info, new_pages_info)
        logger.info(f"Computed common DPI: {common_dpi:.1f} (max width: {MAX_WIDTH_FOR_BASE_DPI}\")")
        
        # Render all pages at common DPI in single pass per PDF
        old_pages = _render_pages_at_dpi(old_doc, old_pages_info, common_dpi)
        new_pages = _render_pages_at_dpi(new_doc, new_pages_info, common_dpi)
        
        # Check for page size mismatches (compare first page of each)
        size_mismatch = False
        mismatch_details = {}
        if old_pages and new_pages:
            old_w, old_h = old_pages[0]["width_in"], old_pages[0]["height_in"]
            new_w, new_h = new_pages[0]["width_in"], new_pages[0]["height_in"]
            width_diff = abs(old_w - new_w) / max(old_w, new_w)
            height_diff = abs(old_h - new_h) / max(old_h, new_h)
            if width_diff > PAGE_SIZE_MISMATCH_THRESHOLD or height_diff > PAGE_SIZE_MISMATCH_THRESHOLD:
                size_mismatch = True
                mismatch_details = {
                    "old_page_size_in": {"width": round(old_w, 2), "height": round(old_h, 2)},
                    "new_page_size_in": {"width": round(new_w, 2), "height": round(new_h, 2)},
                    "width_diff_pct": round(width_diff * 100, 1),
                    "height_diff_pct": round(height_diff * 100, 1),
                }
                logger.warning(f"Page size mismatch detected: OLD={old_w:.1f}x{old_h:.1f}\" NEW={new_w:.1f}x{new_h:.1f}\" "
                              f"(diff: {width_diff*100:.1f}% x {height_diff*100:.1f}%)")
        
        return old_pages, new_pages, common_dpi, size_mismatch, mismatch_details
    finally:
        old_doc.close()
        new_doc.close()


# Backward compatibility: simple list-of-images API from bytes
def pdf_bytes_to_images(pdf_bytes: bytes, dpi: int = 200) -> List[np.ndarray]:
    """Legacy API - renders at fixed DPI, returns only images."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    images = []
    try:
        for page in doc:
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            images.append(img)
    finally:
        doc.close()
    if not images:
        raise ValueError("PDF has no pages")
    return images


def image_bytes_to_array(image_bytes: bytes) -> np.ndarray:
    """Decode image bytes (PNG/JPG/etc) to BGR numpy array."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes")
    return img
