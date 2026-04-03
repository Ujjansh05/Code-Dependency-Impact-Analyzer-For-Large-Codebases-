from cli.commands.serve import serve
from cli.commands.start import start
from cli.commands.status import status
from cli.commands.stop import stop


def _capture_console_print(monkeypatch):
    messages: list[str] = []

    def _fake_print(*args, **kwargs):
        messages.append(" ".join(str(arg) for arg in args))

    monkeypatch.setattr("cli.commands.status.console.print", _fake_print)
    return messages


def test_start_with_no_pull_passes_none(monkeypatch, runner):
    called = {}

    def _fake_start_services(tg_port, ollama_port, pull_model):
        called["tg_port"] = tg_port
        called["ollama_port"] = ollama_port
        called["pull_model"] = pull_model
        return True

    monkeypatch.setattr("cli.commands.start.ensure_docker_installed", lambda: True)
    monkeypatch.setattr("cli.commands.start.start_services", _fake_start_services)

    result = runner.invoke(start, ["--no-pull"])

    assert result.exit_code == 0
    assert called == {"tg_port": 9000, "ollama_port": 11434, "pull_model": None}


def test_start_exits_if_docker_missing(monkeypatch, runner):
    monkeypatch.setattr("cli.commands.start.ensure_docker_installed", lambda: False)

    result = runner.invoke(start, [])

    assert result.exit_code == 1


def test_stop_passes_volumes_flag(monkeypatch, runner):
    called = {}

    def _fake_stop_services(remove_volumes):
        called["remove_volumes"] = remove_volumes
        return True

    monkeypatch.setattr("cli.commands.stop.stop_services", _fake_stop_services)

    result = runner.invoke(stop, ["--volumes"])

    assert result.exit_code == 0
    assert called["remove_volumes"] is True


def test_stop_exits_on_failure(monkeypatch, runner):
    monkeypatch.setattr("cli.commands.stop.stop_services", lambda remove_volumes: False)

    result = runner.invoke(stop, [])

    assert result.exit_code == 1


def test_status_reports_all_healthy(monkeypatch, runner):
    messages = _capture_console_print(monkeypatch)
    monkeypatch.setattr(
        "cli.commands.status.get_service_status",
        lambda: [
            {"name": "TigerGraph", "port": "9000", "status": " Running", "url": "http://localhost:9000"},
            {"name": "GraphStudio", "port": "14240", "status": " Running", "url": "http://localhost:14240"},
            {"name": "Ollama", "port": "11434", "status": " Running", "url": "http://localhost:11434"},
        ],
    )

    result = runner.invoke(status, [])

    assert result.exit_code == 0
    assert any("All services are healthy." in message for message in messages)


def test_status_reports_partial_running(monkeypatch, runner):
    messages = _capture_console_print(monkeypatch)
    monkeypatch.setattr(
        "cli.commands.status.get_service_status",
        lambda: [
            {"name": "TigerGraph", "port": "9000", "status": " Running", "url": "http://localhost:9000"},
            {"name": "GraphStudio", "port": "14240", "status": " Stopped", "url": "http://localhost:14240"},
            {"name": "Ollama", "port": "11434", "status": " Stopped", "url": "http://localhost:11434"},
        ],
    )

    result = runner.invoke(status, [])

    assert result.exit_code == 0
    assert any("1/3 services running." in message for message in messages)


def test_status_reports_none_running(monkeypatch, runner):
    messages = _capture_console_print(monkeypatch)
    monkeypatch.setattr(
        "cli.commands.status.get_service_status",
        lambda: [
            {"name": "TigerGraph", "port": "9000", "status": " Stopped", "url": "http://localhost:9000"},
            {"name": "GraphStudio", "port": "14240", "status": " Stopped", "url": "http://localhost:14240"},
            {"name": "Ollama", "port": "11434", "status": " Stopped", "url": "http://localhost:11434"},
        ],
    )

    result = runner.invoke(status, [])

    assert result.exit_code == 0
    assert any("No services are running." in message for message in messages)


def test_serve_invokes_uvicorn(monkeypatch, runner):
    import uvicorn

    called = {}

    def _fake_uvicorn_run(app, host, port, reload):
        called["app"] = app
        called["host"] = host
        called["port"] = port
        called["reload"] = reload

    monkeypatch.setattr(uvicorn, "run", _fake_uvicorn_run)

    result = runner.invoke(serve, ["--host", "127.0.0.1", "--port", "9001", "--reload"])

    assert result.exit_code == 0
    assert called == {
        "app": "backend.main:app",
        "host": "127.0.0.1",
        "port": 9001,
        "reload": True,
    }
