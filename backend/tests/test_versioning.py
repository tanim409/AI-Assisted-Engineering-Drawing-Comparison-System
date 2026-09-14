"""Version-history support tests: drawings, revisions, comparisons.

Covers the functional requirements (Flow A/B/C, caching, defaults, history),
edge cases (single revision, cross-drawing, missing IDs, concurrent uploads,
pipeline mismatch conditions) and data-integrity requirements (no delete
behavior, restart survival, standalone /compare regression).
"""
import concurrent.futures
import time

import pytest

from conftest import make_pdf_bytes, make_png_bytes, poll_job
from model import versioning_db

PDF_A4 = (595, 842)


def upload_revision(client, drawing_id, data, filename, label=None):
    params = {"file": (filename, data)}
    if label:
        params["revision_label"] = (None, label)
    return client.post(f"/api/drawings/{drawing_id}/revisions", files=params)


def create_drawing_with_revisions(client, sizes_list, labels=None):
    """sizes_list: list of page_sizes for each revision. Returns (drawing_id, [revisions])."""
    r = client.post("/api/drawings", json={})
    assert r.status_code == 201
    drawing_id = r.json()["drawing_id"]
    revs = []
    for i, sizes in enumerate(sizes_list):
        label = labels[i] if labels else None
        r = upload_revision(client, drawing_id, make_pdf_bytes(sizes), f"rev{i + 1}.pdf", label)
        assert r.status_code == 201
        revs.append(r.json())
    return drawing_id, revs


# ---------------------------------------------------------------- Flow A

def test_flow_a_two_files_create_drawing_revisions_and_comparison(client, pipeline_counter):
    old_pdf = make_pdf_bytes([PDF_A4])
    new_pdf = make_pdf_bytes([PDF_A4], mark_last_page=True)
    drawings_before = len(client.get("/api/drawings").json()["drawings"])

    r = client.post(
        "/api/drawings/upload-and-compare",
        files={"old_drawing": ("part_a_rev1.pdf", old_pdf), "new_drawing": ("part_a_rev2.pdf", new_pdf)},
    )
    assert r.status_code == 200, r.text
    body = r.json()

    # One drawing, two revisions, one comparison — created with no extra user action
    assert body["drawing"]["name"] == "part_a_rev1"  # derived from old filename
    assert body["revisions"][0]["sequence_number"] == 1
    assert body["revisions"][1]["sequence_number"] == 2
    assert body["old_revision_id"] == body["revisions"][0]["revision_id"]
    assert body["new_revision_id"] == body["revisions"][1]["revision_id"]
    assert body["comparison_id"]
    assert body["total_pages"] == 1
    assert body["pages"][0]["page_status"] == "matched"
    assert pipeline_counter["runs"] == 1

    hist = client.get(f"/api/drawings/{body['drawing_id']}/history").json()
    assert len(hist["revisions"]) == 2
    assert hist["consecutive_pairs"][0]["has_comparison"] is True
    assert hist["consecutive_pairs"][0]["comparison_id"] == body["comparison_id"]

    # Flow A created exactly one drawing (relative assertion: other tests in
    # the session may own drawings too, since the test DB is shared).
    drawings = client.get("/api/drawings").json()["drawings"]
    assert len(drawings) == drawings_before + 1
    created = next(d for d in drawings if d["drawing_id"] == body["drawing"]["drawing_id"])
    assert created["revision_count"] == 2


def test_flow_a_result_matches_standalone_compare_shape(client, pipeline_counter):
    old_pdf = make_pdf_bytes([PDF_A4])
    new_pdf = make_pdf_bytes([PDF_A4], mark_last_page=True)

    flow_a = client.post(
        "/api/drawings/upload-and-compare",
        files={"old_drawing": ("a.pdf", old_pdf), "new_drawing": ("b.pdf", new_pdf)},
    ).json()

    standalone = client.post(
        "/api/compare",
        files={"old_drawing": ("a.pdf", old_pdf), "new_drawing": ("b.pdf", new_pdf)},
    )
    assert standalone.status_code == 202
    standalone = poll_job(client, standalone.json()["job_id"])["result"]

    # Same pipeline, same structural outcome. Same input bytes hash to the
    # same stored report, so the standalone job correctly reuses Flow A's
    # report instead of recomputing it.
    assert standalone["total_pages"] == flow_a["total_pages"] == 1
    sa, fa = standalone["pages"][0], flow_a["pages"][0]
    assert sa["page_status"] == fa["page_status"] == "matched"
    assert sa["total_changes"] == fa["total_changes"]
    assert sa["comparison_mode"] == fa["comparison_mode"]
    assert standalone["report_id"] == flow_a["report_id"]


