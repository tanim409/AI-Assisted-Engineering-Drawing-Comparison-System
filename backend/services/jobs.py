"""Async job tracking for long-running comparisons in MySQL.
"""
import uuid
from typing import Any, Dict, List, Optional
from model.db import connect

JOB_TYPE_STANDALONE = "standalone_compare"
JOB_TYPE_DRAWING = "drawing_compare"

STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

_VALID_TYPES = (JOB_TYPE_STANDALONE, JOB_TYPE_DRAWING)
_TERMINAL = (STATUS_COMPLETED, STATUS_FAILED)


def create_job(job_type: str, owner_user_id: int = 1, drawing_id: Optional[str] = None) -> Dict[str, Any]:
    if job_type not in _VALID_TYPES:
        raise ValueError(f"Unknown job_type: {job_type}")
    job_id = str(uuid.uuid4())
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO jobs (job_id, owner_user_id, job_type, status, drawing_id, created_at, updated_at)
                VALUES (%s, %s, %s, 'pending', %s, NOW(), NOW())
                """,
                (job_id, owner_user_id, job_type, drawing_id),
            )
    return get_job(job_id, owner_user_id=owner_user_id)


def get_job(job_id: str, owner_user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    with connect() as conn:
        with conn.cursor() as cursor:
            if owner_user_id is not None:
                cursor.execute("SELECT * FROM jobs WHERE job_id = %s AND owner_user_id = %s", (job_id, owner_user_id))
            else:
                cursor.execute("SELECT * FROM jobs WHERE job_id = %s", (job_id,))
            row = cursor.fetchone()
    return dict(row) if row else None


def list_jobs(status: Optional[str] = None, owner_user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    with connect() as conn:
        with conn.cursor() as cursor:
            query = "SELECT * FROM jobs WHERE 1=1"
            params = []
            if owner_user_id is not None:
                query += " AND owner_user_id = %s"
                params.append(owner_user_id)
            if status:
                query += " AND status = %s"
                params.append(status)
            query += " ORDER BY created_at DESC, job_id"
            cursor.execute(query, params)
            rows = cursor.fetchall()
    return [dict(r) for r in rows]


def set_processing(job_id: str, message: Optional[str] = None, owner_user_id: Optional[int] = None) -> None:
    with connect() as conn:
        with conn.cursor() as cursor:
            if owner_user_id is not None:
                cursor.execute(
                    """
                    UPDATE jobs
                    SET status = 'processing', progress_message = %s, updated_at = NOW()
                    WHERE job_id = %s AND owner_user_id = %s AND status IN ('pending', 'processing')
                    """,
                    (message, job_id, owner_user_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE jobs
                    SET status = 'processing', progress_message = %s, updated_at = NOW()
                    WHERE job_id = %s AND status IN ('pending', 'processing')
                    """,
                    (message, job_id),
                )


def set_progress(job_id: str, message: str, owner_user_id: Optional[int] = None) -> None:
    with connect() as conn:
        with conn.cursor() as cursor:
            if owner_user_id is not None:
                cursor.execute(
                    """
                    UPDATE jobs
                    SET progress_message = %s, updated_at = NOW()
                    WHERE job_id = %s AND owner_user_id = %s AND status IN ('pending', 'processing')
                    """,
                    (message, job_id, owner_user_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE jobs
                    SET progress_message = %s, updated_at = NOW()
                    WHERE job_id = %s AND status IN ('pending', 'processing')
                    """,
                    (message, job_id),
                )


def set_completed(job_id: str, result_id: str, was_cached: Optional[bool] = None, owner_user_id: Optional[int] = None) -> None:
    with connect() as conn:
        with conn.cursor() as cursor:
            if owner_user_id is not None:
                cursor.execute(
                    """
                    UPDATE jobs
                    SET status = 'completed', result_id = %s, was_cached = %s, progress_message = NULL, updated_at = NOW()
                    WHERE job_id = %s AND owner_user_id = %s AND status IN ('pending', 'processing')
                    """,
                    (result_id, None if was_cached is None else int(was_cached), job_id, owner_user_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE jobs
                    SET status = 'completed', result_id = %s, was_cached = %s, progress_message = NULL, updated_at = NOW()
                    WHERE job_id = %s AND status IN ('pending', 'processing')
                    """,
                    (result_id, None if was_cached is None else int(was_cached), job_id),
                )


def set_failed(job_id: str, error_message: str, owner_user_id: Optional[int] = None) -> None:
    with connect() as conn:
        with conn.cursor() as cursor:
            if owner_user_id is not None:
                cursor.execute(
                    """
                    UPDATE jobs
                    SET status = 'failed', error_message = %s, progress_message = NULL, updated_at = NOW()
                    WHERE job_id = %s AND owner_user_id = %s AND status IN ('pending', 'processing')
                    """,
                    (error_message, job_id, owner_user_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE jobs
                    SET status = 'failed', error_message = %s, progress_message = NULL, updated_at = NOW()
                    WHERE job_id = %s AND status IN ('pending', 'processing')
                    """,
                    (error_message, job_id),
                )


def mark_stale_jobs_failed(owner_user_id: Optional[int] = None) -> int:
    with connect() as conn:
        with conn.cursor() as cursor:
            query = """
                UPDATE jobs
                SET status = 'failed',
                    error_message = 'Server restarted while this job was running; please resubmit.',
                    progress_message = NULL,
                    updated_at = NOW()
                WHERE status IN ('pending', 'processing')
            """
            params = []
            if owner_user_id is not None:
                query += " AND owner_user_id = %s"
                params.append(owner_user_id)
            cursor.execute(query, params)
            return cursor.rowcount
