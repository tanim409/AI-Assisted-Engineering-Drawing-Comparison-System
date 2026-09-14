import uuid
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, BackgroundTasks, UploadFile, File, HTTPException, Query, Depends
from fastapi.responses import JSONResponse, Response

from schemas.drawing_schema import AskRequest, ChangeReviewRequest
from services import comparison_engine, jobs, annotate, auth
from services.change_reviews import (
    build_review_summary, ensure_change_exists, get_change_review, upsert_change_review,
)
from services.report_data import (
    get_report, get_full_report, get_full_report_by_hash, get_annotated_export_pages, _compute_content_hash,
)
from services.history_export import build_summary_export_pdf, build_history_export_pdf
from services.revision_storage import load_revision_file


router = APIRouter()


def _run_standalone_compare_job(job_id: str, old_bytes: bytes, new_bytes: bytes, owner_user_id: int) -> None:
    jobs.set_processing(job_id, "Starting comparison")

    def _on_progress(message: str) -> None:
        try:
            jobs.set_progress(job_id, message)
        except Exception:
            pass

    try:
        content_hash = _compute_content_hash(old_bytes, new_bytes)
        existing = get_full_report_by_hash(content_hash, owner_user_id=owner_user_id)
        if existing:
            jobs.set_completed(job_id, existing["report_id"])
            return

        report_id = str(uuid.uuid4())
        comparison_engine.run_comparison(
            old_bytes, new_bytes, result_id=report_id, on_progress=_on_progress, owner_user_id=owner_user_id
        )
        if get_full_report(report_id, owner_user_id=owner_user_id) is None:
            hit = get_full_report_by_hash(content_hash, owner_user_id=owner_user_id)
            if hit is not None:
                jobs.set_completed(job_id, hit["report_id"])
                return
            jobs.set_failed(job_id, "Comparison finished but its result could not be retrieved.")
            return
        jobs.set_completed(job_id, report_id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        jobs.set_failed(job_id, f"Comparison failed: {e}")


@router.post("/compare")
async def compare_drawings(
    background_tasks: BackgroundTasks,
    old_drawing: UploadFile = File(...),
    new_drawing: UploadFile = File(...),
    current_user: dict = Depends(auth.get_current_user),
):
    try:
        old_bytes = await old_drawing.read()
        new_bytes = await new_drawing.read()
        if not old_bytes:
            raise HTTPException(status_code=400, detail=f"File '{old_drawing.filename}' is empty")
        if not new_bytes:
            raise HTTPException(status_code=400, detail=f"File '{new_drawing.filename}' is empty")

        job = jobs.create_job(jobs.JOB_TYPE_STANDALONE, owner_user_id=current_user["user_id"])
        background_tasks.add_task(_run_standalone_compare_job, job["job_id"], old_bytes, new_bytes, current_user["user_id"])
        return JSONResponse(status_code=202, content={"job_id": job["job_id"], "status": "pending"})

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Exception in /compare: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask")
async def ask_question(payload: AskRequest, current_user: dict = Depends(auth.get_current_user)):
    changes = get_report(payload.report_id, owner_user_id=current_user["user_id"])
    if changes is None:
        raise HTTPException(status_code=404, detail="Report not found or access denied")

    from services.qa import answer_question
    result = answer_question(changes, payload.question)
    return JSONResponse(content=result)


@router.get("/reports")
async def list_completed_reports(current_user: dict = Depends(auth.get_current_user)):
    from services.report_data import list_user_reports
    return JSONResponse(content={"reports": list_user_reports(current_user["user_id"])})


@router.get("/reports/{report_id}")
async def get_completed_report(report_id: str, current_user: dict = Depends(auth.get_current_user)):
    report = get_full_report(report_id, owner_user_id=current_user["user_id"])
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found or access denied")
    return JSONResponse(content=report)


@router.delete("/reports/{report_id}")
async def delete_completed_report(report_id: str, current_user: dict = Depends(auth.get_current_user)):
    from services.report_data import delete_report
    success = delete_report(report_id, owner_user_id=current_user["user_id"])
    if not success:
        raise HTTPException(status_code=404, detail="Report not found or access denied")
    return JSONResponse(content={"status": "ok", "message": "Report deleted successfully"})



def _ensure_review_target(report_id: str, page_number: int, change_index: int, owner_user_id: int) -> None:
    try:
        ensure_change_exists(report_id, page_number, change_index, owner_user_id=owner_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/reports/{report_id}/changes/{page_number}/{change_index}/review")
async def review_change(
    report_id: str, page_number: int, change_index: int, payload: ChangeReviewRequest,
    current_user: dict = Depends(auth.get_current_user),
):
    _ensure_review_target(report_id, page_number, change_index, current_user["user_id"])
    return JSONResponse(content=upsert_change_review(
        report_id, page_number, change_index, payload.status, payload.note, payload.reviewer_id, owner_user_id=current_user["user_id"]
    ))


@router.get("/reports/{report_id}/changes/{page_number}/{change_index}/review")
async def get_review(report_id: str, page_number: int, change_index: int, current_user: dict = Depends(auth.get_current_user)):
    _ensure_review_target(report_id, page_number, change_index, current_user["user_id"])
    return JSONResponse(content=get_change_review(report_id, page_number, change_index, owner_user_id=current_user["user_id"]))


@router.get("/reports/{report_id}/reviews/summary")
async def get_reviews_summary(report_id: str, current_user: dict = Depends(auth.get_current_user)):
    report = get_full_report(report_id, owner_user_id=current_user["user_id"])
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found or access denied")
    return JSONResponse(content=build_review_summary(report_id, report["pages"]))


@router.get("/reports/{report_id}/annotated")
async def export_annotated_report(
    report_id: str,
    format: str = Query("png", regex="^(png|pdf)$"),
    page: Optional[int] = Query(None, description="Page number (1-based) for PNG export; ignored for PDF"),
    current_user: dict = Depends(auth.get_current_user),
):
    report = get_full_report(report_id, owner_user_id=current_user["user_id"])
    if not report:
        raise HTTPException(status_code=404, detail="Report not found or access denied")

    pages = get_annotated_export_pages(report_id, owner_user_id=current_user["user_id"])
    if not pages:
        raise HTTPException(status_code=400, detail="Report has no pages")

    annotated_images = []

    for i, report_page in enumerate(pages):
        changes = report_page.get("changes", [])
        source_png = report_page.get("annotated_source_png")
        if source_png:
            annotated_images.append(
                annotate.render_annotated_page(changes, {"image_bytes": source_png})
            )

    if not annotated_images:
        raise HTTPException(
            status_code=501,
            detail="Could not reconstruct page images for annotation. Report may be missing image data."
        )

    if format == "png":
        if page is None:
            if len(annotated_images) == 1:
                page = 1
            else:
                raise HTTPException(status_code=400, detail="?page= is required for PNG export of a multi-page report")
        if not (1 <= page <= len(annotated_images)):
            raise HTTPException(status_code=404, detail="Page index out of range")
        png_bytes = annotate.export_annotated_png(annotated_images[page - 1])
        return Response(content=png_bytes, media_type="image/png",
                        headers={"Content-Disposition": f"attachment; filename=annotated_{report_id}_page_{page}.png"})
    else:
        pdf_bytes = annotate.export_annotated_pdf(annotated_images)
        return Response(content=pdf_bytes, media_type="application/pdf",
                        headers={"Content-Disposition": f"attachment; filename=annotated_{report_id}.pdf"})


@router.get("/reports/{report_id}/summary-pdf")
async def export_summary_pdf(report_id: str, current_user: dict = Depends(auth.get_current_user)):
    """Clean, text-only PDF summary report (no page image rendering or bounding box overlays required)."""
    report = get_full_report(report_id, owner_user_id=current_user["user_id"])
    if not report:
        raise HTTPException(status_code=404, detail="Report not found or access denied")

    pdf_bytes = build_summary_export_pdf(report)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=comparison_summary_{report_id}.pdf"},
    )

