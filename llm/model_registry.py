"""Persistent model configuration registry.

Stores mounted models at ~/.graphxploit/models.json and provides
a single get_active_model() entry point used by all analysis code.
"""

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm.adapters.base import ModelAdapter, ModelCapabilities

REGISTRY_DIR = os.path.join(Path.home(), ".graphxploit")
REGISTRY_FILE = os.path.join(REGISTRY_DIR, "models.json")


@dataclass
class ModelConfig:
    """Serializable configuration for a mounted model."""

    id: str = ""
    name: str = ""
    provider: str = "ollama"          # ollama | openai | huggingface | custom
    base_url: str = ""
    api_key: str = ""                 # stored at rest (consider encrypting)
    model_name: str = ""
    is_active: bool = False
    capabilities: dict = field(default_factory=dict)
    settings: dict = field(default_factory=dict)
    created_at: str = ""
    last_used: str | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        if hasattr(self, "api_key") and self.api_key:
            from llm.crypto import encrypt
            data["api_key"] = encrypt(self.api_key)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ModelConfig":
        known_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_keys}
        
        from llm.crypto import decrypt
        if "api_key" in filtered and filtered["api_key"]:
            filtered["api_key"] = decrypt(filtered["api_key"])
            
        return cls(**filtered)


# ── Registry I/O ────────────────────────────────────────────────


def _ensure_registry() -> list[dict]:
    """Load the registry from disk, creating it if it doesn't exist."""
    os.makedirs(REGISTRY_DIR, exist_ok=True)
    if not os.path.exists(REGISTRY_FILE):
        _save([])
        return []
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return data
    except (json.JSONDecodeError, OSError):
        return []


def _save(models: list[dict]) -> None:
    os.makedirs(REGISTRY_DIR, exist_ok=True)
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(models, f, indent=2, default=str)


# ── CRUD Operations ─────────────────────────────────────────────


def register_model(config: ModelConfig) -> ModelConfig:
    """Mount a new model in the registry."""
    models = _ensure_registry()

    if not config.id:
        config.id = uuid.uuid4().hex[:8]
    if not config.created_at:
        config.created_at = datetime.now(timezone.utc).isoformat()
    if not config.name:
        config.name = f"{config.provider} / {config.model_name}"

    # If set_active, deactivate all others.
    if config.is_active:
        for m in models:
            m["is_active"] = False

    models.append(config.to_dict())
    _save(models)
    return config


def list_models() -> list[ModelConfig]:
    """Return all registered models."""
    return [ModelConfig.from_dict(m) for m in _ensure_registry()]


def get_model(model_id: str) -> ModelConfig | None:
    """Get a single model by ID."""
    for m in _ensure_registry():
        if m["id"] == model_id:
            return ModelConfig.from_dict(m)
    return None


def get_active_config() -> ModelConfig | None:
    """Return the active model config, or None if none is active."""
    for m in _ensure_registry():
        if m.get("is_active"):
            return ModelConfig.from_dict(m)
    return None


def set_active_model(model_id: str) -> ModelConfig | None:
    """Set a model as active (deactivates all others). Returns the model or None."""
    models = _ensure_registry()
    target = None
    for m in models:
        if m["id"] == model_id:
            m["is_active"] = True
            target = ModelConfig.from_dict(m)
        else:
            m["is_active"] = False
    if target:
        _save(models)
    return target


def update_model(model_id: str, **updates) -> ModelConfig | None:
    """Update fields on a model. Returns updated config or None."""
    models = _ensure_registry()
    for m in models:
        if m["id"] == model_id:
            for k, v in updates.items():
                m[k] = v
            _save(models)
            return ModelConfig.from_dict(m)
    return None


def delete_model(model_id: str) -> bool:
    """Remove a model from the registry. Returns True if deleted."""
    models = _ensure_registry()
    before = len(models)
    models = [m for m in models if m["id"] != model_id]
    if len(models) < before:
        _save(models)
        return True
    return False


def find_by_provider_and_model(provider: str, model_name: str) -> ModelConfig | None:
    """Find an existing registration for a specific provider+model combo."""
    for m in _ensure_registry():
        if m.get("provider") == provider and m.get("model_name") == model_name:
            return ModelConfig.from_dict(m)
    return None


# ── Adapter Instantiation ───────────────────────────────────────


def _create_adapter_from_config(config: ModelConfig) -> ModelAdapter:
    """Create a ModelAdapter instance from a ModelConfig."""
    from llm.adapters import create_adapter
    return create_adapter(
        provider=config.provider,
        base_url=config.base_url or None,
        model_name=config.model_name or None,
        api_key=config.api_key or None,
    )


def get_active_model() -> ModelAdapter:
    """Return a ready-to-use ModelAdapter for the active model.

    Falls back to auto-detecting local Ollama if no model is mounted.
    """
    config = get_active_config()
    if config:
        _mark_used(config.id)
        return _create_adapter_from_config(config)

    # Fallback: auto-detect local Ollama.
    adapter = _try_auto_detect_ollama()
    if adapter:
        return adapter

    raise RuntimeError(
        "No model is mounted. Run 'graphxploit model mount' to configure one.\n"
        "  Examples:\n"
        "    graphxploit model mount --provider ollama --model qwen2.5-coder:7b\n"
        "    graphxploit model mount --provider openai --api-key sk-... --model gpt-4o\n"
    )


def get_adapter_for_model(model_id: str) -> ModelAdapter:
    """Return an adapter for a specific model ID."""
    config = get_model(model_id)
    if not config:
        raise ValueError(f"Model '{model_id}' not found in registry.")
    return _create_adapter_from_config(config)


def _mark_used(model_id: str) -> None:
    """Update last_used timestamp."""
    models = _ensure_registry()
    for m in models:
        if m["id"] == model_id:
            m["last_used"] = datetime.now(timezone.utc).isoformat()
            _save(models)
            return


def _try_auto_detect_ollama() -> ModelAdapter | None:
    """Try to connect to a local Ollama and use whatever is available."""
    import logging
    _logger = logging.getLogger("graphxploit.model_registry")

    try:
        from llm.adapters.ollama_adapter import OllamaAdapter
        adapter = OllamaAdapter()
        if adapter.check_health():
            models = adapter.list_available_models()
            if models:
                # Prefer qwen2.5-coder if available, else first model.
                preferred = [m for m in models if "qwen" in m.lower() and "coder" in m.lower()]
                model_name = preferred[0] if preferred else models[0]
                adapter = OllamaAdapter(model_name=model_name)

                # Auto-register it.
                existing = find_by_provider_and_model("ollama", model_name)
                if not existing:
                    register_model(ModelConfig(
                        provider="ollama",
                        model_name=model_name,
                        name=f"Ollama ({model_name})",
                        base_url=adapter.base_url,
                        is_active=True,
                    ))
                return adapter
    except (ConnectionError, OSError) as e:
        _logger.debug("Ollama auto-detect failed (connection): %s", e)
    except ImportError as e:
        _logger.debug("Ollama adapter not available: %s", e)
    except Exception as e:
        _logger.debug("Ollama auto-detect failed: %s", e)
    return None
