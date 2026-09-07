"""Main entry point for ARC CLOUD CLI."""

from __future__ import annotations

from typing import Optional
import typer
from rich.console import Console

from arc_cloud import __app_name__, __version__
from arc_cloud.commands.explain import explain_command
from arc_cloud.commands.init import init_command
from arc_cloud.commands.report import report_command
from arc_cloud.commands.scan import scan_command
from arc_cloud.commands.version import version_command

console = Console()

app = typer.Typer(
    name=__app_name__,
    help="ARC CLOUD — Software Engineering Health Platform CLI.",
    no_args_is_help=True,
    add_completion=False,
)

# Register CLI commands
app.command(name="init", help="Initialize .arccloud.yml configuration in a project.")(init_command)
app.command(name="scan", help="Analyze a software project and evaluate engineering health.")(scan_command)
app.command(name="explain", help="Explain an ARC CLOUD static analysis rule and remediation guidance.")(explain_command)
app.command(name="report", help="Generate and export engineering health reports.")(report_command)
app.command(name="version", help="Show detailed platform architecture and engine versions.")(version_command)


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
    """ARC CLOUD — Software Engineering Health Platform."""
    pass


if __name__ == "__main__":
    app()
