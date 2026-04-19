"""graphxploit serve command."""

import os
import pathlib
import secrets
import stat
import subprocess
import sys

import re

import click

from cli.console import print_banner, print_info, print_warning, console

# Where the auto-generated API key is persisted between runs.
_KEY_DIR = pathlib.Path.home() / ".graphxploit"
_KEY_FILE = _KEY_DIR / "server.key"


def _load_or_create_api_key() -> str:
    """Return the persistent server API key, creating it if it does not exist.

    The key file is created with mode 0600 so only the current user can read it.
    """
    _KEY_DIR.mkdir(parents=True, exist_ok=True)

    if _KEY_FILE.exists():
        key = _KEY_FILE.read_text(encoding="utf-8").strip()
        if key:
            return key

    # Generate a new cryptographically-random 32-byte hex key.
    key = secrets.token_hex(32)
    _KEY_FILE.write_text(key, encoding="utf-8")

    # Restrict permissions: owner read/write only (POSIX).
    try:
        _KEY_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except (AttributeError, NotImplementedError, OSError):
        # Windows does not support POSIX chmod — best-effort.
        pass

    return key


def _inject_key_into_dist(api_key: str) -> None:
    """Patch frontend/dist/index.html with the real API key.

    Replaces the placeholder   window.__GX_API_KEY__ = '';   with the
    actual key so the built React app sends it automatically.
    """
    project_root = pathlib.Path(__file__).resolve().parents[2]
    dist_index = project_root / "frontend" / "dist" / "index.html"
    if not dist_index.exists():
        return  # Frontend not built yet — skip.

    html = dist_index.read_text(encoding="utf-8")
    # Replace the placeholder value (single or double-quoted).
    patched = re.sub(
        r"window\.__GX_API_KEY__\s*=\s*['\"][^'\"]*['\"]\s*;",
        f"window.__GX_API_KEY__ = '{api_key}';",
        html,
    )
    if patched != html:
        dist_index.write_text(patched, encoding="utf-8")


@click.command()
@click.option(
    "--host",
    default="127.0.0.1",
    show_default=True,
    help="Host to bind the server to.  Defaults to localhost (127.0.0.1).",
)
@click.option(
    "--port", "-p",
    default=8000,
    show_default=True,
    help="Port to serve on.",
)
@click.option(
    "--dev",
    is_flag=True,
    default=False,
    help=(
        "Enable development mode: auto-reload, Swagger /docs, verbose logging. "
        "NEVER use in production."
    ),
)
@click.option(
    "--reset-key",
    is_flag=True,
    default=False,
    help="Generate a new API key (invalidates existing sessions).",
)
def serve(host: str, port: int, dev: bool, reset_key: bool):
    """Start the GraphXploit backend server.

    \\b
    This command is the only supported way to launch GraphXploit.
    It automatically manages the API key required by the frontend.

    \\b
    Examples:
      graphxploit serve                   # localhost:8000
      graphxploit serve --port 9090
      graphxploit serve --dev             # development mode (hot-reload + /docs)
      graphxploit serve --host 0.0.0.0   # expose on all interfaces (non-default)
    """
    print_banner()

    # ── Safety warning for public binding ────────────────────────────────────
    if host not in ("127.0.0.1", "localhost"):
        print_warning(
            f"You are binding to [bold]{host}[/bold]. "
            "The server will be reachable from other machines on the network. "
            "Make sure a firewall is in place."
        )

    # ── API key management ────────────────────────────────────────────────────
    if reset_key and _KEY_FILE.exists():
        _KEY_FILE.unlink()
        print_info("Previous API key deleted. A new one will be generated.")

    api_key = _load_or_create_api_key()

    # ── Print launch info ─────────────────────────────────────────────────────
    console.print()
    console.print(f"  [bold cyan]GraphXploit[/bold cyan] is starting …")
    console.print()
    console.print(f"  [dim]Backend URL[/dim]    →  [link]http://{host}:{port}[/link]")
    console.print(f"  [dim]Health check[/dim]   →  [link]http://{host}:{port}/health[/link]")
    if dev:
        console.print(f"  [dim]API docs[/dim]      →  [link]http://{host}:{port}/docs[/link]  [yellow](dev mode)[/yellow]")
    console.print()
    console.print(f"  [bold yellow]API Key[/bold yellow]       →  [dim]{api_key}[/dim]")
    console.print(f"  [dim]Key file[/dim]       →  {_KEY_FILE}")
    console.print()
    console.print(
        "  [dim]The frontend uses this key automatically. "
        "You only need it for direct API calls.[/dim]"
    )
    console.print()

    if dev:
        print_warning("Development mode is ON. Do not expose this server publicly.")

    # ── Build environment for child process ───────────────────────────────────
    env = os.environ.copy()
    env["GRAPHXPLOIT_API_KEY"] = api_key
    env["GRAPHXPLOIT_DEV"] = "true" if dev else "false"
    # Ensure CORS allows the Vite dev server when in dev mode.
    if dev and "CORS_ORIGINS" not in env:
        env["CORS_ORIGINS"] = "http://localhost:3000"

    # ── Inject key into built frontend ────────────────────────────────────────
    _inject_key_into_dist(api_key)

    # ── Launch uvicorn ────────────────────────────────────────────────────────
    cmd = [
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--host", host,
        "--port", str(port),
    ]
    if dev:
        cmd.append("--reload")

    print_info(f"Starting FastAPI on [accent]{host}:{port}[/accent] …\n")

    try:
        subprocess.run(cmd, env=env, check=False)
    except KeyboardInterrupt:
        console.print("\n[dim]Server stopped.[/dim]")
