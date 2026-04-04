"""Resolve natural-language targets to vertex IDs before running graph queries."""

import csv
import os
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

    if not os.path.exists(vertices_csv_path):
        return None

    target = target.strip()
    matches: list[str] = []

    with open(vertices_csv_path, "r", encoding="utf-8") as f:
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