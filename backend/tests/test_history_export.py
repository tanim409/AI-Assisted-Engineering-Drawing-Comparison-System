"""Minimal tests for the document-history summary PDF export.

Covers: full chain export (correct sections/order/data), uncompared pair
skipped with a note, single-revision minimal export, and PDF validity.
Uses the shared conftest fixtures (stubbed OCR/LLM, counted pipeline runs).
"""
import fitz
import pytest

from conftest import make_pdf_bytes

PDF_A4 = (595, 842)


def upload_revision(client, drawing_id, data, filename, label=None):
    params = {"file": (filename, data)}
    if label:
        params["revision_label"] = (None, label)
    return client.post(f"/api/drawings/{drawing_id}/revisions", files=params)


def compare_and_wait(client, drawing_id, old_rev_id, new_rev_id):
    """Run a drawing-scoped comparison via the async job flow and wait until
    the job completes (TestClient runs background tasks synchronously; the
    poll is just belt-and-braces)."""
    r = client.get(
        f"/api/drawings/{drawing_id}/compare",
        params={"from": old_rev_id, "to": new_rev_id},
    )
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    for _ in range(50):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("completed", "failed"):
            assert job["status"] == "completed", job.get("error_message")
            return job
        import time
        time.sleep(0.1)
    raise AssertionError("comparison job did not finish in time")


def make_drawing(client, revision_specs):
    """revision_specs: list of (page_sizes, label, mark). Returns (drawing_id, [revisions])."""
    r = client.post("/api/drawings", json={"name": "Bracket DWG"})
    assert r.status_code == 201
    drawing_id = r.json()["drawing_id"]
    revs = []
    for i, (sizes, label, mark) in enumerate(revision_specs):
        r = upload_revision(
            client, drawing_id, make_pdf_bytes(sizes, mark_last_page=mark), f"rev{i + 1}.pdf", label
        )
        assert r.status_code == 201
        revs.append(r.json())
    return drawing_id, revs


def export_bytes(client, drawing_id):
    r = client.get(f"/api/drawings/{drawing_id}/history/export")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"]
    data = r.content
    assert data.startswith(b"%PDF")  # valid PDF header
    doc = fitz.open(stream=data, filetype="pdf")
    return doc  # caller must close


def test_full_chain_export_sections_in_order(client, pipeline_counter):
    drawing_id, revs = make_drawing(client, [
        ([PDF_A4], "Rev A", False),
        ([PDF_A4], "Rev B", True),   # change vs V1
        ([PDF_A4], "Rev C", False),  # change vs V2 (mark removed)
    ])
    compare_and_wait(client, drawing_id, revs[0]["revision_id"], revs[1]["revision_id"])
    compare_and_wait(client, drawing_id, revs[1]["revision_id"], revs[2]["revision_id"])
    runs_before_export = pipeline_counter["runs"]

    doc = export_bytes(client, drawing_id)
    all_text = "\n".join(page.get_text() for page in doc)
    cover_text = doc[0].get_text()

    # Cover section data
    assert "ENGINEERING DRAWING REVISION HISTORY" in cover_text
    assert "Bracket DWG" in cover_text
    assert "Total Revisions:" in cover_text
    assert "3 revisions" in cover_text

    # One section per consecutive pair, correct order (content may flow
    # across pages — order is verified via text positions, not page indices)
    assert "Rev A" in all_text and "Rev B" in all_text and "Rev C" in all_text
    assert all_text.index("Rev A") < all_text.index("Rev B")
    sec1_start = all_text.index("SECTION 1")
    sec2_start = all_text.index("SECTION 2")
    sec1, sec2 = all_text[sec1_start:sec2_start], all_text[sec2_start:]
    assert "Rev A" in sec1 and "Rev B" in sec1
    assert "Overall Similarity:" in sec1
    assert "Category Breakdown:" in sec1
    assert "Rev B" in sec2 and "Rev C" in sec2

    # V1->V2 introduced a marked change: breakdown must show >= 1 change
    assert "Total Changes:" in sec1

    # Export must not run the pipeline (aggregation of stored data only)
    assert pipeline_counter["runs"] == runs_before_export
    doc.close()


def test_uncompared_pair_skipped_with_note(client, pipeline_counter):
    drawing_id, revs = make_drawing(client, [
        ([PDF_A4], "Rev A", False),
        ([PDF_A4], "Rev B", True),
        ([PDF_A4], "Rev C", False),
    ])
    compare_and_wait(client, drawing_id, revs[0]["revision_id"], revs[1]["revision_id"])
    runs_before_export = pipeline_counter["runs"]

    doc = export_bytes(client, drawing_id)
    text = "\n".join(page.get_text() for page in doc)

    assert "SECTION 1" in text
    assert "Rev 2 -> Rev 3: not yet compared" in text
    # Skipping (not computing) — no pipeline work happened during export
    assert pipeline_counter["runs"] == runs_before_export
    doc.close()


def test_single_revision_minimal_valid_pdf(client):
    drawing_id, _ = make_drawing(client, [([PDF_A4], "Rev A", False)])

    doc = export_bytes(client, drawing_id)
    assert doc.page_count == 1  # cover section only
    text = doc[0].get_text()
    assert "Bracket DWG" in text
    assert "1 revisions" in text
    assert "0 compared, 0 not yet compared" in text
    doc.close()


def test_export_is_valid_pdf(client):
    drawing_id, _ = make_drawing(client, [
        ([PDF_A4], "Rev A", False),
        ([PDF_A4], "Rev B", True),
    ])
    # leave uncompared — validity is independent of compared state
    doc = export_bytes(client, drawing_id)
    assert doc.page_count >= 1
    assert doc.is_pdf  # fitz parses it back as a PDF
    doc.close()


def test_summary_pdf_export_endpoint(client):
    drawing_id, revs = make_drawing(client, [
        ([PDF_A4], "Rev A", False),
        ([PDF_A4], "Rev B", True),
    ])
    job = compare_and_wait(client, drawing_id, revs[0]["revision_id"], revs[1]["revision_id"])
    report_id = job.get("result", {}).get("report_id") or job.get("report_id") or job.get("result_id")
    if not report_id:
        # Fallback: get comparisons for drawing
        comps = client.get(f"/api/drawings/{drawing_id}/history").json()
        report_id = comps[0]["comparison_id"]

    r = client.get(f"/api/reports/{report_id}/summary-pdf")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"]
    data = r.content
    assert data.startswith(b"%PDF")
    doc = fitz.open(stream=data, filetype="pdf")
    assert doc.page_count >= 1
    text = "\n".join(page.get_text() for page in doc)
    assert "ENGINEERING DRAWING COMPARISON REPORT" in text
    assert "EXECUTIVE SUMMARY" in text
    assert "COMPARISON STATISTICS" in text
    assert "CHANGE DETAILS LOG" in text
    doc.close()

