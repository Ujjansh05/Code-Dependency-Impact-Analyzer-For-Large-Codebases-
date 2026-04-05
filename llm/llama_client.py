"""HTTP client for Ollama API."""

import os
from typing import Any

import requests

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")


def _env_int(name: str, default: int) -> int:
    """Parse an int env var with fallback."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


DEFAULT_THREADS = max(1, (os.cpu_count() or 8) - 2)
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
OLLAMA_NUM_CTX = _env_int("OLLAMA_NUM_CTX", 2048)
OLLAMA_NUM_BATCH = _env_int("OLLAMA_NUM_BATCH", 128)
OLLAMA_NUM_THREAD = _env_int("OLLAMA_NUM_THREAD", DEFAULT_THREADS)
OLLAMA_FAST_NUM_CTX = _env_int("OLLAMA_FAST_NUM_CTX", 1024)
OLLAMA_FAST_NUM_BATCH = _env_int("OLLAMA_FAST_NUM_BATCH", 64)
OLLAMA_FAST_NUM_THREAD = _env_int("OLLAMA_FAST_NUM_THREAD", DEFAULT_THREADS)
OLLAMA_SLOW_NUM_CTX = _env_int("OLLAMA_SLOW_NUM_CTX", 3072)
OLLAMA_SLOW_NUM_BATCH = _env_int("OLLAMA_SLOW_NUM_BATCH", 128)
OLLAMA_SLOW_NUM_THREAD = _env_int("OLLAMA_SLOW_NUM_THREAD", DEFAULT_THREADS)

INFERENCE_MODES = {"fast", "slow", "balanced"}
DEFAULT_INFERENCE_MODE = os.getenv("OLLAMA_INFERENCE_MODE", "fast").strip().lower()
if DEFAULT_INFERENCE_MODE not in INFERENCE_MODES:
    DEFAULT_INFERENCE_MODE = "fast"


def normalize_mode(mode: str | None) -> str:
    """Normalize mode to one of: fast, slow, balanced."""
    candidate = (mode or DEFAULT_INFERENCE_MODE).strip().lower()
    if candidate in INFERENCE_MODES:
        return candidate
    return DEFAULT_INFERENCE_MODE


def _mode_options(mode: str, temperature: float, max_tokens: int) -> dict[str, Any]:
    """Return Ollama options for the selected inference mode."""
    selected = normalize_mode(mode)
    if selected == "fast":
        return {
            "temperature": temperature,
            "num_predict": max_tokens,
            "num_ctx": OLLAMA_FAST_NUM_CTX,
            "num_batch": OLLAMA_FAST_NUM_BATCH,
            "num_thread": OLLAMA_FAST_NUM_THREAD,
        }
    if selected == "slow":
        return {
            "temperature": temperature,
            "num_predict": max_tokens,
            "num_ctx": OLLAMA_SLOW_NUM_CTX,
            "num_batch": OLLAMA_SLOW_NUM_BATCH,
            "num_thread": OLLAMA_SLOW_NUM_THREAD,
        }

    # "balanced" preserves previous single-profile settings.
    return {
        "temperature": temperature,
        "num_predict": max_tokens,
        "num_ctx": OLLAMA_NUM_CTX,
        "num_batch": OLLAMA_NUM_BATCH,
        "num_thread": OLLAMA_NUM_THREAD,
    }


def generate(
    prompt: str,
    model: str = OLLAMA_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 512,
    mode: str | None = None,
) -> str:
    """Send a prompt to Ollama and return the generated text."""
    url = f"{OLLAMA_BASE_URL}/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": _mode_options(mode=mode or DEFAULT_INFERENCE_MODE,
                                 temperature=temperature,
                                 max_tokens=max_tokens),
    }

    try:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data.get("response", "")
    except requests.ConnectionError:
        return "[Error] Cannot connect to Ollama. Is it running?"
    except requests.Timeout:
        return "[Error] Ollama request timed out."
    except Exception as e:
        return f"[Error] Ollama error: {e}"


def check_health() -> bool:
    """Return True if Ollama is reachable."""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def list_models() -> list[str]:
    """Return a list of available model names."""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        return [m["name"] for m in models]
    except Exception:
        return []
