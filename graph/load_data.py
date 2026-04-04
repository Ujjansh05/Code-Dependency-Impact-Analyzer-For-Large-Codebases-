"""Wait for TigerGraph, create schema, and load CSVs."""

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from graph.wait_for_tg import wait_for_tigergraph
from graph.tigergraph_client import get_connection

VERTICES_PATH = os.getenv("VERTICES_CSV", os.path.join("data", "vertices.csv"))
EDGES_PATH = os.getenv("EDGES_CSV", os.path.join("data", "edges.csv"))

VERTEX_TYPE_MAP = {
    "File": "CodeFile",
    "Function": "CodeFunction",
}

EDGE_SCHEMA = {
    "CALLS": ("CodeFunction", "CodeFunction"),
    "IMPORTS": ("CodeFile", "CodeFile"),
    "CONTAINS": ("CodeFile", "CodeFunction"),
}


def load_vertices(conn, csv_path: str):
    """Upsert vertices from CSV into TigerGraph."""
    if not os.path.exists(csv_path):
        print(f"Vertices file not found: {csv_path}")
        return 0

    count = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            vertex_type = VERTEX_TYPE_MAP.get(row["type"], row["type"])
            vertex_id = row["id"]
            attrs = {k: v for k, v in row.items() if k not in ("id", "type")}
            conn.upsertVertex(vertex_type, vertex_id, attrs)
            count += 1

    print(f"Loaded {count} vertices from {csv_path}")
    return count


def load_edges(conn, csv_path: str):
    """Upsert edges from CSV into TigerGraph."""
    if not os.path.exists(csv_path):
        print(f"Edges file not found: {csv_path}")
        return 0

    count = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            edge_type = row["type"]
            if edge_type not in EDGE_SCHEMA:
                print(f"Unknown edge type: {edge_type}")
                continue

            src_type, tgt_type = EDGE_SCHEMA[edge_type]
            conn.upsertEdge(src_type, row["source"], edge_type, tgt_type, row["target"])
            count += 1

    print(f"Loaded {count} edges from {csv_path}")
    return count


def main():
    """Full load pipeline."""
    if not wait_for_tigergraph():
        print("Aborting: TigerGraph not available.")
        sys.exit(1)

    conn = get_connection()
    print(f"Connected to TigerGraph at {conn.host}")

    v_count = load_vertices(conn, VERTICES_PATH)
    e_count = load_edges(conn, EDGES_PATH)

    print(f"\nLoad complete — {v_count} vertices, {e_count} edges")


if __name__ == "__main__":
    main()
