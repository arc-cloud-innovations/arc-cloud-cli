"""The 'ci' command for ARC CLOUD CLI — Automated CI/CD Quality Gate."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

from arc_cloud.core.config import ArcConfig
from arc_cloud.core.models import FindingSeverity
from arc_cloud.core.orchestrator import ScanOrchestrator
from arc_cloud.reporting.sarif_reporter import SARIFReporter

console = Console()
err_console = Console(stderr=True)


def ci_command(
    path: Optional[str] = typer.Argument(
        None,
        help="Project path to evaluate (defaults to current working directory).",
        show_default=False,
    ),
    fail_on: str = typer.Option(
        "high",
        "--fail-on",
        help="Severity threshold to fail quality gate: 'critical', 'high', 'medium', 'low', 'none'.",
    ),
    min_health: float = typer.Option(
        0.0,
        "--min-health",
        help="Minimum required overall health score (0-100).",
    ),
    max_debt_hours: float = typer.Option(
        9999.0,
        "--max-debt-hours",
        help="Maximum allowable technical debt in hours.",
    ),
    sarif_output: str = typer.Option(
        "arc-results.sarif",
        "--sarif-file",
        help="File path to save SARIF output for GitHub Code Scanning.",
    ),
    config_path: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to .arccloud.yml config file.",
    ),
) -> None:
    """Run automated CI quality gate with strict exit codes and GitHub Actions integration."""
    target_path = Path(path).resolve() if path else Path.cwd()

    if not target_path.exists() or not target_path.is_dir():
        err_console.print(f"[bold red]✗ CI Error:[/bold red] Target directory does not exist: {target_path}")
        raise typer.Exit(code=2)

    config = None
    if config_path:
        cfg_file = Path(config_path).resolve()
        if not cfg_file.is_file():
            err_console.print(f"[bold red]✗ Config Error:[/bold red] Config file not found: {cfg_file}")
            raise typer.Exit(code=2)
        try:
            config = ArcConfig.load(cfg_file.parent)
        except Exception as exc:
            err_console.print(f"[bold red]✗ Config Error:[/bold red] {exc}")
            raise typer.Exit(code=2)

    threshold = fail_on.lower().strip()
    if threshold not in ("critical", "high", "medium", "low", "none"):
        err_console.print(f"[bold red]✗ Argument Error:[/bold red] Invalid --fail-on value '{threshold}'.")
        raise typer.Exit(code=2)

    # 1. Execute Scan
    try:
        orchestrator = ScanOrchestrator(config=config)
        report = orchestrator.run_scan(target_path)
    except PermissionError as exc:
        err_console.print(f"[bold red]✗ CI Engine Error:[/bold red] Permission denied: {exc}")
        raise typer.Exit(code=3)
    except Exception as exc:
        err_console.print(f"[bold red]✗ CI Engine Error:[/bold red] {exc}")
        raise typer.Exit(code=3)

    # 2. Write SARIF report for GitHub Code Scanning
    try:
        sarif_p = Path(sarif_output)
        if not sarif_p.is_absolute():
            sarif_p = (target_path / sarif_output).resolve()
        else:
            sarif_p = sarif_p.resolve()
        sarif_p.parent.mkdir(parents=True, exist_ok=True)
        sarif_json = SARIFReporter.render(report)
        sarif_p.write_text(sarif_json, encoding="utf-8")
        sarif_saved = True
    except Exception as exc:
        err_console.print(f"[yellow]Warning:[/yellow] Could not write SARIF file: {exc}")
        sarif_saved = False

    # 3. Compact CI Summary in Terminal
    health = report.health_score
    risk = report.risk_assessment
    debt = report.technical_debt_estimate or {}
    debt_hours = debt.get("estimated_hours", 0.0)

    console.print()
    console.rule("[bold cyan]ARC CLOUD CI/CD Quality Gate[/bold cyan]")
    console.print()

    summary_table = Table(box=None, padding=(0, 2))
    summary_table.add_column("Metric", style="bold white")
    summary_table.add_column("Value", style="cyan")
    summary_table.add_column("Threshold / Gate", style="yellow")
    summary_table.add_column("Status", style="bold")

    # Gate 1: Health Score
    health_pass = health.overall_score >= min_health
    summary_table.add_row(
        "Health Score",
        f"{health.overall_score:.0f}/100 ({health.letter_grade})",
        f">= {min_health:.0f}",
        "[green]PASS[/green]" if health_pass else "[red]FAIL[/red]",
    )

    # Gate 2: Technical Debt
    debt_pass = debt_hours <= max_debt_hours
    summary_table.add_row(
        "Technical Debt",
        f"{debt_hours:.1f} hrs",
        f"<= {max_debt_hours:.1f} hrs",
        "[green]PASS[/green]" if debt_pass else "[red]FAIL[/red]",
    )

    # Gate 3: Severity Threshold
    sev_fail = False
    if threshold == "critical":
        sev_fail = risk.critical_count > 0
    elif threshold == "high":
        sev_fail = (risk.critical_count > 0) or (risk.high_count > 0)
    elif threshold == "medium":
        sev_fail = (risk.critical_count > 0) or (risk.high_count > 0) or (risk.medium_count > 0)
    elif threshold == "low":
        sev_fail = (risk.critical_count > 0) or (risk.high_count > 0) or (risk.medium_count > 0) or (risk.low_count > 0)
    elif threshold == "none":
        sev_fail = False

    summary_table.add_row(
        "Findings Count",
        f"Crit:{risk.critical_count} High:{risk.high_count} Med:{risk.medium_count}",
        f"Fail on {threshold.upper()}",
        "[red]FAIL[/red]" if sev_fail else "[green]PASS[/green]",
    )

    console.print(summary_table)
    console.print()

    if sarif_saved:
        console.print(f"[dim]SARIF report generated: {sarif_output}[/dim]")

    # 4. GitHub Actions Step Summary Support ($GITHUB_STEP_SUMMARY)
    gh_step_summary = os.getenv("GITHUB_STEP_SUMMARY")
    if gh_step_summary:
        try:
            with open(gh_step_summary, "a", encoding="utf-8") as f:
                f.write(f"## ARC CLOUD Quality Gate Summary\n\n")
                f.write(f"- **Health Score:** {health.overall_score:.0f}/100 ({health.letter_grade})\n")
                f.write(f"- **Coverage:** {health.analysis_coverage}\n")
                f.write(f"- **Total Findings:** {len(report.findings)}\n")
                f.write(f"- **Critical:** {risk.critical_count} | **High:** {risk.high_count} | **Medium:** {risk.medium_count}\n")
                f.write(f"- **Technical Debt:** {debt_hours:.1f} hrs\n")
                if not health_pass or not debt_pass or sev_fail:
                    f.write("\n> ❌ **Result: Quality Gate FAILED**\n")
                else:
                    f.write("\n> ✅ **Result: Quality Gate PASSED**\n")
        except Exception:
            pass

    # 5. Determine Exit Code
    if not health_pass or not debt_pass or sev_fail:
        console.print("[bold red]✗ CI Quality Gate FAILED[/bold red]\n")
        raise typer.Exit(code=1)

    console.print("[bold green]✓ CI Quality Gate PASSED[/bold green]\n")
    raise typer.Exit(code=0)
