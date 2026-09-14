from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from model.report_db import init_db
from model.versioning_db import init_versioning_db
from router.auth import router as auth_router
from router.drawings import router as compare_drawings
from router.jobs import router as jobs_router
from router.versioning import router as versioning_router
from router.payment import router as payment_router
from services import jobs

app = FastAPI(title="Engineering Drawing Comparison Application")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from services.env_config import validate_environment

@app.on_event("startup")
def startup():
    validate_environment()
    try:
        init_db()
        init_versioning_db()
        stale = jobs.mark_stale_jobs_failed()
        if stale:
            print(f"[startup] Marked {stale} stale job(s) as failed after restart")
    except Exception as e:
        print(f"[startup ERROR] Failed to initialize MySQL tables: {e}")

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(compare_drawings, prefix="/api", tags=["Drawings"])
app.include_router(versioning_router, prefix="/api", tags=["Drawings"])
app.include_router(jobs_router, prefix="/api", tags=["Jobs"])
app.include_router(payment_router, prefix="/api", tags=["Payment"])

import os
from fastapi.staticfiles import StaticFiles

frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")
