"""pyTigerGraph wrapper for CodeGraph."""

import os
from functools import lru_cache

import pyTigerGraph as tg


@lru_cache(maxsize=1)
def get_connection() -> tg.TigerGraphConnection:
    """Return a cached pyTigerGraph connection to the CodeGraph graph."""
    conn = tg.TigerGraphConnection(
        host=f"http://{os.getenv('TG_HOST', 'tigergraph')}",
        restppPort=os.getenv("TG_PORT", "9000"),
        username=os.getenv("TG_USERNAME", "tigergraph"),
        password=os.getenv("TG_PASSWORD", "tigergraph"),
        graphname=os.getenv("TG_GRAPH_NAME", "CodeGraph"),
    )

    try:
        conn.getToken(conn.createSecret())
    except Exception:
        pass

    return conn


def get_graph_stats(conn: tg.TigerGraphConnection | None = None) -> dict:
    """Return basic vertex/edge counts."""
    conn = conn or get_connection()
    return {
        "vertices": {
            "File": conn.getVertexCount("CodeFile"),
            "Function": conn.getVertexCount("CodeFunction"),
        },
        "edges": {
            "CALLS": conn.getEdgeCount("CALLS"),
            "IMPORTS": conn.getEdgeCount("IMPORTS"),
            "CONTAINS": conn.getEdgeCount("CONTAINS"),
        },
    }
