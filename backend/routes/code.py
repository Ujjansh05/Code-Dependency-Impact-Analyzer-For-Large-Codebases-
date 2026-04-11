"""GET /api/file and PUT /api/file endpoints for reading and modifying source code."""

import os
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

router = APIRouter()

class FileUpdateRequest(BaseModel):
    content: str

@router.get("/file")
async def get_file_content(path: str):
    """Retrieve the text content of a source file."""
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found on disk.")
    
    if not os.path.isfile(path):
        raise HTTPException(status_code=400, detail="Path is not a regular file.")
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content, "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")

@router.put("/file")
async def update_file_content(path: str, request: FileUpdateRequest):
    """Modify the text content of a source file."""
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found on disk.")
    
    if not os.path.isfile(path):
        raise HTTPException(status_code=400, detail="Path is not a regular file.")

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(request.content)
        return {"status": "ok", "message": "File updated successfully", "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file: {e}")
