from typer.testing import CliRunner

from changesrequested.cli import app

runner = CliRunner()


def test_help_lists_top_level_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in ("index", "review", "eval", "report"):
        assert command in result.output


def test_short_help_matches_long_help() -> None:
    short = runner.invoke(app, ["-h"])
    long = runner.invoke(app, ["--help"])

    assert short.exit_code == 0
    assert short.output == long.output
