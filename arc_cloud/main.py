"""Main entry point for ARC CLOUD CLI."""

from __future__ import annotations

from typing import Optional
import typer
from rich.console import Console

from arc_cloud import __app_name__, __version__
from arc_cloud.commands.ci import ci_command
from arc_cloud.commands.engine_commands import (
    architecture_command,
    debt_command,
    deps_command,
    performance_command,
    reliability_command,
    secrets_command,
    security_command,
    test_command,
    ai_risk_command,
)
from arc_cloud.commands.ai_commands import (
    fix_command,
    plan_command,
    review_command,
    verify_command,
)
from arc_cloud.commands.explain import explain_command
from arc_cloud.commands.init import init_command
from arc_cloud.commands.report import report_command
from arc_cloud.commands.scan import scan_command
from arc_cloud.commands.start import start_command
from arc_cloud.commands.version import version_command

console = Console()

app = typer.Typer(
    name=__app_name__,
    help="ARC CLOUD — Software Engineering Health Platform CLI.",
    no_args_is_help=True,
    add_completion=False,
)

# Core Platform Commands
app.command(name="start", help="Live engineering health monitoring mode (continuous watcher, tests, regressions).")(start_command)
app.command(name="scan", help="Analyze a software project and evaluate engineering health.")(scan_command)
app.command(name="report", help="Generate and export engineering health reports (terminal, json, sarif, html).")(report_command)
app.command(name="ci", help="Automated CI/CD quality gate with strict exit codes and SARIF output.")(ci_command)
app.command(name="init", help="Initialize .arccloud.yml configuration in a project.")(init_command)
app.command(name="version", help="Show detailed platform architecture and engine versions.")(version_command)

# AI-Assisted Diagnosis & Remediation Commands
app.command(name="explain", help="Explain a finding or rule with root cause, side effects, and verification test.")(explain_command)
app.command(name="fix", help="Generate and apply an automated fix patch for a finding with backup & re-scan.")(fix_command)
app.command(name="plan", help="Generate a prioritized, sprint-ready engineering remediation plan (P0, P1, P2).")(plan_command)
app.command(name="review", help="Pre-commit AI code review of uncommitted git changes to prevent regressions.")(review_command)
app.command(name="verify", help="Compare current scan against baseline (.arc/baseline.json) and track trends.")(verify_command)

# Dedicated Analysis Engine Subcommands
app.command(name="reliability", help="Run targeted reliability analysis (exception handling, resource leaks).")(reliability_command)
app.command(name="security", help="Run targeted security vulnerability analysis (SQLi, command injection, crypto).")(security_command)
app.command(name="secrets", help="Scan for hardcoded secrets, API tokens, and credentials (safely masked).")(secrets_command)
app.command(name="deps", help="Analyze dependencies, package manifests, and wildcard pinning risks.")(deps_command)
app.command(name="architecture", help="Analyze circular dependencies, layer boundaries, and modularity.")(architecture_command)
app.command(name="debt", help="Calculate technical debt hours, remediation breakdown, and code smells.")(debt_command)
app.command(name="test", help="Evaluate automated test existence, test/source ratios, and test suite health.")(test_command)
app.command(name="performance", help="Identify algorithmic complexity hotspots and regex compilation issues.")(performance_command)
app.command(name="ai-risk", help="Assess composite AI and engineering compounding risk signals.")(ai_risk_command)


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
