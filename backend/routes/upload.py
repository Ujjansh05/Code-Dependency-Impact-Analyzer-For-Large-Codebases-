"""POST /api/upload endpoint for codebase upload and processing."""

import os
import shutil
import tempfile
import zipfile

from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.models import UploadResponse
from parser.ast_parser import parse_directory
from parser.graph_builder import build_csvs
from graph.load_data import load_vertices, load_edges
from graph.tigergraph_client import get_connection

router = APIRouter()

UPLOAD_DIR = os.path.join("data", "uploaded_code")


@router.post("/upload", response_model=UploadResponse)
async def upload_codebase(file: UploadFile = File(...)):
    """Upload a codebase as a zip file for analysis."""
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Please upload a .zip file.")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {e}")

    try:
        if os.path.exists(UPLOAD_DIR):
            shutil.rmtree(UPLOAD_DIR)
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        with zipfile.ZipFile(tmp_path, "r") as zf:
            zf.extractall(UPLOAD_DIR)

        parsed = parse_directory(UPLOAD_DIR)
        files_parsed = len(parsed)

        if files_parsed == 0:
            raise HTTPException(
                status_code=400,
                detail="No Python files found in the uploaded archive.",
            )

        vertices_path, edges_path = build_csvs(parsed)

        conn = get_connection()
        v_count = load_vertices(conn, vertices_path)
        e_count = load_edges(conn, edges_path)

        return UploadResponse(
            message="Codebase uploaded and graph built successfully.",
            files_parsed=files_parsed,
            vertices_count=v_count,
            edges_count=e_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
