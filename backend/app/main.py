from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.api.routes import router

app = FastAPI(
    title="QueryMind",
    version="1.1.0",
    description="Natural language to SQL pipeline with self-correction.",
)

app.include_router(router)

# Keep API routes before the static mount so /query, /health, and /docs work.
app.mount("/", StaticFiles(directory=Path(__file__).parent / "web", html=True), name="workspace")
