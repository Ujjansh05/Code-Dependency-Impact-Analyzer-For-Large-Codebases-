"""Manage Docker Compose lifecycle for TigerGraph + Ollama."""

import os
import shutil
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

from cli.console import console, print_error, print_info, print_success, print_warning

DEFAULT_TG_IMAGE = "tigergraph/community:4.2.2"
DEFAULT_TG_ARCHIVE_DIR = Path.home() / "Downloads" / "tigergraph-4.2.2-community-docker-image"
TG_IMAGE_ENV = "TG_DOCKER_IMAGE"
TG_ARCHIVE_ENV = "TG_DOCKER_ARCHIVE"
TG_ARCHIVE_DIR_ENV = "TG_DOCKER_ARCHIVE_DIR"

COMPOSE_TEMPLATE = """\
services:
  tigergraph:
    image: {tg_image}
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
    gpus: all
    ports:
      - "{ollama_port}:11434"
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
    volumes:
      - code_impact_ollama_data:/root/.ollama

volumes:
  code_impact_tg_data:
  code_impact_ollama_data:
"""

DATA_DIR = Path.home() / ".graphxploit"
COMPOSE_PATH = DATA_DIR / "docker-compose.yml"


def ensure_docker_installed() -> bool:
    """Check if Docker and docker compose are available."""
    docker = shutil.which("docker")
    if not docker:
        print_error("Docker is not installed or not in PATH.")
        print_info("Install Docker: https://docs.docker.com/get-docker/")
        return False
    return True


def _run_command(
    args: list[str],
    *,
    capture: bool = False,
    cwd: Path | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        capture_output=capture,
        text=True,
        cwd=str(cwd) if cwd else None,
        input=input_text,
    )


def _run_compose(args: list[str], capture: bool = False) -> subprocess.CompletedProcess:
    """Run a `docker compose` command against our compose file."""
    cmd = ["docker", "compose", "-f", str(COMPOSE_PATH), "-p", "graphxploit"] + args
    return _run_command(cmd, capture=capture, cwd=DATA_DIR)


def _image_exists(image: str) -> bool:
    result = _run_command(["docker", "image", "inspect", image], capture=True)
    return result.returncode == 0


def _archive_candidates(path_hint: Path) -> list[Path]:
    if path_hint.is_file():
        return [path_hint]
    if path_hint.is_dir() and (path_hint / "manifest.json").exists():
        return [path_hint]
    if not path_hint.is_dir():
        return []

    candidates: list[Path] = []
    for pattern in ("*.tar", "*.tar.gz", "*.tgz"):
        candidates.extend(path_hint.glob(pattern))
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates


def _resolve_tg_archive_path(tg_archive: str | None) -> Path | None:
    candidates: list[Path] = []

    if tg_archive:
        candidates.extend(_archive_candidates(Path(tg_archive).expanduser()))
    else:
        env_archive = os.getenv(TG_ARCHIVE_ENV, "").strip()
        if env_archive:
            candidates.extend(_archive_candidates(Path(env_archive).expanduser()))

        archive_dir = os.getenv(TG_ARCHIVE_DIR_ENV, "").strip()
        if archive_dir:
            candidates.extend(_archive_candidates(Path(archive_dir).expanduser()))
        else:
            candidates.extend(_archive_candidates(DEFAULT_TG_ARCHIVE_DIR))

    return candidates[0] if candidates else None


def _load_tg_image_from_archive(archive_path: Path) -> bool:
    print_info(f"Loading TigerGraph image from archive: {archive_path}")
    if archive_path.is_file():
        result = _run_command(["docker", "load", "-i", str(archive_path)])
        return result.returncode == 0

    if archive_path.is_dir() and (archive_path / "manifest.json").exists():
        temp_tar_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tmp:
                temp_tar_path = Path(tmp.name)
            with tarfile.open(temp_tar_path, "w") as tar:
                for child in archive_path.iterdir():
                    tar.add(child, arcname=child.name)
            result = _run_command(["docker", "load", "-i", str(temp_tar_path)])
            return result.returncode == 0
        finally:
            if temp_tar_path and temp_tar_path.exists():
                temp_tar_path.unlink(missing_ok=True)

    return False


def _pull_tg_image(image: str) -> bool:
    print_info(f"Pulling TigerGraph image: {image}")
    result = _run_command(["docker", "pull", image])
    return result.returncode == 0


def ensure_tigergraph_image_available(image: str, tg_archive: str | None = None) -> bool:
    """Ensure the target TigerGraph image exists locally."""
    if _image_exists(image):
        return True

    archive_path = _resolve_tg_archive_path(tg_archive)
    if archive_path:
        if _load_tg_image_from_archive(archive_path) and _image_exists(image):
            print_success(f"TigerGraph image is ready: {image}")
            return True
        print_warning("Image archive load did not produce the expected TigerGraph image tag.")

    if _pull_tg_image(image) and _image_exists(image):
        print_success(f"TigerGraph image is ready: {image}")
        return True

    print_error(f"Unable to prepare TigerGraph image: {image}")
    return False


