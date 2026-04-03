"""Natural language to target name extraction."""

import os

from llm.llama_client import generate


EXTRACTION_PROMPT = """You are a code analysis assistant.
Given a user's natural language question about code impact, extract the specific
function name or file name they are asking about.

Rules:
1. Return ONLY the function or file name — nothing else.
2. If the user mentions a function, return the function name.
3. If the user mentions a file, return the file name (with extension).
4. If you cannot determine a specific name, return "UNKNOWN".

Examples:
- "What happens if I change the login function?" → login
- "What will break if I modify utils.py?" → utils.py
- "Impact of changing the calculate_total method?" → calculate_total
- "If I refactor the database connection handler?" → database connection handler

User question: {question}

Extracted name:"""

EXTRACTION_MODE = os.getenv("OLLAMA_EXTRACTION_MODE", "fast")


def extract_target(question: str) -> dict[str, str]:
    """Parse a natural language query to extract the target function/file name."""
    prompt = EXTRACTION_PROMPT.format(question=question)
    raw_response = generate(prompt, temperature=0.1, max_tokens=64, mode=EXTRACTION_MODE)
    target = raw_response.strip().strip('"').strip("'")

    if target == "UNKNOWN" or not target:
        target_type = "unknown"
    elif target.endswith(".py"):
        target_type = "file"
    else:
        target_type = "function"

    return {
        "target": target,
        "type": target_type,
        "raw": raw_response,
    }
