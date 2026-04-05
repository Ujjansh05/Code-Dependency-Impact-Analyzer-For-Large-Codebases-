"""Resolve natural-language targets to vertex IDs before running graph queries."""

import csv
import os
from pathlib import Path
from typing import Literal


VERTICES_CSV = os.getenv("VERTICES_CSV", os.path.join("data", "vertices.csv"))


def resolve_target_id(
    target: str,
    target_type: Literal["function", "file", "unknown"],
    vertices_csv_path: str = VERTICES_CSV,
) -> str | None:
    """Resolve a parsed function/file target to a concrete vertex id from vertices.csv."""
    if target_type == "unknown" or not target:
        return None

    target = target.strip()
    for csv_path in _candidate_vertices_csvs(vertices_csv_path):
        resolved = _resolve_target_id_from_csv(csv_path, target, target_type)
        if resolved:
            return resolved

    return None


def _candidate_vertices_csvs(preferred_path: str) -> list[Path]:
    """Find likely vertices.csv files, newest first after explicit paths."""
    candidates: list[Path] = []
    seen: set[str] = set()

    def _add(path: Path):
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            return
        seen.add(key)
        candidates.append(path)

    if preferred_path:
        _add(Path(preferred_path))

    env_path = os.getenv("VERTICES_CSV", "").strip()
    if env_path:
        _add(Path(env_path))

    _add(Path("data") / "vertices.csv")

    data_dir = Path("data")
    if data_dir.exists():
        nested = sorted(
            data_dir.rglob("vertices.csv"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
            reverse=True,
        )
        for path in nested:
            _add(path)

    return [p for p in candidates if p.exists()]


def _resolve_target_id_from_csv(
    csv_path: Path,
    target: str,
    target_type: Literal["function", "file", "unknown"],
) -> str | None:
    matches: list[str] = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_type = row.get("type", "")
            row_id = row.get("id", "")
            row_name = row.get("name", "")
            row_path = row.get("filepath", "")

            if target_type == "function" and row_type == "Function":
                if row_id == target:
                    return row_id
                if row_name == target:
                    matches.append(row_id)

            if target_type == "file" and row_type == "File":
                if row_id == target or row_name == target or row_path == target:
                    return row_id
                if row_path.endswith(target):
                    matches.append(row_id)

    return matches[0] if matches else None
