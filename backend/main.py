import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.db.database import get_db, close_db
from backend.routers import profile, tailor, jobs, export, saved_cvs
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
app.include_router(saved_cvs.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "godcv"}


@app.get("/api/usage")
async def get_usage():
    from backend.services.gemini import get_usage as _get_usage
    return _get_usage()


@app.get("/api/models")
async def list_models():
    """List available Gemini models for the configured API key."""
    import httpx
    from backend.services.gemini import _usage
    from backend.config import GEMINI_BASE_URL, GEMINI_API_KEY
    from backend.services import profile as profile_service
    profile = await profile_service.get_profile()
    api_key = (profile.get("gemini_api_key", "") if profile else "") or GEMINI_API_KEY
    if not api_key:
        return {"models": [], "current": _usage.get("model", ""), "error": "No API key configured"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{GEMINI_BASE_URL}/models?key={api_key}")
            if resp.status_code != 200:
                return {"models": [], "current": _usage.get("model", ""), "error": f"API error {resp.status_code}"}
            data = resp.json()
            models = []
            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                if "generateContent" in str(m.get("supportedGenerationMethods", [])):
                    models.append({
                        "id": name,
                        "displayName": m.get("displayName", name),
                        "inputTokenLimit": m.get("inputTokenLimit", 0),
                        "outputTokenLimit": m.get("outputTokenLimit", 0),
                    })
            return {"models": models, "current": _usage.get("model", "")}
    except Exception as e:
        return {"models": [], "current": _usage.get("model", ""), "error": str(e)}


@app.post("/api/models/select")
async def select_model(body: dict):
    """Set the active model."""
    from backend.services.gemini import _usage
    model_id = body.get("model", "")
    if model_id:
        _usage["model"] = model_id
    return {"current": _usage.get("model", "")}


# Serve frontend (production)
dist_path = Path(FRONTEND_DIST)
if dist_path.exists() and (dist_path / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(dist_path / "assets")), name="static")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            return {"detail": "Not found"}
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
