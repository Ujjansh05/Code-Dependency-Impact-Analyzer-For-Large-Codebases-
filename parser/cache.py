"""Incremental parse cache — skip re-parsing unchanged files.

Stores parse results keyed by file path + modification time + size.
Cache lives at ~/.graphxploit/parse_cache/<project_hash>/cache.json.
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("graphxploit.parse_cache")

CACHE_DIR = os.path.join(Path.home(), ".graphxploit", "parse_cache")


def _project_hash(directory: str) -> str:
    """Derive a stable cache key from the project directory path."""
    norm = os.path.normpath(os.path.abspath(directory))
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:12]


def _file_stat_key(filepath: str) -> str:
    """Return a cache key based on file mtime and size."""
    try:
        stat = os.stat(filepath)
        return f"{stat.st_mtime_ns}:{stat.st_size}"
    except OSError:
        return ""


def _cache_path(directory: str) -> str:
    """Return the cache file path for a given project directory."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{_project_hash(directory)}.json")


def load_cache(directory: str) -> dict[str, dict[str, Any]]:
    """Load the parse cache for a directory.

    Returns a dict: filepath -> {"stat_key": str, "result": dict}
    """
    path = _cache_path(directory)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.debug("Failed to load parse cache: %s", e)
        return {}


def save_cache(directory: str, cache: dict[str, dict[str, Any]]) -> None:
    """Persist the parse cache to disk."""
    path = _cache_path(directory)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=1)
    except OSError as e:
        logger.warning("Failed to save parse cache: %s", e)


def get_cached_result(
    cache: dict[str, dict[str, Any]], filepath: str
) -> dict[str, Any] | None:
    """Return the cached parse result if the file hasn't changed, else None."""
    entry = cache.get(filepath)
    if not entry:
        return None

    current_key = _file_stat_key(filepath)
    if not current_key or current_key != entry.get("stat_key"):
        return None

    return entry.get("result")


def update_cache(
    cache: dict[str, dict[str, Any]],
    filepath: str,
    result: dict[str, Any],
) -> None:
    """Store a parse result in the cache."""
    stat_key = _file_stat_key(filepath)
    if stat_key:
        cache[filepath] = {"stat_key": stat_key, "result": result}


def clear_cache(directory: str) -> bool:
    """Delete the cache file for a project. Returns True if deleted."""
    path = _cache_path(directory)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def clear_all_caches() -> int:
    """Delete all cache files. Returns count deleted."""
    if not os.path.isdir(CACHE_DIR):
        return 0
    count = 0
    for fname in os.listdir(CACHE_DIR):
        if fname.endswith(".json"):
            os.remove(os.path.join(CACHE_DIR, fname))
            count += 1
    return count