# ---------------------------------------------------------------- Flow B

def test_flow_b_register_revision_triggers_no_comparison(client, pipeline_counter):
    drawing_id, _ = create_drawing_with_revisions(client, [[PDF_A4]])
    assert pipeline_counter["runs"] == 0

    r = upload_revision(client, drawing_id, make_pdf_bytes([PDF_A4], mark_last_page=True), "rev2.pdf")
    assert r.status_code == 201
    rev = r.json()
    assert rev["sequence_number"] == 2
    assert rev["revision_label"] == "Revision 2"  # auto-generated from sequence
    assert pipeline_counter["runs"] == 0  # no pipeline work at upload time

    hist = client.get(f"/api/drawings/{drawing_id}/history").json()
    assert len(hist["consecutive_pairs"]) == 1
    assert hist["consecutive_pairs"][0]["has_comparison"] is False


def test_manual_compare_consecutive_and_non_consecutive(client, pipeline_counter):
    sizes = [[PDF_A4], [PDF_A4], [PDF_A4], [(595, 842)]]
    drawing_id, revs = create_drawing_with_revisions(client, sizes, labels=["Rev A", "Rev B", "Rev C", "Rev D"])
    assert pipeline_counter["runs"] == 0

    # Consecutive pair V1 vs V2 (first computation goes through a job)
    r = client.get(
        f"/api/drawings/{drawing_id}/compare",
        params={"from": revs[0]["revision_id"], "to": revs[1]["revision_id"]},
    )
    assert r.status_code == 202
    body = poll_job(client, r.json()["job_id"])["result"]
    assert body["old_revision_id"] == revs[0]["revision_id"]
    assert body["new_revision_id"] == revs[1]["revision_id"]
    assert body["was_cached"] is False
    assert pipeline_counter["runs"] == 1

    # Non-consecutive pair V1 vs V4
    r = client.get(
        f"/api/drawings/{drawing_id}/compare",
        params={"from": revs[0]["revision_id"], "to": revs[3]["revision_id"]},
    )
    assert r.status_code == 202
    assert poll_job(client, r.json()["job_id"])["result"]["new_revision_id"] == revs[3]["revision_id"]
    assert pipeline_counter["runs"] == 2

    hist = client.get(f"/api/drawings/{drawing_id}/history").json()
    flags = [p["has_comparison"] for p in hist["consecutive_pairs"]]
    assert flags == [True, False, False]  # only V1-V2 among consecutive pairs


def test_repeat_compare_returns_stored_result_without_rerun(client, pipeline_counter):
    drawing_id, revs = create_drawing_with_revisions(client, [[PDF_A4], [PDF_A4]])

    first_r = client.get(
        f"/api/drawings/{drawing_id}/compare",
        params={"from": revs[0]["revision_id"], "to": revs[1]["revision_id"]},
    )
    assert first_r.status_code == 202
    first = poll_job(client, first_r.json()["job_id"])["result"]
    assert pipeline_counter["runs"] == 1

    time.sleep(1.1)  # computed_at has second precision — would change if recomputed
    second = client.get(
        f"/api/drawings/{drawing_id}/compare",
        params={"from": revs[0]["revision_id"], "to": revs[1]["revision_id"]},
    ).json()

    assert second["was_cached"] is True
    assert second["comparison_id"] == first["comparison_id"]
    assert second["computed_at"] == first["computed_at"]
    assert second["pages"] == first["pages"]
    assert pipeline_counter["runs"] == 1  # pipeline did not execute again


