"""Async job status polling with auth protection.
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from model import versioning_db
from router.versioning import _comparison_response
from services import jobs, auth
from services.report_data import get_full_report


router = APIRouter()


@router.get("/jobs/{job_id}", tags=["Jobs"])
def get_job_status(job_id: str, current_user: dict = Depends(auth.get_current_user)):
    user_id = current_user["user_id"]
    job = jobs.get_job(job_id, owner_user_id=user_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found or access denied")

    status = job["status"]
    if status in (jobs.STATUS_PENDING, jobs.STATUS_PROCESSING):
        return JSONResponse(content={
            "job_id": job["job_id"],
            "status": status,
            "progress_message": job["progress_message"],
        })

    if status == jobs.STATUS_FAILED:
        return JSONResponse(content={
            "job_id": job["job_id"],
            "status": status,
            "error_message": job["error_message"],
        })

    if job["job_type"] == jobs.JOB_TYPE_DRAWING:
        comparison = versioning_db.get_comparison(job["result_id"], owner_user_id=user_id)
        if comparison is None:
            raise HTTPException(status_code=500, detail="Job result could not be retrieved.")
        full = get_full_report(job["result_id"], owner_user_id=user_id)
        was_cached = job["was_cached"]
        result = _comparison_response(
            comparison, full,
            was_cached=True if was_cached is None else bool(was_cached),
        )
    else:
        result = get_full_report(job["result_id"], owner_user_id=user_id)
        if result is None:
            raise HTTPException(status_code=500, detail="Job result could not be retrieved.")

    return JSONResponse(content={
        "job_id": job["job_id"],
        "status": status,
        "result": result,
    })
