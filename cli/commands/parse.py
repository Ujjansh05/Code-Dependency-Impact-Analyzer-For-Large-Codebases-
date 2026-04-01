"""code-impact parse command."""

import os
import click

from cli.console import (
    print_banner, print_success, print_error, print_info,
    print_step, console, make_table,
)


@click.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option(
    "--output-dir", "-o", default=None,
    help="Directory to write CSVs. Defaults to ./data/ inside the target project.",
)
@click.option(
    "--format", "output_format", type=click.Choice(["csv", "json"]), default="csv",
    show_default=True,
    help="Output format for the dependency data.",
)
def parse(path: str, output_dir: str | None, output_format: str):
    """ Parse a Python codebase and emit dependency graph CSVs.

    PATH is the root directory of the Python project to parse.

    \b
    Examples:
      code-impact parse ./myproject
      code-impact parse ./myproject -o ./output
      code-impact parse ./myproject --format json
    """
    print_banner()

    # Default output dir
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), "data")

    os.makedirs(output_dir, exist_ok=True)

    print_step(1, 3, f"Scanning [accent]{path}[/accent] for Python files …")

    from parser.utils import discover_python_files
    py_files = discover_python_files(path)

    if not py_files:
        print_error("No Python files found in the specified directory.")
        raise SystemExit(1)

    print_info(f"Found {len(py_files)} Python files")

    print_step(2, 3, "Parsing AST (functions, calls, imports) …")

    from parser.ast_parser import parse_directory
    parsed = parse_directory(path)

    total_funcs = sum(len(f.get("functions", [])) for f in parsed)
    total_imports = sum(len(f.get("imports", [])) for f in parsed)
    errors = sum(1 for f in parsed if f.get("error"))

    print_info(f"Extracted {total_funcs} functions, {total_imports} import statements")
    if errors:
        from cli.console import print_warning
        print_warning(f"{errors} files had syntax errors and were skipped")

    print_step(3, 3, f"Building dependency graph ({output_format.upper()}) …")

    if output_format == "csv":
        from parser.graph_builder import build_csvs
        vertices_path = os.path.join(output_dir, "vertices.csv")
        edges_path = os.path.join(output_dir, "edges.csv")
        build_csvs(parsed, vertices_path=vertices_path, edges_path=edges_path)
    else:
        # JSON output
        import json
        output_path = os.path.join(output_dir, "dependency_graph.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2)
        print_info(f"Written to {output_path}")

    # Summary
    console.print()
    print_success("Parsing complete!\n")

    table = make_table(
        title="Parse Summary",
        columns=[
            ("Metric", "bold white"),
            ("Value", "cyan"),
        ],
        rows=[
            ["Python files", str(len(py_files))],
            ["Functions extracted", str(total_funcs)],
            ["Import statements", str(total_imports)],
            ["Syntax errors", str(errors)],
            ["Output directory", output_dir],
        ],
    )
    console.print(table)
    console.print()
    console.print("  [muted]Next step:[/muted]  code-impact analyze " + path)
    console.print()
