"""Persistence and read-time attachment of human change reviews in PostgreSQL."""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from model.db import connect
from model.report_db import resolve_report_id


VALID_REVIEW_STATUSES = {"confirmed", "false_positive"}


def default_review(report_id: str, page_number: int, change_index: int) -> dict[str, Any]:
    return {
        "review_id": None,
        "report_id": report_id,
        "page_number": page_number,
        "change_index": change_index,
        "status": "unreviewed",
        "note": None,
        "reviewed_at": None,
        "reviewer_id": None,
    }


def _row_to_review(row) -> dict[str, Any]:
    d = dict(row)
    if d.get("reviewed_at"):
        d["reviewed_at"] = str(d["reviewed_at"])
    return d


def _review_page_number(page: dict[str, Any]) -> Optional[int]:
    return page.get("page_number") if page.get("page_number") is not None else page.get("matched_new_page_number")


def ensure_change_exists(report_id: str, page_number: int, change_index: int, owner_user_id: Optional[int] = None) -> None:
    report_id = resolve_report_id(report_id, owner_user_id=owner_user_id)
    if page_number < 1 or change_index < 0:
        raise ValueError("page_number must be positive and change_index must be non-negative")
    with connect() as conn:
        with conn.cursor() as cursor:
            if owner_user_id is not None:
                cursor.execute(
                    "SELECT 1 FROM reports WHERE report_id = %s AND owner_user_id = %s AND status = 'complete'",
                    (report_id, owner_user_id)
                )
            else:
                cursor.execute("SELECT 1 FROM reports WHERE report_id = %s AND status = 'complete'", (report_id,))
            report = cursor.fetchone()
            if not report:
                raise ValueError("Report not found or access denied")

            cursor.execute(
                """SELECT changes FROM report_pages
                   WHERE report_id = %s
                     AND (page_number = %s OR (page_number IS NULL AND matched_new_page_number = %s))""",
                (report_id, page_number, page_number),
            )
            row = cursor.fetchone()
    if row is None:
        raise ValueError(f"Page {page_number} does not exist in this report")
    if change_index >= len(json.loads(row["changes"])):
        raise ValueError(f"Change index {change_index} does not exist on page {page_number}")


def get_change_review(report_id: str, page_number: int, change_index: int, owner_user_id: Optional[int] = None) -> dict[str, Any]:
    report_id = resolve_report_id(report_id, owner_user_id=owner_user_id)
    with connect() as conn:
        with conn.cursor() as cursor:
            if owner_user_id is not None:
                cursor.execute(
                    """SELECT cr.* FROM change_reviews cr
                       JOIN reports r ON r.report_id = cr.report_id
                       WHERE cr.report_id = %s AND cr.page_number = %s AND cr.change_index = %s AND r.owner_user_id = %s""",
                    (report_id, page_number, change_index, owner_user_id),
                )
            else:
                cursor.execute(
                    """SELECT * FROM change_reviews
                       WHERE report_id = %s AND page_number = %s AND change_index = %s""",
                    (report_id, page_number, change_index),
                )
            row = cursor.fetchone()
    return _row_to_review(row) if row else default_review(report_id, page_number, change_index)


def upsert_change_review(
    report_id: str, page_number: int, change_index: int, status: str,
    note: Optional[str], reviewer_id: Optional[str], owner_user_id: Optional[int] = None,
) -> dict[str, Any]:
    report_id = resolve_report_id(report_id, owner_user_id=owner_user_id)
    if status not in VALID_REVIEW_STATUSES:
        raise ValueError("status must be 'confirmed' or 'false_positive'")
    review_id = str(uuid.uuid4())
    reviewed_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with connect() as conn:
        with conn.cursor() as cursor:
            if owner_user_id is not None:
                cursor.execute("SELECT 1 FROM reports WHERE report_id = %s AND owner_user_id = %s", (report_id, owner_user_id))
                if not cursor.fetchone():
                    raise ValueError("Report not found or access denied")

            cursor.execute(
                """INSERT INTO change_reviews
                       (review_id, report_id, page_number, change_index, status, note, reviewed_at, reviewer_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (report_id, page_number, change_index) DO UPDATE SET
                       status = EXCLUDED.status,
                       note = EXCLUDED.note,
                       reviewed_at = EXCLUDED.reviewed_at,
                       reviewer_id = EXCLUDED.reviewer_id""",
                (review_id, report_id, page_number, change_index, status, note, reviewed_at, reviewer_id),
            )
    return get_change_review(report_id, page_number, change_index, owner_user_id=owner_user_id)


def attach_reviews_to_pages(report_id: str, pages: list[dict[str, Any]], owner_user_id: Optional[int] = None) -> None:
    report_id = resolve_report_id(report_id, owner_user_id=owner_user_id)
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM change_reviews WHERE report_id = %s", (report_id,))
            rows = cursor.fetchall()
    reviews = {(row["page_number"], row["change_index"]): _row_to_review(row) for row in rows}
    for page in pages:
        page_number = _review_page_number(page)
        for change_index, change in enumerate(page.get("changes", [])):
            change["review"] = reviews.get(
                (page_number, change_index), default_review(report_id, page_number, change_index)
            )


def build_review_summary(report_id: str, pages: list[dict[str, Any]]) -> dict[str, Any]:
    confirmed = false_positive = 0
    unreviewed_changes = []
    for page in pages:
        page_number = _review_page_number(page)
        for change_index, change in enumerate(page.get("changes", [])):
            status = change.get("review", {}).get("status", "unreviewed")
            if status == "confirmed":
                confirmed += 1
            elif status == "false_positive":
                false_positive += 1
            else:
                unreviewed_changes.append({"page_number": page_number, "change_index": change_index})
    return {
        "report_id": report_id,
        "total_changes": confirmed + false_positive + len(unreviewed_changes),
        "confirmed": confirmed,
        "false_positive": false_positive,
        "unreviewed": len(unreviewed_changes),
        "unreviewed_changes": unreviewed_changes,
    }
