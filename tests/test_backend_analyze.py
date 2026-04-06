from fastapi.testclient import TestClient

from backend.main import app
from backend.routes import analyze as analyze_route


def test_analyze_file_query_uses_typed_vertex(monkeypatch):
    class FakeConn:
        def __init__(self):
            self.calls = []

        def runInstalledQuery(self, name, params):
            self.calls.append((name, params))
            return [{"@@reachable": ["file::auth.py", "func::auth.py::authenticate"]}]

    conn = FakeConn()

    monkeypatch.setattr(
        analyze_route,
        "extract_target",
        lambda q: {"target": "auth.py", "type": "file", "raw": "auth.py"},
    )
    monkeypatch.setattr(analyze_route, "resolve_target_id", lambda **_: "file::auth.py")
    monkeypatch.setattr(analyze_route, "get_connection", lambda: conn)
    monkeypatch.setattr(
        analyze_route,
        "explain_impact",
        lambda question, target, affected_nodes, mode: "ok",
    )

    client = TestClient(app)
    resp = client.post(
        "/api/analyze",
        json={"query": "What breaks if I modify auth.py?", "max_depth": 3, "inference_mode": "fast"},
    )

    assert resp.status_code == 200
    assert conn.calls == [
        ("hop_detection", {"start_node": ("file::auth.py", "CodeFile"), "num_hops": 3})
    ]

