"""Minimal checkpoint/resume tests for multi-page comparisons.

1. Forced failure on one page: other pages still complete + stored, failed
   page checkpointed with the error (page_status='failed').
2. Retry: only the failed page is recomputed (counted via a patched
   compare_single_page); completed pages are not touched.
3. After retry the assembled report is complete and correctly ordered.
4. All-pages-success path is unaffected.
"""
import time

from conftest import make_pdf_bytes
from services import comparison_engine
from services.report_data import get_page_status_map

A4 = (595, 842)


def _upload(client, drawing_id, data, filename):
    r = client.post(f"/api/drawings/{drawing_id}/revisions", files={"file": (filename, data)})
    assert r.status_code == 201
    return r.json()


def _compare_async(client, drawing_id, old_rev_id, new_rev_id):
    r = client.get(
        f"/api/drawings/{drawing_id}/compare",
        params={"from": old_rev_id, "to": new_rev_id},
    )
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    for _ in range(100):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("completed", "failed"):
            return job
        time.sleep(0.2)
    raise AssertionError("job did not finish in time")


def _make_drawing_with_pair(client, old_pdf, new_pdf):
    r = client.post("/api/drawings", json={"name": "Retry DWG"})
    assert r.status_code == 201
    drawing_id = r.json()["drawing_id"]
    rev1 = _upload(client, drawing_id, old_pdf, "v1.pdf")
    rev2 = _upload(client, drawing_id, new_pdf, "v2.pdf")
    return drawing_id, rev1, rev2


def test_page_failure_checkpoint_resume_and_final_report(client, pipeline_counter, monkeypatch):
    old_pdf = make_pdf_bytes([A4, A4])
    new_pdf = make_pdf_bytes([A4, A4], mark_last_page=True)  # change on page 2
    drawing_id, rev1, rev2 = _make_drawing_with_pair(client, old_pdf, new_pdf)

    # Force the SECOND page's comparison to raise (simulating a page-specific
    # pipeline failure, e.g. an LLM call blowing up on page 2 of 2).
    real_csp = comparison_engine.compare_single_page
    state = {"attempted": 0, "real": 0, "fail_attempt": 2}

    def flaky(old, new, **kwargs):
        state["attempted"] += 1
        if state["attempted"] == state["fail_attempt"]:
            raise RuntimeError("LLM call failed on page 2")
        state["real"] += 1
        return real_csp(old, new, **kwargs)

    monkeypatch.setattr(comparison_engine, "compare_single_page", flaky)

    job = _compare_async(client, drawing_id, rev1["revision_id"], rev2["revision_id"])
    assert job["status"] == "completed", job.get("error_message")
    first = job["result"]

    # Other pages still complete and stored; failed page marked, not aborting.
    assert [p["page_status"] for p in first["pages"]] == ["matched", "failed"]
    assert "LLM call failed on page 2" in first["pages"][1]["alignment_error"]
    assert state["real"] == 1  # only page 1 actually processed
    comparison_id = first["comparison_id"]
    statuses = get_page_status_map(comparison_id)
    assert sorted((s["page_number"], s["page_status"]) for s in statuses) == [(1, "matched"), (2, "failed")]
    page1_before = first["pages"][0]

    # --- Retry: failure removed, resume must reprocess ONLY page 2.
    state["fail_attempt"] = 999
    real_before_retry = state["real"]

    job2 = _compare_async(client, drawing_id, rev1["revision_id"], rev2["revision_id"])
    assert job2["status"] == "completed", job2.get("error_message")
    second = job2["result"]

    # Same comparison record, now fully complete
    assert second["comparison_id"] == comparison_id
    assert [p["page_status"] for p in second["pages"]] == ["matched", "matched"]
    # Final report correctly ordered (retried page slotted into position)
    assert [p["page_number"] for p in second["pages"]] == [1, 2]
    # Page 1 was NOT recomputed: identical stored result, no new pipeline call
    assert second["pages"][0] == page1_before
    assert state["real"] - real_before_retry == 1
    # Retried page 2 produced a real result (the marked change is detected)
    assert second["pages"][1]["total_changes"] >= 1

    # --- Now fully complete: subsequent request is served from cache, synchronously
    r = client.get(
        f"/api/drawings/{drawing_id}/compare",
        params={"from": rev1["revision_id"], "to": rev2["revision_id"]},
    )
    assert r.status_code == 200
    assert r.json()["was_cached"] is True
    assert state["real"] == real_before_retry + 1  # no further recomputation


