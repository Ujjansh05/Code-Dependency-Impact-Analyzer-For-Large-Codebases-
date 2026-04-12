"""HuggingFace Inference API adapter."""

import logging
import os
from typing import Any

import requests

from llm.adapters.base import ModelAdapter, ModelCapabilities

logger = logging.getLogger("graphxploit.adapters.huggingface")


_DEFAULT_HF_URL = "https://api-inference.huggingface.co/models"


class HuggingFaceAdapter(ModelAdapter):
    """Adapter for HuggingFace Inference API (free and Pro/Enterprise)."""

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        api_key: str | None = None,
        **_kwargs,
    ):
        self.base_url = (base_url or os.getenv("HF_BASE_URL", _DEFAULT_HF_URL)).rstrip("/")
        self.model_name = model_name or os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
        self.api_key = api_key or os.getenv("HF_API_KEY", "")

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _endpoint_url(self) -> str:
        """Build the full inference endpoint URL."""
        if self.base_url.endswith("/models"):
            return f"{self.base_url}/{self.model_name}"
        if self.model_name in self.base_url:
            return self.base_url
        return f"{self.base_url}/{self.model_name}"

    def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 512,
        mode: str | None = None,
    ) -> str:
        url = self._endpoint_url()

        if mode == "fast":
            max_tokens = min(max_tokens, 256)
        elif mode == "slow":
            max_tokens = max(max_tokens, 1024)

        payload: dict[str, Any] = {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens,
                "return_full_text": False,
            },
        }

        try:
            resp = requests.post(
                url, json=payload, headers=self._headers(), timeout=120
            )
            resp.raise_for_status()
            data = resp.json()

            # HF returns a list of generated texts.
            if isinstance(data, list) and data:
                first = data[0]
                if isinstance(first, dict):
                    return first.get("generated_text", "")
                return str(first)
            if isinstance(data, dict):
                return data.get("generated_text", data.get("text", ""))
            return str(data)

        except requests.ConnectionError:
            return "[Error] Cannot connect to HuggingFace. Check your network."
        except requests.Timeout:
            return "[Error] HuggingFace request timed out."
        except requests.HTTPError as e:
            status = getattr(e.response, "status_code", "?")
            body = ""
            try:
                body = str(e.response.json())
            except (ValueError, KeyError):
                pass
            if status == 503:
                return "[Error] Model is loading on HuggingFace. Please retry in 30-60 seconds."
            return f"[Error] HuggingFace API error (HTTP {status}): {body or str(e)}"
        except Exception as e:
            return f"[Error] HuggingFace adapter error: {e}"

    def check_health(self) -> bool:
        try:
            resp = requests.post(
                self._endpoint_url(),
                json={"inputs": "test", "parameters": {"max_new_tokens": 1}},
                headers=self._headers(),
                timeout=15,
            )
            # 503 = model loading (still healthy, just cold).
            return resp.status_code in (200, 503)
        except (requests.RequestException, OSError) as e:
            logger.debug("HuggingFace health check failed: %s", e)
            return False

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            context_window=4096,
            supports_streaming=False,
            supports_json_mode=False,
            estimated_speed="slow",  # hosted inference can be slower
            max_output_tokens=2048,
        )

    def get_info(self) -> dict:
        return {
            "provider": "huggingface",
            "model_name": self.model_name,
            "base_url": self.base_url,
            "has_api_key": bool(self.api_key),
            "status": "healthy" if self.check_health() else "unreachable",
        }
