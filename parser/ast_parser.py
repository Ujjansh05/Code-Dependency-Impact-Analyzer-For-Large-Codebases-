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


def parse_directory(directory: str) -> list[dict[str, Any]]:
    """Recursively parse every `.py` file under *directory*."""
    from parser.utils import discover_python_files

    results = []
    for filepath in discover_python_files(directory):
        results.append(parse_file(filepath))
    return results