def _ensure_tigergraph_services_started() -> None:
    # Community images can require explicit startup of TG services.
    gadmin_binary = _find_gadmin_binary()
    if not gadmin_binary:
        return
    _run_command(
        [
            "docker",
            "exec",
            "code_impact_tigergraph",
            "sh",
            "-lc",
            f"{gadmin_binary} start all >/dev/null 2>&1 || true",
        ]
    )


def _find_gadmin_binary() -> str | None:
    probe = _run_command(
        [
            "docker",
            "exec",
            "code_impact_tigergraph",
            "sh",
            "-lc",
            "command -v gadmin || "
            "( [ -x /home/tigergraph/tigergraph/app/cmd/gadmin ] && "
            "echo /home/tigergraph/tigergraph/app/cmd/gadmin ) || "
            "find /home/tigergraph/tigergraph/app -name gadmin 2>/dev/null | head -n 1",
        ],
        capture=True,
    )
    if probe.returncode != 0:
        return None
    path = probe.stdout.strip().splitlines()
    return path[0].strip() if path else None


def _find_gsql_binary() -> str | None:
    probe = _run_command(
        [
            "docker",
            "exec",
            "code_impact_tigergraph",
            "sh",
            "-lc",
            "command -v gsql || "
            "( [ -x /home/tigergraph/tigergraph/app/cmd/gsql ] && "
            "echo /home/tigergraph/tigergraph/app/cmd/gsql ) || "
            "find /home/tigergraph/tigergraph/app -name gsql 2>/dev/null | head -n 1",
        ],
        capture=True,
    )
    if probe.returncode != 0:
        return None
    path = probe.stdout.strip().splitlines()
    return path[0].strip() if path else None


def _tigergraph_stale_volume_hint() -> bool:
    logs = _run_command(
        ["docker", "logs", "--tail", "120", "code_impact_tigergraph"],
        capture=True,
    )
    combined = f"{logs.stdout}\n{logs.stderr}".lower()
    return "lstat /home/tigergraph/tigergraph/app/3.9.3" in combined


def _graph_exists(graph_name: str, gsql_binary: str) -> bool:
    result = _run_command(
        [
            "docker",
            "exec",
            "-i",
            "code_impact_tigergraph",
            gsql_binary,
            "-u",
            "tigergraph",
            "-p",
            "tigergraph",
        ],
        capture=True,
        input_text="ls\n",
    )
    if result.returncode != 0:
        return False
    return graph_name in result.stdout


def _queries_installed(graph_name: str) -> bool:
    import requests

    try:
        impact_resp = requests.get(
            f"http://localhost:9000/query/{graph_name}/impact_analysis",
            params={"start_func": "func::missing::node", "max_depth": 1},
            timeout=5,
        )
        hop_resp = requests.get(
            f"http://localhost:9000/query/{graph_name}/hop_detection",
            params={"start_node": "file::missing", "num_hops": 1},
            timeout=5,
        )
        return impact_resp.status_code != 404 and hop_resp.status_code != 404
    except (requests.RequestException, OSError):
        return False


def _run_gsql_script(script_path: Path, gsql_binary: str) -> bool:
    if not script_path.exists():
        print_warning(f"GSQL script not found: {script_path}")
        return False

    container_script = f"/tmp/{script_path.name}"
    copy_result = _run_command(
        ["docker", "cp", str(script_path), f"code_impact_tigergraph:{container_script}"],
        capture=True,
    )
    if copy_result.returncode != 0:
        print_warning(f"Failed to copy GSQL script into container: {script_path.name}")
        return False

    result = _run_command(
        [
            "docker",
            "exec",
            "code_impact_tigergraph",
            gsql_binary,
            "-u",
            "tigergraph",
            "-p",
            "tigergraph",
            container_script,
        ],
        capture=True,
    )
    _run_command(
        [
            "docker",
            "exec",
            "code_impact_tigergraph",
            "sh",
            "-lc",
            f"rm -f {container_script} >/dev/null 2>&1 || true",
        ]
    )
    if result.returncode == 0:
        return True

    combined = f"{result.stdout}\n{result.stderr}".lower()
    if "already exists" in combined:
        return True

    if "license has expired" in combined:
        print_warning("TigerGraph reported an expired license while applying GSQL scripts.")
    else:
        print_warning(f"Failed to apply GSQL script: {script_path.name}")
    return False


