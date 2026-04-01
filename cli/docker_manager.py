"""Manage Docker Compose lifecycle for TigerGraph + Ollama."""

import os
import shutil
import subprocess
import time
from pathlib import Path

from cli.console import console, print_success, print_error, print_info, print_warning

COMPOSE_TEMPLATE = """\
version: "3.8"

services:
  tigergraph:
    image: docker.io/tigergraph/tigergraph:3.9.3
    container_name: code_impact_tigergraph
    ports:
      - "{tg_port}:9000"
      - "{tg_studio_port}:14240"
    volumes:
      - code_impact_tg_data:/home/tigergraph/tigergraph/data
    ulimits:
      nofile:
        soft: 1000000
        hard: 1000000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/echo"]
      interval: 15s
      timeout: 10s
      retries: 20
      start_period: 60s

  ollama:
    image: ollama/ollama:latest
    container_name: code_impact_ollama
    ports:
      - "{ollama_port}:11434"
    volumes:
      - code_impact_ollama_data:/root/.ollama

volumes:
  code_impact_tg_data:
  code_impact_ollama_data:
"""

DATA_DIR = Path.home() / ".code-impact"
COMPOSE_PATH = DATA_DIR / "docker-compose.yml"


def ensure_docker_installed() -> bool:
    """Check if Docker and docker compose are available."""
    docker = shutil.which("docker")
    if not docker:
        print_error("Docker is not installed or not in PATH.")
        print_info("Install Docker: https://docs.docker.com/get-docker/")
        return False
    return True


def _run_compose(args: list[str], capture: bool = False) -> subprocess.CompletedProcess:
    """Run a `docker compose` command against our compose file."""
    cmd = ["docker", "compose", "-f", str(COMPOSE_PATH), "-p", "code-impact"] + args
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        cwd=str(DATA_DIR),
    )


def generate_compose_file(
    tg_port: int = 9000,
    tg_studio_port: int = 14240,
    ollama_port: int = 11434,
) -> Path:
    """Generate the docker-compose.yml from the embedded template."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    content = COMPOSE_TEMPLATE.format(
        tg_port=tg_port,
        tg_studio_port=tg_studio_port,
        ollama_port=ollama_port,
    )
    COMPOSE_PATH.write_text(content, encoding="utf-8")
    return COMPOSE_PATH


def start_services(
    tg_port: int = 9000,
    ollama_port: int = 11434,
    pull_model: str = "codellama:7b",
) -> bool:
    """Start TigerGraph and Ollama containers."""
    if not ensure_docker_installed():
        return False

    generate_compose_file(tg_port=tg_port, ollama_port=ollama_port)

    print_info("Starting Docker services …")
    result = _run_compose(["up", "-d"])
    if result.returncode != 0:
        print_error("Failed to start Docker services.")
        return False

    if not wait_for_service(f"http://localhost:{tg_port}/echo", "TigerGraph", timeout=180):
        return False

    if not wait_for_service(f"http://localhost:{ollama_port}/api/tags", "Ollama", timeout=30):
        print_warning("Ollama is not responding. LLM features will be unavailable.")

    if pull_model:
        pull_ollama_model(pull_model)

    return True


def stop_services(remove_volumes: bool = False) -> bool:
    """Stop and remove containers."""
    if not COMPOSE_PATH.exists():
        print_warning("No compose file found. Nothing to stop.")
        return True

    if not ensure_docker_installed():
        return False

    args = ["down"]
    if remove_volumes:
        args.append("-v")

    print_info("Stopping Docker services …")
    result = _run_compose(args)
    if result.returncode != 0:
        print_error("Failed to stop Docker services.")
        return False

    print_success("Docker services stopped.")
    return True


def get_service_status() -> list[dict[str, str]]:
    """Return a list of service statuses."""
    import requests

    services = []

    try:
        resp = requests.get("http://localhost:9000/echo", timeout=3)
        tg_status = " Running" if resp.status_code == 200 else " Unhealthy"
    except Exception:
        tg_status = " Stopped"

    services.append({
        "name": "TigerGraph",
        "port": "9000",
        "status": tg_status,
        "url": "http://localhost:9000",
    })

    services.append({
        "name": "GraphStudio",
        "port": "14240",
        "status": tg_status.replace("Running", "Running").replace("Stopped", "Stopped"),
        "url": "http://localhost:14240",
    })

    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        ollama_status = " Running" if resp.status_code == 200 else " Unhealthy"
    except Exception:
        ollama_status = " Stopped"

    services.append({
        "name": "Ollama (LLaMA)",
        "port": "11434",
        "status": ollama_status,
        "url": "http://localhost:11434",
    })

    return services


def wait_for_service(url: str, name: str, timeout: int = 120) -> bool:
    """Poll a URL until it responds or timeout."""
    import requests

    start = time.time()
    delay = 2

    with console.status(f"[info]Waiting for {name} …[/info]", spinner="dots"):
        while time.time() - start < timeout:
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    elapsed = round(time.time() - start, 1)
                    print_success(f"{name} is ready ({elapsed}s)")
                    return True
            except Exception:
                pass
            time.sleep(delay)
            delay = min(delay * 1.5, 10)

    print_error(f"{name} did not become ready within {timeout}s.")
    return False


def pull_ollama_model(model: str = "codellama:7b"):
    """Pull an Ollama model inside the Ollama container."""
    print_info(f"Pulling model '{model}' (this may take a few minutes) …")
    try:
        result = subprocess.run(
            ["docker", "exec", "code_impact_ollama", "ollama", "pull", model],
            capture_output=False,
            text=True,
        )
        if result.returncode == 0:
            print_success(f"Model '{model}' is ready.")
        else:
            print_warning(f"Could not pull model '{model}'. Pull it manually with:")
            console.print(f"    docker exec -it code_impact_ollama ollama pull {model}")
    except Exception:
        print_warning(f"Could not pull model. Ollama container may not be running.")


def are_services_running() -> bool:
    """Quick check if TigerGraph is reachable."""
    import requests
    try:
        resp = requests.get("http://localhost:9000/echo", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False
