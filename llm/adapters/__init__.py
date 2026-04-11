"""Model adapter registry — factory for provider-specific adapters."""

from llm.adapters.base import ModelAdapter, ModelCapabilities

_ADAPTER_MAP: dict[str, type[ModelAdapter]] = {}


def _register_builtin_adapters() -> None:
    """Lazily register built-in adapters on first access."""
    if _ADAPTER_MAP:
        return

    from llm.adapters.ollama_adapter import OllamaAdapter
    from llm.adapters.openai_adapter import OpenAIAdapter
    from llm.adapters.huggingface_adapter import HuggingFaceAdapter

    _ADAPTER_MAP["ollama"] = OllamaAdapter
    _ADAPTER_MAP["openai"] = OpenAIAdapter
    _ADAPTER_MAP["huggingface"] = HuggingFaceAdapter
    _ADAPTER_MAP["custom"] = OpenAIAdapter  # custom endpoints use OpenAI-compatible API


def get_adapter_class(provider: str) -> type[ModelAdapter]:
    """Return the adapter class for *provider* ('ollama', 'openai', 'huggingface', 'custom')."""
    _register_builtin_adapters()
    provider = provider.strip().lower()
    if provider not in _ADAPTER_MAP:
        raise ValueError(
            f"Unknown provider '{provider}'. "
            f"Available: {', '.join(sorted(_ADAPTER_MAP))}"
        )
    return _ADAPTER_MAP[provider]


def create_adapter(provider: str, **kwargs) -> ModelAdapter:
    """Instantiate an adapter for the given provider with configuration kwargs."""
    cls = get_adapter_class(provider)
    return cls(**kwargs)


SUPPORTED_PROVIDERS = ("ollama", "openai", "huggingface", "custom")

__all__ = [
    "ModelAdapter",
    "ModelCapabilities",
    "get_adapter_class",
    "create_adapter",
    "SUPPORTED_PROVIDERS",
]
