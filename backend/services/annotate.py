"""Annotated diff image export — text-overlay sidebar for hybrid VLM pipeline.

No bounding boxes (the new pipeline produces no pixel coordinates).
Renders the full page image with a numbered legend panel alongside it.

Track A changes (source='extraction', confidence_tier='high') shown in teal.
Track B changes (source='visual', confidence_tier='needs_review') shown in amber with ⚠ prefix.
"""
"""Annotated diff image export with direct bounding box overlays and legend sidebar.

Supports the Diff-Driven ROI pipeline:
- Draws colored, numbered bounding boxes directly onto the drawing page.
- Renders a clean engineering legend sidebar matching change IDs and categories.
"""
from typing import List, Dict, Any, Optional

import cv2
import numpy as np
import fitz  # PyMuPDF


# ── Color Palette (BGR for OpenCV) ────────────────────────────────────────────
COLOR_MAP = {
    "dimensional_change": (0, 165, 255),    # Orange / Amber
    "geometry_change": (255, 100, 0),       # Blue
    "symbol_change": (180, 105, 255),       # Pink / Magenta
    "text_annotation": (0, 200, 200),       # Yellow
    "title_block": (200, 200, 0),           # Cyan
    "addition": (80, 200, 80),              # Green
    "deletion": (60, 60, 230),              # Red
    "other": (180, 180, 180),               # Gray
}

DEFAULT_COLOR = (0, 165, 255)
HEADER_BG = (35, 39, 46)
TEXT_WHITE = (255, 255, 255)
TEXT_MUTED = (170, 175, 185)
PANEL_BG = (22, 25, 30)
DIVIDER_COLOR = (50, 55, 65)

CATEGORY_SHORT = {
    "dimensional_change": "DIM",
    "geometry_change": "GEO",
    "symbol_change": "SYM",
    "text_annotation": "TXT",
    "title_block": "TITLE",
    "addition": "ADD",
    "deletion": "DEL",
    "other": "REV",
}

FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE_SMALL = 0.42
FONT_SCALE_NORMAL = 0.52
FONT_THICKNESS = 1


# ── Text Wrapping Helper ──────────────────────────────────────────────────────

