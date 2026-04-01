"""Convert parsed AST data into CSV files for TigerGraph bulk load."""

import csv
import os
from typing import Any

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
                callee_id = _resolve_call(call_name, file_data, parsed_files)
                if callee_id and callee_id in seen_vertices:
                    edges.append({
                        "source": func_id,
                        "target": callee_id,
                        "type": "CALLS",
                    })

        for imp in file_data.get("imports", []):
            target_file_id = _resolve_import(imp["module"], parsed_files)
            if target_file_id:
                edges.append({
                    "source": file_id,
                    "target": target_file_id,
                    "type": "IMPORTS",
                })

    _write_vertices(vertices, vertices_path)
    _write_edges(edges, edges_path)

    print(f"Generated {len(vertices)} vertices → {vertices_path}")
    print(f"Generated {len(edges)} edges    → {edges_path}")

    return vertices_path, edges_path


def _make_file_id(filepath: str) -> str:
    """Stable ID for a file vertex."""
    return f"file::{os.path.normpath(filepath)}"


def _make_func_id(filepath: str, func_name: str) -> str:
    """Stable ID for a function vertex."""
    return f"func::{os.path.normpath(filepath)}::{func_name}"


def _resolve_call(
    call_name: str,
    current_file: dict[str, Any],
    all_files: list[dict[str, Any]],
) -> str | None:
    """Try to resolve a call name to a function ID (same-file first, then global)."""
    for func in current_file.get("functions", []):
        if func["name"] == call_name:
            return _make_func_id(current_file["file"], call_name)

    for file_data in all_files:
        for func in file_data.get("functions", []):
            if func["name"] == call_name:
                return _make_func_id(file_data["file"], call_name)

    return None


def _resolve_import(module_name: str, all_files: list[dict[str, Any]]) -> str | None:
    """Try to map an import module name to a file ID."""
    module_path_part = module_name.replace(".", os.sep)
    for file_data in all_files:
        filepath = os.path.normpath(file_data["file"])
        if filepath.endswith(f"{module_path_part}.py") or filepath.endswith(
            os.path.join(module_path_part, "__init__.py")
        ):
            return _make_file_id(filepath)
    return None


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
