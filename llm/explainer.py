"""Graph traversal results to human-readable explanation.

Uses the active model from the model registry.
"""


EXPLANATION_PROMPT = """You are a code dependency impact analyst.

A developer asked: "{question}"

The graph analysis found that changing `{target}` would affect the following
functions and files:

{affected_list}

Please provide:
1. A clear, concise summary of the impact (2-3 sentences).
2. A risk assessment (Low / Medium / High) based on how many components are affected.
3. A bullet-point list of the most critical dependencies to review.

Keep your response professional and actionable."""


def explain_impact(
    question: str,
    target: str,
    affected_nodes: list[str],
    mode: str | None = None,
) -> str:
    """Generate a human-readable explanation of the impact analysis results."""
    if not affected_nodes:
        return (
            f"**No downstream impact detected.**\n\n"
            f"Changing `{target}` does not appear to affect any other "
            f"functions or files in the analyzed codebase."
        )

    from llm.model_registry import get_active_model

    adapter = get_active_model()

    affected_list = "\n".join(f"  • {node}" for node in affected_nodes)

    prompt = EXPLANATION_PROMPT.format(
        question=question,
        target=target,
        affected_list=affected_list,
    )

    max_tokens = 256 if (mode or "").lower() == "fast" else 512
    return adapter.generate(prompt, temperature=0.4, max_tokens=max_tokens, mode=mode)
