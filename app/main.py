from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import cohort, graph, search

app = FastAPI(
    title="EHR Data Explorer",
    description="FHIR patient graph explorer — search clinical concepts and expand patient relationships",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, tags=["SEARCH"])
app.include_router(graph.router, tags=["GRAPH"])
app.include_router(cohort.router, tags=["COHORT"])

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@app.get("/health")
def health():
    return {"status": "ok"}


if FRONTEND_DIST.is_dir():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def serve_frontend():
        return FileResponse(FRONTEND_DIST / "index.html")
