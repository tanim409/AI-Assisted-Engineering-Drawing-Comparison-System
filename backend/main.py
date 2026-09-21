from dotenv import load_dotenv
load_dotenv()
import services.config  # Loads .env variables
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from model.report_db import init_db
from model.versioning_db import init_versioning_db
from router.auth import router as auth_router
from router.drawings import router as compare_drawings
from router.jobs import router as jobs_router
from router.versioning import router as versioning_router
from router.payment import router as payment_router
from services import jobs
from services.env_config import validate_environment


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_environment()
    try:
        init_db()
        init_versioning_db()
        stale = jobs.mark_stale_jobs_failed()
        if stale:
            print(f"[startup] Marked {stale} stale job(s) as failed after restart")
    except Exception as e:
        print(f"[startup ERROR] Failed to initialize database tables: {e}")
    yield


app = FastAPI(title="Engineering Drawing Comparison Application", lifespan=lifespan)

allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]
frontend_env = os.getenv("FRONTEND_URL", "").rstrip("/")
if frontend_env:
    allowed_origins.append(frontend_env)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://[a-zA-Z0-9-]+\.onrender\.com$|^https?://localhost:\d+$|^https?://127\.0\.0\.1:\d+$",
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(compare_drawings, prefix="/api", tags=["Drawings"])
app.include_router(versioning_router, prefix="/api", tags=["Drawings"])
app.include_router(jobs_router, prefix="/api", tags=["Jobs"])
app.include_router(payment_router, prefix="/api", tags=["Payment"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}


@app.get("/api/health", tags=["Health"])
async def api_health():
    return {"status": "ok"}


frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    # Catch-all route to serve React's index.html for SPA routing
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Ignore API and Auth routes so they return proper 404s instead of the React app
        if full_path.startswith("api/") or full_path.startswith("auth/"):
            raise HTTPException(status_code=404, detail="Not Found")
            
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        
        return FileResponse(os.path.join(frontend_dist, "index.html"))
