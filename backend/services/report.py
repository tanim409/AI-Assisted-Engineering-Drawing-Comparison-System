from datetime import timezone, datetime


def build_report(region_data, alignment_info, similarity_score,
                 comparison_mode="normal", redesign_detected=False,
                 redesign_metrics=None, alignment_error=None, overall_summary="",
                 render_dpi=None, page_size_pts=None, page_size_mismatch=None, page_mismatch_details=None):
    changes = []
    verified_count = 0
    disagreement_count = 0
    for r in region_data:
        # Prefer the LLM decision; rule-based classification is only a fallback.
        final_category = (
            r.get('llm_classification', {}).get('category')
            or r.get('classification', {}).get('category')
        )
        r.setdefault('classification', {})['category'] = final_category
        verification = r.get('verification', {})
        if verification.get('verified') is False:
            disagreement_count += 1
        else:
            verified_count += 1
        if final_category and final_category != 'no_change':
            changes.append(r)

    by_category = {}
    for r in changes:
        cat = r['classification']['category']
        by_category[cat] = by_category.get(cat, 0) + 1

    llm_response = [r.get("llm_classification") for r in region_data]

    report = {
        "changes": changes,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        "alignment": {
            "match_count": alignment_info["match_count"],
            "inlier_count": alignment_info["inlier_count"],
            "confidence": round(alignment_info["confidence"], 3),
        },
        "overall_similarity": round(similarity_score, 4),
        "total_regions_detected": len(region_data),
        "total_changes": len(changes),
        "changes_by_category": by_category,
        "llm_response": llm_response,
        "comparison_mode": comparison_mode,
        "redesign_detected": redesign_detected,
        "redesign_metrics": redesign_metrics or {},
        "verification_summary": {
            "ocr_llm_agreement_count": verified_count,
            "ocr_llm_disagreement_count": disagreement_count,
        },
        "overall_summary": overall_summary,
    }
    if alignment_error:
        report["alignment_error"] = alignment_error
    if render_dpi is not None:
        report["render_dpi"] = round(render_dpi, 1)
    if page_size_pts is not None:
        report["page_size_pts"] = {
            "width": round(page_size_pts[0], 1),
            "height": round(page_size_pts[1], 1),
        }
    if page_size_mismatch is not None:
        report["page_size_mismatch"] = page_size_mismatch
        if page_mismatch_details:
            report["page_size_mismatch_details"] = page_mismatch_details
    return report
