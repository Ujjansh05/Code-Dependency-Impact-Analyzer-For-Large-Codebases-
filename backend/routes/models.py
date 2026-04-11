"""Model management REST endpoints for the frontend."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

router = APIRouter()


# ── Request / Response Schemas ──────────────────────────────────


class ModelMountRequest(BaseModel):
    """Request body for POST /api/models."""
    name: str | None = None
    provider: Literal["ollama", "openai", "huggingface", "custom"]
    base_url: str | None = None
    api_key: str | None = None
    model_name: str
    settings: dict = Field(default_factory=dict)
    set_active: bool = True


class ModelInfo(BaseModel):
    """Model info returned by list and detail endpoints."""
    id: str
    name: str
    provider: str
    model_name: str
    base_url: str
    is_active: bool
    capabilities: dict | None = None
    last_used: str | None = None
    created_at: str | None = None


class ModelTestRequest(BaseModel):
    """Request body for POST /api/models/test."""
    provider: Literal["ollama", "openai", "huggingface", "custom"]
    base_url: str | None = None
    api_key: str | None = None
    model_name: str


# ── Endpoints ───────────────────────────────────────────────────


@router.get("/models")
async def list_models():
    """Return all mounted models."""
    from llm.model_registry import list_models as _list_models

    models = _list_models()
    return {
        "models": [
            ModelInfo(
                id=m.id,
                name=m.name,
                provider=m.provider,
                model_name=m.model_name,
                base_url=m.base_url,
                is_active=m.is_active,
                capabilities=m.capabilities or None,
                last_used=m.last_used,
                created_at=m.created_at,
            ).model_dump()
            for m in models
        ]
    }


@router.get("/models/active")
async def get_active_model():
    """Return the currently active model."""
    from llm.model_registry import get_active_config

    config = get_active_config()
    if not config:
        return {"model": None, "message": "No active model. Mount one first."}

    return {
        "model": ModelInfo(
            id=config.id,
            name=config.name,
            provider=config.provider,
            model_name=config.model_name,
            base_url=config.base_url,
            is_active=True,
            capabilities=config.capabilities or None,
            last_used=config.last_used,
            created_at=config.created_at,
        ).model_dump()
    }


@router.post("/models")
async def mount_model(request: ModelMountRequest):
    """Mount a new model."""
    from llm.model_registry import ModelConfig, register_model

    config = ModelConfig(
        provider=request.provider,
        base_url=request.base_url or "",
        api_key=request.api_key or "",
        model_name=request.model_name,
        name=request.name or f"{request.provider.capitalize()} ({request.model_name})",
        is_active=request.set_active,
        settings=request.settings,
    )

    result = register_model(config)

    return {
        "status": "ok",
        "model": {
            "id": result.id,
            "name": result.name,
            "provider": result.provider,
            "model_name": result.model_name,
            "is_active": result.is_active,
        },
        "message": f"Model '{result.name}' mounted successfully.",
    }


@router.put("/models/{model_id}/active")
async def set_active(model_id: str):
    """Set a model as the active model."""
    from llm.model_registry import set_active_model

    result = set_active_model(model_id)
    if not result:
        raise HTTPException(status_code=404, detail="Model not found.")

    return {
        "status": "ok",
        "model": {
            "id": result.id,
            "name": result.name,
            "is_active": True,
        },
        "message": f"Active model switched to '{result.name}'.",
    }


@router.delete("/models/{model_id}")
async def delete_model(model_id: str):
    """Remove a mounted model."""
    from llm.model_registry import delete_model as _delete_model

    if _delete_model(model_id):
        return {"status": "ok", "message": "Model removed."}
    raise HTTPException(status_code=404, detail="Model not found.")


@router.get("/models/{model_id}/health")
async def model_health(model_id: str):
    """Check connectivity for a specific model."""
    from llm.model_registry import get_model
    from llm.adapters import create_adapter

    config = get_model(model_id)
    if not config:
        raise HTTPException(status_code=404, detail="Model not found.")

    adapter = create_adapter(
        provider=config.provider,
        base_url=config.base_url or None,
        model_name=config.model_name or None,
        api_key=config.api_key or None,
    )

    healthy = adapter.check_health()
    return {
        "model_id": model_id,
        "healthy": healthy,
        "status": "reachable" if healthy else "unreachable",
    }


@router.post("/models/{model_id}/probe")
async def probe_model_endpoint(model_id: str):
    """Run auto-detection on a model and update its capabilities."""
    from llm.model_registry import get_model, update_model
    from llm.adapters import create_adapter
    from llm.auto_config import run_full_probe

    config = get_model(model_id)
    if not config:
        raise HTTPException(status_code=404, detail="Model not found.")

    adapter = create_adapter(
        provider=config.provider,
        base_url=config.base_url or None,
        model_name=config.model_name or None,
        api_key=config.api_key or None,
    )

    results = run_full_probe(adapter)

    if results.get("capabilities"):
        update_model(model_id, capabilities=results["capabilities"])

    return results


@router.post("/models/test")
async def test_model(request: ModelTestRequest):
    """Test a model configuration without saving it."""
    from llm.adapters import create_adapter
    from llm.auto_config import run_full_probe

    try:
        adapter = create_adapter(
            provider=request.provider,
            base_url=request.base_url or None,
            model_name=request.model_name or None,
            api_key=request.api_key or None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    results = run_full_probe(adapter)
    return results
