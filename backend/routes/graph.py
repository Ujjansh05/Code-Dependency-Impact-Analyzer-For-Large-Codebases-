"""GET /api/graph-data endpoint for graph visualization."""

import csv
import os

from fastapi import APIRouter, HTTPException

from backend.models import GraphData, GraphNode, GraphEdge

router = APIRouter()

VERTICES_PATH = os.path.join("data", "vertices.csv")
EDGES_PATH = os.path.join("data", "edges.csv")


@router.get("/graph-data", response_model=GraphData)
async def get_graph_data():
    """Return all graph nodes and edges for the frontend vis-network canvas."""
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    if not os.path.exists(VERTICES_PATH):
        raise HTTPException(
            status_code=404,
            detail="No graph data found. Please upload a codebase first.",
        )

    try:
        with open(VERTICES_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                nodes.append(GraphNode(
                    id=row["id"],
                    label=row["name"],
                    type=row["type"],
                    filepath=row.get("filepath"),
                ))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading vertices: {e}")

    if os.path.exists(EDGES_PATH):
        try:
            with open(EDGES_PATH, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    edges.append(GraphEdge(
                        source=row["source"],
                        target=row["target"],
                        type=row["type"],
                    ))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading edges: {e}")

    return GraphData(nodes=nodes, edges=edges)
