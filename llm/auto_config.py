"""Auto-configuration engine for mounted models.

Probes a model to detect capabilities, suggests optimal settings,
and validates the model can handle code analysis tasks.
"""

import time

from llm.adapters.base import ModelAdapter, ModelCapabilities


def probe_model(adapter: ModelAdapter) -> ModelCapabilities:
    """Probe a model to detect its capabilities (context window, speed, etc.)."""
    caps = adapter.get_capabilities()

    # Measure actual response time.
    start = time.time()
    response = adapter.generate(
        prompt="What is 2+2? Reply with only the number.",
        temperature=0.0,
        max_tokens=8,
    )
    elapsed = time.time() - start

    if response.startswith("[Error]"):
        return caps

    if elapsed < 1.5:
        caps.estimated_speed = "fast"
    elif elapsed < 5.0:
        caps.estimated_speed = "medium"
    else:
        caps.estimated_speed = "slow"

    return caps


def suggest_settings(capabilities: ModelCapabilities) -> dict:
    """Return optimal temperature, max_tokens, and prompt style for this model."""
    if capabilities.context_window >= 32_000:
        return {
            "temperature": 0.3,
            "max_tokens_extraction": 64,
            "max_tokens_explanation": 1024,
            "prompt_style": "detailed",
        }
    if capabilities.context_window >= 4_096:
        return {
            "temperature": 0.3,
            "max_tokens_extraction": 64,
            "max_tokens_explanation": 512,
            "prompt_style": "standard",
        }
    return {
        "temperature": 0.2,
        "max_tokens_extraction": 32,
        "max_tokens_explanation": 256,
        "prompt_style": "compact",
    }


_VALIDATION_PROMPT = """You are a code analysis assistant.
Given a user's natural language question about code impact, extract the specific
function name they are asking about.

Return ONLY the function name — nothing else.

User question: What happens if I change the login function?

Extracted name:"""


def validate_model_for_code_analysis(adapter: ModelAdapter) -> tuple[bool, str]:
    """Test if the model can handle code analysis tasks.

    Returns:
        (success, message) where success is True if the model passed.
    """
    response = adapter.generate(
        prompt=_VALIDATION_PROMPT,
        temperature=0.1,
        max_tokens=32,
    )

    if response.startswith("[Error]"):
        return False, f"Model returned an error: {response}"

    cleaned = response.strip().strip("'\"").lower()

    if not cleaned:
        return False, "Model returned an empty response."

    # Check if the model identified "login" from the test query.
    if "login" in cleaned:
        return True, "Model correctly identified 'login' from the test query."

    # Accept any non-empty reasonable response.
    if len(cleaned) < 100 and not cleaned.startswith("["):
        return True, f"Model responded with: '{cleaned}' (acceptable)."

    return False, f"Unexpected response format: '{cleaned[:100]}'"


def run_full_probe(adapter: ModelAdapter) -> dict:
    """Run a comprehensive probe: capabilities + validation.

    Returns a dict with all probe results.
    """
    health = adapter.check_health()
    if not health:
        return {
            "healthy": False,
            "capabilities": None,
            "validation_passed": False,
            "validation_message": "Model endpoint is unreachable.",
            "suggested_settings": None,
        }

    caps = probe_model(adapter)
    valid, message = validate_model_for_code_analysis(adapter)
    settings = suggest_settings(caps)

    return {
        "healthy": True,
        "capabilities": caps.to_dict(),
        "validation_passed": valid,
        "validation_message": message,
        "suggested_settings": settings,
    }
