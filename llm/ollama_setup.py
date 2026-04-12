"""Ollama bootstrap — install, start server, pull models automatically.

Provides a zero-friction setup experience so users never need to
manually install Ollama or pull models outside of GraphXploit.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import time
from typing import Callable

import requests


# ── Detection ───────────────────────────────────────────────────


def is_ollama_installed() -> bool:
    """Check if the `ollama` binary is on PATH."""
    return shutil.which("ollama") is not None


def is_ollama_running(base_url: str = "http://localhost:11434") -> bool:
    """Return True if the Ollama server is reachable."""
    try:
        resp = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=5)
        return resp.status_code == 200
    except (requests.RequestException, OSError):
        return False


def list_local_models(base_url: str = "http://localhost:11434") -> list[str]:
    """Return the list of models already pulled locally."""
    try:
        resp = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=10)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        return [m["name"] for m in models]
    except (requests.RequestException, OSError):
        return []


def is_model_available(
    model_name: str, base_url: str = "http://localhost:11434"
) -> bool:
    """Check if a specific model is already available locally.

    Handles partial name matching (e.g. 'qwen2.5-coder:7b' matches
    'qwen2.5-coder:7b' in the tag list).
    """
    available = list_local_models(base_url)
    name_lower = model_name.lower().strip()
    for m in available:
        m_lower = m.lower().strip()
        if m_lower == name_lower:
            return True
        # Handle the case where `:latest` is implicit.
        if m_lower == f"{name_lower}:latest" or f"{m_lower}:latest" == name_lower:
            return True
    return False


# ── Installation ────────────────────────────────────────────────


def install_ollama(
    on_status: Callable[[str], None] | None = None,
) -> bool:
    """Attempt to install Ollama automatically.

    - Linux/macOS: uses the official install script.
    - Windows: prints manual instructions (requires admin).

    Returns True if installation succeeded (or was already installed).
    """
    if is_ollama_installed():
        return True

    system = platform.system().lower()

    if system == "linux" or system == "darwin":
        if on_status:
            on_status("Downloading and installing Ollama ...")
        try:
            result = subprocess.run(
                ["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                if on_status:
                    on_status("Ollama installed successfully!")
                return True
            else:
                if on_status:
                    on_status(
                        f"Installation failed (exit {result.returncode}). "
                        f"Try manually: curl -fsSL https://ollama.com/install.sh | sh"
                    )
                return False
        except subprocess.TimeoutExpired:
            if on_status:
                on_status("Installation timed out. Try manually: curl -fsSL https://ollama.com/install.sh | sh")
            return False
        except Exception as e:
            if on_status:
                on_status(f"Installation error: {e}")
            return False

    elif system == "windows":
        if on_status:
            on_status(
                "Automatic installation is not supported on Windows.\n"
                "  Download Ollama from: https://ollama.com/download/windows\n"
                "  After installing, restart your terminal and try again."
            )
        return False

    else:
        if on_status:
            on_status(f"Unsupported OS '{system}'. Install Ollama manually from https://ollama.com")
        return False


# ── Server Management ───────────────────────────────────────────


def start_ollama_server(
    base_url: str = "http://localhost:11434",
    on_status: Callable[[str], None] | None = None,
    timeout: int = 30,
) -> bool:
    """Start the Ollama server in the background and wait for it to be ready.

    Returns True if the server is running after this call.
    """
    if is_ollama_running(base_url):
        return True

    ollama_bin = shutil.which("ollama")
    if not ollama_bin:
        if on_status:
            on_status("Cannot start Ollama: binary not found on PATH.")
        return False

    if on_status:
        on_status("Starting Ollama server ...")

    try:
        # Spawn 'ollama serve' as a detached background process.
        env = os.environ.copy()
        if sys.platform == "win32":
            # On Windows, use CREATE_NEW_PROCESS_GROUP to detach.
            subprocess.Popen(
                [ollama_bin, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.DETACHED_PROCESS,
            )
        else:
            subprocess.Popen(
                [ollama_bin, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                start_new_session=True,
            )
    except Exception as e:
        if on_status:
            on_status(f"Failed to start Ollama: {e}")
        return False

    # Wait for the server to become reachable.
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_ollama_running(base_url):
            if on_status:
                on_status("Ollama server is ready!")
            return True
        time.sleep(1)

    if on_status:
        on_status(
            f"Ollama did not become ready within {timeout}s. "
            "Try starting it manually: ollama serve"
        )
    return False


# ── Model Pulling ───────────────────────────────────────────────


def pull_model(
    model_name: str,
    base_url: str = "http://localhost:11434",
    on_progress: Callable[[str, int, int], None] | None = None,
    on_status: Callable[[str], None] | None = None,
) -> bool:
    """Pull a model from the Ollama registry with streaming progress.

    Args:
        model_name: The model to pull (e.g. 'qwen2.5-coder:7b').
        base_url: Ollama server URL.
        on_progress: Callback(status_text, completed_bytes, total_bytes)
                     called as download progresses.
        on_status: Callback(message) for status text updates.

    Returns True if the pull completed successfully.
    """
    url = f"{base_url.rstrip('/')}/api/pull"

    if on_status:
        on_status(f"Pulling '{model_name}' ...")

    try:
        resp = requests.post(
            url,
            json={"name": model_name, "stream": True},
            stream=True,
            timeout=600,
        )
        resp.raise_for_status()
    except requests.ConnectionError:
        if on_status:
            on_status("Cannot connect to Ollama. Is the server running?")
        return False
    except Exception as e:
        if on_status:
            on_status(f"Pull request failed: {e}")
        return False

    last_status = ""
    try:
        for line in resp.iter_lines():
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            status = data.get("status", "")
            completed = data.get("completed", 0)
            total = data.get("total", 0)

            # Report progress for download phases.
            if on_progress and total > 0:
                on_progress(status, completed, total)
            elif on_status and status != last_status:
                on_status(status)
                last_status = status

            # Check for errors in the stream.
            if "error" in data:
                if on_status:
                    on_status(f"Pull error: {data['error']}")
                return False
    except Exception as e:
        if on_status:
            on_status(f"Error during pull: {e}")
        return False

    if on_status:
        on_status(f"Model '{model_name}' pulled successfully!")
    return True


# ── Orchestrator ────────────────────────────────────────────────


def ensure_ollama_ready(
    model_name: str,
    base_url: str = "http://localhost:11434",
    on_status: Callable[[str], None] | None = None,
    on_progress: Callable[[str, int, int], None] | None = None,
    auto_install: bool = False,
    auto_start: bool = True,
    auto_pull: bool = True,
) -> tuple[bool, str]:
    """Full orchestrator: ensure Ollama is installed, running, and model is available.

    Returns (success, message).
    """
    # Step 1: Check/install Ollama.
    if not is_ollama_installed():
        if auto_install:
            success = install_ollama(on_status=on_status)
            if not success:
                return False, "Ollama installation failed."
        else:
            return False, (
                "Ollama is not installed.\n"
                "  Install it with: curl -fsSL https://ollama.com/install.sh | sh\n"
                "  Or visit: https://ollama.com"
            )

    # Step 2: Check/start server.
    if not is_ollama_running(base_url):
        if auto_start:
            success = start_ollama_server(
                base_url=base_url, on_status=on_status
            )
            if not success:
                return False, "Failed to start Ollama server."
        else:
            return False, (
                f"Ollama server is not running at {base_url}.\n"
                "  Start it with: ollama serve"
            )

    # Step 3: Check/pull model.
    if is_model_available(model_name, base_url):
        if on_status:
            on_status(f"Model '{model_name}' is already available locally.")
        return True, "ready"

    if auto_pull:
        success = pull_model(
            model_name=model_name,
            base_url=base_url,
            on_progress=on_progress,
            on_status=on_status,
        )
        if not success:
            return False, f"Failed to pull model '{model_name}'."
        return True, "pulled"
    else:
        return False, (
            f"Model '{model_name}' is not available locally.\n"
            f"  Pull it with: ollama pull {model_name}"
        )
