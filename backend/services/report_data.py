import json
import hashlib
import time
from typing import Optional, List, Dict, Any

from model.db import connect
from model.report_db import resolve_report_id
from services.change_reviews import attach_reviews_to_pages
from psycopg.errors import UniqueViolation


def _compute_content_hash(old_bytes: bytes, new_bytes: bytes) -> str:
    """Compute a deterministic hash of the input file pair."""
    combined = old_bytes + b"|" + new_bytes
    return hashlib.sha256(combined).hexdigest()


def reserve_report(old_bytes: bytes, new_bytes: bytes, owner_user_id: int) -> Optional[tuple]:
    """
    Reserve the report slot for a given input pair for a specific user.
    """
    content_hash = _compute_content_hash(old_bytes, new_bytes)

    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT report_id, status FROM reports WHERE owner_user_id = %s AND content_hash = %s",
                (owner_user_id, content_hash)
            )
            existing = cursor.fetchone()

            if existing:
                if existing["status"] == "pending":
                    return None

                if existing["status"] == "complete":
                    cursor.execute(
                        "SELECT 1 FROM report_pages WHERE report_id = %s AND page_status = 'failed' LIMIT 1",
                        (existing["report_id"],),
                    )
                    has_failed = cursor.fetchone()
                    if not has_failed:
                        return (existing["report_id"], "complete")

                cursor.execute(
                    "UPDATE reports SET status = 'pending' WHERE report_id = %s AND status = %s",
                    (existing["report_id"], existing["status"]),
                )
                if cursor.rowcount == 0:
                    return None
                return (existing["report_id"], "resume")

            report_id = f"pending_{content_hash[:16]}_{int(time.time()*1000)}"
            try:
                cursor.execute("""
                    INSERT INTO reports (report_id, owner_user_id, content_hash, status, created_at)
                    VALUES (%s, %s, %s, 'pending', NOW())
                """, (report_id, owner_user_id, content_hash))
                return (report_id, "reserved")
            except UniqueViolation:
                return None


def wait_for_report(report_id: str, timeout: float = 30.0, poll_interval: float = 0.2, owner_user_id: Optional[int] = None) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        with connect() as conn:
            with conn.cursor() as cursor:
                if owner_user_id is not None:
                    cursor.execute(
                        "SELECT status FROM reports WHERE report_id = %s AND owner_user_id = %s",
                        (report_id, owner_user_id)
                    )
                else:
                    cursor.execute("SELECT status FROM reports WHERE report_id = %s", (report_id,))
                row = cursor.fetchone()
                if row is None:
                    return True
                if row["status"] == "complete":
                    return True
                if row["status"] == "failed":
                    return False
        time.sleep(poll_interval)
    return False


def init_report(report_id: str, total_pages: int, page_matching: dict, common_render_dpi: float,
                page_size_mismatch: bool, page_size_mismatch_details: dict, content_hash: str,
                owner_user_id: int = 1) -> None:
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT report_id FROM reports WHERE owner_user_id = %s AND content_hash = %s",
                (owner_user_id, content_hash)
            )
            existing = cursor.fetchone()
            if existing:
                canonical_id = existing["report_id"]
                if canonical_id != report_id:
                    cursor.execute(
                        "INSERT INTO report_aliases (alias_id, report_id) VALUES (%s, %s) ON CONFLICT (alias_id) DO UPDATE SET report_id = EXCLUDED.report_id",
                        (report_id, canonical_id)
                    )
                report_id = canonical_id

            cursor.execute("""
                INSERT INTO reports (
                    report_id, owner_user_id, content_hash, status, total_pages, page_matching, common_render_dpi,
                    page_size_mismatch, page_size_mismatch_details, created_at
                ) VALUES (%s, %s, %s, 'pending', %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (report_id) DO UPDATE SET
                    total_pages = EXCLUDED.total_pages,
                    page_matching = EXCLUDED.page_matching,
                    common_render_dpi = EXCLUDED.common_render_dpi,
                    page_size_mismatch = EXCLUDED.page_size_mismatch,
                    page_size_mismatch_details = EXCLUDED.page_size_mismatch_details,
                    status = 'pending'
            """, (
                report_id,
                owner_user_id,
                content_hash,
                total_pages,
                json.dumps(page_matching) if page_matching else None,
                common_render_dpi,
                1 if page_size_mismatch else 0,
                json.dumps(page_size_mismatch_details) if page_size_mismatch_details else None,
            ))
            return report_id


