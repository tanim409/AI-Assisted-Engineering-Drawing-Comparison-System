"""Document-history summary PDF export.

Renders one PDF summarizing a drawing's entire revision chain for
audit/compliance review. Pure aggregation/rendering: it consumes only
already-stored data (revisions, comparisons, per-change classifications)
and never runs the comparison pipeline.

Choices (documented per the export task):
- Uncompared consecutive pairs are SKIPPED with a "not yet compared" note.
  Triggering comparisons inline would make this read-only export slow and
  would run the pipeline; the compare flow is now async/job-based, so the
  safer default is to note the gap instead.
- No page images: no annotated-diff-image export feature exists yet, so the
  report is text/table only.
- The category breakdown aggregates the stored per-change classifications
  (the same data build_report's changes_by_category is derived from). The
  per-comparison aggregate itself is not persisted in report_pages, so it is
  tallied here from the stored changes — no analysis is recomputed.

PDF generation uses PyMuPDF (fitz), already a project dependency.
"""
from datetime import datetime, timezone

import fitz

PAGE_W, PAGE_H = 595, 842  # A4 in points
MARGIN = 54
LINE_H = 16


def _safe(text) -> str:
    """fitz base-14 fonts are Latin-1; replace anything outside."""
    if text is None:
        return ""
    return str(text).encode("latin-1", "replace").decode("latin-1")


class _PdfWriter:
    """Sequential text writer that flows onto new pages when full."""

    def __init__(self, doc: fitz.Document):
        self.doc = doc
        self.page = doc.new_page(width=PAGE_W, height=PAGE_H)
        self.y = MARGIN

    def line(self, text: str, fontsize: float = 10, bold: bool = False, gap: float = 0) -> None:
        if self.y > PAGE_H - MARGIN:
            self.page = self.doc.new_page(width=PAGE_W, height=PAGE_H)
            self.y = MARGIN
        fontname = "hebo" if bold else "helv"
        self.page.insert_text((MARGIN, self.y), _safe(text), fontsize=fontsize, fontname=fontname)
        self.y += fontsize + 6 + gap

    def blank(self, amount: float = LINE_H) -> None:
        self.y += amount


