"""code-impact visualize command."""

import os
import sys
import webbrowser
import threading
import click

from cli.console import print_banner, print_success, print_info, print_step, print_error, print_warning, console


def _pick_project_interactive():
    """Show an interactive project picker when no PATH is given."""
    from cli.project_registry import list_projects

    projects = list_projects()
    if not projects:
        print_error("No projects registered yet.")
        print_info('Run [accent]code-impact analyze ./your-project[/accent] first to register a project.')
        raise SystemExit(1)

    console.print()
    console.print("  [accent]Registered Projects[/accent]")
    console.print()

    for i, p in enumerate(projects, 1):
        last = p.get("last_analyzed", "n/a")
        if "T" in last:
            last = last.split("T")[0]
        console.print(
            f"    [bold cyan]{i}[/bold cyan])  [bold white]{p['name']}[/bold white]  "
            f"[muted]({p['files']} files, {p['vertices']} vertices)[/muted]"
        )
        console.print(f"        [muted]{p['path']}[/muted]")
        console.print(f"        [muted]Last analyzed: {last}[/muted]")
        console.print()

    console.print()
    choice = click.prompt(
        "  Select a project number",
        type=click.IntRange(1, len(projects)),
    )
    return projects[choice - 1]


@click.command()
@click.argument("path", required=False, default=None,
                type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option(
    "--port", "-p", default=8000, show_default=True,
    help="Port to serve on.",
)
@click.option(
    "--no-browser", is_flag=True, default=False,
    help="Do not open the browser automatically.",
)
def visualize(path: str | None, port: int, no_browser: bool):
    """Visualize a codebase dependency graph in the browser.

    If PATH is omitted, shows a list of previously analyzed projects
    that you can pick from.

    \b
    Examples:
      code-impact visualize
      code-impact visualize ./myproject
      code-impact visualize --port 9090
    """
    print_banner()

    # If no path given, let the user pick from the registry
    if path is None:
        project = _pick_project_interactive()
        path = project["path"]
        if not os.path.isdir(path):
            print_error(f"Project directory no longer exists: {path}")
            print_info("The original directory may have been moved or deleted.")
            raise SystemExit(1)
        print_info(f"Using project [accent]{project['name']}[/accent]")
    else:
        # Register or update this project 
        from cli.project_registry import register_project
        register_project(path=path)

    current = 1
    total_steps = 3

    print_step(current, total_steps, f"Parsing [accent]{path}[/accent] for visualization …")
    from parser.ast_parser import parse_directory
    parsed = parse_directory(path)

    if not parsed:
        print_error("No Python files found.")
        raise SystemExit(1)

    print_info(f"Found {len(parsed)} files. Building graph …")

    output_dir = os.path.join(os.getcwd(), "data")
    os.makedirs(output_dir, exist_ok=True)

    from parser.graph_builder import build_csvs
    vertices_path = os.path.join(output_dir, "vertices.csv")
    edges_path = os.path.join(output_dir, "edges.csv")
    build_csvs(parsed, vertices_path=vertices_path, edges_path=edges_path)

    # Update registry with fresh stats
    from cli.project_registry import register_project
    def _count(p):
        try:
            with open(p, "r") as f:
                return max(0, sum(1 for _ in f) - 1)
        except Exception:
            return 0
    register_project(
        path=path,
        vertices=_count(vertices_path),
        edges=_count(edges_path),
        files=len(parsed),
    )

    print_success(f"Graph built at {output_dir}")

    current += 1
    print_step(current, total_steps, "Preparing server …")

    # Check if the frontend is built
    frontend_dist = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
    if not os.path.exists(frontend_dist):
        print_error(f"Frontend build directory not found at {frontend_dist}")
        print_info("Please build the frontend: cd frontend && npm run build")
        raise SystemExit(1)

    current += 1
    url = f"http://localhost:{port}"
    print_step(current, total_steps, f"Starting standalone server at [link]{url}[/link] …")

    if not no_browser:
        console.print()
        print_info("Opening browser automatically...")
        def open_browser():
            import time
            time.sleep(1.5)
            webbrowser.open(url)
        threading.Thread(target=open_browser, daemon=True).start()

    console.print()
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )
