"""Shared utilities for the parser module."""

import logging
import os
from pathlib import Path

logger = logging.getLogger("parser")


def setup_logging(level: int = logging.INFO):
    """Configure the parser logger."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s │ %(name)s │ %(levelname)s │ %(message)s",
        datefmt="%H:%M:%S",
    )


def discover_python_files(directory: str) -> list[str]:
    """Recursively find all `.py` files under *directory*."""
    skip_dirs = {
        "__pycache__", ".git", ".hg", "node_modules",
        "venv", ".venv", "env", ".env", ".tox",
    }

    py_files: list[str] = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]

        for fname in sorted(files):
            if fname.endswith(".py"):
                py_files.append(os.path.join(root, fname))

    logger.info("Discovered %d Python files in %s", len(py_files), directory)
    return py_files


def normalize_path(path: str) -> str:
    """Return an absolute, normalized path."""
    return str(Path(path).resolve())
