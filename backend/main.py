import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.db.database import get_db, close_db
from backend.routers import profile, tailor, jobs, export
from backend.config import FRONTEND_DIST

logger = logging.getLogger("godcv.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting GodCV — initializing database")
    await get_db()
    yield
    logger.info("Shutting down GodCV")
    await close_db()


app = FastAPI(title="GodCV", version="1.0.0", lifespan=lifespan)

# CORS for dev mode
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(profile.router)
app.include_router(tailor.router)
app.include_router(jobs.router)
app.include_router(export.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "godcv"}


# Serve frontend (production)
dist_path = Path(FRONTEND_DIST)
if dist_path.exists() and (dist_path / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(dist_path / "assets")), name="static")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = dist_path / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(dist_path / "index.html")
else:
    from fastapi.responses import HTMLResponse

    @app.get("/")
    async def no_frontend():
        return HTMLResponse(
            "<h2>GodCV API is running</h2>"
            "<p>Frontend not built yet. Run:</p>"
            "<pre>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</pre>"
            "<p>Then restart the server. Or run the frontend dev server separately:</p>"
            "<pre>cd frontend &amp;&amp; npm run dev</pre>"
            f"<p><small>Looking for dist at: {dist_path}</small></p>",
            status_code=200,
        )
