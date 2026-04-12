"""pyTigerGraph wrapper for CodeGraph."""

import logging
import os
from functools import lru_cache

import pyTigerGraph as tg

logger = logging.getLogger("graphxploit.tigergraph")


@lru_cache(maxsize=1)
def get_connection() -> tg.TigerGraphConnection:
    """Return a cached pyTigerGraph connection to the CodeGraph graph."""
    conn = tg.TigerGraphConnection(
        host=f"http://{os.getenv('TG_HOST', 'localhost')}",
        restppPort=os.getenv("TG_PORT", "9000"),
        username=os.getenv("TG_USERNAME", "tigergraph"),
        password=os.getenv("TG_PASSWORD", "tigergraph"),
        graphname=os.getenv("TG_GRAPH_NAME", "CodeGraph"),
    )

    try:
        conn.getToken(conn.createSecret())
    except (ConnectionError, OSError, RuntimeError) as e:
        logger.warning("TigerGraph token auth skipped: %s", e)
    except Exception as e:
        logger.debug("TigerGraph auth attempt failed (non-critical): %s", e)

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