def test_compare_without_params_defaults_to_two_most_recent(client, pipeline_counter):
    drawing_id, revs = create_drawing_with_revisions(client, [[PDF_A4], [PDF_A4], [PDF_A4]])

    r = client.get(f"/api/drawings/{drawing_id}/compare")  # no from/to
    assert r.status_code == 202
    body = poll_job(client, r.json()["job_id"])["result"]
    assert body["old_revision_id"] == revs[1]["revision_id"]
    assert body["new_revision_id"] == revs[2]["revision_id"]


# --------------------------------------------------------------- history

def test_history_ordered_by_sequence_not_label(client):
    drawing_id, revs = create_drawing_with_revisions(
        client,
        [[PDF_A4], [PDF_A4], [PDF_A4]],
        labels=["ZZZ-label", "AAA-label", "MMM-label"],
    )

    hist = client.get(f"/api/drawings/{drawing_id}/history").json()
    assert [r["sequence_number"] for r in hist["revisions"]] == [1, 2, 3]
    assert [r["revision_id"] for r in hist["revisions"]] == [r["revision_id"] for r in revs]
    labels = [r["revision_label"] for r in hist["revisions"]]
    assert labels == ["ZZZ-label", "AAA-label", "MMM-label"]  # order unaffected by label text
    assert len(hist["consecutive_pairs"]) == 2
    assert all(p["has_comparison"] is False for p in hist["consecutive_pairs"])


def test_rename_drawing_affects_nothing_else(client, pipeline_counter):
    drawing_id, revs = create_drawing_with_revisions(client, [[PDF_A4], [PDF_A4]])
    before = client.get(f"/api/drawings/{drawing_id}/history").json()

    r = client.patch(f"/api/drawings/{drawing_id}", json={"name": "Bracket Assembly DWG"})
    assert r.status_code == 200
    assert r.json()["name"] == "Bracket Assembly DWG"

    after = client.get(f"/api/drawings/{drawing_id}/history").json()
    assert after["name"] == "Bracket Assembly DWG"
    assert [r["revision_id"] for r in after["revisions"]] == [r["revision_id"] for r in before["revisions"]]
    assert [r["sequence_number"] for r in after["revisions"]] == [1, 2]
    assert after["consecutive_pairs"] == before["consecutive_pairs"]


# --------------------------------------------------- standalone regression

def test_standalone_compare_unaffected(client, pipeline_counter):
    before = len(client.get("/api/drawings").json()["drawings"])
    r = client.post(
        "/api/compare",
        files={
            "old_drawing": ("x.pdf", make_pdf_bytes([PDF_A4])),
            "new_drawing": ("y.pdf", make_pdf_bytes([PDF_A4], mark_last_page=True)),
        },
    )
    assert r.status_code == 202
    assert r.json()["job_id"]
    body = poll_job(client, r.json()["job_id"])["result"]
    assert body["report_id"]
    assert body["total_pages"] == 1
    assert "comparison_id" not in body  # no drawing concept leaked in

    after = len(client.get("/api/drawings").json()["drawings"])
    assert after == before  # standalone compare creates no drawings/revisions
    assert versioning_db.list_revisions("nonexistent") == []


# ------------------------------------------------------------- edge cases

def test_single_revision_history_and_compare_errors(client):
    drawing_id, revs = create_drawing_with_revisions(client, [[PDF_A4]])

    hist = client.get(f"/api/drawings/{drawing_id}/history").json()
    assert len(hist["revisions"]) == 1
    assert hist["consecutive_pairs"] == []  # no consecutive pairs to report

    r = client.get(f"/api/drawings/{drawing_id}/compare")
    assert r.status_code == 400
    assert "at least 2" in r.json()["detail"]

    r = client.get(f"/api/drawings/{drawing_id}/compare", params={"from": revs[0]["revision_id"], "to": revs[0]["revision_id"]})
    assert r.status_code == 400
    assert "itself" in r.json()["detail"]


def test_cross_drawing_compare_rejected(client):
    d1, revs1 = create_drawing_with_revisions(client, [[PDF_A4]])
    d2, revs2 = create_drawing_with_revisions(client, [[PDF_A4]])

    r = client.get(
        f"/api/drawings/{d1}/compare",
        params={"from": revs1[0]["revision_id"], "to": revs2[0]["revision_id"]},
    )
    assert r.status_code == 400
    assert "same drawing" in r.json()["detail"]


