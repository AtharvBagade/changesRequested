"""Typed settings and model entries loaded from config.yaml."""

import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

logger = logging.getLogger(__name__)

CONFIG_ENV_VAR = "CHREQ_CONFIG"
DEFAULT_CONFIG_PATH = Path("config.yaml")

# Each cloud provider reads its key from one fixed env var, the SDK default.
PROVIDER_KEY_ENV = {"anthropic": "ANTHROPIC_API_KEY", "google": "GEMINI_API_KEY"}


class ConfigError(Exception):
    """config.yaml is missing, malformed, or has no usable model."""


class UnknownModelError(ConfigError):
    """No model entry has the requested name."""


class MissingApiKeyError(ConfigError):
    """A model entry's API key env var is not set."""


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context_token_budget: int = 6000
    max_attempts: int = 2
    naive_chunk_lines: int = 60
    naive_chunk_overlap: int = 10
    results_dir: Path = Path("results")
    # One sentence-transformers model for every study. No default, so the id
    # lives only in config.yaml.
    embedding_model: str | None = None


class CloudModel(BaseModel):
    """A hosted model. Available when its provider's key env var is set."""

    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, str_min_length=1
    )

    name: str
    provider: Literal["anthropic", "google"]
    model: str
    endpoint: str | None = None

    @property
    def key_env(self) -> str:
        return PROVIDER_KEY_ENV[self.provider]

    def unavailable_reason(self) -> str | None:
        if os.environ.get(self.key_env):
            return None
        return f"{self.key_env} not set"


class LocalModel(BaseModel):
    """A model served locally. Available when its endpoint is set."""

    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, str_min_length=1
    )

    name: str
    provider: Literal["ollama", "vllm"]
    model: str
    endpoint: str

    def unavailable_reason(self) -> str | None:
        return None


ModelEntry = Annotated[CloudModel | LocalModel, Field(discriminator="provider")]


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")

    settings: Settings = Field(default_factory=Settings)
    models: list[ModelEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def _names_are_unique(self) -> "Config":
        seen: set[str] = set()
        for entry in self.models:
            if entry.name in seen:
                raise ValueError(f"duplicate model name '{entry.name}'")
            seen.add(entry.name)
        return self

    def available_models(self) -> list[CloudModel | LocalModel]:
        return [entry for entry in self.models if entry.unavailable_reason() is None]

    def get_model(self, name: str) -> CloudModel | LocalModel:
        for entry in self.models:
            if entry.name == name:
                if isinstance(entry, CloudModel) and entry.unavailable_reason():
                    raise MissingApiKeyError(
                        f"model '{name}' needs env var {entry.key_env}, "
                        "which is not set (export it or add it to .env)"
                    )
                return entry
        known = ", ".join(entry.name for entry in self.models)
        raise UnknownModelError(f"unknown model '{name}' (known: {known})")


def config_path() -> Path:
    return Path(os.environ.get(CONFIG_ENV_VAR, DEFAULT_CONFIG_PATH))


def read_config(path: Path | None = None) -> Config:
    """Parse and validate config.yaml without checking model availability."""
    path = path or config_path()
    try:
        raw = yaml.safe_load(path.read_text())
    except FileNotFoundError:
        raise ConfigError(
            f"config file not found: {path} (set {CONFIG_ENV_VAR} to override)"
        ) from None
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path} is not valid YAML: {exc}") from None
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} must be a mapping with 'settings' and 'models'")
    try:
        return Config.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"{path} is invalid:\n{_describe(exc, raw)}") from None


def load_config(path: Path | None = None) -> Config:
    """Read config.yaml and require at least one available model."""
    config = read_config(path)
    reasons = {entry.name: entry.unavailable_reason() for entry in config.models}
    for name, reason in reasons.items():
        if reason is not None:
            logger.info("%s: %s, skipping", name, reason)
    if not config.available_models():
        listed = ", ".join(f"{name} ({reason})" for name, reason in reasons.items())
        raise ConfigError(f"no usable models in {path or config_path()}: {listed}")
    return config


def endpoint_reachable(endpoint: str, timeout: float = 2.0) -> bool:
    """True if an OpenAI-compatible server answers at endpoint."""
    try:
        with urllib.request.urlopen(f"{endpoint.rstrip('/')}/models", timeout=timeout):
            return True
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _describe(exc: ValidationError, raw: dict[str, Any]) -> str:
    """One line per error, naming the model entry instead of its list index."""
    models = raw.get("models")
    lines = []
    for error in exc.errors():
        loc = list(error["loc"])
        if len(loc) >= 2 and loc[0] == "models" and isinstance(loc[1], int):
            entry = models[loc[1]] if isinstance(models, list) else None
            entry = entry if isinstance(entry, dict) else {}
            rest = loc[2:]
            # Pydantic inserts the provider tag after the index; drop it.
            if rest and rest[0] == entry.get("provider"):
                rest = rest[1:]
            loc = [f"models[{entry.get('name') or loc[1]}]", *rest]
        where = ".".join(str(part) for part in loc) or "config"
        lines.append(f"  {where}: {error['msg']}")
    return "\n".join(lines)
