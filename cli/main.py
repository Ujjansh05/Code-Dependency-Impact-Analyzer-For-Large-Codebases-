"""Click CLI entry point."""

import sys

import click

from cli import __version__


def _configure_stdio_for_unicode() -> None:
    """Avoid Windows cp1252 crashes when rendering Unicode output."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            # Best effort only: keep CLI usable even if stream is not reconfigurable.
            pass


_configure_stdio_for_unicode()


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(version=__version__, prog_name="graphxploit")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Enable verbose output.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool):
    """GraphXploit."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG, format="%(name)s │ %(message)s")


from cli.commands.start import start
from cli.commands.stop import stop
from cli.commands.status import status
from cli.commands.analyze import analyze
from cli.commands.parse import parse
from cli.commands.query import query
from cli.commands.serve import serve
from cli.commands.visualize import visualize
from cli.commands.projects import projects
from cli.commands.model import model

cli.add_command(start)
cli.add_command(stop)
cli.add_command(status)
cli.add_command(analyze)
cli.add_command(parse)
cli.add_command(query)
cli.add_command(serve)
cli.add_command(visualize)
cli.add_command(projects)
cli.add_command(model)


if __name__ == "__main__":
    cli()

