"""FastAPI application entry point."""

import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.routes import analyze, upload, graph, code
from backend.routes import projects as projects_route

app = FastAPI(
    title="Code Dependency Impact Analyzer",
    description="Analyze code dependencies and predict the impact of changes using AST parsing, TigerGraph, and LLaMA.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api", tags=["Analysis"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(graph.router, prefix="/api", tags=["Graph"])
app.include_router(code.router, prefix="/api", tags=["Code Editor"])
app.include_router(projects_route.router, prefix="/api", tags=["Projects"])


@app.get("/health", tags=["Health"])
async def health():
    """Detailed health check."""
    from llm.llama_client import check_health as llm_health

    return {
        "api": "ok",
        "ollama": "ok" if llm_health() else "unavailable",
    }


# Serve static files from frontend/dist if it exists
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")
else:
    @app.get("/", tags=["Health"])
    async def root():
        """Health check / welcome endpoint when frontend is not built."""
        return {
            "status": "ok",
            "service": "Code Dependency Impact Analyzer",
            "docs": "/docs",
            "note": "Frontend is not built. Run 'npm run build' in the frontend directory."
        }