def save_report_page(report_id: str, page: Dict[str, Any], owner_user_id: Optional[int] = None) -> None:
    report_id = resolve_report_id(report_id, owner_user_id=owner_user_id)
    page_number = page.get("page_number")
    matched_new_page_number = page.get("matched_new_page_number")
    page_status = page.get("page_status", "matched")
    page_match_method = page.get("page_match_method")
    page_match_score = page.get("page_match_score")
    comparison_mode = page.get("comparison_mode")
    redesign_detected = page.get("redesign_detected", False)

    alignment = page.get("alignment", {})
    alignment_match_count = alignment.get("match_count")
    alignment_inlier_count = alignment.get("inlier_count")
    alignment_confidence = alignment.get("confidence")
    alignment_error = page.get("alignment_error")

    render_dpi = page.get("render_dpi")
    page_size_pts = page.get("page_size_pts", {})
    page_size_pts_width = page_size_pts.get("width") if page_size_pts else None
    page_size_pts_height = page_size_pts.get("height") if page_size_pts else None
    page_size_mismatch_page = page.get("page_size_mismatch", False)
    page_size_mismatch_details_page = page.get("page_size_mismatch_details")

    overall_similarity = page.get("overall_similarity")
    overall_summary = page.get("overall_summary")
    changes = page.get("changes", [])
    annotated_source_png = page.get("annotated_source_png")

    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO report_pages (
                    report_id, page_number, matched_new_page_number, page_status,
                    page_match_method, page_match_score, comparison_mode,
                    redesign_detected, alignment_match_count, alignment_inlier_count,
                    alignment_confidence, alignment_error, render_dpi,
                    page_size_pts_width, page_size_pts_height,
                    page_size_mismatch, page_size_mismatch_details,
                    overall_similarity, overall_summary, changes, annotated_source_png, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                report_id,
                page_number,
                matched_new_page_number,
                page_status,
                page_match_method,
                page_match_score,
                comparison_mode,
                1 if redesign_detected else 0,
                alignment_match_count,
                alignment_inlier_count,
                alignment_confidence,
                alignment_error,
                render_dpi,
                page_size_pts_width,
                page_size_pts_height,
                1 if page_size_mismatch_page else 0,
                json.dumps(page_size_mismatch_details_page) if page_size_mismatch_details_page else None,
                overall_similarity,
                overall_summary,
                json.dumps(changes),
                annotated_source_png,
            ))


