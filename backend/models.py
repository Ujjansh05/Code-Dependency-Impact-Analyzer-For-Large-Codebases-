"""Pydantic schemas for requests and responses."""

from typing import Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Request body for POST /api/analyze."""
    query: str = Field(..., description="Natural language impact query", example="What happens if I change the login function?")
    max_depth: int = Field(5, description="Maximum traversal depth", ge=1, le=20)
    inference_mode: Literal["fast", "slow", "balanced"] = Field(
        "fast",
        description="LLM inference profile for explanation generation.",
    )


class AffectedNode(BaseModel):
    """A single affected node in the impact result."""
    id: str
    name: str
    type: str  # "File" or "Function"


class AnalyzeResponse(BaseModel):
    """Response body for POST /api/analyze."""
    query: str
    target: str
    target_type: str
    affected_nodes: list[AffectedNode]
    explanation: str
    total_affected: int


class UploadResponse(BaseModel):
    """Response body for POST /api/upload."""
    message: str
    files_parsed: int
    vertices_count: int
    edges_count: int


class GraphNode(BaseModel):
    """A node in the visualization graph."""
    id: str
    label: str
    type: str
    filepath: str | None = None


class GraphEdge(BaseModel):
    """An edge in the visualization graph."""
    source: str
    target: str
    type: str  # "CALLS", "IMPORTS", "CONTAINS"


class GraphData(BaseModel):
    """Full graph data for frontend visualization."""
    nodes: list[GraphNode]
    edges: list[GraphEdge]
