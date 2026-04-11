"""graphxploit start command."""

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
    "--model", default="qwen2.5-coder:7b", show_default=True,
    help="Ollama model to pull on startup.",
)
@click.option(
    "--tg-image", default=None,
    help="TigerGraph Docker image tag (defaults to tigergraph/community:4.2.2).",
)
@click.option(
    "--tg-archive", default=None, type=click.Path(exists=True, resolve_path=True),
    help="Optional TigerGraph image archive file or directory to load before pull.",
)
@click.option(
    "--no-pull", is_flag=True, default=False,
    help="Skip pulling the Ollama model.",
)
def start(
    tg_port: int,
    ollama_port: int,
    model: str,
    tg_image: str | None,
    tg_archive: str | None,
    no_pull: bool,
):
    """Start TigerGraph and Ollama Docker services."""
    print_banner()

    if not ensure_docker_installed():
        raise SystemExit(1)

    print_info("Starting graphxploit infrastructure ...\n")

    pull_model = None if no_pull else model
    start_kwargs = {
        "tg_port": tg_port,
        "ollama_port": ollama_port,
        "pull_model": pull_model,
    }
    if tg_image:
        start_kwargs["tg_image"] = tg_image
    if tg_archive:
        start_kwargs["tg_archive"] = tg_archive

    ok = start_services(**start_kwargs)

    if ok:
        console.print()
        print_success("All services are running!\n")
        console.print(f"  |  TigerGraph REST   ->  [link]http://localhost:{tg_port}[/link]")
        console.print(f"  |  GraphStudio       ->  [link]http://localhost:14240[/link]")
        console.print(f"  |  Ollama            ->  [link]http://localhost:{ollama_port}[/link]")

        # Auto-register Ollama model in the model registry.
        try:
            from llm.model_registry import (
                find_by_provider_and_model, register_model,
                ModelConfig, get_active_config,
            )
            existing = find_by_provider_and_model("ollama", model)
            if not existing:
                is_first = get_active_config() is None
                register_model(ModelConfig(
                    provider="ollama",
                    model_name=model,
                    name=f"Ollama ({model})",
                    base_url=f"http://localhost:{ollama_port}",
                    is_active=is_first,
                ))
                if is_first:
                    print_info(f"Auto-registered [accent]{model}[/accent] as active model")
                else:
                    print_info(f"Auto-registered [accent]{model}[/accent] in model registry")

            active = get_active_config()
            if active:
                console.print(f"  |  Active Model      ->  [accent]{active.name}[/accent]")
        except Exception:
            pass

        console.print()
        console.print("  [muted]Next step:[/muted]  graphxploit analyze ./your-project")
    else:
        print_error("Some services failed to start. Check Docker logs.")
        raise SystemExit(1)
