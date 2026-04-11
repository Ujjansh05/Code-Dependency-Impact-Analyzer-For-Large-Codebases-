"""Ollama model adapter — migrated from the original llama_client.py."""

import os
from typing import Any

import requests

from llm.adapters.base import ModelAdapter, ModelCapabilities


# Preserve the existing inference-mode tuning logic.
def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


DEFAULT_THREADS = max(1, (os.cpu_count() or 8) - 2)

_MODE_DEFAULTS: dict[str, dict[str, int]] = {
    "fast": {
        "num_ctx": _env_int("OLLAMA_FAST_NUM_CTX", 1024),
        "num_batch": _env_int("OLLAMA_FAST_NUM_BATCH", 64),
        "num_thread": _env_int("OLLAMA_FAST_NUM_THREAD", DEFAULT_THREADS),
    },
    "balanced": {
        "num_ctx": _env_int("OLLAMA_NUM_CTX", 2048),
        "num_batch": _env_int("OLLAMA_NUM_BATCH", 128),
        "num_thread": _env_int("OLLAMA_NUM_THREAD", DEFAULT_THREADS),
    },
    "slow": {
        "num_ctx": _env_int("OLLAMA_SLOW_NUM_CTX", 3072),
        "num_batch": _env_int("OLLAMA_SLOW_NUM_BATCH", 128),
        "num_thread": _env_int("OLLAMA_SLOW_NUM_THREAD", DEFAULT_THREADS),
    },
}

INFERENCE_MODES = {"fast", "slow", "balanced"}


class OllamaAdapter(ModelAdapter):
    """Adapter for Ollama-hosted models (local or remote)."""

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        api_key: str | None = None,  # unused, accepted for interface consistency
        **_kwargs,
    ):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
        self.keep_alive = os.getenv("OLLAMA_KEEP_ALIVE", "30m")

    def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 512,
        mode: str | None = None,
    ) -> str:
        url = f"{self.base_url}/api/generate"
        selected = (mode or "fast").strip().lower()
        if selected not in INFERENCE_MODES:
            selected = "fast"

        mode_opts = _MODE_DEFAULTS.get(selected, _MODE_DEFAULTS["fast"])

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                **mode_opts,
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

    def check_health(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            context_window=_MODE_DEFAULTS["balanced"]["num_ctx"],
            supports_streaming=True,
            supports_json_mode=False,
            estimated_speed="medium",
            max_output_tokens=_MODE_DEFAULTS["balanced"]["num_ctx"] // 2,
        )

    def get_info(self) -> dict:
        return {
            "provider": "ollama",
            "model_name": self.model_name,
            "base_url": self.base_url,
            "status": "healthy" if self.check_health() else "unreachable",
        }

    def list_available_models(self) -> list[str]:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
            resp.raise_for_status()
            models = resp.json().get("models", [])
            return [m["name"] for m in models]
        except Exception:
            return []
