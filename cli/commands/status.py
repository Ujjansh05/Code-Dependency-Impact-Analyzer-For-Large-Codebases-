"""code-impact status command."""

import click

from cli.console import print_banner, console, make_table
from cli.docker_manager import get_service_status


@click.command()
def status():
    """ Check the health of all code-impact services."""
    print_banner()

    services = get_service_status()

    table = make_table(
        title="Service Status",
        columns=[
            ("Service", "bold white"),
            ("Port", "cyan"),
            ("Status", ""),
            ("URL", "dim"),
        ],
        rows=[
            [s["name"], s["port"], s["status"], s["url"]]
            for s in services
        ],
    )

    console.print(table)
    console.print()

    running = sum(1 for s in services if "" in s["status"])
    total = len(services)

    if running == total:
        console.print("  [success]All services are healthy.[/success]")
    elif running > 0:
        console.print(f"  [warning]{running}/{total} services running.[/warning]")
    else:
        console.print("  [error]No services are running.[/error]  Run [accent]code-impact start[/accent] first.")

    console.print()