def test_missing_revision_and_drawing_rejected(client):
    d1, _ = create_drawing_with_revisions(client, [[PDF_A4], [PDF_A4]])

    r = client.get(f"/api/drawings/{d1}/compare", params={"from": "no-such-id", "to": "also-nope"})
    assert r.status_code == 404
    assert "not found" in r.json()["detail"]

    r = client.get("/api/drawings/no-such-drawing/history")
    assert r.status_code == 404

    r = client.get("/api/drawings/no-such-drawing/compare")
    assert r.status_code == 404

    r = upload_revision(client, "no-such-drawing", make_pdf_bytes([PDF_A4]), "x.pdf")
    assert r.status_code == 404


def test_concurrent_revisions_get_strict_sequence_numbers(client):
    d1, _ = create_drawing_with_revisions(client, [[PDF_A4]])
    drawing_id = d1
    data = make_pdf_bytes([PDF_A4])

    def upload(_):
        return versioning_db.create_revision(
            drawing_id=drawing_id,
            revision_label=None,
            page_count=1,
            file_reference="revisions/unused.pdf",
            original_filename="conc.pdf",
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(upload, range(8)))

    seqs = sorted(r["sequence_number"] for r in results)
    assert seqs == [2, 3, 4, 5, 6, 7, 8, 9]  # V1 pre-existed; no collisions, no gaps

    hist = client.get(f"/api/drawings/{drawing_id}/history").json()
    assert [r["sequence_number"] for r in hist["revisions"]] == list(range(1, 10))


def test_rapid_api_uploads_keep_order(client):
    r = client.post("/api/drawings", json={"name": "Rapid"})
    drawing_id = r.json()["drawing_id"]
    ids = []
    for i in range(6):
        rev = upload_revision(client, drawing_id, make_pdf_bytes([PDF_A4]), f"r{i}.pdf", label=f"L{i}")
        assert rev.status_code == 201
        ids.append(rev.json()["revision_id"])

    hist = client.get(f"/api/drawings/{drawing_id}/history").json()
    assert [r["revision_id"] for r in hist["revisions"]] == ids
    assert [r["sequence_number"] for r in hist["revisions"]] == [1, 2, 3, 4, 5, 6]
    assert [r["revision_label"] for r in hist["revisions"]] == ["L0", "L1", "L2", "L3", "L4", "L5"]


def test_page_size_mismatch_and_added_page_surface_in_revision_compare(client, pipeline_counter):
    drawing_id, revs = create_drawing_with_revisions(client, [[(300, 225)], [(450, 337)]])
    r = client.get(
        f"/api/drawings/{drawing_id}/compare",
        params={"from": revs[0]["revision_id"], "to": revs[1]["revision_id"]},
    )
    assert r.status_code == 202
    page = poll_job(client, r.json()["job_id"])["result"]["pages"][0]
    assert page["page_size_mismatch"] is True
    assert page["page_size_mismatch_details"]["width_diff_pct"] > 5

    # Added page: new revision has an extra page
    drawing_id2, revs2 = create_drawing_with_revisions(
        client, [[PDF_A4], [PDF_A4, PDF_A4]]
    )
    r = client.get(
        f"/api/drawings/{drawing_id2}/compare",
        params={"from": revs2[0]["revision_id"], "to": revs2[1]["revision_id"]},
    )
    assert r.status_code == 202
    statuses = [p["page_status"] for p in poll_job(client, r.json()["job_id"])["result"]["pages"]]
    assert "added" in statuses
    assert pipeline_counter["runs"] == 2


def test_alignment_failure_surfaces_in_revision_compare(client, pipeline_counter):
    # Featureless images cannot be aligned — existing AlignmentError handling
    # must surface (tiled mode + alignment error), same as standalone /compare.
    r = client.post(
        "/api/drawings/upload-and-compare",
        files={"old_drawing": ("a.png", make_png_bytes()), "new_drawing": ("b.png", make_png_bytes())},
    )
    assert r.status_code == 200
    page = r.json()["pages"][0]
    assert page["comparison_mode"] == "tiled"
    assert page["alignment_error"] is not None


