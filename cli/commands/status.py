"""graphxploit status command."""

import click

from cli.console import print_banner, console, make_table, print_info
from cli.docker_manager import get_service_status


@click.command()
def status():
    """Check the health of all graphxploit services."""
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

    running = sum(1 for s in services if "Running" in s["status"])
    total = len(services)

    if running == total:
        console.print("  [success]All services are healthy.[/success]")
    elif running > 0:
        console.print(f"  [warning]{running}/{total} services running.[/warning]")
    else:
        console.print("  [error]No services are running.[/error]  Run [accent]graphxploit start[/accent] first.")

    # Show active model info.
    try:
        from llm.model_registry import get_active_config
        active = get_active_config()
        if active:
            console.print(f"\n  [bold]Active Model:[/bold]  [accent]{active.name}[/accent]  ({active.provider} / {active.model_name})")
        else:
            console.print("\n  [muted]No active model. Run 'graphxploit model mount' to configure one.[/muted]")
    except (ImportError, OSError, ValueError):
        pass

    console.print()
