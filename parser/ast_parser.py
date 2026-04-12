"""Extract functions, calls, and imports from Python source files."""

import ast
import os
from typing import Any


class FunctionInfo:
    """Stores metadata about a single function definition."""

    def __init__(self, name: str, filepath: str, start_line: int, end_line: int,
                 calls: list[str] | None = None, docstring: str | None = None):
        self.name = name
        self.filepath = filepath
        self.start_line = start_line
        self.end_line = end_line
        self.calls = calls or []
        self.docstring = docstring

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "filepath": self.filepath,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "calls": self.calls,
            "docstring": self.docstring,
        }


class ImportInfo:
    """Stores metadata about an import statement."""

    def __init__(self, module: str, names: list[str], filepath: str, line: int):
        self.module = module
        self.names = names
        self.filepath = filepath
        self.line = line

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "names": self.names,
            "filepath": self.filepath,
            "line": self.line,
        }


class _CallCollector(ast.NodeVisitor):
    """Walk a function body and collect names of called functions."""

    def __init__(self):
        self.calls: list[str] = []

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            self.calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.calls.append(node.func.attr)
        self.generic_visit(node)


def parse_file(filepath: str) -> dict[str, Any]:
    """Parse a single Python file and return structured data."""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        source = f.read()

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return {"file": filepath, "functions": [], "imports": [], "error": "SyntaxError"}

    functions: list[FunctionInfo] = []
    imports: list[ImportInfo] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            collector = _CallCollector()
            for child in ast.iter_child_nodes(node):
                collector.visit(child)

            docstring = ast.get_docstring(node)
            end_line = getattr(node, "end_lineno", node.lineno)

            functions.append(FunctionInfo(
                name=node.name,
                filepath=filepath,
                start_line=node.lineno,
                end_line=end_line,
                calls=collector.calls,
                docstring=docstring,
            ))

        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(ImportInfo(
                    module=alias.name,
                    names=[alias.asname or alias.name],
                    filepath=filepath,
                    line=node.lineno,
                ))

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = [alias.name for alias in node.names]
            imports.append(ImportInfo(
                module=module,
                names=names,
                filepath=filepath,
                line=node.lineno,
            ))

    return {
        "file": filepath,
        "functions": [f.to_dict() for f in functions],
        "imports": [i.to_dict() for i in imports],
    }


def parse_directory(
    directory: str,
    use_cache: bool = True,
    show_progress: bool = True,
) -> list[dict[str, Any]]:
    """Recursively parse every `.py` file under *directory*.

    Args:
        directory: Root directory to scan.
        use_cache: If True, skip files that haven't changed since last parse.
        show_progress: If True, show a Rich progress bar in the terminal.
    """
    from parser.utils import discover_python_files

    py_files = discover_python_files(directory)
    if not py_files:
        return []

    # Load incremental cache.
    cache = {}
    cache_hits = 0
    if use_cache:
        from parser.cache import load_cache, get_cached_result, update_cache, save_cache
        cache = load_cache(directory)

    results: list[dict[str, Any]] = []

    if show_progress:
        try:
            from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, MofNCompleteColumn
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold cyan]Parsing"),
                BarColumn(bar_width=30),
                MofNCompleteColumn(),
                TextColumn("[muted]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task("", total=len(py_files))
                for filepath in py_files:
                    short_name = os.path.basename(filepath)
                    progress.update(task, description=short_name)

                    # Check cache first.
                    if use_cache:
                        cached = get_cached_result(cache, filepath)
                        if cached is not None:
                            results.append(cached)
                            cache_hits += 1
                            progress.advance(task)
                            continue

                    result = parse_file(filepath)
                    results.append(result)

                    if use_cache:
                        update_cache(cache, filepath, result)

                    progress.advance(task)
        except ImportError:
            # Rich not available, fall back to silent parsing.
            for filepath in py_files:
                if use_cache:
                    cached = get_cached_result(cache, filepath)
                    if cached is not None:
                        results.append(cached)
                        cache_hits += 1
                        continue
                result = parse_file(filepath)
                results.append(result)
                if use_cache:
                    update_cache(cache, filepath, result)
    else:
        for filepath in py_files:
            if use_cache:
                from parser.cache import get_cached_result, update_cache
                cached = get_cached_result(cache, filepath)
                if cached is not None:
                    results.append(cached)
                    cache_hits += 1
                    continue
            result = parse_file(filepath)
            results.append(result)
            if use_cache:
                from parser.cache import update_cache
                update_cache(cache, filepath, result)

    # Save updated cache.
    if use_cache and cache:
        from parser.cache import save_cache
        save_cache(directory, cache)

    if cache_hits > 0:
        import logging
        logging.getLogger("graphxploit.parser").info(
            "Cache: %d/%d files unchanged (skipped), %d re-parsed",
            cache_hits, len(py_files), len(py_files) - cache_hits,
        )

    return results
