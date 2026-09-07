"""The 'scan' command for ARC CLOUD CLI."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console

from arc_cloud.blueprint.generator import BlueprintGenerator
from arc_cloud.core.config import ArcConfig
from arc_cloud.core.models import FindingSeverity
from arc_cloud.core.orchestrator import ScanOrchestrator
from arc_cloud.reporting.json_reporter import JSONReporter
from arc_cloud.reporting.sarif_reporter import SARIFReporter
from arc_cloud.reporting.terminal import TerminalReporter
from arc_cloud.scanner.engine import ScannerEngine

console = Console()
err_console = Console(stderr=True)


def scan_command(
    path: Optional[str] = typer.Argument(
        None,
        help="Path to the software project to analyze (defaults to current working directory).",
        show_default=False,
    ),
    format_type: str = typer.Option(
        "terminal",
        "--format",
        "-f",
        help="Output report format: 'terminal', 'json', or 'sarif'.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Shortcut for --format json.",
    ),
    output_file: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Save report to a specified file.",
    ),
    config_path: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Custom path to .arccloud.yml configuration file.",
    ),
    fail_on: str = typer.Option(
        "high",
        "--fail-on",
        help="Severity threshold to fail scan with exit code 1: 'critical', 'high', 'medium', 'low', 'none'.",
    ),
    blueprint: bool = typer.Option(
        False,
        "--blueprint",
        help="Run legacy Software Blueprint generator instead of health scan.",
    ),
) -> None:
    """Analyze a software project statically and evaluate engineering health."""
    target_path = Path(path).resolve() if path else Path.cwd()

    # Pre-flight path validations (Exit code 2 for config / argument errors)
    if not target_path.exists():
        err_console.print(f"[bold red]✗ Error:[/bold red] Project path does not exist: '{target_path}'")
        raise typer.Exit(code=2)

    if not target_path.is_dir():
        err_console.print(f"[bold red]✗ Error:[/bold red] Project path is not a directory: '{target_path}'")
        raise typer.Exit(code=2)

    # Legacy Blueprint mode if requested
    if blueprint:
        _run_legacy_blueprint_scan(target_path, json_output or (format_type == "json"), output_file)
        return

    # Load custom config if provided
    config: Optional[ArcConfig] = None
    if config_path:
        cfg_file = Path(config_path).resolve()
        if not cfg_file.is_file():
            err_console.print(f"[bold red]✗ Configuration Error:[/bold red] Config file not found: {cfg_file}")
            raise typer.Exit(code=2)
        try:
            config = ArcConfig.load(cfg_file.parent)
        except Exception as e:
            err_console.print(f"[bold red]✗ Configuration Error:[/bold red] Invalid configuration: {e}")
            raise typer.Exit(code=2)

    # Format resolution
    selected_format = "json" if json_output else format_type.lower().strip()
    if output_file and selected_format == "terminal" and not json_output:
        if output_file.endswith(".json"):
            selected_format = "json"
        elif output_file.endswith(".sarif"):
            selected_format = "sarif"

    if selected_format not in ("terminal", "json", "sarif"):
        err_console.print(f"[bold red]✗ Error:[/bold red] Invalid format '{selected_format}'. Valid options: terminal, json, sarif.")
        raise typer.Exit(code=2)

    # Execute Scan Orchestration (Exit code 3 for runtime scan errors)
    try:
        orchestrator = ScanOrchestrator(config=config)
        report = orchestrator.run_scan(target_path)
    except PermissionError as exc:
        err_console.print(f"[bold red]✗ Permission Error:[/bold red] {exc}")
        raise typer.Exit(code=3)
    except Exception as exc:
        err_console.print(f"[bold red]✗ Scan Error:[/bold red] Unexpected error: {exc}")
        raise typer.Exit(code=3)

    # Render Report
    rendered_text = ""
    if selected_format == "terminal":
        terminal_reporter = TerminalReporter(console=console)
        terminal_reporter.render(report)
    elif selected_format == "json":
        rendered_text = JSONReporter.render(report)
    elif selected_format == "sarif":
        rendered_text = SARIFReporter.render(report)

    # Save output to file if requested
    if output_file:
        try:
            out_path = Path(output_file).resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            if selected_format == "terminal":
                from rich.console import Console as FileConsole
                fc = FileConsole(record=True, width=100)
                TerminalReporter(console=fc).render(report)
                out_path.write_text(fc.export_text(), encoding="utf-8")
            else:
                out_path.write_text(rendered_text, encoding="utf-8")
            console.print(f"[bold green]✓[/bold green] Report saved to [cyan]{out_path}[/cyan]\n")
        except Exception as exc:
            err_console.print(f"[bold red]✗ Error saving report:[/bold red] {exc}")
            raise typer.Exit(code=3)
    elif selected_format in ("json", "sarif"):
        print(rendered_text)

    # Evaluate fail-on threshold (Exit code 1 for findings exceeding threshold)
    threshold = fail_on.lower().strip()
    should_fail = False

    risk = report.risk_assessment
    if threshold == "critical":
        should_fail = risk.critical_count > 0
    elif threshold == "high":
        should_fail = (risk.critical_count > 0) or (risk.high_count > 0)
    elif threshold == "medium":
        should_fail = (risk.critical_count > 0) or (risk.high_count > 0) or (risk.medium_count > 0)
    elif threshold == "low":
        should_fail = (risk.critical_count > 0) or (risk.high_count > 0) or (risk.medium_count > 0) or (risk.low_count > 0)
    elif threshold == "none":
        should_fail = False
    else:
        err_console.print(f"[yellow]Warning:[/yellow] Unrecognized fail-on threshold '{threshold}'. Defaulting to 'high'.")
        should_fail = (risk.critical_count > 0) or (risk.high_count > 0)

    if should_fail:
        raise typer.Exit(code=1)


def _run_legacy_blueprint_scan(target_path: Path, is_json: bool, output_file: Optional[str]) -> None:
    """Fallback legacy blueprint scan."""
    engine = ScannerEngine()
    try:
        blueprint = engine.scan(target_path)
    except Exception as exc:
        err_console.print(f"[bold red]✗ Scan Failed:[/bold red] {exc}")
        raise typer.Exit(code=3)

    if output_file:
        BlueprintGenerator.save_to_file(blueprint, output_file)
        if not is_json:
            console.print(f"[bold green]✓[/bold green] Blueprint written to [cyan]{output_file}[/cyan]\n")

    if is_json:
        print(BlueprintGenerator.to_json(blueprint))
        return

    from arc_cloud.commands.scan import _render_rich_blueprint_report  # fallback helper
    console.print(f"[green]Scanned {blueprint.project.name} successfully.[/green]")