# ---------------------------------------------------------- data integrity

def test_no_overwrite_on_duplicate_uploads(client):
    drawing_id, _ = create_drawing_with_revisions(client, [[PDF_A4]])
    data = make_pdf_bytes([PDF_A4])

    r1 = upload_revision(client, drawing_id, data, "same.pdf")
    r2 = upload_revision(client, drawing_id, data, "same.pdf")
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["revision_id"] != r2.json()["revision_id"]

    revisions = versioning_db.list_revisions(drawing_id)
    assert len(revisions) == 3
    refs = [r["file_reference"] for r in revisions]
    assert len(set(refs)) == 3  # distinct stored files, nothing overwritten
    from services import revision_storage
    for ref in refs:
        content = revision_storage.load_revision_file(ref)
        assert content.startswith(b"%PDF-")  # intact, loadable file
    # The two uploads sent identical bytes: both must be stored byte-for-byte.
    # (V1 is excluded: it was generated by a separate make_pdf_bytes call, and
    # MuPDF embeds unique IDs/timestamps, so its bytes legitimately differ.)
    dup_refs = [r["file_reference"] for r in revisions if r["sequence_number"] in (2, 3)]
    assert len(dup_refs) == 2
    for ref in dup_refs:
        assert revision_storage.load_revision_file(ref) == data


def test_comparisons_survive_restart(client, pipeline_counter):
    drawing_id, revs = create_drawing_with_revisions(client, [[PDF_A4], [(595, 842)]])
    first_r = client.get(
        f"/api/drawings/{drawing_id}/compare",
        params={"from": revs[0]["revision_id"], "to": revs[1]["revision_id"]},
    )
    assert first_r.status_code == 202
    first = poll_job(client, first_r.json()["job_id"])["result"]
    assert pipeline_counter["runs"] == 1

    # Simulate a server restart (re-running startup initializations)
    from model.report_db import init_db
    from model.versioning_db import init_versioning_db
    init_db()
    init_versioning_db()

    # History and stored comparison must still be fully queryable
    hist = client.get(f"/api/drawings/{drawing_id}/history").json()
    assert len(hist["revisions"]) == 2
    assert hist["consecutive_pairs"][0]["has_comparison"] is True

    again = client.get(
        f"/api/drawings/{drawing_id}/compare",
        params={"from": revs[0]["revision_id"], "to": revs[1]["revision_id"]},
    ).json()
    assert again["was_cached"] is True
    assert again["comparison_id"] == first["comparison_id"]
    assert again["pages"] == first["pages"]
    assert pipeline_counter["runs"] == 1  # nothing was recomputed after restart


def test_compare_via_revision_ids_never_accepts_files(client):
    """The drawing-scoped compare action takes revision IDs only; there is no
    file parameter on it (verified via the OpenAPI schema)."""
    schema = client.get("/openapi.json").json()
    compare = schema["paths"]["/api/drawings/{drawing_id}/compare"]
    assert set(compare.keys()) == {"get"}  # GET only, no POST/PUT
    get_op = compare["get"]
    assert "requestBody" not in get_op  # no file upload accepted on compare
    params = {p["name"] for p in get_op.get("parameters", [])}
    assert {"from", "to"} <= params


def test_delete_completed_report(client):
    """Test that standalone reports and linked reports can be deleted via DELETE /api/reports/{report_id}."""
    old_pdf = make_pdf_bytes([PDF_A4])
    new_pdf = make_pdf_bytes([PDF_A4], mark_last_page=True)

    r = client.post(
        "/api/compare",
        files={"old_drawing": ("a.pdf", old_pdf), "new_drawing": ("b.pdf", new_pdf)},
    )
    assert r.status_code == 202
    report_id = poll_job(client, r.json()["job_id"])["result"]["report_id"]

    reports_before = client.get("/api/reports").json()["reports"]
    assert any(rep["report_id"] == report_id for rep in reports_before)

    del_res = client.delete(f"/api/reports/{report_id}")
    assert del_res.status_code == 200

    reports_after = client.get("/api/reports").json()["reports"]
    assert not any(rep["report_id"] == report_id for rep in reports_after)

