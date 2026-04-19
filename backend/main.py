"""FastAPI application entry point."""

import os
import sys
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.routes import analyze, upload, graph, code
from backend.routes import projects as projects_route
from backend.routes import models as models_route
from backend.middleware.auth import APIKeyMiddleware

log = logging.getLogger("graphxploit.backend")

# ── Mode detection ────────────────────────────────────────────────────────────
# Set GRAPHXPLOIT_DEV=true ONLY in local development.  The CLI sets this
# automatically when --dev is passed to `graphxploit serve`.
_is_dev = os.getenv("GRAPHXPLOIT_DEV", "false").strip().lower() == "true"

# ── FastAPI instance ──────────────────────────────────────────────────────────
app = FastAPI(
    title="GraphXploit",
    description=(
        "Analyze code dependencies and predict the impact of changes "
        "using AST parsing, TigerGraph, and pluggable LLMs."
    ),
    version="2.0.0",
    # Disable interactive docs in production (VULN-008)
    docs_url="/docs" if _is_dev else None,
    redoc_url="/redoc" if _is_dev else None,
    openapi_url="/openapi.json" if _is_dev else None,
)


# ── Security headers ──────────────────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach basic security headers to every HTTP response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Cache-Control", "no-store")
        return response


app.add_middleware(SecurityHeadersMiddleware)

# ── API-Key authentication (VULN-004) ─────────────────────────────────────────
# Reads GRAPHXPLOIT_API_KEY from the environment.  The CLI injects this before
# starting uvicorn so users never have to configure it manually.
app.add_middleware(APIKeyMiddleware)

# ── CORS (VULN-003) ───────────────────────────────────────────────────────────
# Default: allow only the local Vite dev server.
# Override with CORS_ORIGINS=https://myapp.example.com in production.
_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(analyze.router, prefix="/api", tags=["Analysis"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(graph.router, prefix="/api", tags=["Graph"])
app.include_router(code.router, prefix="/api", tags=["Code Editor"])
app.include_router(projects_route.router, prefix="/api", tags=["Projects"])
app.include_router(models_route.router, prefix="/api", tags=["Models"])


# ── Health check (no auth required) ─────────────────────────────────────────
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
        log.debug("Health check model probe failed: %s", exc)

    return {
        "api": "ok",
        "model": {
            "status": "ok" if model_healthy else "unavailable",
            "info": model_info,
        },
    }


# ── Static frontend ───────────────────────────────────────────────────────────
# When the React app has been built (`npm run build`), serve it from /
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")
else:
    @app.get("/", tags=["Health"])
    async def root():
        """Welcome endpoint when the frontend has not been built yet."""
        return {
            "status": "ok",
            "service": "GraphXploit",
            "note": "Frontend is not built. Run 'npm run build' in the frontend directory.",
        }
