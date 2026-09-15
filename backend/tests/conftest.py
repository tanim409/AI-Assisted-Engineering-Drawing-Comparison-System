"""Shared test setup.

- Points the SQLite DB and revision storage at a temp location so tests never
  touch real data. Must run before any app module is imported (DB paths are
  read at import time).
- Stubs the heavy external steps (LLM classification, OCR) inside the
  comparison engine namespace, and counts real pipeline executions so tests
  can verify caching without relying on network/tesseract.
"""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="drawing_poc_tests_")
os.environ.setdefault("DRAWINGS_DB_PATH", os.path.join(_TMP, "test_reports.db"))
os.environ.setdefault("REVISION_STORAGE_DIR", os.path.join(_TMP, "storage"))
# For testing: lower title-block OCR word count threshold so simple title-block text works
os.environ.setdefault("MIN_TITLE_WORDS", "1")
os.environ.setdefault("MIN_TITLE_OCR_CONFIDENCE", "10")

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    from model.db import connect
    from model.report_db import init_db
    from model.versioning_db import init_versioning_db
    init_db()
    init_versioning_db()
    with connect() as conn:
        with conn.cursor() as cursor:
            for table in ["change_reviews", "report_pages", "report_aliases", "reports", "jobs", "comparisons", "revisions", "drawings"]:
                try:
                    cursor.execute(f"TRUNCATE TABLE {table} CASCADE;")
                except Exception:
                    pass
            # Ensure test user exists (auth override uses user_id=1)
            cursor.execute("""
                INSERT INTO users (user_id, email, password_hash, email_verified, is_active)
                VALUES (1, 'test@example.com', '$2b$12$test_hash_placeholder', TRUE, TRUE)
                ON CONFLICT (user_id) DO NOTHING
            """)



@pytest.fixture()
def pipeline_counter(monkeypatch):
    """Stub OCR + LLM inside the engine and count pipeline executions."""
    import services.comparison_engine as engine

    counter = {"runs": 0}
    real_run = engine.run_comparison

    def counting_run(*args, **kwargs):
        counter["runs"] += 1
        return real_run(*args, **kwargs)

    def fake_ocr(region_img):
        return {"text": "STUB-TEXT-123", "confidence": 90.0}

    def fake_llm(flagged_regions, patch_images=None, old_gray=None, new_gray=None):
        results = {
            i: {
                "region_index": i,
                "category": "note_or_annotation_change",
                "description": "stub change",
                "confidence": 0.9,
                "source": "fallback",
            }
            for i, _ in enumerate(flagged_regions)
        }
        return {"results": results, "overall_summary": "stub summary"}

    monkeypatch.setattr(engine, "run_comparison", counting_run)
    monkeypatch.setattr(engine, "llm_classify_batch", fake_llm)
    return counter



@pytest.fixture()
def client(pipeline_counter):
    from main import app
    from services import auth
    from fastapi.testclient import TestClient

    app.dependency_overrides[auth.get_current_user] = lambda: {
        "user_id": 1,
        "email": "test@example.com",
        "email_verified": True,
        "is_active": True,
    }
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_pdf_bytes(page_sizes, mark_last_page=False):
    """Build an in-memory PDF. page_sizes: list of (width_pts, height_pts)."""
    import fitz

    doc = fitz.open()
    for i, (w, h) in enumerate(page_sizes):
        page = doc.new_page(width=w, height=h)
        # Put text in title block area (bottom-right) so page matching works
        # Use 3+ words to ensure MIN_TITLE_WORDS >= 2 is satisfied even with OCR variations
        page.insert_text((w * 0.7, h * 0.9), f"DRAWING TITLE SHEET {i + 1}", fontsize=12)
    if mark_last_page and len(doc) > 0:
        last = doc[len(doc) - 1]
        last.draw_rect(fitz.Rect(w * 0.1, h * 0.1, w * 0.3, h * 0.3), color=None, fill=(0, 0, 0))
    data = doc.tobytes()
    doc.close()
    return data


def make_png_bytes(width=300, height=300):
    """Build a featureless (uniform) in-memory PNG."""
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("L", (width, height), 200).save(buf, format="PNG")
    return buf.getvalue()


def poll_job(client, job_id, timeout=60.0, interval=0.2):
    """Poll GET /jobs/{job_id} until it reaches a terminal state.

    Note: FastAPI's TestClient waits for BackgroundTasks before returning a
    response, so by the time a 202 comes back the job is usually already
    completed. This helper just abstracts the poll loop either way.
    """
    import time

    deadline = time.time() + timeout
    while True:
        r = client.get(f"/api/jobs/{job_id}")
        assert r.status_code == 200, r.text
        body = r.json()
        if body["status"] in ("completed", "failed"):
            return body
        assert time.time() < deadline, f"Timed out waiting for job {job_id}"
        time.sleep(interval)
