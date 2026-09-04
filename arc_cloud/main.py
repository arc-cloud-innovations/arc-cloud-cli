"""Main entry point for ARC CLOUD CLI."""

from __future__ import annotations

from typing import Optional
import typer
from rich.console import Console

from arc_cloud import __app_name__, __version__
from arc_cloud.commands.scan import scan_command

console = Console()

app = typer.Typer(
    name=__app_name__,
    help="ARC CLOUD CLI — Local, deterministic Software X-Ray scanner and Software Blueprint generator.",
    no_args_is_help=True,
    add_completion=False,
)

# Register primary command
app.command(name="scan", help="Analyze a software project statically and generate a Software Blueprint.")(scan_command)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold cyan]{__app_name__}[/bold cyan] version [green]{__version__}[/green]")
        raise typer.Exit()



@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show ARC CLOUD CLI version and exit.",
        callback=_version_callback,
        is_eager=True,
    )
) -> None:
    """ARC CLOUD — Software X-Ray platform."""
    pass


if __name__ == "__main__":
    app()
