"""Async job-status pattern tests for POST /compare and GET /drawings/{id}/compare.

Covers the acceptance criteria:
1. POST /compare returns 202 with a job_id without waiting for the pipeline
   (proven by observing the job row while the pipeline is deliberately blocked).
2. Polling immediately shows pending/processing, never completed.
3. After the task finishes: completed + full result in the old sync shape.
4. Pipeline failure -> failed with a clear error_message, never stuck.
5. Drawing compare cache hit -> synchronous 200, untouched fast path.
6. Drawing compare miss -> 202 + job_id, polling yields the correct pair result.
7. Unknown job_id -> 404.
8. Concurrent requests get independent jobs.
9. Restart marks stale (pending/processing) jobs failed; completed survive.

Note on TestClient: it waits for BackgroundTasks before returning a response,
so "returns immediately" is verified structurally — the job row exists and is
pollable while the pipeline itself is still blocked — not by wall-clock timing.
"""
import threading

import pytest

from conftest import make_pdf_bytes, make_png_bytes, poll_job
from services import jobs

PDF_A4 = (595, 842)


def _standalone_files(old=None, new=None):
    old = old if old is not None else make_pdf_bytes([PDF_A4])
    new = new if new is not None else make_pdf_bytes([PDF_A4], mark_last_page=True)
    return {
        "old_drawing": ("old.pdf", old),
        "new_drawing": ("new.pdf", new),
    }


@pytest.fixture()
def blocking_pipeline(monkeypatch, pipeline_counter):
    """Gate run_comparison behind events so tests can observe the job while
    the pipeline is still blocked. Layers on top of pipeline_counter (which
    already stubs OCR/LLM), so releasing the gate runs the real fast pipeline."""
    import services.comparison_engine as engine

    started = threading.Event()
    release = threading.Event()
    inner_run = engine.run_comparison  # counting_run from pipeline_counter

    def gated(old_bytes, new_bytes, result_id, on_progress=None, *args, **kwargs):
        started.set()
        assert release.wait(timeout=60), "background task was never released"
        return inner_run(old_bytes, new_bytes, result_id, on_progress=on_progress, *args, **kwargs)

    monkeypatch.setattr(engine, "run_comparison", gated)
    return {"started": started, "release": release}


def _new_job_ids(before):
    before_ids = {j["job_id"] for j in before}
    return [j for j in jobs.list_jobs() if j["job_id"] not in before_ids]


def _post_in_thread(files):
    """POST /compare from a worker thread with its own TestClient (the call
    blocks until BackgroundTasks finish, by TestClient design)."""
    from fastapi.testclient import TestClient
    from main import app

    outcome = {}
    worker = TestClient(app)

    def do_post():
        r = worker.post("/api/compare", files=files)
        outcome["status"] = r.status_code
        outcome["body"] = r.json()

    thread = threading.Thread(target=do_post, daemon=True)
    thread.start()
    return thread, outcome


# ------------------------------------------------------------ criteria 1 + 2

def test_compare_returns_202_and_job_pollable_while_pipeline_blocked(
    client, pipeline_counter, blocking_pipeline
):
    before = jobs.list_jobs()
    thread, outcome = _post_in_thread(_standalone_files())

    assert blocking_pipeline["started"].wait(timeout=30), "pipeline never started"
    # The job row exists while the pipeline is still blocked: the endpoint
    # did not wait for the pipeline before recording the job.
    created = _new_job_ids(before)
    assert len(created) == 1
    job_id = created[0]["job_id"]
    assert created[0]["job_type"] == "standalone_compare"

    # Polling right now shows pending/processing, never completed.
    body = client.get(f"/api/jobs/{job_id}").json()
    assert body["job_id"] == job_id
    assert body["status"] in ("pending", "processing")
    assert "result" not in body

    blocking_pipeline["release"].set()
    thread.join(timeout=120)
    assert outcome["status"] == 202
    assert outcome["body"] == {"job_id": job_id, "status": "pending"}

    final = poll_job(client, job_id)
    assert final["status"] == "completed"
    assert final["result"]["report_id"]
    assert final["result"]["total_pages"] == 1


# --------------------------------------------------------------- criterion 3

def test_completed_result_matches_old_sync_shape(client, pipeline_counter):
    r = client.post("/api/compare", files=_standalone_files())
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    final = poll_job(client, job_id)
    assert final["status"] == "completed"
    result = final["result"]
    # Same shape the report fetcher returns (used as-is per spec, not
    # reshaped). Note: the old sync envelope also carried
    # "page_count_warning": None, but that was a hardcoded transient field,
    # never persisted — the stored result is the source of truth here.
    for key in ("report_id", "pages", "total_pages",
                "page_matching", "common_render_dpi"):
        assert key in result, f"missing key {key}"
    assert result["total_pages"] == 1
    assert result["pages"][0]["page_status"] == "matched"
    assert "comparison_id" not in result  # no drawing concept leaked in


# --------------------------------------------------------------- criterion 4

def test_failed_job_on_pipeline_error(client, pipeline_counter, monkeypatch):
    import services.comparison_engine as engine

    def boom(*args, **kwargs):
        raise RuntimeError("boom-ocr-failure")

    monkeypatch.setattr(engine, "run_comparison", boom)

    r = client.post("/api/compare", files=_standalone_files())
    assert r.status_code == 202
    final = poll_job(client, r.json()["job_id"])
    assert final["status"] == "failed"
    assert "boom-ocr-failure" in final["error_message"]
    assert "Traceback" not in final["error_message"]