def build_history_export_pdf(drawing: dict, total_revisions: int, sections: list[dict]) -> bytes:
    """Render a styled PDF summarizing a drawing's entire revision history chain.

    drawing: {drawing_id, name, created_at}
    sections: one per consecutive revision pair, in chronological order:
        {old_label, old_uploaded_at, new_label, new_uploaded_at,
         similarity, total_changes, by_category, note}
    """
    doc = fitz.open()
    pages = [doc.new_page(width=PAGE_W, height=PAGE_H)]
    page_idx = 0
    margin = 40
    content_w = PAGE_W - 2 * margin
    y = margin

    def current_page():
        return pages[page_idx]

    def check_space(needed_h: float):
        nonlocal page_idx, y
        if y + needed_h > PAGE_H - margin - 30:
            page = doc.new_page(width=PAGE_W, height=PAGE_H)
            pages.append(page)
            page_idx += 1
            y = margin

    # 1. Dark Header Accent Banner
    page = current_page()
    page.draw_rect(fitz.Rect(margin, y, margin + content_w, y + 4), color=None, fill=(0.06, 0.09, 0.16))  # Dark Navy #0F172A
    y += 12

    page.insert_text((margin, y + 14), "ENGINEERING DRAWING REVISION HISTORY", fontsize=16, fontname="hebo", color=(0.06, 0.09, 0.16))
    y += 26

    # 2. Document Meta Info Card Box
    meta_box_h = 72
    page.draw_rect(fitz.Rect(margin, y, margin + content_w, y + meta_box_h), color=(0.89, 0.91, 0.94), fill=(0.97, 0.98, 0.99))

    dwg_name = _safe(drawing.get("name") or drawing.get("drawing_id") or "Drawing")
    dwg_id_raw = str(drawing.get("drawing_id") or "n/a")
    dwg_id_disp = _safe(dwg_id_raw[:22] + "..." if len(dwg_id_raw) > 24 and "-" in dwg_id_raw else dwg_id_raw)
    created_at = _safe(str(drawing.get("created_at") or datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')))
    export_date = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    compared_count = sum(1 for s in sections if s.get("note") is None)
    uncompared_count = len(sections) - compared_count

    # Line 1: Drawing Name
    page.insert_text((margin + 12, y + 16), "Drawing Name:", fontsize=9, fontname="hebo", color=(0.2, 0.25, 0.33))
    page.insert_text((margin + 95, y + 16), dwg_name[:55], fontsize=9, fontname="helv", color=(0.06, 0.09, 0.16))

    # Line 2: Drawing ID & Created At
    page.insert_text((margin + 12, y + 34), "Drawing ID:", fontsize=9, fontname="hebo", color=(0.2, 0.25, 0.33))
    page.insert_text((margin + 95, y + 34), dwg_id_disp, fontsize=9, fontname="helv", color=(0.06, 0.09, 0.16))

    page.insert_text((margin + 310, y + 34), "Created At:", fontsize=9, fontname="hebo", color=(0.2, 0.25, 0.33))
    page.insert_text((margin + 375, y + 34), created_at[:22], fontsize=9, fontname="helv", color=(0.06, 0.09, 0.16))

    # Line 3: Revisions & Compared Summary
    page.insert_text((margin + 12, y + 52), "Total Revisions:", fontsize=9, fontname="hebo", color=(0.2, 0.25, 0.33))
    page.insert_text((margin + 95, y + 52), f"{total_revisions} revisions ({compared_count} compared, {uncompared_count} not yet compared)", fontsize=9, fontname="helv", color=(0.09, 0.44, 0.85))

    page.insert_text((margin + 310, y + 52), "Export Date:", fontsize=9, fontname="hebo", color=(0.2, 0.25, 0.33))
    page.insert_text((margin + 375, y + 52), export_date[:22], fontsize=9, fontname="helv", color=(0.06, 0.09, 0.16))

    y += meta_box_h + 18

    def _format_rev_label(seq_num, label, orig_filename) -> str:
        seq_str = f"Rev {seq_num}" if seq_num is not None else "Rev"
        name_detail = str(label).strip() if label and str(label).strip() else str(orig_filename or "").strip()
        if name_detail and name_detail != seq_str:
            return f"{seq_str} ({name_detail})"
        return seq_str

    # 3. Revision Pair Cards
    for idx, s in enumerate(sections, start=1):
        old_seq = s.get("old_sequence_number", idx)
        new_seq = s.get("new_sequence_number", idx + 1)
        old_lbl = _safe(_format_rev_label(old_seq, s.get("old_label"), s.get("old_original_filename")))
        new_lbl = _safe(_format_rev_label(new_seq, s.get("new_label"), s.get("new_original_filename")))

        if s.get("note") is not None:
            # Uncompared Section Box
            box_h = 44
            check_space(box_h + 10)
            p = current_page()
            p.draw_rect(fitz.Rect(margin, y, margin + content_w, y + box_h), color=(0.85, 0.88, 0.92), fill=(0.96, 0.97, 0.98))
            p.insert_text((margin + 12, y + 16), f"SECTION {idx}: {old_lbl}  ->  {new_lbl}", fontsize=10, fontname="hebo", color=(0.3, 0.35, 0.45))
            p.insert_text((margin + 12, y + 32), s["note"], fontsize=9, fontname="helv", color=(0.5, 0.55, 0.65))
            y += box_h + 12
            continue

        # Compared Pair Section Box
        by_category = s.get("by_category") or {}
        cat_items = sorted(by_category.items()) if by_category else []
        cat_map = {
            "dimension_change": "Dimension",
            "note_or_annotation_change": "Note Change",
            "note_change": "Note Change",
            "addition": "Addition",
            "removal": "Removal",
            "symbol_or_code_change": "Symbol",
            "symbol_change": "Symbol",
        }

        cat_str_parts = []
        for cat, cnt in cat_items:
            lbl = cat_map.get(cat, cat.replace("_", " ").title())
            cat_str_parts.append(f"{lbl}: {cnt}")
        cat_summary = "  |  ".join(cat_str_parts) if cat_str_parts else "(no changes recorded)"

        box_h = 70
        check_space(box_h + 12)
        p = current_page()

        # Section Card Background with Left Border Highlight
        p.draw_rect(fitz.Rect(margin, y, margin + content_w, y + box_h), color=(0.85, 0.88, 0.92), fill=(0.98, 0.99, 1.0))
        p.draw_rect(fitz.Rect(margin, y, margin + 4, y + box_h), color=None, fill=(0.09, 0.44, 0.85))

        # Title row
        p.insert_text((margin + 14, y + 16), f"SECTION {idx}: {old_lbl}  ->  {new_lbl}", fontsize=11, fontname="hebo", color=(0.06, 0.09, 0.16))

        # Metrics row: Similarity (green) & Total Changes (bold dark)
        sim_val = s.get("similarity")
        sim_str = f"{sim_val:.1f}%" if sim_val is not None else "n/a"
        tot_changes = s.get("total_changes", 0)

        p.insert_text((margin + 14, y + 36), "Overall Similarity:", fontsize=9, fontname="hebo", color=(0.2, 0.25, 0.33))
        p.insert_text((margin + 105, y + 36), sim_str, fontsize=10, fontname="hebo", color=(0.05, 0.6, 0.4))

        p.insert_text((margin + 200, y + 36), "Total Changes:", fontsize=9, fontname="hebo", color=(0.2, 0.25, 0.33))
        p.insert_text((margin + 275, y + 36), str(tot_changes), fontsize=10, fontname="hebo", color=(0.06, 0.09, 0.16))

        # Category Breakdown row
        p.insert_text((margin + 14, y + 54), "Category Breakdown:", fontsize=8.5, fontname="hebo", color=(0.3, 0.35, 0.45))
        p.insert_text((margin + 115, y + 54), cat_summary[:85], fontsize=8.5, fontname="helv", color=(0.1, 0.15, 0.25))

        y += box_h + 12

    # Footer Page Numbers
    total_pages_count = len(pages)
    for p_i, p in enumerate(pages, start=1):
        p.draw_line(fitz.Point(margin, PAGE_H - 30), fitz.Point(PAGE_W - margin, PAGE_H - 30), color=(0.85, 0.88, 0.92), width=0.5)
        p.insert_text((margin, PAGE_H - 16), "Engineering Drawing Comparison System • Revision History Summary", fontsize=8, fontname="helv", color=(0.5, 0.55, 0.65))
        p.insert_text((PAGE_W - margin - 60, PAGE_H - 16), f"Page {p_i} of {total_pages_count}", fontsize=8, fontname="hebo", color=(0.3, 0.35, 0.45))

    return doc.tobytes()


def _wrap_text(text: str, max_w: float, fontsize: float = 9, fontname: str = "helv") -> list[str]:
    font = fitz.Font(fontname)
    words = text.split()
    if not words:
        return []
    lines = []
    current = []
    for w in words:
        test_str = " ".join(current + [w])
        if font.text_length(_safe(test_str), fontsize) <= max_w:
            current.append(w)
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))
    return lines


