"""code-impact query command."""

import os

import click

from cli.console import (
    print_banner, print_success, print_error, print_info,
    print_warning, console,
)


def _default_inference_mode() -> str:
    mode = os.getenv("OLLAMA_INFERENCE_MODE", "fast").strip().lower()
    return mode if mode in {"fast", "slow", "balanced"} else "fast"


@click.command()
@click.argument("question")
@click.option(
    "--depth", "-d", default=5, show_default=True,
    help="Maximum graph traversal depth.",
)
@click.option(
    "--no-ai", is_flag=True, default=False,
    help="Skip LLM explanation, show only graph results.",
)
@click.option(
    "--mode",
    type=click.Choice(["fast", "slow", "balanced"], case_sensitive=False),
    default=_default_inference_mode,
    show_default=True,
    help="LLM inference profile for AI explanation.",
)
def query(question: str, depth: int, no_ai: bool, mode: str):
    """ Run a natural language impact query.

    QUESTION is your impact question in plain English.

    \b
    Examples:
      code-impact query "What happens if I change the login function?"
      code-impact query "Impact of modifying database.py?" --depth 3
      code-impact query "What depends on calculate_total?" --no-ai
    """
    print_banner()
    mode = mode.lower()

    print_info(f"Query: [accent]{question}[/accent]\n")

    try:
        from llm.query_parser import extract_target

        parsed = extract_target(question)
        target = parsed["target"]
        target_type = parsed["type"]
        raw = parsed.get("raw", "")

        if target_type == "unknown":
            if isinstance(raw, str) and raw.startswith("[Error]"):
                print_error(f"Target extraction failed: {raw}")
                print_info("Check Ollama model availability with:  curl http://localhost:11434/api/tags")
            else:
                print_error(
                    "Could not identify a function or file from your question.\n"
                    "  Try being more specific, e.g.:\n"
                    '  code-impact query "What breaks if I change the authenticate function?"'
                )
            print_error(
                'Use a concrete target, e.g. "What breaks if I change authenticate?"'
            )
            raise SystemExit(1)

        print_info(f"Identified target: [accent]{target}[/accent] (type: {target_type})")

    except ImportError:
        print_error("LLM module not available. Is Ollama running?")
        raise SystemExit(1)

    print_info("Traversing dependency graph …\n")

    try:
        from graph.tigergraph_client import get_connection
        from graph.target_resolver import resolve_target_id

        conn = get_connection()
        target_id = resolve_target_id(target=target, target_type=target_type)

        if target_type == "function":
            start_func = target_id or target
            results = conn.runInstalledQuery(
                "impact_analysis",
                params={"start_func": (start_func,), "max_depth": depth},
            )
        else:
            start_node = target_id or target
            start_node_type = "CodeFile" if target_type == "file" else "CodeFunction"
            results = conn.runInstalledQuery(
                "hop_detection",
                params={"start_node": (start_node, start_node_type), "num_hops": depth},
            )

        affected = _extract_affected_nodes(results)

    except Exception as e:
        print_error(f"Graph query failed: {e}")
        print_info("Make sure TigerGraph is running: code-impact status")
        raise SystemExit(1)

    if not affected:
        print_success(f"No downstream impact detected for '{target}'.")
        console.print(
            "  [muted]This function/file has no outgoing dependencies in the loaded graph.[/muted]"
        )
        return

    node_names = [n.split("::")[-1] if "::" in n else n for n in affected]

    from cli.console import make_table
    table = make_table(
        title=f"Impact Analysis — {target}",
        columns=[
            ("#", "dim"),
            ("Affected Component", "bold yellow"),
            ("Type", "cyan"),
        ],
        rows=[
            [
                str(i + 1),
                name,
                "Function" if n.startswith("func::") else "File",
            ]
            for i, (n, name) in enumerate(zip(affected, node_names))
        ],
    )
    console.print(table)

    # Risk assessment
    console.print()
    risk = " Low" if len(affected) <= 2 else " Medium" if len(affected) <= 5 else " High"
    console.print(f"  Risk Level: {risk}  ({len(affected)} components affected)")

    if not no_ai:
        console.print()
        print_info(f"Generating AI explanation … (mode: {mode})")

        try:
            from llm.explainer import explain_impact
            from rich.panel import Panel

            explanation = explain_impact(question, target, node_names, mode=mode)
            console.print()
            console.print(Panel(explanation, title=" AI Explanation", border_style="blue"))
        except Exception as e:
            print_warning(f"AI explanation unavailable: {e}")
            print_info("Run with --no-ai to skip, or check Ollama: code-impact status")

    console.print()


def _extract_affected_nodes(results: list[dict] | None) -> list[str]:
    """Normalize installed-query outputs to a flat list of vertex IDs."""
    affected: list[str] = []
    if not results or not isinstance(results, list):
        return affected

    for rs in results:
        if "@@affected" in rs:
            raw_nodes = rs["@@affected"]
        elif "@@reachable" in rs:
            raw_nodes = rs["@@reachable"]
        else:
            continue

        for node in list(raw_nodes):
            if isinstance(node, str):
                affected.append(node)
            elif isinstance(node, dict):
                node_id = node.get("v_id") or node.get("id") or node.get("name")
                if node_id:
                    affected.append(str(node_id))
            else:
                affected.append(str(node))

    return affected
