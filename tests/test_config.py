from pathlib import Path

import pytest
from typer.testing import CliRunner

from changesrequested import cli
from changesrequested.cli import app
from changesrequested.config import (
    ConfigError,
    MissingApiKeyError,
    UnknownModelError,
    load_config,
    read_config,
)

REPO_CONFIG = Path(__file__).resolve().parents[1] / "config.yaml"

CLAUDE = """
  - name: claude-main
    provider: anthropic
    model: claude-x
"""
LOCAL = """
  - name: local-main
    provider: ollama
    model: local-x
    endpoint: http://localhost:11434/v1
"""


@pytest.fixture(autouse=True)
def no_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Run from an empty dir so a developer's real .env is never loaded.
    monkeypatch.chdir(tmp_path)
    for var in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def write_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "config.yaml"
    monkeypatch.setenv("CHREQ_CONFIG", str(path))

    def write(text: str) -> Path:
        path.write_text(text)
        return path

    return write


def test_settings_override_defaults(write_config) -> None:
    write_config("settings:\n  max_attempts: 3\nmodels:" + LOCAL)

    settings = read_config().settings

    assert settings.max_attempts == 3
    assert settings.context_token_budget == 6000


def test_missing_settings_block_uses_defaults(write_config) -> None:
    write_config("models:" + LOCAL)

    assert read_config().settings.naive_chunk_lines == 60


def test_wrong_setting_type_names_the_field(write_config) -> None:
    write_config("settings:\n  max_attempts: two\nmodels:" + LOCAL)

    with pytest.raises(ConfigError, match="settings.max_attempts"):
        read_config()


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        (
            "  - name: claude-main\n    provider: anthropic\n",
            r"models\[claude-main\].model",
        ),
        (
            "  - name: claude-main\n    provider: anthropic\n    model: '  '\n",
            r"models\[claude-main\].model",
        ),
        (
            (
                "  - name: local-main\n    provider: ollama\n    model: x\n"
                "    endpoint: ''\n"
            ),
            r"models\[local-main\].endpoint",
        ),
        (
            (
                "  - name: claude-main\n    provider: anthropic\n    model: x\n"
                "    api_key_env: ANTHROPIC_API_KEY\n"
            ),
            r"models\[claude-main\].api_key_env",
        ),
        (
            "  - name: local-main\n    provider: ollama\n    model: x\n",
            r"models\[local-main\].endpoint",
        ),
        (
            "  - name: odd-main\n    provider: openai\n    model: x\n",
            r"models\[odd-main\]",
        ),
    ],
)
def test_invalid_entry_names_the_entry(write_config, entry: str, message: str) -> None:
    write_config("models:\n" + entry)

    with pytest.raises(ConfigError, match=message):
        read_config()


def test_duplicate_names_are_rejected(write_config) -> None:
    write_config("models:" + LOCAL + LOCAL)

    with pytest.raises(ConfigError, match="duplicate model name 'local-main'"):
        read_config()


def test_availability(write_config, monkeypatch: pytest.MonkeyPatch) -> None:
    write_config("models:" + CLAUDE + LOCAL)

    config = load_config()
    assert [m.name for m in config.available_models()] == ["local-main"]

    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret")
    assert len(config.available_models()) == 2


def test_no_available_model_fails(write_config) -> None:
    write_config("models:" + CLAUDE)

    with pytest.raises(ConfigError, match=r"claude-main \(ANTHROPIC_API_KEY not set\)"):
        load_config()


def test_get_model_errors(write_config) -> None:
    write_config("models:" + CLAUDE + LOCAL)
    config = load_config()

    with pytest.raises(MissingApiKeyError, match="ANTHROPIC_API_KEY"):
        config.get_model("claude-main")
    with pytest.raises(UnknownModelError, match="unknown model 'nope'"):
        config.get_model("nope")
    assert config.get_model("local-main").provider == "ollama"


def test_chreq_config_env_var_selects_file(write_config) -> None:
    path = write_config("models:" + LOCAL)

    assert read_config().models[0].name == "local-main"
    assert path.exists()


@pytest.mark.parametrize(("reachable", "exit_code"), [(True, 0), (False, 1)])
def test_config_check_exit_code(
    write_config, monkeypatch: pytest.MonkeyPatch, reachable: bool, exit_code: int
) -> None:
    write_config("models:" + CLAUDE + LOCAL)
    monkeypatch.setattr(cli, "endpoint_reachable", lambda endpoint: reachable)

    result = CliRunner().invoke(app, ["config", "check"])

    assert result.exit_code == exit_code
    assert "claude-main: missing key (ANTHROPIC_API_KEY)" in result.output


def test_committed_config_loads_without_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHREQ_CONFIG", str(REPO_CONFIG))

    config = load_config()

    assert {m.name for m in config.models} == {
        "claude-main",
        "gemini-main",
        "local-main",
    }


def test_config_check_reads_keys_from_dotenv(
    write_config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_config("models:" + CLAUDE)
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=secret\n")

    result = CliRunner().invoke(app, ["config", "check"])

    assert result.exit_code == 0
    assert "claude-main: ok" in result.output
    assert "secret" not in result.output