def bootstrap_codegraph_if_missing() -> bool:
    """Install schema + queries when CodeGraph or installed queries are missing."""
    graph_name = os.getenv("TG_GRAPH_NAME", "CodeGraph")
    gsql_binary = _find_gsql_binary()
    if not gsql_binary:
        print_warning("Could not locate gsql binary inside TigerGraph container.")
        return False

    graph_exists = _graph_exists(graph_name, gsql_binary)
    if not graph_exists:
        print_info(f"Initializing TigerGraph graph '{graph_name}' from bundled GSQL scripts...")
    else:
        print_info(f"TigerGraph graph '{graph_name}' already exists.")

    project_root = Path(__file__).resolve().parents[1]
    schema_path = project_root / "graph" / "schema.gsql"
    queries_path = project_root / "graph" / "queries.gsql"

    if not graph_exists:
        if not _run_gsql_script(schema_path, gsql_binary):
            return False

    if _queries_installed(graph_name):
        print_success("TigerGraph installed queries are ready.")
        return True

    if not _run_gsql_script(queries_path, gsql_binary):
        return False

    print_success(f"TigerGraph graph '{graph_name}' is ready.")
    return True


def generate_compose_file(
    tg_port: int = 9000,
    tg_studio_port: int = 14240,
    ollama_port: int = 11434,
    tg_image: str | None = None,
) -> Path:
    """Generate the docker-compose.yml from the embedded template."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    content = COMPOSE_TEMPLATE.format(
        tg_image=tg_image or os.getenv(TG_IMAGE_ENV, DEFAULT_TG_IMAGE),
        tg_port=tg_port,
        tg_studio_port=tg_studio_port,
        ollama_port=ollama_port,
    )
    COMPOSE_PATH.write_text(content, encoding="utf-8")
    return COMPOSE_PATH


def start_services(
    tg_port: int = 9000,
    ollama_port: int = 11434,
    pull_model: str | None = "qwen2.5-coder:7b",
    tg_image: str | None = None,
    tg_archive: str | None = None,
) -> bool:
    """Start TigerGraph and Ollama containers."""
    if not ensure_docker_installed():
        return False

    resolved_tg_image = tg_image or os.getenv(TG_IMAGE_ENV, DEFAULT_TG_IMAGE)
    if not ensure_tigergraph_image_available(resolved_tg_image, tg_archive=tg_archive):
        return False

    generate_compose_file(
        tg_port=tg_port,
        ollama_port=ollama_port,
        tg_image=resolved_tg_image,
    )

    print_info("Starting Docker services ...")
    result = _run_compose(["up", "-d"])
    if result.returncode != 0:
        print_error("Failed to start Docker services.")
        return False

    _ensure_tigergraph_services_started()

    if not wait_for_service(f"http://localhost:{tg_port}/echo", "TigerGraph", timeout=420):
        if _tigergraph_stale_volume_hint():
            print_warning(
                "TigerGraph detected stale data from an older image version. "
                "Run `graphxploit stop --volumes` once, then start again."
            )
        return False

    if not bootstrap_codegraph_if_missing():
        print_warning("TigerGraph graph bootstrap did not complete cleanly.")

    if not wait_for_service(f"http://localhost:{ollama_port}/api/tags", "Ollama", timeout=45):
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

    print_info("Stopping Docker services ...")
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
    except (requests.RequestException, OSError):
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
    except (requests.RequestException, OSError):
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

    with console.status(f"[info]Waiting for {name} ...[/info]", spinner="dots"):
        while time.time() - start < timeout:
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    elapsed = round(time.time() - start, 1)
                    print_success(f"{name} is ready ({elapsed}s)")
                    return True
            except (requests.RequestException, OSError):
                pass
            time.sleep(delay)
            delay = min(delay * 1.5, 10)

    print_error(f"{name} did not become ready within {timeout}s.")
    return False


def pull_ollama_model(model: str = "qwen2.5-coder:7b"):
    """Pull an Ollama model inside the Ollama container."""
    print_info(f"Pulling model '{model}' (this may take a few minutes) ...")
    try:
        result = _run_command(["docker", "exec", "code_impact_ollama", "ollama", "pull", model])
        if result.returncode == 0:
            print_success(f"Model '{model}' is ready.")
        else:
            print_warning(f"Could not pull model '{model}'. Pull it manually with:")
            console.print(f"    docker exec -it code_impact_ollama ollama pull {model}")
    except (subprocess.SubprocessError, OSError):
        print_warning("Could not pull model. Ollama container may not be running.")


def are_services_running() -> bool:
    """Quick check if TigerGraph is reachable."""
    import requests

    try:
        resp = requests.get("http://localhost:9000/echo", timeout=3)
        return resp.status_code == 200
    except (requests.RequestException, OSError):
        return False
