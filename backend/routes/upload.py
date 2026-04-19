"""POST /api/upload endpoint for codebase upload and processing.

import logging
import os
import pathlib
import shutil
import tempfile
import zipfile

from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.models import UploadResponse
from parser.ast_parser import parse_directory
from parser.graph_builder import build_csvs
from graph.load_data import load_vertices, load_edges
from graph.tigergraph_client import get_connection

log = logging.getLogger("graphxploit.upload")

router = APIRouter()

UPLOAD_DIR = os.path.join("data", "uploaded_code")

# Maximum accepted upload size (100 MB).
MAX_UPLOAD_BYTES = 100 * 1024 * 1024


def _safe_extract(zf: zipfile.ZipFile, dest: str) -> None:
    """Extract a zip archive while preventing Zip Slip path-traversal attacks.

    Raises ValueError if any member attempts to escape *dest*.
    """
    dest_path = pathlib.Path(dest).resolve()
    for member in zf.namelist():
        member_path = (dest_path / member).resolve()
        if not member_path.is_relative_to(dest_path):
            raise ValueError(
                f"Zip Slip detected: member '{member}' would extract outside the target directory."
            )
    # All members are safe — proceed with normal extraction.
    zf.extractall(dest)


@router.post("/upload", response_model=UploadResponse)
async def upload_codebase(file: UploadFile = File(...)):
    """Upload a codebase as a zip file for analysis."""
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Please upload a .zip file.")

    # ── Size guard ────────────────────────────────────────────────────────────
    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
    except Exception:
        log.exception("Failed to read upload stream")
        raise HTTPException(status_code=500, detail="Failed to read uploaded file.")

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Upload too large. Maximum allowed size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )

    # ── Write to temp file ────────────────────────────────────────────────────
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
    except Exception:
        log.exception("Failed to save upload to temp file")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")

    try:
        # ── Wipe and recreate upload directory ────────────────────────────────
        if os.path.exists(UPLOAD_DIR):
            shutil.rmtree(UPLOAD_DIR)
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        # ── Zip Slip-safe extraction ──────────────────────────────────────────
        try:
            with zipfile.ZipFile(tmp_path, "r") as zf:
                _safe_extract(zf, UPLOAD_DIR)
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid zip archive.")
        except ValueError as exc:
            log.warning("Rejected malicious zip: %s", exc)
            raise HTTPException(status_code=400, detail="Zip archive contains invalid paths.")

        # ── Parse & build graph ───────────────────────────────────────────────
        parsed = parse_directory(UPLOAD_DIR)
        files_parsed = len(parsed)

        if files_parsed == 0:
            raise HTTPException(
                status_code=400,
                detail="No Python files found in the uploaded archive.",
            )

        vertices_path, edges_path = build_csvs(parsed)

        try:
            conn = get_connection()
            v_count = load_vertices(conn, vertices_path)
            e_count = load_edges(conn, edges_path)
        except Exception:
            log.exception("Failed to load data into TigerGraph")
            raise HTTPException(status_code=503, detail="Graph database is unavailable.")

        return UploadResponse(
            message="Codebase uploaded and graph built successfully.",
            files_parsed=files_parsed,
            vertices_count=v_count,
            edges_count=e_count,
        )

    except HTTPException:
        raise
    except Exception:
        log.exception("Unexpected error processing upload")
        raise HTTPException(status_code=500, detail="Upload processing failed.")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

