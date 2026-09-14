"""Focused API tests for human review annotations."""
import uuid

from model.report_db import connect, init_db
from services.report_data import complete_report, init_report, save_report_page


def _make_report(change_count=3):
    report_id = f"review-report-{uuid.uuid4()}"
    report_id = init_report(
        report_id=report_id,
        total_pages=1,
        page_matching={},
        common_render_dpi=150,
        page_size_mismatch=False,
        page_size_mismatch_details={},
        content_hash=f"review-hash-{uuid.uuid4()}",
    ) or report_id
    save_report_page(report_id, {
        "page_number": 1,
        "matched_new_page_number": 1,
        "page_status": "matched",
        "changes": [
            {"bbox": {"x": i * 10, "y": 0, "w": 8, "h": 8}, "classification": {"category": "addition"}}
            for i in range(change_count)
        ],
    })
    complete_report(report_id, 1, {}, 150, False, {})
    return report_id


def test_creates_change_review(client):
    report_id = _make_report()
    response = client.post(
        f"/api/reports/{report_id}/changes/1/0/review",
        json={"status": "confirmed", "note": "Verified in field", "reviewer_id": "sam@example.com"},
    )
    assert response.status_code == 200
    review = response.json()
    assert review["status"] == "confirmed"
    assert review["note"] == "Verified in field"
    assert review["reviewer_id"] == "sam@example.com"
    assert review["reviewed_at"] is not None


def test_review_upsert_updates_existing_record_without_duplicate(client):
    report_id = _make_report()
    first = client.post(f"/api/reports/{report_id}/changes/1/0/review", json={"status": "confirmed"})
    second = client.post(
        f"/api/reports/{report_id}/changes/1/0/review",
        json={"status": "false_positive", "note": "Alignment artifact", "reviewer_id": "Rina"},
    )
    assert first.status_code == second.status_code == 200
    assert second.json()["review_id"] == first.json()["review_id"]
    assert second.json()["status"] == "false_positive"
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as cnt FROM change_reviews WHERE report_id = %s", (report_id,))
            count = cursor.fetchone()["cnt"]
    assert count == 1


def test_unreviewed_change_returns_default_review_state(client):
    report_id = _make_report()
    response = client.get(f"/api/reports/{report_id}/changes/1/1/review")
    assert response.status_code == 200
    assert response.json() == {
        "review_id": None, "report_id": report_id, "page_number": 1, "change_index": 1,
        "status": "unreviewed", "note": None, "reviewed_at": None, "reviewer_id": None,
    }


def test_report_response_merges_review_state_inline(client):
    report_id = _make_report(change_count=2)
    client.post(f"/api/reports/{report_id}/changes/1/0/review", json={"status": "confirmed"})
    response = client.get(f"/api/reports/{report_id}")
    assert response.status_code == 200
    changes = response.json()["pages"][0]["changes"]
    assert changes[0]["review"]["status"] == "confirmed"
    assert changes[1]["review"]["status"] == "unreviewed"


def test_review_summary_counts_and_lists_unreviewed_changes(client):
    report_id = _make_report(change_count=3)
    client.post(f"/api/reports/{report_id}/changes/1/0/review", json={"status": "confirmed"})
    client.post(f"/api/reports/{report_id}/changes/1/1/review", json={"status": "false_positive"})
    response = client.get(f"/api/reports/{report_id}/reviews/summary")
    assert response.status_code == 200
    assert response.json() == {
        "report_id": report_id,
        "total_changes": 3,
        "confirmed": 1,
        "false_positive": 1,
        "unreviewed": 1,
        "unreviewed_changes": [{"page_number": 1, "change_index": 2}],
    }


def test_review_rejects_missing_change_reference(client):
    report_id = _make_report()
    response = client.post(
        f"/api/reports/{report_id}/changes/1/99/review", json={"status": "confirmed"},
    )
    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]