def _wrap_text(text: str, max_chars: int = 44) -> list[str]:
    """Wrap text to lines of at most max_chars characters."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = f"{current} {word}".strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


# ── Drawing Canvas Overlay ────────────────────────────────────────────────────

def _draw_bounding_boxes(image: np.ndarray, changes: List[Dict[str, Any]]) -> np.ndarray:
    """Draw numbered revision boxes on the image using normalized bboxes."""
    annotated = image.copy()
    h, w = annotated.shape[:2]

    for idx, change in enumerate(changes):
        bbox = change.get("bbox") or change.get("norm_bbox")
        if not bbox:
            continue

        bx = int(bbox.get("x", 0.0) * w)
        by = int(bbox.get("y", 0.0) * h)
        bw = int(bbox.get("w", 0.0) * w)
        bh = int(bbox.get("h", 0.0) * h)

        cat = change.get("category", "other")
        color = COLOR_MAP.get(cat, DEFAULT_COLOR)

        # Draw revision boundary box
        cv2.rectangle(annotated, (bx, by), (bx + bw, by + bh), color, 2)

        # Draw corner tag badge: [1], [2], etc.
        tag = f"#{idx + 1}"
        (tw, th), _ = cv2.getTextSize(tag, FONT, 0.45, 1)
        badge_x1 = bx
        badge_y1 = max(0, by - th - 6)
        badge_x2 = bx + tw + 8
        badge_y2 = by

        cv2.rectangle(annotated, (badge_x1, badge_y1), (badge_x2, badge_y2), color, -1)
        cv2.putText(
            annotated,
            tag,
            (badge_x1 + 4, badge_y2 - 3),
            FONT,
            0.45,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )

    return annotated


# ── Legend Line Builder ───────────────────────────────────────────────────────

def _build_legend_entries(changes: List[Dict[str, Any]]) -> list[dict]:
    """Format changes into structured items for sidebar rendering."""
    entries = []
    for idx, change in enumerate(changes):
        cat = change.get("category", "other")
        short_cat = CATEGORY_SHORT.get(cat, cat[:4].upper())
        color = COLOR_MAP.get(cat, DEFAULT_COLOR)

        tag = f"#{idx + 1}"
        change_id = change.get("id", f"CHG-{idx + 1:03d}")
        header = f"{tag} [{short_cat}] {change_id}"

        detail_lines = []
        loc = change.get("location") or change.get("zone")
        if loc:
            detail_lines.extend(_wrap_text(f"Loc: {loc}", 44))

        old_val = change.get("baseline_value") or change.get("old_value")
        new_val = change.get("current_value") or change.get("new_value")
        if old_val and new_val:
            detail_lines.extend(_wrap_text(f"Old: {old_val}", 44))
            detail_lines.extend(_wrap_text(f"New: {new_val}", 44))
        elif old_val:
            detail_lines.extend(_wrap_text(f"Removed: {old_val}", 44))
        elif new_val:
            detail_lines.extend(_wrap_text(f"Added: {new_val}", 44))

        desc = change.get("description", "")
        if desc:
            detail_lines.extend(_wrap_text(desc, 44))

        entries.append({
            "header": header,
            "detail_lines": detail_lines,
            "color": color,
        })
    return entries


# ── Sidebar Renderer ──────────────────────────────────────────────────────────

SIDEBAR_WIDTH_PX = 420
LINE_HEIGHT = 18
PADDING = 12


def _render_sidebar(height: int, entries: list[dict]) -> np.ndarray:
    """Render the dark sidebar legend panel."""
    sidebar = np.full((height, SIDEBAR_WIDTH_PX, 3), PANEL_BG, dtype=np.uint8)

    # Header title bar
    cv2.rectangle(sidebar, (0, 0), (SIDEBAR_WIDTH_PX, 40), HEADER_BG, -1)
    cv2.putText(
        sidebar,
        "ENGINEERING CHANGE LEGEND",
        (PADDING, 26),
        FONT,
        FONT_SCALE_NORMAL,
        TEXT_WHITE,
        FONT_THICKNESS,
        cv2.LINE_AA,
    )

    y = 52
    for entry in entries:
        color = entry["color"]
        header = entry["header"]

        # Left accent stripe
        cv2.rectangle(sidebar, (0, y - 4), (4, y + LINE_HEIGHT - 2), color, -1)

        # Delta header
        cv2.putText(
            sidebar,
            header[:50],
            (PADDING, y + 12),
            FONT,
            FONT_SCALE_SMALL,
            color,
            FONT_THICKNESS,
            cv2.LINE_AA,
        )
        y += LINE_HEIGHT + 3

        # Delta details
        for dline in entry["detail_lines"]:
            if y + LINE_HEIGHT >= height - PADDING:
                cv2.putText(
                    sidebar,
                    "... (truncated)",
                    (PADDING, y + 12),
                    FONT,
                    FONT_SCALE_SMALL,
                    DIVIDER_COLOR,
                    FONT_THICKNESS,
                    cv2.LINE_AA,
                )
                y += LINE_HEIGHT
                break
            cv2.putText(
                sidebar,
                dline[:54],
                (PADDING, y + 12),
                FONT,
                FONT_SCALE_SMALL,
                TEXT_MUTED,
                FONT_THICKNESS,
                cv2.LINE_AA,
            )
            y += LINE_HEIGHT

        # Section divider line
        if y < height - PADDING:
            cv2.line(
                sidebar,
                (PADDING, y + 4),
                (SIDEBAR_WIDTH_PX - PADDING, y + 4),
                DIVIDER_COLOR,
                1,
            )
        y += 10

        if y >= height - PADDING:
            break

    return sidebar


# ── Summary Top Bar ───────────────────────────────────────────────────────────

def _render_summary_bar(width: int, changes: List[Dict[str, Any]]) -> np.ndarray:
    """Render the top banner displaying total deltas and primary discipline."""
    bar_h = 36
    bar = np.full((bar_h, width, 3), HEADER_BG, dtype=np.uint8)

    total = len(changes)
    disciplines = list(dict.fromkeys(c.get("discipline") for c in changes if c.get("discipline")))
    disc_text = disciplines[0] if disciplines else "General Engineering"

    title_str = f"CAD Comparison Studio  |  Discipline: {disc_text}  |  Total Deltas Identified: {total}"
    cv2.putText(bar, title_str, (PADDING, 23), FONT, FONT_SCALE_NORMAL, TEXT_WHITE, FONT_THICKNESS, cv2.LINE_AA)
    return bar


# ── Public Page Renderer ──────────────────────────────────────────────────────

def render_annotated_page(
    changes: List[Dict[str, Any]],
    new_page_source: Dict[str, Any],
) -> np.ndarray:
    """Render drawing sheet with overlays and attached sidebar panel."""
    if "pdf_bytes" in new_page_source:
        img = _render_new_page_for_annotation(
            new_page_source["pdf_bytes"],
            new_page_source["page_number"],
            new_page_source["dpi"],
        )
    elif "image_bytes" in new_page_source:
        img = _render_image_bytes_for_annotation(new_page_source["image_bytes"])
    else:
        raise ValueError("new_page_source must contain 'pdf_bytes' or 'image_bytes'")

    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    # 1. Draw revision bounding boxes directly on the CAD drawing
    annotated_sheet = _draw_bounding_boxes(img, changes)
    h, _ = annotated_sheet.shape[:2]

    # 2. Render sidebar legend matching the boxes
    legend_entries = _build_legend_entries(changes)
    sidebar = _render_sidebar(h, legend_entries)

    # 3. Stack horizontally [Annotated CAD Sheet | Sidebar Legend]
    composite = np.hstack([annotated_sheet, sidebar])

    # 4. Attach summary banner across the top
    summary_bar = _render_summary_bar(composite.shape[1], changes)
    return np.vstack([summary_bar, composite])


# ── File Decoders & Exporters ─────────────────────────────────────────────────

def _render_new_page_for_annotation(
    pdf_bytes: bytes,
    page_number: int,
    dpi: float,
) -> np.ndarray:
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
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode image bytes")
    return img


def export_annotated_png(annotated_image: np.ndarray) -> bytes:
    """Encode composite image as PNG bytes."""
    ok, buf = cv2.imencode(".png", annotated_image)
    if not ok:
        raise RuntimeError("Failed to encode annotated PNG buffer")
    return buf.tobytes()


def export_annotated_pdf(
    annotated_images: List[np.ndarray],
    dpi: float = 200.0,
) -> bytes:
    """Combine composite images into a multi-page PDF."""
    doc = fitz.open()
    try:
        for img in annotated_images:
            h, w = img.shape[:2]
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            _, png_buf = cv2.imencode(".png", img_rgb)
            page = doc.new_page(width=w, height=h)
            page.insert_image(page.rect, stream=png_buf.tobytes())
        return doc.tobytes()
    finally:
        doc.close()


def build_page_source_from_report(
    report: Dict[str, Any],
    page_idx: int,
) -> Dict[str, Any]:
    """Retrieve raw PDF/image bytes for the given page index from report payload."""
    page = report["pages"][page_idx]
    dpi = page.get("render_dpi") or report.get("common_render_dpi", 200.0)
    page_num = page.get("page_number") or (page_idx + 1)
    return {
        "pdf_bytes": page.get("new_pdf_bytes"),
        "image_bytes": page.get("image_bytes"),
        "page_number": page_num,
        "dpi": dpi,
    }