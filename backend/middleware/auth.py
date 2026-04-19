"""API-key authentication middleware.

Reads the expected key from the GRAPHXPLOIT_API_KEY environment variable.
All /api/* requests must include the header  X-API-Key: <key>.

Paths that bypass auth (health + docs):
    /health, /, /docs, /redoc, /openapi.json

When GRAPHXPLOIT_API_KEY is not set the middleware passes every request through
so that development with `uvicorn backend.main:app` still works — the CLI
always injects the key before starting uvicorn.
"""

import os
import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

log = logging.getLogger("graphxploit.auth")

# Paths that never require auth
_SKIP_PREFIXES = {"/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Reject /api/* requests that do not carry a valid X-API-Key header."""

    async def dispatch(self, request: Request, call_next):
        expected_key = os.environ.get("GRAPHXPLOIT_API_KEY", "")

        # No key configured → development mode, let everything through.
        if not expected_key:
            return await call_next(request)

        # Whitelisted paths → always allow.
        path = request.url.path
        if path in _SKIP_PREFIXES or not path.startswith("/api"):
            return await call_next(request)

        provided_key = request.headers.get("X-API-Key", "")
        if provided_key != expected_key:
            log.warning(
                "Rejected request to %s from %s — invalid or missing X-API-Key",
                path,
                request.client.host if request.client else "unknown",
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized. Provide a valid X-API-Key header."},
            )

        return await call_next(request)
