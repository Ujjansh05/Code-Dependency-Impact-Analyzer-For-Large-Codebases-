"""Rich console helpers and branding for the CLI."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from rich.theme import Theme

THEME = Theme({
    "info": "bright_cyan",
    "success": "bold bright_green",
    "warning": "bold bright_yellow",
    "error": "bold bright_red",
    "user": "bold white",
    "assistant": "bold bright_green",
    "system": "dim bright_blue",
    "highlight": "bold bright_magenta",
    "accent": "bold bright_cyan",
    "secondary": "bright_blue",
    "muted": "dim #a0a0a0",
    "border": "#3a3a3a",
    "prompt": "bold bright_green",
    "cursor": "blink bold white",
})

console = Console(theme=THEME)

BANNER = r"""
  ██████╗ ██████╗  █████╗ ██████╗ ██╗  ██╗██╗  ██╗██████╗ ██╗      ██████╗ ██╗████████╗
 ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██║  ██║╚██╗██╔╝██╔══██╗██║     ██╔═══██╗██║╚══██╔══╝
 ██║  ███╗██████╔╝███████║██████╔╝███████║ ╚███╔╝ ██████╔╝██║     ██║   ██║██║   ██║   
 ██║   ██║██╔══██╗██╔══██║██╔═══╝ ██╔══██║ ██╔██╗ ██╔═══╝ ██║     ██║   ██║██║   ██║   
 ╚██████╔╝██║  ██║██║  ██║██║     ██║  ██║██╔╝ ██╗██║     ███████╗╚██████╔╝██║   ██║   
  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝ ╚═════╝ ╚═╝   ╚═╝   
"""


def print_banner():
    """Display the startup banner."""
    text = Text(BANNER, style="bold red")
    console.print(text)
    console.print(
        "  [accent]GraphXploit[/accent]  │  "
        "[muted]If I change this → what will break?[/muted]\n"
    )


def print_success(message: str):
    """Print a success message."""
    console.print(f"  [success]✔[/success]  {message}")


def print_error(message: str):
    """Print an error message."""
    console.print(f"  [error]✘[/error]  {message}")


def print_warning(message: str):
    """Print a warning message."""
    console.print(f"  [warning]⚠[/warning]  {message}")


def print_info(message: str):
    """Print an info message."""
    console.print(f"  [info]ℹ[/info]  {message}")


def print_step(step: int, total: int, message: str):
    """Print a numbered step."""
    console.print(f"  [accent][{step}/{total}][/accent]  {message}")


def make_table(title: str, columns: list[tuple[str, str]], rows: list[list[str]]) -> Table:
    """Create a Rich table."""
    table = Table(title=title, show_header=True, header_style="bold cyan", border_style="dim")
    for name, style in columns:
        table.add_column(name, style=style)
    for row in rows:
        table.add_row(*row)
    return table


def make_panel(content: str, title: str = "", style: str = "blue") -> Panel:
    """Create a Rich panel."""
    return Panel(content, title=title, border_style=style, padding=(1, 2))
