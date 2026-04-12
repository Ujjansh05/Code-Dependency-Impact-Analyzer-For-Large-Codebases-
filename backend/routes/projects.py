"""GET /api/projects endpoint for the frontend project switcher."""

import os
import sys

from fastapi import APIRouter, HTTPException

# Ensure the CLI module is available
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from cli.project_registry import list_projects, get_project

router = APIRouter()


@router.get("/projects")
async def get_projects():
    """Return all registered projects."""
    return {"projects": list_projects()}


@router.post("/projects/{project_id}/load")
async def load_project(project_id: str):
    """Re-parse a registered project and update graph CSVs for visualization."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found in registry.")

    path = project["path"]
    if not os.path.isdir(path):
        raise HTTPException(
            status_code=400,
            detail=f"Project directory no longer exists: {path}",
        )

    try:
        from parser.ast_parser import parse_directory
        from parser.graph_builder import build_csvs
        from cli.project_registry import register_project

        parsed = parse_directory(path)
        if not parsed:
            raise HTTPException(status_code=400, detail="No Python files found.")

        output_dir = os.path.join(os.getcwd(), "data")
        os.makedirs(output_dir, exist_ok=True)

        vertices_path = os.path.join(output_dir, "vertices.csv")
        edges_path = os.path.join(output_dir, "edges.csv")
        build_csvs(parsed, vertices_path=vertices_path, edges_path=edges_path)

        def _count(p):
            try:
                with open(p, "r") as f:
                    return max(0, sum(1 for _ in f) - 1)
            except OSError:
                return 0

        v_count = _count(vertices_path)
        e_count = _count(edges_path)

        register_project(
            path=path,
            vertices=v_count,
            edges=e_count,
            files=len(parsed),
        )

        return {
            "status": "ok",
            "project": project["name"],
            "files": len(parsed),
            "vertices": v_count,
            "edges": e_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load project: {e}")
