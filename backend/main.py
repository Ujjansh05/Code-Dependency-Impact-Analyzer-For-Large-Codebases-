"""FastAPI application entry point."""

import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.routes import analyze, upload, graph, code
from backend.routes import projects as projects_route
from backend.routes import models as models_route

app = FastAPI(
    title="GraphXploit",
    description="Analyze code dependencies and predict the impact of changes using AST parsing, TigerGraph, and pluggable LLMs.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api", tags=["Analysis"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(graph.router, prefix="/api", tags=["Graph"])
app.include_router(code.router, prefix="/api", tags=["Code Editor"])
app.include_router(projects_route.router, prefix="/api", tags=["Projects"])
app.include_router(models_route.router, prefix="/api", tags=["Models"])


@app.get("/health", tags=["Health"])
async def health():
    """Detailed health check including active model status."""
    model_info = None
    model_healthy = False

    try:
        from llm.model_registry import get_active_config
        from llm.adapters import create_adapter

        config = get_active_config()
        if config:
            model_info = {
                "name": config.name,
                "provider": config.provider,
                "model_name": config.model_name,
            }
            adapter = create_adapter(
                provider=config.provider,
                base_url=config.base_url or None,
                model_name=config.model_name or None,
                api_key=config.api_key or None,
            )
            model_healthy = adapter.check_health()
    except (ImportError, ConnectionError, OSError) as exc:
        import logging
        logging.getLogger("graphxploit.backend").debug("Health check model probe failed: %s", exc)

    return {
        "api": "ok",
        "model": {
            "status": "ok" if model_healthy else "unavailable",
            "info": model_info,
        },
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
            "service": "GraphXploit",
            "docs": "/docs",
            "note": "Frontend is not built. Run 'npm run build' in the frontend directory."
        }
