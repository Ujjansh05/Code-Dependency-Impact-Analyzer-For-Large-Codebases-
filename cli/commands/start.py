"""code-impact start command."""

import click

from cli.console import print_banner, print_success, print_info, print_error, console
from cli.docker_manager import start_services, ensure_docker_installed


@click.command()
@click.option(
    "--tg-port", default=9000, show_default=True,
    help="Host port for TigerGraph REST API.",
)
@click.option(
    "--ollama-port", default=11434, show_default=True,
    help="Host port for Ollama API.",
)
@click.option(
    "--model", default="qwen2.5-coder:14b", show_default=True,
    help="Ollama model to pull on startup.",
)
@click.option(
    "--no-pull", is_flag=True, default=False,
    help="Skip pulling the Ollama model.",
)
def start(tg_port: int, ollama_port: int, model: str, no_pull: bool):
    """ Start TigerGraph and Ollama Docker services."""
    print_banner()

    if not ensure_docker_installed():
        raise SystemExit(1)

    print_info("Starting code-impact infrastructure …\n")

    pull_model = None if no_pull else model
    ok = start_services(tg_port=tg_port, ollama_port=ollama_port, pull_model=pull_model)

    if ok:
        console.print()
        print_success("All services are running!\n")
        console.print(f"  │  TigerGraph REST   →  [link]http://localhost:{tg_port}[/link]")
        console.print(f"  │  GraphStudio       →  [link]http://localhost:14240[/link]")
        console.print(f"  │  Ollama            →  [link]http://localhost:{ollama_port}[/link]")
        console.print()
        console.print("  [muted]Next step:[/muted]  code-impact analyze ./your-project")
    else:
        print_error("Some services failed to start. Check Docker logs.")
        raise SystemExit(1)
