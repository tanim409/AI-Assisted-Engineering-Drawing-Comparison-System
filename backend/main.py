import services.config  # MUST be first to load .env variables
import os

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

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:5173", "http://localhost:3000"],
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
from fastapi.responses import FileResponse
from fastapi import Request

frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    # Catch-all route to serve React's index.html for SPA routing
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Ignore API and Auth routes so they return proper 404s instead of the React app
        if full_path.startswith("api/") or full_path.startswith("auth/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not Found")
            
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        
        return FileResponse(os.path.join(frontend_dist, "index.html"))
