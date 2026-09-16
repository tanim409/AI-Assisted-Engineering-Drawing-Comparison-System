"""Drawing version-history endpoints with authentication.
"""
import threading
import traceback
import uuid
from typing import Callable, Optional
from contextlib import contextmanager

import cv2
import numpy as np

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, UploadFile, Depends
from fastapi.responses import JSONResponse, Response

from schemas.drawing_schema import CreateDrawingRequest, RenameDrawingRequest
from services import comparison_engine, jobs, revision_storage, auth
from services.history_export import build_history_export_pdf
from services.pdf_pages import is_pdf_bytes, pdf_bytes_get_page_metadata, pdf_bytes_render_single_page
from services.report_data import get_full_report, get_page_status_map
from model import versioning_db


router = APIRouter()

DEFAULT_DRAWING_NAME = "Untitled Drawing"

_pair_locks: dict[tuple[str, str], list] = {}
_pair_locks_guard = threading.Lock()


@contextmanager
def acquire_pair_lock(old_revision_id: str, new_revision_id: str):
    key = (old_revision_id, new_revision_id)
    with _pair_locks_guard:
        if key not in _pair_locks:
            _pair_locks[key] = [threading.Lock(), 0]
        lock_info = _pair_locks[key]
        lock_info[1] += 1
    
    with lock_info[0]:
        try:
            yield
        finally:
            with _pair_locks_guard:
                lock_info[1] -= 1
                if lock_info[1] == 0:
                    del _pair_locks[key]


def _page_count_for_bytes(data: bytes, original_filename: str) -> int:
    if is_pdf_bytes(data):
        try:
            return len(pdf_bytes_get_page_metadata(data))
        except Exception:
            raise HTTPException(status_code=400, detail=f"File '{original_filename}' is not a valid PDF")
    return 1


async def _register_revision(drawing_id: str, file: UploadFile, revision_label: str | None, owner_user_id: int) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail=f"File '{file.filename}' is empty")

    page_count = _page_count_for_bytes(data, file.filename or "")
    revision_id = str(uuid.uuid4())
    file_reference = revision_storage.save_revision_file(revision_id, file.filename or "", data)
    revision = versioning_db.create_revision(
        drawing_id=drawing_id,
        revision_label=revision_label,
        page_count=page_count,
        file_reference=file_reference,
        original_filename=file.filename,
        owner_user_id=owner_user_id,
    )
    return revision


def _revision_response(revision: dict) -> dict:
    return {
        "revision_id": revision["revision_id"],
        "drawing_id": revision["drawing_id"],
        "sequence_number": revision["sequence_number"],
        "revision_label": revision["revision_label"],
        "uploaded_at": str(revision["uploaded_at"]),
        "page_count": revision["page_count"],
        "original_filename": revision["original_filename"],
    }


def _resolve_compare_pair(drawing_id: str, from_revision_id: str | None, to_revision_id: str | None, owner_user_id: int):
    if (from_revision_id is None) != (to_revision_id is None):
        raise HTTPException(status_code=400, detail="Parameters 'from' and 'to' must be provided together")

    if from_revision_id is not None:
        old_rev = versioning_db.get_revision(from_revision_id, owner_user_id=owner_user_id)
        if old_rev is None:
            raise HTTPException(status_code=404, detail=f"Revision '{from_revision_id}' not found or access denied")
        new_rev = versioning_db.get_revision(to_revision_id, owner_user_id=owner_user_id)
        if new_rev is None:
            raise HTTPException(status_code=404, detail=f"Revision '{to_revision_id}' not found or access denied")
        if old_rev["drawing_id"] != drawing_id or new_rev["drawing_id"] != drawing_id:
            raise HTTPException(status_code=400, detail="Both revisions must belong to the same drawing")
        if old_rev["revision_id"] == new_rev["revision_id"]:
            raise HTTPException(status_code=400, detail="Cannot compare a revision with itself")
        return old_rev, new_rev

    revisions = versioning_db.list_revisions(drawing_id, owner_user_id=owner_user_id)
    if len(revisions) < 2:
        raise HTTPException(
            status_code=400,
            detail=f"Drawing has {len(revisions)} revision(s); at least 2 are required to run a comparison",
        )
    return revisions[-2], revisions[-1]


def _has_failed_pages(comparison_id: str, owner_user_id: int) -> bool:
    return any(s["page_status"] == "failed" for s in get_page_status_map(comparison_id, owner_user_id=owner_user_id))


