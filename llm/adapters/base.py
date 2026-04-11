"""Abstract base class for all model adapters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ModelCapabilities:
    """Detected capabilities of a mounted model."""

    context_window: int = 4096
    supports_streaming: bool = False
    supports_json_mode: bool = False
    estimated_speed: str = "medium"  # "fast" / "medium" / "slow"
    max_output_tokens: int = 2048

    def to_dict(self) -> dict:
        return {
            "context_window": self.context_window,
            "supports_streaming": self.supports_streaming,
            "supports_json_mode": self.supports_json_mode,
            "estimated_speed": self.estimated_speed,
            "max_output_tokens": self.max_output_tokens,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ModelCapabilities":
        if not data:
            return cls()
        return cls(
            context_window=data.get("context_window", 4096),
            supports_streaming=data.get("supports_streaming", False),
            supports_json_mode=data.get("supports_json_mode", False),
            estimated_speed=data.get("estimated_speed", "medium"),
            max_output_tokens=data.get("max_output_tokens", 2048),
        )


class ModelAdapter(ABC):
    """Universal interface that every model provider must implement."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 512,
        mode: str | None = None,
    ) -> str:
        """Send a prompt and return the generated text."""

    @abstractmethod
    def check_health(self) -> bool:
        """Return True if the model endpoint is reachable and functional."""

    @abstractmethod
    def get_capabilities(self) -> ModelCapabilities:
        """Return the detected capabilities of this model."""

    @abstractmethod
    def get_info(self) -> dict:
        """Return metadata about this adapter instance (name, provider, model, etc.)."""

    def list_available_models(self) -> list[str]:
        """Return a list of models available at this endpoint. Optional."""
        return []
