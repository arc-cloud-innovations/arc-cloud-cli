"""The 'report' command for ARC CLOUD CLI."""
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console

from arc_cloud.core.config import ArcConfig
from arc_cloud.core.orchestrator import ScanOrchestrator
from arc_cloud.reporting.json_reporter import JSONReporter
from arc_cloud.reporting.sarif_reporter import SARIFReporter
from arc_cloud.reporting.terminal import TerminalReporter
from arc_cloud.reporting.html_reporter import HTMLReporter

console = Console()
err_console = Console(stderr=True)


def report_command(
    path: Optional[str] = typer.Argument(
        None,
        help="Path to project directory (defaults to current working directory).",
        show_default=False,
    ),
    format_type: str = typer.Option(
        "terminal",
        "--format",
        "-f",
        help="Report format: terminal, json, sarif, or html.",
    ),
    output_file: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Path to write the report file.",
    ),
    config_path: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to .arccloud.yml configuration file.",
    ),
) -> None:
    """Generate and export a software engineering health report."""
    target_path = Path(path).resolve() if path else Path.cwd()

    if not target_path.exists() or not target_path.is_dir():
        err_console.print(f"[bold red]✗ Error:[/bold red] Project directory does not exist: {target_path}")
        raise typer.Exit(code=2)

    cfg = None
    if config_path:
        cfg_file = Path(config_path).resolve()
        if not cfg_file.is_file():
            err_console.print(f"[bold red]✗ Config Error:[/bold red] Specified config file not found: {cfg_file}")
            raise typer.Exit(code=2)
        cfg = ArcConfig.load(cfg_file.parent)

    try:
        orchestrator = ScanOrchestrator(config=cfg)
        health_report = orchestrator.run_scan(target_path)
    except Exception as e:
        err_console.print(f"[bold red]✗ Scan Error:[/bold red] {e}")
        raise typer.Exit(code=3)

    fmt = format_type.lower().strip()
    rendered_content = ""

    if fmt == "json":
        rendered_content = JSONReporter.render(health_report)
    elif fmt == "sarif":
        rendered_content = SARIFReporter.render(health_report)
    elif fmt == "html":
        html_reporter = HTMLReporter(health_report)
        rendered_content = html_reporter.render()
        if not output_file:
            output_file = "arc_health_report.html"
    elif fmt == "terminal":
        terminal_reporter = TerminalReporter(console=console)
        terminal_reporter.render(health_report)
    else:
        err_console.print(f"[bold red]✗ Error:[/bold red] Unknown report format '{format_type}'. Choose from terminal, json, sarif, html.")
        raise typer.Exit(code=2)

    if output_file:
        try:
            out_p = Path(output_file).resolve()
            out_p.parent.mkdir(parents=True, exist_ok=True)
            if fmt == "terminal":
                # For terminal output to file, record text
                from rich.console import Console as FileConsole
                file_console = FileConsole(record=True, width=100)
                TerminalReporter(console=file_console).render(health_report)
                out_p.write_text(file_console.export_text(), encoding="utf-8")
            else:
                out_p.write_text(rendered_content, encoding="utf-8")
            console.print(f"[bold green]✓ Report saved to:[/bold green] [cyan]{out_p}[/cyan]")
        except Exception as e:
            err_console.print(f"[bold red]✗ Error saving report:[/bold red] {e}")
            raise typer.Exit(code=3)
    elif fmt in ("json", "sarif"):
        print(rendered_content)
