"""Command-line entry point for chreq."""

import typer

app = typer.Typer(
    help="Review a code diff using retrieval over the surrounding repo.",
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
)


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