def _compare_revisions(
    drawing_id: str,
    old_rev: dict,
    new_rev: dict,
    owner_user_id: int,
    on_progress: Optional[Callable[[str], None]] = None,
) -> dict:
    with acquire_pair_lock(old_rev["revision_id"], new_rev["revision_id"]):
        existing = versioning_db.get_comparison_by_pair(old_rev["revision_id"], new_rev["revision_id"], owner_user_id=owner_user_id)
        if existing:
            if not _has_failed_pages(existing["comparison_id"], owner_user_id=owner_user_id):
                full = get_full_report(existing["comparison_id"], owner_user_id=owner_user_id)
                if full is not None:
                    return _comparison_response(existing, full, was_cached=True)

            try:
                old_bytes = revision_storage.load_revision_file(old_rev["file_reference"])
                new_bytes = revision_storage.load_revision_file(new_rev["file_reference"])
            except FileNotFoundError as e:
                raise HTTPException(status_code=410, detail=f"Stored revision file is missing: {e}")

            try:
                comparison_engine.run_comparison(
                    old_bytes, new_bytes,
                    result_id=existing["comparison_id"],
                    on_progress=on_progress,
                    resume=True,
                    owner_user_id=owner_user_id,
                )
            except Exception as e:
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"Comparison retry failed: {e}")

            full = get_full_report(existing["comparison_id"], owner_user_id=owner_user_id)
            return _comparison_response(existing, full, was_cached=False)

        try:
            old_bytes = revision_storage.load_revision_file(old_rev["file_reference"])
            new_bytes = revision_storage.load_revision_file(new_rev["file_reference"])
        except FileNotFoundError as e:
            raise HTTPException(status_code=410, detail=f"Stored revision file is missing: {e}")

        comparison_id = str(uuid.uuid4())
        try:
            comparison = versioning_db.create_comparison(
                drawing_id, old_rev["revision_id"], new_rev["revision_id"], comparison_id, owner_user_id=owner_user_id
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        try:
            document_report = comparison_engine.run_comparison(
                old_bytes, new_bytes, result_id=comparison["comparison_id"], on_progress=on_progress, owner_user_id=owner_user_id
            )
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Comparison pipeline failed: {e}")

        full = get_full_report(comparison["comparison_id"], owner_user_id=owner_user_id)
        return _comparison_response(comparison, full, was_cached=False)


def _comparison_response(comparison: dict, full_report: dict | None, was_cached: bool) -> dict:
    response = {
        "comparison_id": comparison["comparison_id"],
        "report_id": comparison["comparison_id"],
        "drawing_id": comparison["drawing_id"],
        "old_revision_id": comparison["old_revision_id"],
        "new_revision_id": comparison["new_revision_id"],
        "computed_at": str(comparison["computed_at"]),
        "was_cached": was_cached,
    }
    if full_report:
        response.update(full_report)
    return response


# ------------------------------------------------------------------ Flow A

@router.post("/drawings/upload-and-compare", tags=["Drawings"])
async def upload_and_compare(
    background_tasks: BackgroundTasks,
    old_drawing: UploadFile = File(...),
    new_drawing: UploadFile = File(...),
    name: str | None = Form(default=None),
    old_revision_label: str | None = Form(default=None),
    new_revision_label: str | None = Form(default=None),
    current_user: dict = Depends(auth.get_current_user),
):
    user_id = current_user["user_id"]
    default_name = name or (
        old_drawing.filename.rsplit(".", 1)[0] if old_drawing.filename else None
    ) or DEFAULT_DRAWING_NAME

    drawing = versioning_db.create_drawing(user_id, default_name)
    old_rev = await _register_revision(drawing["drawing_id"], old_drawing, old_revision_label, user_id)
    new_rev = await _register_revision(drawing["drawing_id"], new_drawing, new_revision_label, user_id)

    drawing_resp = {"drawing_id": drawing["drawing_id"], "name": drawing["name"], "created_at": str(drawing["created_at"])}
    revisions_resp = [_revision_response(old_rev), _revision_response(new_rev)]

    existing = versioning_db.get_comparison_by_pair(old_rev["revision_id"], new_rev["revision_id"], owner_user_id=user_id)
    if existing and not _has_failed_pages(existing["comparison_id"], owner_user_id=user_id):
        full = get_full_report(existing["comparison_id"], owner_user_id=user_id)
        if full is not None:
            result = _comparison_response(existing, full, was_cached=True)
            result["drawing"] = drawing_resp
            result["revisions"] = revisions_resp
            return JSONResponse(content=result)

    job = jobs.create_job(jobs.JOB_TYPE_DRAWING, owner_user_id=user_id, drawing_id=drawing["drawing_id"])
    background_tasks.add_task(_run_drawing_compare_job, job["job_id"], drawing["drawing_id"], old_rev, new_rev, user_id)
    return JSONResponse(status_code=202, content={
        "job_id": job["job_id"],
        "status": "pending",
        "drawing": drawing_resp,
        "revisions": revisions_resp,
    })


# ------------------------------------------------------- explicit management

@router.post("/drawings", tags=["Drawings"])
def create_drawing(payload: CreateDrawingRequest | None = None, current_user: dict = Depends(auth.get_current_user)):
    user_id = current_user["user_id"]
    name = payload.name if (payload and payload.name) else DEFAULT_DRAWING_NAME
    drawing = versioning_db.create_drawing(user_id, name)
    drawing["created_at"] = str(drawing["created_at"])
    return JSONResponse(content=drawing, status_code=201)


@router.get("/drawings", tags=["Drawings"])
def list_drawings(current_user: dict = Depends(auth.get_current_user)):
    user_id = current_user["user_id"]
    drawings = versioning_db.list_drawings(user_id)
    for d in drawings:
        d["created_at"] = str(d["created_at"])
    return JSONResponse(content={"drawings": drawings})


@router.patch("/drawings/{drawing_id}", tags=["Drawings"])
def rename_drawing(drawing_id: str, payload: RenameDrawingRequest, current_user: dict = Depends(auth.get_current_user)):
    user_id = current_user["user_id"]
    if versioning_db.get_drawing(drawing_id, owner_user_id=user_id) is None:
        raise HTTPException(status_code=404, detail=f"Drawing '{drawing_id}' not found or access denied")
    versioning_db.rename_drawing(drawing_id, payload.name, owner_user_id=user_id)
    updated = versioning_db.get_drawing(drawing_id, owner_user_id=user_id)
    updated["created_at"] = str(updated["created_at"])
    return JSONResponse(content=updated)


@router.delete("/drawings/{drawing_id}", tags=["Drawings"])
def delete_drawing(drawing_id: str, current_user: dict = Depends(auth.get_current_user)):
    user_id = current_user["user_id"]
    if versioning_db.get_drawing(drawing_id, owner_user_id=user_id) is None:
        raise HTTPException(status_code=404, detail=f"Drawing '{drawing_id}' not found or access denied")
    success = versioning_db.delete_drawing(drawing_id, owner_user_id=user_id)
    if not success:
        raise HTTPException(status_code=500, detail="Could not delete drawing")
    return JSONResponse(content={"status": "ok"})


# ------------------------------------------------------------------ Flow B

@router.post("/drawings/{drawing_id}/revisions", tags=["Drawings"])
async def register_revision(
    drawing_id: str,
    file: UploadFile = File(...),
    revision_label: str | None = Form(default=None),
    current_user: dict = Depends(auth.get_current_user),
):
    user_id = current_user["user_id"]
    if versioning_db.get_drawing(drawing_id, owner_user_id=user_id) is None:
        raise HTTPException(status_code=404, detail=f"Drawing '{drawing_id}' not found or access denied")
    revision = await _register_revision(drawing_id, file, revision_label, user_id)
    return JSONResponse(content=_revision_response(revision), status_code=201)


@router.delete("/drawings/{drawing_id}/revisions/{revision_id}", tags=["Drawings"])
def delete_revision(
    drawing_id: str,
    revision_id: str,
    current_user: dict = Depends(auth.get_current_user),
):
    user_id = current_user["user_id"]
    if versioning_db.get_drawing(drawing_id, owner_user_id=user_id) is None:
        raise HTTPException(status_code=404, detail=f"Drawing '{drawing_id}' not found or access denied")

    success = versioning_db.delete_revision(revision_id, owner_user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Revision '{revision_id}' not found")

    return JSONResponse(content={"message": "Revision deleted successfully"})


@router.get("/drawings/{drawing_id}/revisions/{revision_id}/render", tags=["Drawings"])
def render_drawing_revision(
    drawing_id: str,
    revision_id: str,
    page: int = Query(default=1, ge=1),
    dpi: float = Query(default=150.0, ge=30.0, le=600.0),
    current_user: dict = Depends(auth.get_current_user_or_query),
):
    user_id = current_user["user_id"]
    drawing = versioning_db.get_drawing(drawing_id, owner_user_id=user_id)
    if drawing is None:
        raise HTTPException(status_code=404, detail=f"Drawing '{drawing_id}' not found or access denied")

    revision = versioning_db.get_revision(revision_id, owner_user_id=user_id)
    if revision is None or revision["drawing_id"] != drawing_id:
        raise HTTPException(status_code=404, detail=f"Revision '{revision_id}' not found or access denied")

    try:
        data = revision_storage.load_revision_file(revision["file_reference"])
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Revision file bytes missing on disk")

    if is_pdf_bytes(data):
        try:
            page_dict = pdf_bytes_render_single_page(data, page_number=page, dpi=dpi)
            img = page_dict["image"]
            success, encoded = cv2.imencode(".png", img)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to encode rendered page image")
            return Response(content=encoded.tobytes(), media_type="image/png")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to render PDF page: {e}")
    else:
        # Standard image file (PNG/JPEG/TIFF/BMP)
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return Response(content=data, media_type="image/png")
        success, encoded = cv2.imencode(".png", img)
        if not success:
            return Response(content=data, media_type="image/png")
        return Response(content=encoded.tobytes(), media_type="image/png")


# --------------------------------------------------- compare within drawing

def _run_drawing_compare_job(job_id: str, drawing_id: str, old_rev: dict, new_rev: dict, owner_user_id: int) -> None:
    jobs.set_processing(job_id, "Starting comparison")

    def _on_progress(message: str) -> None:
        try:
            jobs.set_progress(job_id, message)
        except Exception:
            pass

    try:
        result = _compare_revisions(drawing_id, old_rev, new_rev, owner_user_id, on_progress=_on_progress)
        jobs.set_completed(job_id, result["comparison_id"],
                           was_cached=result.get("was_cached", False))
    except HTTPException as e:
        detail = e.detail if isinstance(e.detail, str) else "Comparison failed"
        jobs.set_failed(job_id, detail)
    except Exception:
        traceback.print_exc()
        jobs.set_failed(job_id, "An unexpected error occurred while running the comparison.")


@router.get("/drawings/{drawing_id}/compare", tags=["Drawings"])
def compare_drawing_revisions(
    drawing_id: str,
    background_tasks: BackgroundTasks,
    from_revision_id: str | None = Query(default=None, alias="from"),
    to_revision_id: str | None = Query(default=None, alias="to"),
    current_user: dict = Depends(auth.get_current_user),
):
    user_id = current_user["user_id"]
    if versioning_db.get_drawing(drawing_id, owner_user_id=user_id) is None:
        raise HTTPException(status_code=404, detail=f"Drawing '{drawing_id}' not found or access denied")
    old_rev, new_rev = _resolve_compare_pair(drawing_id, from_revision_id, to_revision_id, user_id)

    existing = versioning_db.get_comparison_by_pair(old_rev["revision_id"], new_rev["revision_id"], owner_user_id=user_id)
    if existing and not _has_failed_pages(existing["comparison_id"], owner_user_id=user_id):
        full = get_full_report(existing["comparison_id"], owner_user_id=user_id)
        if full is not None:
            return JSONResponse(content=_comparison_response(existing, full, was_cached=True))

    job = jobs.create_job(jobs.JOB_TYPE_DRAWING, owner_user_id=user_id, drawing_id=drawing_id)
    background_tasks.add_task(_run_drawing_compare_job, job["job_id"], drawing_id, old_rev, new_rev, user_id)
    return JSONResponse(status_code=202, content={"job_id": job["job_id"], "status": "pending"})


# ----------------------------------------------------------------- history

def _build_history(drawing_id: str, owner_user_id: int) -> dict:
    drawing = versioning_db.get_drawing(drawing_id, owner_user_id=owner_user_id)
    if drawing is None:
        raise HTTPException(status_code=404, detail=f"Drawing '{drawing_id}' not found or access denied")

    revisions = versioning_db.list_revisions(drawing_id, owner_user_id=owner_user_id)
    revisions_by_id = {r["revision_id"]: r for r in revisions}
    all_stored_comparisons = versioning_db.list_comparisons(drawing_id, owner_user_id=owner_user_id)

    all_comparisons = []
    for c in sorted(all_stored_comparisons, key=lambda x: str(x["computed_at"]), reverse=True):
        old_rev = revisions_by_id.get(c["old_revision_id"])
        new_rev = revisions_by_id.get(c["new_revision_id"])
        if old_rev and new_rev:
            all_comparisons.append({
                "old_revision_id": c["old_revision_id"],
                "new_revision_id": c["new_revision_id"],
                "old_sequence_number": old_rev["sequence_number"],
                "new_sequence_number": new_rev["sequence_number"],
                "has_comparison": True,
                "comparison_id": c["comparison_id"],
                "computed_at": str(c["computed_at"]),
            })

    comparisons_map = {
        (c["old_revision_id"], c["new_revision_id"]): c
        for c in all_stored_comparisons
    }

    consecutive_pairs = []
    for prev, nxt in zip(revisions, revisions[1:]):
        c = comparisons_map.get((prev["revision_id"], nxt["revision_id"]))
        consecutive_pairs.append({
            "old_revision_id": prev["revision_id"],
            "new_revision_id": nxt["revision_id"],
            "old_sequence_number": prev["sequence_number"],
            "new_sequence_number": nxt["sequence_number"],
            "has_comparison": c is not None,
            "comparison_id": c["comparison_id"] if c else None,
            "computed_at": str(c["computed_at"]) if c else None,
        })

    return {
        "drawing_id": drawing["drawing_id"],
        "name": drawing["name"],
        "created_at": str(drawing["created_at"]),
        "revisions": [_revision_response(r) for r in revisions],
        "consecutive_pairs": consecutive_pairs,
        "all_comparisons": all_comparisons,
    }


@router.get("/drawings/{drawing_id}/history", tags=["Drawings"])
def drawing_history(drawing_id: str, current_user: dict = Depends(auth.get_current_user)):
    return JSONResponse(content=_build_history(drawing_id, current_user["user_id"]))


@router.get("/drawings/{drawing_id}/history/export", tags=["Drawings"])
def export_drawing_history(drawing_id: str, current_user: dict = Depends(auth.get_current_user)):
    user_id = current_user["user_id"]
    history = _build_history(drawing_id, user_id)
    revisions_by_id = {r["revision_id"]: r for r in history["revisions"]}

    sections = []
    for pair in history["consecutive_pairs"]:
        old_rev = revisions_by_id[pair["old_revision_id"]]
        new_rev = revisions_by_id[pair["new_revision_id"]]
        section = {
            "old_sequence_number": old_rev["sequence_number"],
            "new_sequence_number": new_rev["sequence_number"],
            "old_label": old_rev["revision_label"],
            "new_label": new_rev["revision_label"],
            "old_original_filename": old_rev.get("original_filename"),
            "new_original_filename": new_rev.get("original_filename"),
            "old_uploaded_at": old_rev["uploaded_at"],
            "new_uploaded_at": new_rev["uploaded_at"],
            "similarity": None,
            "total_changes": None,
            "by_category": None,
            "note": None,
        }
        if pair["has_comparison"]:
            full = get_full_report(pair["comparison_id"], owner_user_id=user_id)
            pages = full["pages"] if full else []
            similarities = [p["overall_similarity"] for p in pages if p.get("overall_similarity") is not None]
            stored_changes = [c for p in pages for c in p.get("changes", [])]
            by_category = {}
            for change in stored_changes:
                cat = (change.get("classification") or {}).get("category") or "unknown"
                by_category[cat] = by_category.get(cat, 0) + 1
            avg_sim = (sum(similarities) / len(similarities)) if similarities else None
            if avg_sim is not None:
                sim_val = float(avg_sim)
                section["similarity"] = round(sim_val * 100, 1) if sim_val <= 1.0 else round(sim_val, 1)
            else:
                section["similarity"] = None
            section["total_changes"] = len(stored_changes)
            section["by_category"] = by_category
        else:
            section["note"] = (
                f"Rev {old_rev['sequence_number']} -> Rev {new_rev['sequence_number']}: "
                f"not yet compared"
            )
        sections.append(section)

    pdf_bytes = build_history_export_pdf(history, len(history["revisions"]), sections)
    safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in history["name"]) or "drawing"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="history-{safe_name}.pdf"'},
    )
