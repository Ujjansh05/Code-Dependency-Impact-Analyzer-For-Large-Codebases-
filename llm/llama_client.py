"""HTTP client for Ollama API."""

import os
from typing import Any

import requests

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "codellama:7b")


def generate(
    prompt: str,
    model: str = OLLAMA_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 512,
) -> str:
    """Send a prompt to Ollama and return the generated text."""
    url = f"{OLLAMA_BASE_URL}/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
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
