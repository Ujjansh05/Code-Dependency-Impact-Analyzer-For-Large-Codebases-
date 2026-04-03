from cli import __version__
from cli.main import cli


def test_cli_help_lists_commands(runner):
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    for command in ("start", "stop", "status", "analyze", "parse", "query", "serve"):
        assert command in result.output


def test_cli_version_flag(runner):
    result = runner.invoke(cli, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.output
