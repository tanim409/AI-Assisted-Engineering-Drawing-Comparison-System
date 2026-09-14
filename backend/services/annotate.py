"""Annotated diff image export — render change boxes onto rendered pages.

Pure rendering step on top of existing comparison results. No recomputation,
no LLM/OCR calls. Uses stored bbox/category data only.
"""
from typing import List, Dict, Any, Optional
import io

import cv2
import numpy as np
import fitz  # PyMuPDF

# Category -> BGR color (OpenCV uses BGR)
CATEGORY_COLORS = {
    "addition": (0, 200, 0),           # green
    "removal": (0, 0, 255),            # red
    "dimension_change": (0, 128, 255), # orange
    "note_or_annotation_change": (255, 0, 0),  # blue
    "symbol_or_code_change": (128, 0, 128),    # purple
    "needs_human_review": (0, 255, 255),       # yellow
    "no_change": (128, 128, 128),      # gray (shouldn't appear in exports)
}

# Default drawing parameters
BOX_THICKNESS = 3
LABEL_FONT = cv2.FONT_HERSHEY_SIMPLEX
LABEL_FONT_SCALE = 0.6
LABEL_THICKNESS = 2
LABEL_PADDING = 4


def _category_short_name(category: str) -> str:
    """Short label for the category (used in numbered tags)."""
    short = {
        "addition": "ADD",
        "removal": "REM",
        "dimension_change": "DIM",
        "note_or_annotation_change": "NOTE",
        "symbol_or_code_change": "SYM",
        "needs_human_review": "REVIEW",
    }
    return short.get(category, category[:4].upper())


def _draw_boxes_on_image(
    image: np.ndarray,
    changes: List[Dict[str, Any]],
    page_width: int,
    page_height: int,
) -> np.ndarray:
    """Draw bounding boxes and numbered labels on a copy of the image.
    Coordinates in changes are assumed to be in pixel space matching the image.
    """
    annotated = image.copy()
    color_map = CATEGORY_COLORS

    for idx, change in enumerate(changes):
        bbox = change.get("bbox", {})
        if not bbox:
            continue
        x = int(bbox.get("x", 0))
        y = int(bbox.get("y", 0))
        w = int(bbox.get("w", 0))
        h = int(bbox.get("h", 0))
        if w <= 0 or h <= 0:
            continue

        category = change.get("classification", {}).get("category", "no_change")
        color = color_map.get(category, (128, 128, 128))
        short = _category_short_name(category)
        label = f"{idx + 1}.{short}"

        # Rectangle
        cv2.rectangle(annotated, (x, y), (x + w, y + h), color, BOX_THICKNESS)

        # Label background + text (top-left, just outside the box)
        (tw, th), _ = cv2.getTextSize(label, LABEL_FONT, LABEL_FONT_SCALE, LABEL_THICKNESS)
        lx, ly = x, y - th - LABEL_PADDING
        if ly < 0:
            ly = y + h + LABEL_PADDING  # below if no room above
        cv2.rectangle(
            annotated,
            (lx - LABEL_PADDING, ly - LABEL_PADDING),
            (lx + tw + LABEL_PADDING, ly + th + LABEL_PADDING),
            color,
            -1,
        )
        cv2.putText(
            annotated, label, (lx, ly + th),
            LABEL_FONT, LABEL_FONT_SCALE, (255, 255, 255), LABEL_THICKNESS, cv2.LINE_AA
        )

    return annotated


def _render_new_page_for_annotation(
    pdf_bytes: bytes,
    page_number: int,
    dpi: float,
) -> np.ndarray:
    """Render a single page from PDF bytes at given DPI as BGR np.ndarray."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        page = doc[page_number - 1]
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        return img
    finally:
        doc.close()


def _render_image_bytes_for_annotation(image_bytes: bytes) -> np.ndarray:
    """Decode raw image bytes (PNG/JPG) as BGR np.ndarray."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes")
    return img


def render_annotated_page(
    changes: List[Dict[str, Any]],
    new_page_source: Dict[str, Any],
) -> np.ndarray:
    """Render an annotated page for a single page's comparison result.

    new_page_source: dict with keys:
        - "pdf_bytes": bytes (for PDF)
        - "page_number": int
        - "dpi": float
        OR
        - "image_bytes": bytes (for single image)
    """
    if "pdf_bytes" in new_page_source:
        img = _render_new_page_for_annotation(
            new_page_source["pdf_bytes"],
            new_page_source["page_number"],
            new_page_source["dpi"],
        )
    else:
        img = _render_image_bytes_for_annotation(new_page_source["image_bytes"])

    h, w = img.shape[:2]
    return _draw_boxes_on_image(img, changes, w, h)


def export_annotated_png(annotated_image: np.ndarray) -> bytes:
    """Encode annotated BGR image as PNG bytes."""
    ok, buf = cv2.imencode(".png", annotated_image)
    if not ok:
        raise RuntimeError("Failed to encode PNG")
    return buf.tobytes()


def export_annotated_pdf(
    annotated_images: List[np.ndarray],
    dpi: float = 200.0,
) -> bytes:
    """Combine annotated BGR images into a single PDF (one image per page)."""
    doc = fitz.open()
    try:
        for img in annotated_images:
            h, w = img.shape[:2]
            # Convert BGR -> RGB for PyMuPDF
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            _, png_buf = cv2.imencode(".png", img_rgb)
            page = doc.new_page(width=w, height=h)
            page.insert_image(page.rect, stream=png_buf.tobytes())
        pdf_bytes = doc.tobytes()
        return pdf_bytes
    finally:
        doc.close()


def build_page_source_from_report(
    report: Dict[str, Any],
    page_idx: int,
) -> Dict[str, Any]:
    """Extract the info needed to re-render the NEW page for a given page index
    from a full report dict (as returned by get_full_report / stored in DB)."""
    page = report["pages"][page_idx]
    # The report stores render_dpi per page (or common_render_dpi for single image)
    dpi = page.get("render_dpi") or report.get("common_render_dpi", 200.0)
    page_num = page.get("page_number") or (page_idx + 1)
    return {
        "pdf_bytes": page.get("new_pdf_bytes"),  # will be populated by caller if available
        "page_number": page_num,
        "dpi": dpi,
    }