def test_empty_upload_rejected_before_job_created(client):
    before = len(jobs.list_jobs())
    r = client.post(
        "/api/compare",
        files={"old_drawing": ("empty.pdf", b""), "new_drawing": ("b.pdf", make_pdf_bytes([PDF_A4]))},
    )
    assert r.status_code == 400
    assert len(jobs.list_jobs()) == before  # validation happens before job creation


# --------------------------------------------------------------- criterion 7

def test_unknown_job_id_returns_404(client):
    r = client.get("/api/jobs/does-not-exist")
    assert r.status_code == 404


# --------------------------------------------------------------- criterion 8

def test_concurrent_compares_get_independent_jobs(client, pipeline_counter):
    files_a = _standalone_files(
        old=make_pdf_bytes([PDF_A4]),
        new=make_pdf_bytes([PDF_A4], mark_last_page=True),
    )
    files_b = _standalone_files(
        # Different inputs -> independent results. NOTE: dimensions must differ
        # from make_png_bytes() defaults: PNG output is byte-deterministic, so
        # default-size PNGs would share a content hash with other tests' PNGs
        # and trip the pipeline's hash-dedup path instead of computing fresh.
        old=make_png_bytes(width=320, height=240),
        new=make_png_bytes(width=320, height=240),
    )
    ra = client.post("/api/compare", files=files_a)
    rb = client.post("/api/compare", files=files_b)
    assert ra.status_code == 202 and rb.status_code == 202
    ida, idb = ra.json()["job_id"], rb.json()["job_id"]
    assert ida != idb

    fa = poll_job(client, ida)
    fb = poll_job(client, idb)
    assert fa["status"] == "completed" and fb["status"] == "completed"
    assert fa["result"]["report_id"] != fb["result"]["report_id"]

    ja, jb = jobs.get_job(ida), jobs.get_job(idb)
    assert ja["status"] == jb["status"] == "completed"
    assert ja["job_type"] == jb["job_type"] == "standalone_compare"


# --------------------------------------------------------------- criterion 9

def test_restart_marks_stale_jobs_failed_but_keeps_completed(client, pipeline_counter):
    pending = jobs.create_job("standalone_compare")
    processing = jobs.create_job("standalone_compare")
    jobs.set_processing(processing["job_id"], "halfway")

    done = jobs.create_job("standalone_compare")
    jobs.set_completed(done["job_id"], "some-report-id")

    marked = jobs.mark_stale_jobs_failed()
    assert marked == 2

    assert jobs.get_job(pending["job_id"])["status"] == "failed"
    failed = jobs.get_job(processing["job_id"])
    assert failed["status"] == "failed"
    assert "resubmit" in failed["error_message"]

    kept = jobs.get_job(done["job_id"])
    assert kept["status"] == "completed"
    assert kept["result_id"] == "some-report-id"


# --------------------------------------------------------- criteria 5 and 6

def _create_drawing_with_two_revisions(client):
    from test_versioning import create_drawing_with_revisions
    return create_drawing_with_revisions(client, [[PDF_A4], [PDF_A4]])


def test_drawing_compare_miss_returns_202_then_correct_result(client, pipeline_counter):
    drawing_id, revs = _create_drawing_with_two_revisions(client)

    r = client.get(
        f"/api/drawings/{drawing_id}/compare",
        params={"from": revs[0]["revision_id"], "to": revs[1]["revision_id"]},
    )
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    assert r.json()["status"] == "pending"

    job = jobs.get_job(job_id)
    assert job["job_type"] == "drawing_compare"
    assert job["drawing_id"] == drawing_id

    final = poll_job(client, job_id)
    assert final["status"] == "completed"
    result = final["result"]
    assert result["drawing_id"] == drawing_id
    assert result["old_revision_id"] == revs[0]["revision_id"]
    assert result["new_revision_id"] == revs[1]["revision_id"]
    assert result["pages"], "expected compared pages in result"
    assert pipeline_counter["runs"] == 1


def test_drawing_compare_cache_hit_returns_200_sync(client, pipeline_counter):
    drawing_id, revs = _create_drawing_with_two_revisions(client)
    params = {"from": revs[0]["revision_id"], "to": revs[1]["revision_id"]}

    first = client.get(f"/api/drawings/{drawing_id}/compare", params=params)
    assert first.status_code == 202
    first_result = poll_job(client, first.json()["job_id"])["result"]
    assert pipeline_counter["runs"] == 1

    # Cache hit: full result synchronously, no job involved.
    second = client.get(f"/api/drawings/{drawing_id}/compare", params=params)
    assert second.status_code == 200
    body = second.json()
    assert body["was_cached"] is True
    assert body["comparison_id"] == first_result["comparison_id"]
    assert body["pages"] == first_result["pages"]
    assert pipeline_counter["runs"] == 1


def test_drawing_compare_failure_marks_job_failed(client, pipeline_counter, monkeypatch):
    import services.comparison_engine as engine

    drawing_id, revs = _create_drawing_with_two_revisions(client)

    def boom(*args, **kwargs):
        raise RuntimeError("drawing-boom")

    monkeypatch.setattr(engine, "run_comparison", boom)
    r = client.get(
        f"/api/drawings/{drawing_id}/compare",
        params={"from": revs[0]["revision_id"], "to": revs[1]["revision_id"]},
    )
    assert r.status_code == 202
    final = poll_job(client, r.json()["job_id"])
    assert final["status"] == "failed"
    assert "drawing-boom" in final["error_message"]
