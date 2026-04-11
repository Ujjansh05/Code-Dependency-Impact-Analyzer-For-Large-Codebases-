"""graphxploit serve command."""

import click

from cli.console import print_banner, print_success, print_info, console


@click.command()
@click.option(
    "--host", default="0.0.0.0", show_default=True,
    help="Host to bind the server to.",
)
@click.option(
    "--port", "-p", default=8000, show_default=True,
    help="Port to serve on.",
)
@click.option(
    "--reload", "auto_reload", is_flag=True, default=False,
    help="Enable auto-reload for development.",
)
def serve(host: str, port: int, auto_reload: bool):
    """ Start the FastAPI backend server.

    \b
    Examples:
      graphxploit serve
      graphxploit serve --port 9090
      graphxploit serve --reload
    """
    print_banner()

    print_info(f"Starting FastAPI on [accent]{host}:{port}[/accent] …\n")

    console.print(f"  │  API docs   →  [link]http://localhost:{port}/docs[/link]")
    console.print(f"  │  Health     →  [link]http://localhost:{port}/health[/link]")
    console.print(f"  │  GraphData  →  [link]http://localhost:{port}/api/graph-data[/link]")
    console.print()

    if auto_reload:
        print_info("Auto-reload enabled (development mode)\n")

    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=auto_reload,
    )
