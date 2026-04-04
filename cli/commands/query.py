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

        if target_type == "unknown":
            print_error(
                "Could not identify a function or file from your question.\n"
                "  Try being more specific, e.g.:\n"
                '  code-impact query "What breaks if I change the authenticate function?"'
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
            results = conn.runInstalledQuery(
                "impact_analysis",
                params={"start_func": target_id or target, "max_depth": depth},
            )
        else:
            results = conn.runInstalledQuery(
                "hop_detection",
                params={"start_node": target_id or target, "num_hops": depth},
            )

        affected = []
        if results and isinstance(results, list):
            for rs in results:
                if "@@affected" in rs:
                    affected = list(rs["@@affected"])
                elif "@@reachable" in rs:
                    affected = list(rs["@@reachable"])

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
