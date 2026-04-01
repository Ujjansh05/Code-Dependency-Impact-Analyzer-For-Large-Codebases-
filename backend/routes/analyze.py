"""POST /api/analyze endpoint for impact analysis."""

from fastapi import APIRouter, HTTPException

from backend.models import AnalyzeRequest, AnalyzeResponse, AffectedNode
from llm.query_parser import extract_target
from llm.explainer import explain_impact
from graph.tigergraph_client import get_connection

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_impact(request: AnalyzeRequest):
    """Analyze the impact of changing a function or file."""
    parsed = extract_target(request.query)
    target = parsed["target"]
    target_type = parsed["type"]

    if target_type == "unknown":
        raise HTTPException(
            status_code=400,
            detail="Could not identify a specific function or file from your query. Please be more specific.",
        )

    try:
        conn = get_connection()

        if target_type == "function":
            results = conn.runInstalledQuery(
                "impact_analysis",
                params={"start_func": target, "max_depth": request.max_depth},
            )
        else:
            results = conn.runInstalledQuery(
                "hop_detection",
                params={"start_node": target, "num_hops": request.max_depth},
            )

        affected_ids = []
        if results and isinstance(results, list):
            for result_set in results:
                if "@@affected" in result_set:
                    affected_ids = list(result_set["@@affected"])
                elif "@@reachable" in result_set:
                    affected_ids = list(result_set["@@reachable"])

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Graph database unavailable: {str(e)}",
        )

    affected_nodes = [
        AffectedNode(
            id=node_id,
            name=node_id.split("::")[-1] if "::" in node_id else node_id,
            type="Function" if node_id.startswith("func::") else "File",
        )
        for node_id in affected_ids
    ]

    explanation = explain_impact(
        question=request.query,
        target=target,
        affected_nodes=[n.name for n in affected_nodes],
    )

    return AnalyzeResponse(
        query=request.query,
        target=target,
        target_type=target_type,
        affected_nodes=affected_nodes,
        explanation=explanation,
        total_affected=len(affected_nodes),
    )
