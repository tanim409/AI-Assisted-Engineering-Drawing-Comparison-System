"""Report builder for the hybrid VLM pipeline.

Builds a per-page report dict from the merged Track A + Track B change list.
No alignment, no SSIM diff, no region bboxes.
"""
from datetime import timezone, datetime


def calculate_overall_similarity(changes: list) -> float:
    """Calculate overall drawing similarity dynamically based on change count and severity."""
    if not changes:
        return 1.0

    total_penalty = 0.0
    for c in changes:
        conf = c.get("confidence_tier") or (c.get("llm_classification", {}) or {}).get("confidence_tier")
        cat = c.get("category", "other")
        if conf == "high" or cat in ("dimensional", "structural", "drawing_structure"):
            total_penalty += 0.04
        elif conf == "medium" or cat in ("fixtures", "annotations"):
            total_penalty += 0.025
        else:
            total_penalty += 0.015

    return round(max(0.05, 1.0 - total_penalty), 3)


def build_report(
    changes: list,
    overall_summary: str = "",
    render_dpi: float = None,
    page_size_pts: tuple = None,
    pipeline_version: str = "hybrid_v1",
) -> dict:
    """Build the per-page report dict from the merged change list.

    Args:
        changes: List of change dicts from compare_drawing_pages().
        overall_summary: AI-generated summary string.
        render_dpi: DPI used to render this page (for informational purposes).
        page_size_pts: (width_pts, height_pts) tuple (informational only).
        pipeline_version: Pipeline identifier tag — 'hybrid_v1' for new pipeline.

    Returns:
        Dict suitable for save_report_page().
    """
    by_category: dict[str, int] = {}
    track_a_count = 0
    track_b_count = 0

    for c in changes:
        cat = c.get("category", "other")
        by_category[cat] = by_category.get(cat, 0) + 1
        if c.get("source") == "extraction":
            track_a_count += 1
        elif c.get("source") == "visual":
            track_b_count += 1

    report = {
        "changes": changes,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_similarity": calculate_overall_similarity(changes),
        "total_regions_detected": len(changes),  # kept for frontend compat
        "total_changes": len(changes),
        "changes_by_category": by_category,
        "overall_summary": overall_summary,
        "pipeline_version": pipeline_version,
        "track_a_count": track_a_count,
        "track_b_count": track_b_count,
    }

    if render_dpi is not None:
        report["render_dpi"] = round(render_dpi, 1)

    if page_size_pts is not None:
        report["page_size_pts"] = {
            "width": round(page_size_pts[0], 1),
            "height": round(page_size_pts[1], 1),
        }

    return report
