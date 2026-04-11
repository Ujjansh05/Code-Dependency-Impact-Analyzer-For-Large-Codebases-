"""OpenAI-compatible model adapter.

Works with OpenAI, Groq, Together AI, Fireworks, Azure OpenAI,
vLLM, LM Studio, and any server exposing /v1/chat/completions.
"""

import os
from typing import Any

import requests

from llm.adapters.base import ModelAdapter, ModelCapabilities

# Known context windows for popular models (used for auto-config).
_KNOWN_CONTEXT_WINDOWS: dict[str, int] = {
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4": 8_192,
    "gpt-3.5-turbo": 16_385,
    "o3": 200_000,
    "o3-mini": 200_000,
    "o4-mini": 200_000,
    "llama3-8b-8192": 8_192,
    "llama3-70b-8192": 8_192,
    "mixtral-8x7b-32768": 32_768,
    "gemma-7b-it": 8_192,
}


class OpenAIAdapter(ModelAdapter):
    """Adapter for any OpenAI-compatible API endpoint."""

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        api_key: str | None = None,
        **_kwargs,
    ):
        self.base_url = (
            base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        ).rstrip("/")
        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 512,
        mode: str | None = None,
    ) -> str:
        url = f"{self.base_url}/chat/completions"

        # Adjust max_tokens by mode.
        if mode == "fast":
            max_tokens = min(max_tokens, 256)
        elif mode == "slow":
            max_tokens = max(max_tokens, 1024)

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            resp = requests.post(
                url, json=payload, headers=self._headers(), timeout=120
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""
        except requests.ConnectionError:
            return f"[Error] Cannot connect to {self.base_url}. Is the endpoint running?"
        except requests.Timeout:
            return "[Error] OpenAI-compatible request timed out."
        except requests.HTTPError as e:
            status = getattr(e.response, "status_code", "?")
            body = ""
            try:
                body = e.response.json().get("error", {}).get("message", "")
            except Exception:
                pass
            return f"[Error] API error (HTTP {status}): {body or str(e)}"
        except Exception as e:
            return f"[Error] OpenAI adapter error: {e}"

    def check_health(self) -> bool:
        """Check connectivity — try the /models endpoint first, fallback to a tiny completion."""
        try:
            resp = requests.get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            pass

        # Fallback: try a minimal completion.
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 1,
                },
                headers=self._headers(),
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def get_capabilities(self) -> ModelCapabilities:
        ctx = _KNOWN_CONTEXT_WINDOWS.get(self.model_name, 4096)
        return ModelCapabilities(
            context_window=ctx,
            supports_streaming=True,
            supports_json_mode=True,
            estimated_speed="fast",
            max_output_tokens=min(ctx // 2, 4096),
        )

    def get_info(self) -> dict:
        return {
            "provider": "openai",
            "model_name": self.model_name,
            "base_url": self.base_url,
            "has_api_key": bool(self.api_key),
            "status": "healthy" if self.check_health() else "unreachable",
        }

    def list_available_models(self) -> list[str]:
        try:
            resp = requests.get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
            return [m["id"] for m in data if isinstance(m, dict) and "id" in m]
        except Exception:
            return []
