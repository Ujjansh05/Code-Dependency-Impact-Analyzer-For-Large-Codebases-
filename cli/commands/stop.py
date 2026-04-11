"""graphxploit stop command."""

import click

from cli.console import print_banner, print_success, print_info
from cli.docker_manager import stop_services


@click.command()
@click.option(
    "--volumes", is_flag=True, default=False,
    help="Also remove persistent data volumes (TigerGraph data, Ollama models).",
)
def stop(volumes: bool):
    """ Stop TigerGraph and Ollama Docker services."""
    print_banner()

    if volumes:
        print_info("Stopping services and removing volumes …\n")
    else:
        print_info("Stopping services (data volumes preserved) …\n")

    ok = stop_services(remove_volumes=volumes)
    if not ok:
        raise SystemExit(1)