def test_all_pages_success_unaffected(client, pipeline_counter, monkeypatch):
    old_pdf = make_pdf_bytes([A4, A4])
    new_pdf = make_pdf_bytes([A4, A4], mark_last_page=True)
    drawing_id, rev1, rev2 = _make_drawing_with_pair(client, old_pdf, new_pdf)

    real_csp = comparison_engine.compare_single_page
    calls = {"real": 0}

    def counting(old, new, **kwargs):
        calls["real"] += 1
        return real_csp(old, new, **kwargs)

    monkeypatch.setattr(comparison_engine, "compare_single_page", counting)

    job = _compare_async(client, drawing_id, rev1["revision_id"], rev2["revision_id"])
    assert job["status"] == "completed"
    result = job["result"]
    assert [p["page_status"] for p in result["pages"]] == ["matched", "matched"]
    assert [p["page_number"] for p in result["pages"]] == [1, 2]
    assert calls["real"] == 2  # one pass, both pages, no retries

    # Cached repeat does not recompute anything
    r = client.get(
        f"/api/drawings/{drawing_id}/compare",
        params={"from": rev1["revision_id"], "to": rev2["revision_id"]},
    )
    assert r.status_code == 200
    assert r.json()["was_cached"] is True
    assert calls["real"] == 2


def test_document_with_no_matched_pages_all_added_no_crash(client, pipeline_counter):
    """Every page 'added' (unrelated documents): the added-page branch must
    not depend on a matched pair having computed a DPI first."""
    old_pdf = make_pdf_bytes([A4])
    # Overwrite title text so signatures differ → nothing matches.
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=A4[0], height=A4[1])
    page.insert_text((A4[0] * 0.7, A4[1] * 0.9), "COMPLETELY OTHER PART ZZ", fontsize=12)
    doc.insert_page(-1, width=A4[0], height=A4[1])  # second page, no title
    new_pdf = doc.tobytes()
    doc.close()

    drawing_id, rev1, rev2 = _make_drawing_with_pair(client, old_pdf, new_pdf)
    job = _compare_async(client, drawing_id, rev1["revision_id"], rev2["revision_id"])
    assert job["status"] == "completed", job.get("error_message")
    pages = job["result"]["pages"]
    statuses = [p["page_status"] for p in pages]
    assert "failed" not in statuses
    assert "added" in statuses


def test_added_page_failure_is_isolated_and_resumable(client, pipeline_counter, monkeypatch):
    """An added page's render failing must not abort the comparison (bug 3),
    and a retry must clean up the failed checkpoint instead of duplicating it
    (bug 5)."""
    old_pdf = make_pdf_bytes([A4])
    new_pdf = make_pdf_bytes([A4, A4])  # second page has no title → unmatched → added

    real_render = comparison_engine.pdf_bytes_render_single_page
    state = {"fail_first": True}

    def flaky_render(pdf_bytes, page_number, dpi):
        # The added page is new-page 2 (old doc has only page 1); the matched
        # pair renders page 1 twice. Failing page 2's render targets exactly
        # the added-page branch.
        if state["fail_first"] and page_number == 2:
            raise RuntimeError("render exploded on added page")
        return real_render(pdf_bytes, page_number, dpi)

    monkeypatch.setattr(comparison_engine, "pdf_bytes_render_single_page", flaky_render)

    drawing_id, rev1, rev2 = _make_drawing_with_pair(client, old_pdf, new_pdf)
    job = _compare_async(client, drawing_id, rev1["revision_id"], rev2["revision_id"])
    assert job["status"] == "completed", job.get("error_message")
    first = job["result"]
    statuses = {p["matched_new_page_number"]: p["page_status"] for p in first["pages"]}
    assert statuses[2] == "failed"  # the added page failed…
    assert "render exploded" in [p["alignment_error"] for p in first["pages"] if p["page_status"] == "failed"][0]
    # …but the run completed and the failed checkpoint is stored exactly once
    rows = get_page_status_map(first["comparison_id"])
    assert len([s for s in rows if s["page_status"] == "failed"]) == 1

    # Retry: the added page is reprocessed, failed checkpoint replaced (no duplicate)
    state["fail_first"] = False
    job2 = _compare_async(client, drawing_id, rev1["revision_id"], rev2["revision_id"])
    assert job2["status"] == "completed", job2.get("error_message")
    second = job2["result"]
    assert second["comparison_id"] == first["comparison_id"]
    statuses2 = {p["matched_new_page_number"]: p["page_status"] for p in second["pages"]}
    assert statuses2[2] == "added"  # now processed successfully
    rows2 = get_page_status_map(first["comparison_id"])
    # no stale 'failed' checkpoint and no duplicate row for that page
    assert all(s["page_status"] != "failed" for s in rows2)
    added_rows = [s for s in rows2 if s["page_number"] is None and s["matched_new_page_number"] == 2]
    assert len(added_rows) == 1 and added_rows[0]["page_status"] == "added"
