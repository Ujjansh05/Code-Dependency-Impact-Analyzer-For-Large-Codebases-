import sys
import types
from pathlib import Path

from cli.commands.analyze import analyze
from cli.commands.parse import parse
from cli.commands.query import query


def test_parse_csv_creates_output_files(runner, sample_code_dir, tmp_path):
    output_dir = tmp_path / "csv_out"

    result = runner.invoke(parse, [str(sample_code_dir), "--format", "csv", "-o", str(output_dir)])

    assert result.exit_code == 0
    assert (output_dir / "vertices.csv").exists()
    assert (output_dir / "edges.csv").exists()


def test_parse_json_creates_output_file(runner, sample_code_dir, tmp_path):
    output_dir = tmp_path / "json_out"

    result = runner.invoke(parse, [str(sample_code_dir), "--format", "json", "-o", str(output_dir)])

    assert result.exit_code == 0
    assert (output_dir / "dependency_graph.json").exists()


def test_parse_fails_when_no_python_files(runner, tmp_path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    result = runner.invoke(parse, [str(empty_dir)])

    assert result.exit_code == 1


def test_analyze_pipeline_runs_without_docker(monkeypatch, runner, sample_code_dir, tmp_path):
    parsed_payload = [
        {
            "file": str(sample_code_dir / "app.py"),
            "functions": [
                {
                    "name": "main",
                    "filepath": str(sample_code_dir / "app.py"),
                    "start_line": 1,
                    "end_line": 3,
                    "calls": [],
                    "docstring": None,
                }
            ],
            "imports": [],
        }
    ]

    def _fake_build_csvs(parsed_files, vertices_path, edges_path):
        Path(vertices_path).write_text(
            "id,type,name,filepath\nfile::app.py,File,app.py,app.py\n",
            encoding="utf-8",
        )
        Path(edges_path).write_text("source,target,type\n", encoding="utf-8")

    fake_tg_module = types.ModuleType("graph.tigergraph_client")
    fake_tg_module.get_connection = lambda: object()
    fake_loader_module = types.ModuleType("graph.load_data")
    fake_loader_module.load_vertices = lambda conn, vertices_path: 1
    fake_loader_module.load_edges = lambda conn, edges_path: 0

    monkeypatch.setattr("parser.ast_parser.parse_directory", lambda path: parsed_payload)
    monkeypatch.setattr("parser.graph_builder.build_csvs", _fake_build_csvs)
    monkeypatch.setitem(sys.modules, "graph.tigergraph_client", fake_tg_module)
    monkeypatch.setitem(sys.modules, "graph.load_data", fake_loader_module)

    output_dir = tmp_path / "analysis_out"
    result = runner.invoke(analyze, [str(sample_code_dir), "--no-docker", "-o", str(output_dir)])

    assert result.exit_code == 0
    assert (output_dir / "vertices.csv").exists()
    assert (output_dir / "edges.csv").exists()


def test_query_exits_on_unknown_target(monkeypatch, runner):
    fake_query_parser = types.ModuleType("llm.query_parser")
    fake_query_parser.extract_target = lambda question: {
        "target": "UNKNOWN",
        "type": "unknown",
        "raw": "UNKNOWN",
    }
    monkeypatch.setitem(sys.modules, "llm.query_parser", fake_query_parser)

    result = runner.invoke(query, ["What breaks if I change everything?"])

    assert result.exit_code == 1


def test_query_runs_graph_query_without_ai(monkeypatch, runner):
    class FakeConnection:
        def __init__(self):
            self.calls = []

        def runInstalledQuery(self, name, params):
            self.calls.append((name, params))
            return [{"@@affected": ["func::app.py::login", "file::app.py"]}]

    conn = FakeConnection()

    fake_query_parser = types.ModuleType("llm.query_parser")
    fake_query_parser.extract_target = lambda question: {
        "target": "login",
        "type": "function",
        "raw": "login",
    }

    fake_tg_module = types.ModuleType("graph.tigergraph_client")
    fake_tg_module.get_connection = lambda: conn

    monkeypatch.setitem(sys.modules, "llm.query_parser", fake_query_parser)
    monkeypatch.setitem(sys.modules, "graph.tigergraph_client", fake_tg_module)

    result = runner.invoke(query, ["Impact of changing login?", "--depth", "2", "--no-ai"])

    assert result.exit_code == 0
    assert conn.calls == [("impact_analysis", {"start_func": ("login",), "max_depth": 2})]


def test_query_runs_file_hop_detection_with_typed_vertex(monkeypatch, runner):
    class FakeConnection:
        def __init__(self):
            self.calls = []

        def runInstalledQuery(self, name, params):
            self.calls.append((name, params))
            return [{"@@reachable": ["file::auth.py"]}]

    conn = FakeConnection()

    fake_query_parser = types.ModuleType("llm.query_parser")
    fake_query_parser.extract_target = lambda question: {
        "target": "auth.py",
        "type": "file",
        "raw": "auth.py",
    }

    fake_tg_module = types.ModuleType("graph.tigergraph_client")
    fake_tg_module.get_connection = lambda: conn

    fake_target_resolver = types.ModuleType("graph.target_resolver")
    fake_target_resolver.resolve_target_id = (
        lambda target, target_type: "file::auth.py"
    )

    monkeypatch.setitem(sys.modules, "llm.query_parser", fake_query_parser)
    monkeypatch.setitem(sys.modules, "graph.tigergraph_client", fake_tg_module)
    monkeypatch.setitem(sys.modules, "graph.target_resolver", fake_target_resolver)

    result = runner.invoke(query, ["What breaks if I modify auth.py?", "--depth", "2", "--no-ai"])

    assert result.exit_code == 0
    assert conn.calls == [
        ("hop_detection", {"start_node": ("file::auth.py", "CodeFile"), "num_hops": 2})
    ]
