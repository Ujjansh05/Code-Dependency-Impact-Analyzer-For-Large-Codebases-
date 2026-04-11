"""Persistent project registry for remembering analyzed codebases.

Stores a JSON list of projects at ~/.graphxploit/projects.json so that
commands like `visualize` and `query` can re-use previously analyzed paths
without the user needing to re-type them every time.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

REGISTRY_DIR = os.path.join(Path.home(), ".graphxploit")
REGISTRY_FILE = os.path.join(REGISTRY_DIR, "projects.json")


def _ensure_registry() -> list[dict]:
    """Load the registry from disk, creating it if it doesn't exist."""
    os.makedirs(REGISTRY_DIR, exist_ok=True)
    if not os.path.exists(REGISTRY_FILE):
        _save([])
        return []
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return data
    except (json.JSONDecodeError, OSError):
        return []


def _save(projects: list[dict]) -> None:
    """Persist the project list to disk."""
    os.makedirs(REGISTRY_DIR, exist_ok=True)
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(projects, f, indent=2, default=str)


def _derive_project_name(path: str) -> str:
    """Derive a human-friendly project name from its directory path."""
    return os.path.basename(os.path.normpath(path))


def list_projects() -> list[dict]:
    """Return all registered projects."""
    return _ensure_registry()


def get_project(project_id: str) -> dict | None:
    """Get a single project by its ID."""
    for p in _ensure_registry():
        if p["id"] == project_id:
            return p
    return None


def find_project_by_path(path: str) -> dict | None:
    """Find a project by its absolute path."""
    norm = os.path.normpath(os.path.abspath(path))
    for p in _ensure_registry():
        if os.path.normpath(p["path"]) == norm:
            return p
    return None


def register_project(path: str, name: str | None = None,
                     vertices: int = 0, edges: int = 0,
                     files: int = 0) -> dict:
    """Add or update a project in the registry.

    If a project with the same path already exists, it is updated in place
    (preserving its ID and name unless a new name is given).
    """
    projects = _ensure_registry()
    norm = os.path.normpath(os.path.abspath(path))
    now = datetime.now(timezone.utc).isoformat()

    existing = None
    for p in projects:
        if os.path.normpath(p["path"]) == norm:
            existing = p
            break

    if existing:
        existing["last_analyzed"] = now
        existing["vertices"] = vertices
        existing["edges"] = edges
        existing["files"] = files
        if name:
            existing["name"] = name
        _save(projects)
        return existing

    project = {
        "id": uuid.uuid4().hex[:8],
        "name": name or _derive_project_name(path),
        "path": norm,
        "created": now,
        "last_analyzed": now,
        "vertices": vertices,
        "edges": edges,
        "files": files,
    }
    projects.append(project)
    _save(projects)
    return project


def rename_project(project_id: str, new_name: str) -> dict | None:
    """Rename a project. Returns the project dict or None if not found."""
    projects = _ensure_registry()
    for p in projects:
        if p["id"] == project_id:
            p["name"] = new_name
            _save(projects)
            return p
    return None


def delete_project(project_id: str) -> bool:
    """Remove a project from the registry. Returns True if deleted."""
    projects = _ensure_registry()
    before = len(projects)
    projects = [p for p in projects if p["id"] != project_id]
    if len(projects) < before:
        _save(projects)
        return True
    return False
