"""GET /api/file and PUT /api/file endpoints for reading and modifying source code.

Security: all file access is sandboxed to the UPLOAD_ROOT directory so that
callers cannot perform path-traversal attacks to read/write arbitrary files.
"""

import logging
import pathlib

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

log = logging.getLogger("graphxploit.code")

router = APIRouter()

# ── Allowed root ────────────────────────────────────────────────────────────
# All file operations are restricted to this directory tree.
UPLOAD_ROOT = pathlib.Path("data") / "uploaded_code"


def _safe_resolve(raw_path: str) -> pathlib.Path:
    """Resolve *raw_path* relative to UPLOAD_ROOT and assert it stays inside.

    The client may send either:
      • a bare filename / relative path  ("mymodule/utils.py")
      • an absolute path that includes the upload root

    In both cases we strip any leading UPLOAD_ROOT prefix so the result is
    always anchored inside UPLOAD_ROOT, preventing path-traversal.

    Raises HTTP 400 for empty/null paths and HTTP 403 for escape attempts.
    """
    if not raw_path or not raw_path.strip():
        raise HTTPException(status_code=400, detail="Path must not be empty.")

    upload_root = UPLOAD_ROOT.resolve()

    # Treat the path as potentially absolute.
    candidate = pathlib.Path(raw_path)

    # If the client sent an absolute path that starts with the upload root,
    # make it relative so the join below still works.
    try:
        relative = candidate.relative_to(upload_root)
    except ValueError:
        # Not already rooted at upload_root — treat as relative.
        relative = candidate

    # Resolve the final absolute path and check containment.
    try:
        resolved = (upload_root / relative).resolve()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path.")

    if not resolved.is_relative_to(upload_root):
        log.warning("Path traversal attempt blocked: %s → %s", raw_path, resolved)
        raise HTTPException(status_code=403, detail="Access denied: path is outside the upload directory.")

    return resolved


# ── Pydantic schema ──────────────────────────────────────────────────────────

class FileUpdateRequest(BaseModel):
    content: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/file")
async def get_file_content(path: str):
    """Retrieve the text content of a source file (sandboxed to upload directory)."""
    safe = _safe_resolve(path)

    if not safe.exists():
        raise HTTPException(status_code=404, detail="File not found.")

    if not safe.is_file():
        raise HTTPException(status_code=400, detail="Path is not a regular file.")

    try:
        content = safe.read_text(encoding="utf-8")
        # Return the path relative to upload root so the client never sees server internals.
        return {"content": content, "path": str(safe.relative_to(UPLOAD_ROOT.resolve()))}
    except Exception:
        log.exception("Failed to read file: %s", safe)
        raise HTTPException(status_code=500, detail="Failed to read file.")


@router.put("/file")
async def update_file_content(path: str, request: FileUpdateRequest):
    """Modify the text content of a source file (sandboxed to upload directory)."""
    safe = _safe_resolve(path)

    if not safe.exists():
        raise HTTPException(status_code=404, detail="File not found.")

    if not safe.is_file():
        raise HTTPException(status_code=400, detail="Path is not a regular file.")

    try:
        safe.write_text(request.content, encoding="utf-8")
        return {
            "status": "ok",
            "message": "File updated successfully.",
            "path": str(safe.relative_to(UPLOAD_ROOT.resolve())),
        }
    except Exception:
        log.exception("Failed to write file: %s", safe)
        raise HTTPException(status_code=500, detail="Failed to write file.")

