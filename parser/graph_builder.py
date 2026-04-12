"""Convert parsed AST data into CSV files for TigerGraph bulk load."""

import csv
import logging
import os
from typing import Any

logger = logging.getLogger("graphxploit.graph_builder")

DEFAULT_VERTICES_PATH = os.path.join("data", "vertices.csv")
DEFAULT_EDGES_PATH = os.path.join("data", "edges.csv")


def build_csvs(
    parsed_files: list[dict[str, Any]],
    vertices_path: str = DEFAULT_VERTICES_PATH,
    edges_path: str = DEFAULT_EDGES_PATH,
) -> tuple[str, str]:
    """Transform parsed AST data into TigerGraph-compatible CSVs."""
    os.makedirs(os.path.dirname(vertices_path), exist_ok=True)
    os.makedirs(os.path.dirname(edges_path), exist_ok=True)

    # Pre-build lookup indexes for O(1) call and import resolution.
    func_index, file_func_index = _build_function_index(parsed_files)
    import_index = _build_import_index(parsed_files)

    vertices: list[dict[str, str]] = []
    edges: list[dict[str, str]] = []
    seen_vertices: set[str] = set()

    for file_data in parsed_files:
        filepath = file_data["file"]
        file_id = _make_file_id(filepath)

        if file_id not in seen_vertices:
            vertices.append({
                "id": file_id,
                "type": "File",
                "name": os.path.basename(filepath),
                "filepath": filepath,
            })
            seen_vertices.add(file_id)

        for func in file_data.get("functions", []):
            func_id = _make_func_id(filepath, func["name"])
            if func_id not in seen_vertices:
                vertices.append({
                    "id": func_id,
                    "type": "Function",
                    "name": func["name"],
                    "filepath": filepath,
                })
                seen_vertices.add(func_id)

            edges.append({
                "source": file_id,
                "target": func_id,
                "type": "CONTAINS",
            })

            for call_name in func.get("calls", []):
                callee_id = _resolve_call_indexed(
                    call_name, filepath, func_index, file_func_index,
                )
                if callee_id and callee_id in seen_vertices:
                    edges.append({
                        "source": func_id,
                        "target": callee_id,
                        "type": "CALLS",
                    })

        for imp in file_data.get("imports", []):
            target_file_id = import_index.get(imp["module"])
            if target_file_id:
                edges.append({
                    "source": file_id,
                    "target": target_file_id,
                    "type": "IMPORTS",
                })

    _write_vertices(vertices, vertices_path)
    _write_edges(edges, edges_path)

    logger.info(
        "Generated %d vertices and %d edges", len(vertices), len(edges),
    )
    print(f"Generated {len(vertices)} vertices → {vertices_path}")
    print(f"Generated {len(edges)} edges    → {edges_path}")

    return vertices_path, edges_path


# ── Index Builders (O(n) one-time cost) ─────────────────────────


def _build_function_index(
    parsed_files: list[dict[str, Any]],
) -> tuple[dict[str, list[str]], dict[str, set[str]]]:
    """Build indexes for O(1) function call resolution.

    Returns:
        func_index: maps function name → list of func_ids across all files.
        file_func_index: maps filepath → set of function names in that file.
    """
    func_index: dict[str, list[str]] = {}
    file_func_index: dict[str, set[str]] = {}

    for file_data in parsed_files:
        filepath = file_data["file"]
        local_names: set[str] = set()

        for func in file_data.get("functions", []):
            name = func["name"]
            func_id = _make_func_id(filepath, name)
            func_index.setdefault(name, []).append(func_id)
            local_names.add(name)

        file_func_index[filepath] = local_names

    return func_index, file_func_index


def _build_import_index(
    parsed_files: list[dict[str, Any]],
) -> dict[str, str]:
    """Build an index mapping module names → file IDs for O(1) import resolution."""
    import_index: dict[str, str] = {}

    for file_data in parsed_files:
        filepath = os.path.normpath(file_data["file"])
        file_id = _make_file_id(filepath)

        # Derive all possible module names this file could match.
        # e.g. "src/auth/utils.py" matches "auth.utils" and "src.auth.utils"
        parts = filepath.replace(os.sep, "/")
        if parts.endswith(".py"):
            parts = parts[:-3]
        if parts.endswith("/__init__"):
            parts = parts[: -len("/__init__")]

        segments = parts.split("/")
        # Register progressively longer module paths.
        for i in range(len(segments)):
            module_name = ".".join(segments[i:])
            if module_name and module_name not in import_index:
                import_index[module_name] = file_id

    return import_index


# ── ID Generators ───────────────────────────────────────────────


def _make_file_id(filepath: str) -> str:
    """Stable ID for a file vertex."""
    return f"file::{os.path.normpath(filepath)}"


def _make_func_id(filepath: str, func_name: str) -> str:
    """Stable ID for a function vertex."""
    return f"func::{os.path.normpath(filepath)}::{func_name}"


# ── Indexed Resolution (O(1) per lookup) ────────────────────────


def _resolve_call_indexed(
    call_name: str,
    current_filepath: str,
    func_index: dict[str, list[str]],
    file_func_index: dict[str, set[str]],
) -> str | None:
    """Resolve a call name to a function ID using pre-built indexes.

    Prefers same-file matches, then falls back to first global match.
    """
    candidates = func_index.get(call_name)
    if not candidates:
        return None

    # Prefer a same-file definition.
    if call_name in file_func_index.get(current_filepath, set()):
        local_id = _make_func_id(current_filepath, call_name)
        if local_id in candidates:
            return local_id

    # Fall back to first global match.
    return candidates[0]


# ── CSV Writers ─────────────────────────────────────────────────


def _write_vertices(vertices: list[dict[str, str]], path: str):
    """Write vertices CSV."""
    fieldnames = ["id", "type", "name", "filepath"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(vertices)


def _write_edges(edges: list[dict[str, str]], path: str):
    """Write edges CSV."""
    fieldnames = ["source", "target", "type"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(edges)
