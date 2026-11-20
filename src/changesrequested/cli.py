"""Command-line entry point for chreq."""

from pathlib import Path

import typer
from dotenv import load_dotenv

from changesrequested.config import (
    CloudModel,
    ConfigError,
    LocalModel,
    endpoint_reachable,
    read_config,
)

app = typer.Typer(
    help="Review a code diff using retrieval over the surrounding repo.",
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
)
config_app = typer.Typer(help="Inspect config.yaml.", no_args_is_help=True)
app.add_typer(config_app, name="config")


@app.callback()
def main() -> None:
    # Keys in ./.env fill in env vars that are not already set.
    load_dotenv(Path(".env"))


def _not_implemented(command: str) -> None:
    typer.echo(f"chreq {command}: not implemented yet", err=True)
    raise typer.Exit(code=1)


@app.command()
def index() -> None:
    """Chunk and embed a target repo."""
    _not_implemented("index")


@app.command()
def review() -> None:
    """Review a diff against an indexed repo."""
    _not_implemented("review")


@app.command("eval")
def eval_() -> None:
    """Run the retrieval or review evals."""
    _not_implemented("eval")


@app.command()
def report() -> None:
    """Render README tables from results/."""
    _not_implemented("report")


@config_app.command()
def check() -> None:
    """Validate config.yaml and report which models are usable."""
    try:
        config = read_config()
    except ConfigError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None

    usable = 0
    for entry in config.models:
        if isinstance(entry, CloudModel) and entry.unavailable_reason():
            status = f"missing key ({entry.key_env})"
        elif isinstance(entry, LocalModel) and not endpoint_reachable(entry.endpoint):
            status = f"unreachable ({entry.endpoint})"
        else:
            status = "ok"
            usable += 1
        typer.echo(f"{entry.name}: {status}")

    if usable == 0:
        typer.echo("error: no usable models", err=True)
        raise typer.Exit(code=1)