def complete_report(report_id: str, total_pages: int, page_matching: dict, 
                    common_render_dpi: float, page_size_mismatch: bool,
                    page_size_mismatch_details: dict, owner_user_id: Optional[int] = None) -> None:
    report_id = resolve_report_id(report_id, owner_user_id=owner_user_id)
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE reports SET
                    status = 'complete',
                    total_pages = %s,
                    page_matching = %s,
                    common_render_dpi = %s,
                    page_size_mismatch = %s,
                    page_size_mismatch_details = %s
                WHERE report_id = %s
            """, (
                total_pages,
                json.dumps(page_matching) if page_matching else None,
                common_render_dpi,
                1 if page_size_mismatch else 0,
                json.dumps(page_size_mismatch_details) if page_size_mismatch_details else None,
                report_id,
            ))


def fail_report(report_id: str, error: str = "", owner_user_id: Optional[int] = None) -> None:
    report_id = resolve_report_id(report_id, owner_user_id=owner_user_id)
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE reports SET status = 'failed' WHERE report_id = %s", (report_id,))


def get_page_status_map(report_id: str, owner_user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    report_id = resolve_report_id(report_id, owner_user_id=owner_user_id)
    with connect() as conn:
        with conn.cursor() as cursor:
            if owner_user_id is not None:
                cursor.execute("""
                    SELECT rp.page_number, rp.matched_new_page_number, rp.page_status
                    FROM report_pages rp
                    JOIN reports r ON r.report_id = rp.report_id
                    WHERE rp.report_id = %s AND r.owner_user_id = %s
                    ORDER BY rp.id
                """, (report_id, owner_user_id))
            else:
                cursor.execute(
                    "SELECT page_number, matched_new_page_number, page_status FROM report_pages WHERE report_id = %s ORDER BY id",
                    (report_id,),
                )
            rows = cursor.fetchall()
    return [dict(r) for r in rows]


def rename_report(old_report_id: str, new_report_id: str) -> None:
    if old_report_id == new_report_id:
        return
    with connect() as conn:
        with conn.cursor() as cursor:
            # The foreign keys use ON UPDATE CASCADE, so updating the parent
            # also updates report_pages, change_reviews, and aliases safely.
            cursor.execute("UPDATE reports SET report_id = %s WHERE report_id = %s", (new_report_id, old_report_id))


def copy_report_rows(source_id: str, target_id: str) -> None:
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO report_aliases (alias_id, report_id) VALUES (%s, %s) ON CONFLICT (alias_id) DO UPDATE SET report_id = EXCLUDED.report_id",
                (target_id, source_id)
            )


def delete_failed_page_result(report_id: str, page_number: Optional[int] = None,
                              matched_new_page_number: Optional[int] = None) -> None:
    with connect() as conn:
        with conn.cursor() as cursor:
            if page_number is not None:
                cursor.execute(
                    "DELETE FROM report_pages WHERE report_id = %s AND page_status = 'failed' AND page_number = %s",
                    (report_id, page_number),
                )
            else:
                cursor.execute(
                    "DELETE FROM report_pages WHERE report_id = %s AND page_status = 'failed' AND page_number IS NULL AND matched_new_page_number = %s",
                    (report_id, matched_new_page_number),
                )


_PAGE_ORDER_SQL = (
    "ORDER BY CASE WHEN page_number IS NOT NULL THEN page_number "
    "ELSE 100000 + COALESCE(matched_new_page_number, 0) END, id"
)


def get_report(report_id: str, owner_user_id: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
    report_id = resolve_report_id(report_id, owner_user_id=owner_user_id)
    with connect() as conn:
        with conn.cursor() as cursor:
            if owner_user_id is not None:
                cursor.execute("""
                    SELECT rp.changes FROM report_pages rp
                    JOIN reports r ON r.report_id = rp.report_id
                    WHERE rp.report_id = %s AND r.owner_user_id = %s
                    ORDER BY rp.id
                """, (report_id, owner_user_id))
            else:
                cursor.execute("SELECT changes FROM report_pages WHERE report_id = %s ORDER BY id", (report_id,))
            rows = cursor.fetchall()
    if not rows:
        return None
    all_changes = []
    for row in rows:
        changes = json.loads(row["changes"])
        all_changes.extend(changes)
    return all_changes


def get_full_report(report_id: str, owner_user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    report_id = resolve_report_id(report_id, owner_user_id=owner_user_id)
    with connect() as conn:
        with conn.cursor() as cursor:
            if owner_user_id is not None:
                cursor.execute(
                    "SELECT * FROM reports WHERE report_id = %s AND (owner_user_id IS NULL OR owner_user_id = %s) AND status = 'complete'",
                    (report_id, owner_user_id),
                )
            else:
                cursor.execute("SELECT * FROM reports WHERE report_id = %s AND status = 'complete'", (report_id,))
            report_row = cursor.fetchone()
            if not report_row:
                return None

            cursor.execute(
                f"SELECT * FROM report_pages WHERE report_id = %s {_PAGE_ORDER_SQL}",
                (report_id,),
            )
            page_rows = cursor.fetchall()

    report = {
        "report_id": report_row["report_id"],
        "owner_user_id": report_row["owner_user_id"],
        "content_hash": report_row["content_hash"],
        "total_pages": report_row["total_pages"],
        "page_matching": json.loads(report_row["page_matching"]) if report_row["page_matching"] else None,
        "common_render_dpi": report_row["common_render_dpi"],
        "page_size_mismatch": bool(report_row["page_size_mismatch"]),
        "page_size_mismatch_details": json.loads(report_row["page_size_mismatch_details"]) if report_row["page_size_mismatch_details"] else None,
        "created_at": str(report_row["created_at"]),
        "pages": []
    }

    for page_row in page_rows:
        page_size_pts = None
        if page_row["page_size_pts_width"] is not None and page_row["page_size_pts_height"] is not None:
            page_size_pts = {
                "width": page_row["page_size_pts_width"],
                "height": page_row["page_size_pts_height"]
            }

        page = {
            "page_number": page_row["page_number"],
            "matched_new_page_number": page_row["matched_new_page_number"],
            "page_status": page_row["page_status"],
            "page_match_method": page_row["page_match_method"],
            "page_match_score": page_row["page_match_score"],
            "comparison_mode": page_row["comparison_mode"],
            "redesign_detected": bool(page_row["redesign_detected"]),
            "alignment": {
                "match_count": page_row["alignment_match_count"],
                "inlier_count": page_row["alignment_inlier_count"],
                "confidence": page_row["alignment_confidence"],
            } if page_row["alignment_match_count"] is not None else None,
            "alignment_error": page_row["alignment_error"],
            "render_dpi": page_row["render_dpi"],
            "page_size_pts": page_size_pts,
            "page_size_mismatch": bool(page_row["page_size_mismatch"]),
            "page_size_mismatch_details": json.loads(page_row["page_size_mismatch_details"]) if page_row["page_size_mismatch_details"] else None,
            "overall_similarity": page_row["overall_similarity"],
            "overall_summary": page_row["overall_summary"],
            "changes": json.loads(page_row["changes"]),
            "total_changes": len(json.loads(page_row["changes"])),
        }
        report["pages"].append(page)
    attach_reviews_to_pages(report_id, report["pages"], owner_user_id=owner_user_id)
    report["overall_summary"] = " ".join([p.get("overall_summary", "") for p in report["pages"] if p.get("overall_summary")]).strip()

    try:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT c.drawing_id, c.old_revision_id, c.new_revision_id,
                           d.name AS drawing_name,
                           r_old.revision_label AS old_revision_label,
                           r_old.sequence_number AS old_sequence_number,
                           r_new.revision_label AS new_revision_label,
                           r_new.sequence_number AS new_sequence_number
                    FROM comparisons c
                    LEFT JOIN drawings d ON d.drawing_id = c.drawing_id
                    LEFT JOIN revisions r_old ON r_old.revision_id = c.old_revision_id
                    LEFT JOIN revisions r_new ON r_new.revision_id = c.new_revision_id
                    WHERE c.comparison_id = %s
                """, (report_id,))
                comp_row = cursor.fetchone()
                if comp_row:
                    report["drawing_id"] = comp_row["drawing_id"]
                    report["drawing_name"] = comp_row["drawing_name"]
                    report["old_revision_id"] = comp_row["old_revision_id"]
                    report["new_revision_id"] = comp_row["new_revision_id"]
                    report["old_revision_label"] = comp_row["old_revision_label"] or f"Rev {comp_row['old_sequence_number']}" if comp_row.get("old_sequence_number") else "Old Revision"
                    report["new_revision_label"] = comp_row["new_revision_label"] or f"Rev {comp_row['new_sequence_number']}" if comp_row.get("new_sequence_number") else "New Revision"
    except Exception as e:
        print(f"[get_full_report] Could not attach comparison metadata: {e}")

    return report