def build_summary_export_pdf(report: dict) -> bytes:
    """Render a clean, text-only PDF report summarizing a single comparison.
    
    Contains:
    - Header (Drawing name, comparison date, old → new revision labels)
    - Executive summary paragraph
    - Statistics block (total changes, category breakdown, overall similarity %, alignment confidence)
    - Change details log table (ID, Category, Review Status, Description & Revision Details)
    - Footer on all pages (Page X of Y, timestamp)
    """
    doc = fitz.open()
    pages = [doc.new_page(width=PAGE_W, height=PAGE_H)]
    page_idx = 0
    margin = 40
    content_w = PAGE_W - 2 * margin
    y = margin

    def current_page():
        return pages[page_idx]

    def check_space(needed_h: float):
        nonlocal page_idx, y
        if y + needed_h > PAGE_H - margin - 30:
            page = doc.new_page(width=PAGE_W, height=PAGE_H)
            pages.append(page)
            page_idx += 1
            y = margin

    # 1. Header Accent Banner
    page = current_page()
    page.draw_rect(fitz.Rect(margin, y, margin + content_w, y + 4), color=None, fill=(0.06, 0.09, 0.16))  # Dark Navy #0F172A
    y += 12

    page.insert_text((margin, y + 14), "ENGINEERING DRAWING COMPARISON REPORT", fontsize=16, fontname="hebo", color=(0.06, 0.09, 0.16))
    y += 26

    # Meta Info Card Box — Vertical stack layout to prevent any overlapping
    meta_box_h = 84
    page.draw_rect(fitz.Rect(margin, y, margin + content_w, y + meta_box_h), color=(0.89, 0.91, 0.94), fill=(0.97, 0.98, 0.99))

    drawing_name = _safe(
        report.get("drawing_name") or report.get("projectName") or report.get("drawingNumber") or "Engineering Drawing"
    )
    created_at = _safe(str(report.get("created_at") or report.get("timestamp") or report.get("generated_at") or datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')))
    
    old_rev_info = report.get("oldDrawing") if isinstance(report.get("oldDrawing"), dict) else {}
    new_rev_info = report.get("newDrawing") if isinstance(report.get("newDrawing"), dict) else {}
    
    old_rev = _safe(str(report.get("old_revision_label") or old_rev_info.get("revisionLabel") or report.get("old_revision_id") or "Old Revision"))
    new_rev = _safe(str(report.get("new_revision_label") or new_rev_info.get("revisionLabel") or report.get("new_revision_id") or "New Revision"))
    
    raw_rep_id = str(report.get("report_id") or report.get("id") or "n/a")
    if len(raw_rep_id) > 20 and "-" in raw_rep_id:
        disp_rep_id = _safe(raw_rep_id[:8] + "...")
    else:
        disp_rep_id = _safe(raw_rep_id)

    # Line 1 (y + 16): Drawing Name
    page.insert_text((margin + 12, y + 16), "Drawing:", fontsize=9, fontname="hebo", color=(0.2, 0.25, 0.33))
    page.insert_text((margin + 75, y + 16), drawing_name[:65], fontsize=9, fontname="helv", color=(0.06, 0.09, 0.16))

    # Line 2 (y + 32): Revisions Transition
    page.insert_text((margin + 12, y + 32), "Revisions:", fontsize=9, fontname="hebo", color=(0.2, 0.25, 0.33))
    page.insert_text((margin + 75, y + 32), f"{old_rev}  ->  {new_rev}", fontsize=9, fontname="hebo", color=(0.09, 0.44, 0.85))

    # Line 3 (y + 48): Report ID
    page.insert_text((margin + 12, y + 48), "Report ID:", fontsize=9, fontname="hebo", color=(0.2, 0.25, 0.33))
    page.insert_text((margin + 75, y + 48), disp_rep_id, fontsize=9, fontname="helv", color=(0.06, 0.09, 0.16))

    # Line 4 (y + 64): Date
    page.insert_text((margin + 12, y + 64), "Date:", fontsize=9, fontname="hebo", color=(0.2, 0.25, 0.33))
    page.insert_text((margin + 75, y + 64), created_at[:30], fontsize=9, fontname="helv", color=(0.06, 0.09, 0.16))

    y += meta_box_h + 16

    # 2. Executive Summary
    check_space(50)
    page = current_page()
    page.insert_text((margin, y + 10), "EXECUTIVE SUMMARY", fontsize=11, fontname="hebo", color=(0.2, 0.25, 0.33))
    y += 16

    summary_text = _safe(report.get("overall_summary") or report.get("overallSummary") or "Automated visual comparison completed across detected drawing regions.")
    wrapped_summary = _wrap_text(summary_text, content_w - 24, fontsize=9, fontname="helv")
    if not wrapped_summary:
        wrapped_summary = ["No executive summary text available."]
    box_h = max(32, len(wrapped_summary) * 14 + 14)

    page.draw_rect(fitz.Rect(margin, y, margin + content_w, y + box_h), color=(0.8, 0.85, 0.92), fill=(0.95, 0.96, 0.98))
    sum_y = y + 14
    for line in wrapped_summary:
        page.insert_text((margin + 12, sum_y), line, fontsize=9, fontname="helv", color=(0.1, 0.15, 0.25))
        sum_y += 14
    y += box_h + 16

    # 3. Statistics Block
    check_space(60)
    page = current_page()
    page.insert_text((margin, y + 10), "COMPARISON STATISTICS", fontsize=11, fontname="hebo", color=(0.2, 0.25, 0.33))
    y += 16

    all_changes = []
    page_sims = []
    align_confs = []
    for p in report.get("pages", []):
        all_changes.extend(p.get("changes", []))
        if p.get("overall_similarity") is not None:
            page_sims.append(float(p["overall_similarity"]))
        if p.get("alignment", {}).get("confidence") is not None:
            align_confs.append(float(p["alignment"]["confidence"]))

    if not all_changes and report.get("changes"):
        all_changes = report.get("changes", [])

    total_changes = report.get("total_changes") or report.get("totalChanges") or len(all_changes)
    
    overall_sim = report.get("overall_similarity") or report.get("overallSimilarity")
    if overall_sim is None and page_sims:
        overall_sim = sum(page_sims) / len(page_sims)

    if overall_sim is not None:
        sim_val = float(overall_sim)
        sim_str = f"{sim_val * 100:.1f}%" if sim_val <= 1.0 else f"{sim_val:.1f}%"
    else:
        sim_str = "n/a"

    # Category counts
    cat_counts = report.get("categoryCounts") or report.get("changes_by_category") or {}
    if not cat_counts and all_changes:
        cat_counts = {}
        for c in all_changes:
            cat = c.get("classification", {}).get("category") if isinstance(c.get("classification"), dict) else c.get("category")
            cat = str(cat or "note_or_annotation_change")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

    stat_box_h = 42
    page.draw_rect(fitz.Rect(margin, y, margin + content_w, y + stat_box_h), color=(0.89, 0.91, 0.94), fill=(0.98, 0.98, 0.99))

    page.insert_text((margin + 15, y + 16), "Total Changes:", fontsize=9, fontname="hebo", color=(0.2, 0.25, 0.33))
    page.insert_text((margin + 85, y + 16), str(total_changes), fontsize=10, fontname="hebo", color=(0.06, 0.09, 0.16))

    page.insert_text((margin + 150, y + 16), "Overall Similarity:", fontsize=9, fontname="hebo", color=(0.2, 0.25, 0.33))
    page.insert_text((margin + 245, y + 16), sim_str, fontsize=10, fontname="hebo", color=(0.05, 0.6, 0.4))

    # Compute genuine alignment confidence level (High / Medium / Low)
    avg_conf = sum(align_confs) / len(align_confs) if align_confs else 0.9
    raw_conf_str = str(report.get("alignmentConfidence") or "").lower()
    if "low" in raw_conf_str or avg_conf < 0.5:
        align_conf = "Low"
    elif "med" in raw_conf_str or avg_conf < 0.8:
        align_conf = "Medium"
    else:
        align_conf = "High"

    page.insert_text((margin + 330, y + 16), "Alignment:", fontsize=9, fontname="hebo", color=(0.2, 0.25, 0.33))
    page.insert_text((margin + 390, y + 16), align_conf, fontsize=10, fontname="hebo", color=(0.09, 0.44, 0.85))

    dim_c = cat_counts.get("dimension_change", 0)
    note_c = cat_counts.get("note_change", 0) + cat_counts.get("note_or_annotation_change", 0)
    add_c = cat_counts.get("addition", 0)
    rem_c = cat_counts.get("removal", 0)
    sym_c = cat_counts.get("symbol_change", 0) + cat_counts.get("symbol_or_code_change", 0)

    breakdown_str = f"Breakdown:  Dimension: {dim_c}  |  Note: {note_c}  |  Added: {add_c}  |  Removed: {rem_c}  |  Symbol: {sym_c}"
    page.insert_text((margin + 15, y + 32), breakdown_str, fontsize=8.5, fontname="helv", color=(0.3, 0.35, 0.45))
    y += stat_box_h + 20

    # 4. Change Detail Table
    check_space(50)
    page = current_page()
    page.insert_text((margin, y + 10), "CHANGE DETAILS LOG", fontsize=11, fontname="hebo", color=(0.2, 0.25, 0.33))
    y += 18

    # Columns: ID (55), Category (90), Status (75), Description & Details (295)
    col_x = [margin, margin + 55, margin + 145, margin + 220, margin + content_w]

    def draw_table_header():
        nonlocal y
        p = current_page()
        p.draw_rect(fitz.Rect(margin, y, margin + content_w, y + 20), color=None, fill=(0.12, 0.16, 0.24))
        p.insert_text((col_x[0] + 6, y + 14), "ID", fontsize=8.5, fontname="hebo", color=(1, 1, 1))
        p.insert_text((col_x[1] + 6, y + 14), "Category", fontsize=8.5, fontname="hebo", color=(1, 1, 1))
        p.insert_text((col_x[2] + 6, y + 14), "Status", fontsize=8.5, fontname="hebo", color=(1, 1, 1))
        p.insert_text((col_x[3] + 6, y + 14), "Description & Revision Details", fontsize=8.5, fontname="hebo", color=(1, 1, 1))
        y += 20

    draw_table_header()

    if not all_changes:
        check_space(24)
        p = current_page()
        p.draw_rect(fitz.Rect(margin, y, margin + content_w, y + 24), color=(0.9, 0.9, 0.9), fill=(1, 1, 1))
        p.insert_text((margin + 12, y + 16), "No change regions detected in this comparison.", fontsize=9, fontname="helv", color=(0.4, 0.4, 0.4))
        y += 24
    else:
        for idx, c in enumerate(all_changes):
            cid = _safe(c.get("id") or f"CHG-{idx+1:03d}")
            raw_cat = c.get("classification", {}).get("category") if isinstance(c.get("classification"), dict) else c.get("category")
            raw_cat = str(raw_cat or "note_or_annotation_change")

            cat_map = {
                "dimension_change": "Dimension",
                "note_or_annotation_change": "Note Change",
                "note_change": "Note Change",
                "addition": "Addition",
                "removal": "Removal",
                "symbol_or_code_change": "Symbol",
                "symbol_change": "Symbol",
                "no_change": "No Change",
            }
            cat_lbl = cat_map.get(raw_cat, raw_cat.replace("_", " ").title())

            review_obj = c.get("review") if isinstance(c.get("review"), dict) else {}
            st = review_obj.get("status") or c.get("status") or "unreviewed"
            if st in ("confirmed", "approved"):
                st_lbl = "Confirmed"
                st_color = (0.05, 0.6, 0.3)
            elif st in ("false_positive", "flagged"):
                st_lbl = "False Positive"
                st_color = (0.85, 0.2, 0.2)
            else:
                st_lbl = "Pending"
                st_color = (0.85, 0.55, 0.05)

            llm_obj = c.get("classification") if isinstance(c.get("classification"), dict) else {}
            desc = _safe(llm_obj.get("description") or c.get("description") or c.get("title") or "Change detected.")
            old_v = _safe(str(c.get("old_text") or c.get("oldValue") or ""))
            new_v = _safe(str(c.get("new_text") or c.get("newValue") or ""))

            wrapped_desc = _wrap_text(desc, 280, fontsize=8.5, fontname="helv")
            if not wrapped_desc:
                wrapped_desc = ["Change region detected."]

            wrapped_val = []
            if old_v or new_v:
                val_line = f"Old: '{old_v}'  ->  New: '{new_v}'"
                wrapped_val = _wrap_text(val_line, 280, fontsize=8, fontname="hebo")

            row_content_h = (len(wrapped_desc) * 12) + (len(wrapped_val) * 12) + 12
            row_h = max(24, row_content_h)

            if y + row_h > PAGE_H - margin - 30:
                page = doc.new_page(width=PAGE_W, height=PAGE_H)
                pages.append(page)
                page_idx += 1
                y = margin
                draw_table_header()

            p = current_page()
            bg = (1, 1, 1) if idx % 2 == 0 else (0.97, 0.98, 0.99)
            p.draw_rect(fitz.Rect(margin, y, margin + content_w, y + row_h), color=(0.88, 0.9, 0.93), fill=bg)

            p.insert_text((col_x[0] + 6, y + 14), cid, fontsize=8.5, fontname="hebo", color=(0.1, 0.15, 0.25))
            p.insert_text((col_x[1] + 6, y + 14), cat_lbl, fontsize=8.5, fontname="helv", color=(0.2, 0.25, 0.35))
            p.insert_text((col_x[2] + 6, y + 14), st_lbl, fontsize=8.5, fontname="hebo", color=st_color)

            desc_y = y + 14
            for line in wrapped_desc:
                p.insert_text((col_x[3] + 6, desc_y), line, fontsize=8.5, fontname="helv", color=(0.06, 0.09, 0.16))
                desc_y += 12

            for line in wrapped_val:
                p.insert_text((col_x[3] + 6, desc_y), line, fontsize=8, fontname="hebo", color=(0.09, 0.44, 0.85))
                desc_y += 12

            y += row_h

    # 5. Footer Page Numbers on all pages
    total_pages_count = len(pages)
    for p_i, p in enumerate(pages, start=1):
        p.draw_line(fitz.Point(margin, PAGE_H - 30), fitz.Point(PAGE_W - margin, PAGE_H - 30), color=(0.85, 0.88, 0.92), width=0.5)
        p.insert_text((margin, PAGE_H - 16), "Engineering Drawing Comparison System • Text Summary Export", fontsize=8, fontname="helv", color=(0.5, 0.55, 0.65))
        p.insert_text((PAGE_W - margin - 60, PAGE_H - 16), f"Page {p_i} of {total_pages_count}", fontsize=8, fontname="hebo", color=(0.3, 0.35, 0.45))

    return doc.tobytes()

