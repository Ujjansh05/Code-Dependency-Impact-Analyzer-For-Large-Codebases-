"""graphxploit analyze command."""

import os
import click

from cli.console import (
    print_banner, print_success, print_error, print_info,
    print_step, print_warning, console, make_table,
)


def _default_inference_mode() -> str:
    mode = os.getenv("OLLAMA_INFERENCE_MODE", "fast").strip().lower()
    return mode if mode in {"fast", "slow", "balanced"} else "fast"


@click.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option(
    "--query", "-q", default=None,
    help='Impact query to run after loading. E.g. "What breaks if I change login?"',
)
@click.option(
    "--depth", "-d", default=5, show_default=True,
    help="Maximum traversal depth for impact analysis.",
)
@click.option(
    "--no-docker", is_flag=True, default=False,
    help="Skip auto-starting Docker (assumes services are already running).",
)
@click.option(
    "--output-dir", "-o", default=None,
    help="Directory for intermediate CSV files.",
)
@click.option(
    "--use-model", default=None,
    help="Model ID from the registry to use (defaults to active model).",
)
@click.option(
    "--mode",
    type=click.Choice(["fast", "slow", "balanced"], case_sensitive=False),
    default=_default_inference_mode,
    show_default=True,
    help="LLM inference profile for query explanation.",
)
@click.option(
    "--force", is_flag=True, default=False,
    help="Force full re-parse (ignore cache).",
)
def analyze(path: str, query: str | None, depth: int, no_docker: bool,
            output_dir: str | None, use_model: str | None, mode: str, force: bool):
    """Full analysis pipeline: parse, graph, load, query.

    PATH is the root directory of the Python project to analyze.

    \b
    Examples:
      graphxploit analyze ./myproject
      graphxploit analyze ./myproject -q "What breaks if I change login?"
      graphxploit analyze ./myproject --no-docker
    """
    print_banner()
    mode = mode.lower()

    total_steps = 5 if query else 4
    current = 0

    current += 1
    if no_docker:
        print_step(current, total_steps, "Skipping Docker (--no-docker)")
    else:
        print_step(current, total_steps, "Checking Docker services …")

        from cli.docker_manager import are_services_running, start_services

        if are_services_running():
            print_info("TigerGraph is already running")
        else:
            print_info("Starting Docker services (TigerGraph + Ollama) …")
            console.print()
            ok = start_services()
            if not ok:
                print_error("Failed to start services. Use --no-docker if they're running elsewhere.")
                raise SystemExit(1)
            console.print()

    # Activate specified model if given.
    if use_model:
        from llm.model_registry import set_active_model
        switched = set_active_model(use_model)
        if switched:
            print_info(f"Using model: [accent]{switched.name}[/accent]")
        else:
            print_warning(f"Model '{use_model}' not found in registry. Using active model.")

    current += 1
    print_step(current, total_steps, f"Parsing [accent]{path}[/accent] …")

    from parser.ast_parser import parse_directory
    parsed = parse_directory(path, use_cache=not force)

    total_funcs = sum(len(f.get("functions", [])) for f in parsed)
    total_imports = sum(len(f.get("imports", [])) for f in parsed)
    print_info(f"Found {len(parsed)} files, {total_funcs} functions, {total_imports} imports")

    if not parsed:
        print_error("No Python files found.")
        raise SystemExit(1)

    current += 1
    print_step(current, total_steps, "Building dependency graph CSVs …")

    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), "data")
    os.makedirs(output_dir, exist_ok=True)

    from parser.graph_builder import build_csvs
    vertices_path = os.path.join(output_dir, "vertices.csv")
    edges_path = os.path.join(output_dir, "edges.csv")
    build_csvs(parsed, vertices_path=vertices_path, edges_path=edges_path)

    # Count results
    v_count = _count_csv_rows(vertices_path)
    e_count = _count_csv_rows(edges_path)

    current += 1
    print_step(current, total_steps, "Loading graph into TigerGraph …")

    try:
        from graph.tigergraph_client import get_connection
        from graph.load_data import load_vertices, load_edges

        conn = get_connection()
        lv = load_vertices(conn, vertices_path)
        le = load_edges(conn, edges_path)
        print_info(f"Loaded {lv} vertices and {le} edges into TigerGraph")
    except Exception as e:
        print_warning(f"Could not load into TigerGraph: {e}")
        print_info("CSVs are still available for manual loading.")

    # Register the project so future commands remember it
    from cli.project_registry import register_project
    proj = register_project(
        path=path,
        vertices=v_count,
        edges=e_count,
        files=len(parsed),
    )
    print_info(f"Project registered as [accent]{proj['name']}[/accent] (id: {proj['id']})")

    if query:
        current += 1
        print_step(current, total_steps, "Running impact analysis …")
        console.print()
        _run_impact_query(query, depth, mode=mode)

    # Summary
    console.print()
    print_success("Analysis complete!\n")

    table = make_table(
        title="Analysis Summary",
        columns=[
            ("Metric", "bold white"),
            ("Value", "cyan"),
        ],
        rows=[
            ["Files parsed", str(len(parsed))],
            ["Functions", str(total_funcs)],
            ["Imports", str(total_imports)],
            ["Graph vertices", str(v_count)],
            ["Graph edges", str(e_count)],
            ["Output dir", output_dir],
        ],
    )
    console.print(table)

    if not query:
        console.print()
        console.print('  [muted]Run a query:[/muted]  graphxploit query "What breaks if I change X?"')
        console.print('  [muted]Visualize:[/muted]    graphxploit visualize')

    console.print()


def _run_impact_query(query: str, depth: int, mode: str):
    """Run an impact query and display results."""
    from rich.panel import Panel

    try:
        from llm.query_parser import extract_target
        from llm.explainer import explain_impact
        from graph.tigergraph_client import get_connection
        from graph.target_resolver import resolve_target_id

        with console.status("[bold cyan]Extracting target …[/bold cyan]", spinner="dots"):
            parsed = extract_target(query)
        target = parsed["target"]
        target_type = parsed["type"]

        if target_type == "unknown":
            print_warning("Could not identify a specific function/file from your query.")
            return

        print_info(f"Target: [accent]{target}[/accent] ({target_type})")

        with console.status("[bold cyan]Traversing dependency graph …[/bold cyan]", spinner="dots"):
            target_id = resolve_target_id(target=target, target_type=target_type)
            conn = get_connection()
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

        if affected:
            node_names = [n.split("::")[-1] if "::" in n else n for n in affected]
            print_info(f"Found {len(affected)} affected components:")
            for name in node_names:
                console.print(f"    [warning]\u2192[/warning]  {name}")

            with console.status("[bold cyan]Generating AI explanation …[/bold cyan]", spinner="dots"):
                explanation = explain_impact(query, target, node_names, mode=mode)
            console.print()
            console.print(Panel(explanation, title=" AI Explanation", border_style="blue"))
        else:
            print_success(f"No downstream impact detected for '{target}'.")

    except (ConnectionError, OSError, RuntimeError) as e:
        print_warning(f"Impact query failed: {e}")
        print_info("Make sure TigerGraph and Ollama are running (graphxploit status).")


def _count_csv_rows(path: str) -> int:
    """Count data rows in a CSV file (excluding header)."""
    try:
        with open(path, "r") as f:
            return max(0, sum(1 for _ in f) - 1)
    except OSError:
        return 0


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