def list_user_reports(owner_user_id: int) -> List[Dict[str, Any]]:
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT r.report_id, r.created_at, r.total_pages,
                       COUNT(rp.id) AS page_count,
                       COALESCE(AVG(rp.overall_similarity), 0) AS avg_similarity
                FROM reports r
                LEFT JOIN report_pages rp ON rp.report_id = r.report_id
                WHERE r.owner_user_id = %s AND r.status = 'complete'
                GROUP BY r.report_id, r.created_at, r.total_pages
                ORDER BY r.created_at DESC
            """, (owner_user_id,))
            rows = cursor.fetchall()
            
    reports = []
    for r in rows:
        report_id = r["report_id"]
        full = get_full_report(report_id, owner_user_id=owner_user_id)
        if not full:
            continue
        total_changes = sum(len(p.get("changes", [])) for p in full.get("pages", []))
        first_page_similarity = full["pages"][0].get("overall_similarity") if full.get("pages") else None
        overall_sim = first_page_similarity if first_page_similarity is not None else float(r["avg_similarity"])
        reports.append({
            "report_id": report_id,
            "created_at": str(r["created_at"]),
            "total_pages": r["total_pages"],
            "total_changes": total_changes,
            "overall_similarity": overall_sim,
        })
    return reports


def delete_report(report_id: str, owner_user_id: Optional[int] = None) -> bool:
    with connect() as conn:
        with conn.cursor() as cursor:
            # Check ownership if requested
            if owner_user_id is not None:
                cursor.execute("SELECT 1 FROM reports WHERE report_id = %s AND owner_user_id = %s", (report_id, owner_user_id))
                if not cursor.fetchone():
                    return False

            cursor.execute("DELETE FROM change_reviews WHERE report_id = %s", (report_id,))
            cursor.execute("DELETE FROM report_pages WHERE report_id = %s", (report_id,))
            cursor.execute("DELETE FROM report_aliases WHERE alias_id = %s OR report_id = %s", (report_id, report_id))
            cursor.execute("DELETE FROM comparisons WHERE comparison_id = %s", (report_id,))
            if owner_user_id is not None:
                cursor.execute("DELETE FROM reports WHERE report_id = %s AND owner_user_id = %s", (report_id, owner_user_id))
            else:
                cursor.execute("DELETE FROM reports WHERE report_id = %s", (report_id,))
            affected = cursor.rowcount
            conn.commit()
    return affected > 0



def get_full_report_by_hash(content_hash: str, owner_user_id: int) -> Optional[Dict[str, Any]]:
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM reports WHERE owner_user_id = %s AND content_hash = %s AND status = 'complete'
                AND NOT EXISTS (SELECT 1 FROM report_pages rp WHERE rp.report_id = reports.report_id AND rp.page_status = 'failed')
            """, (owner_user_id, content_hash))
            report_row = cursor.fetchone()
            if not report_row:
                return None
            report_id = report_row["report_id"]

            cursor.execute(
                f"SELECT * FROM report_pages WHERE report_id = %s {_PAGE_ORDER_SQL}",
                (report_id,),
            )
            page_rows = cursor.fetchall()

    report = {
        "report_id": report_row["report_id"],
        "owner_user_id": report_row["owner_user_id"],
        "content_hash": report_row["content_hash"],
        "total_pages": report_row["total_pages"],
        "page_matching": json.loads(report_row["page_matching"]) if report_row["page_matching"] else None,
        "common_render_dpi": report_row["common_render_dpi"],
        "page_size_mismatch": bool(report_row["page_size_mismatch"]),
        "page_size_mismatch_details": json.loads(report_row["page_size_mismatch_details"]) if report_row["page_size_mismatch_details"] else None,
        "created_at": str(report_row["created_at"]),
        "pages": []
    }

    for page_row in page_rows:
        page_size_pts = None
        if page_row["page_size_pts_width"] is not None and page_row["page_size_pts_height"] is not None:
            page_size_pts = {
                "width": page_row["page_size_pts_width"],
                "height": page_row["page_size_pts_height"]
            }

        page = {
            "page_number": page_row["page_number"],
            "matched_new_page_number": page_row["matched_new_page_number"],
            "page_status": page_row["page_status"],
            "page_match_method": page_row["page_match_method"],
            "page_match_score": page_row["page_match_score"],
            "comparison_mode": page_row["comparison_mode"],
            "redesign_detected": bool(page_row["redesign_detected"]),
            "alignment": {
                "match_count": page_row["alignment_match_count"],
                "inlier_count": page_row["alignment_inlier_count"],
                "confidence": page_row["alignment_confidence"],
            } if page_row["alignment_match_count"] is not None else None,
            "alignment_error": page_row["alignment_error"],
            "render_dpi": page_row["render_dpi"],
            "page_size_pts": page_size_pts,
            "page_size_mismatch": bool(page_row["page_size_mismatch"]),
            "page_size_mismatch_details": json.loads(page_row["page_size_mismatch_details"]) if page_row["page_size_mismatch_details"] else None,
            "overall_similarity": page_row["overall_similarity"],
            "overall_summary": page_row["overall_summary"],
            "changes": json.loads(page_row["changes"]),
            "total_changes": len(json.loads(page_row["changes"])),
        }
        report["pages"].append(page)

    attach_reviews_to_pages(report_id, report["pages"], owner_user_id=owner_user_id)
    return report


def get_annotated_export_pages(report_id: str, owner_user_id: Optional[int] = None) -> list[dict]:
    report_id = resolve_report_id(report_id, owner_user_id=owner_user_id)
    with connect() as conn:
        with conn.cursor() as cursor:
            if owner_user_id is not None:
                cursor.execute(
                    f"""SELECT rp.page_number, rp.matched_new_page_number, rp.changes, rp.annotated_source_png
                       FROM report_pages rp
                       JOIN reports r ON r.report_id = rp.report_id
                       WHERE rp.report_id = %s AND r.owner_user_id = %s {_PAGE_ORDER_SQL}""",
                    (report_id, owner_user_id),
                )
            else:
                cursor.execute(
                    f"""SELECT page_number, matched_new_page_number, changes, annotated_source_png
                       FROM report_pages WHERE report_id = %s {_PAGE_ORDER_SQL}""",
                    (report_id,),
                )
            rows = cursor.fetchall()
    return [
        {
            "page_number": row["page_number"],
            "matched_new_page_number": row["matched_new_page_number"],
            "changes": json.loads(row["changes"]),
            "annotated_source_png": row["annotated_source_png"],
        }
        for row in rows
    ]
