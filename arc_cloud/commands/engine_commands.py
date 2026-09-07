"""Individual Engine Commands for ARC CLOUD CLI."""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from arc_cloud.core.models import EngineStatus
from arc_cloud.core.orchestrator import ScanOrchestrator

console = Console()
err_console = Console(stderr=True)


def _run_engine_command(engine_name: str, display_title: str, path: Optional[str] = None) -> None:
    target_path = Path(path).resolve() if path else Path.cwd()
    if not target_path.exists() or not target_path.is_dir():
        err_console.print(f"[bold red]✗ Error:[/bold red] Project path does not exist or is not a directory: {target_path}")
        raise typer.Exit(code=2)

    try:
        orchestrator = ScanOrchestrator()
        report = orchestrator.run_scan(target_path)
    except Exception as exc:
        err_console.print(f"[bold red]✗ Scan Error:[/bold red] {exc}")
        raise typer.Exit(code=3)

    engine_res = report.engine_results.get(engine_name)
    health = report.health_score
    score_val = getattr(health, engine_name, None)
    status = health.engine_statuses.get(engine_name, EngineStatus.NOT_ANALYZED)
    st_val = status.value if hasattr(status, "value") else str(status)

    # Filter findings for this engine
    findings = [f for f in report.findings if getattr(f, "engine", "").lower() == engine_name.lower()]

    console.print()
    console.rule(f"[bold cyan]ARC CLOUD — {display_title}[/bold cyan]")
    console.print()

    # Overview panel
    meta_table = Table.grid(padding=(0, 2))
    meta_table.add_column(style="bold white")
    meta_table.add_column()
    meta_table.add_row("Status:", f"[bold green]{st_val}[/bold green]" if st_val == "ANALYZED" else f"[bold yellow]{st_val}[/bold yellow]")
    if score_val is not None and st_val == "ANALYZED":
        if isinstance(score_val, (int, float)):
            grade = "A" if score_val >= 90 else "B" if score_val >= 80 else "C" if score_val >= 70 else "D" if score_val >= 60 else "F"
            meta_table.add_row("Engine Score:", f"[bold cyan]{score_val:.0f}/100[/bold cyan] (Grade {grade})")
        else:
            meta_table.add_row("Engine Score:", f"[bold cyan]{score_val}[/bold cyan]")
    else:
        meta_table.add_row("Engine Score:", "[dim]NOT ANALYZED[/dim]")
    meta_table.add_row("Findings Detected:", f"[bold]{len(findings)}[/bold]")
    exec_time = engine_res.get("execution_time_ms") if isinstance(engine_res, dict) else getattr(engine_res, "execution_time_ms", None)
    if exec_time:
        meta_table.add_row("Execution Time:", f"{exec_time:.1f} ms")

    console.print(Panel(meta_table, title="Engine Diagnostic Summary", border_style="cyan"))
    console.print()

    # Engine Metrics (if any)
    metrics = engine_res.get("metrics") if isinstance(engine_res, dict) else getattr(engine_res, "metrics", {})
    if metrics:
        m_table = Table(title="Observed Telemetry & Metrics", box=None, padding=(0, 2))
        m_table.add_column("Metric Key", style="cyan")
        m_table.add_column("Value", style="bold white")
        for k, v in metrics.items():
            m_table.add_row(str(k).replace("_", " ").capitalize(), str(v))
        console.print(m_table)
        console.print()

    # Findings Table
    if findings:
        f_table = Table(title=f"{display_title} Findings", padding=(0, 1))
        f_table.add_column("ID", style="bold cyan")
        f_table.add_column("Rule", style="yellow")
        f_table.add_column("Severity", style="bold")
        f_table.add_column("Location", style="white")
        f_table.add_column("Message")

        for f in findings:
            sev_style = "red" if f.severity.value in ("critical", "high") else "yellow" if f.severity.value == "medium" else "blue"
            loc = f"{f.file_path}:{f.line or 1}"
            f_table.add_row(f.id, f.rule_id, f"[{sev_style}]{f.severity.value.upper()}[/{sev_style}]", loc, f.message)

        console.print(f_table)
        console.print()
        console.print("Run [cyan]arc explain <RULE_OR_FINDING_ID>[/cyan] or [cyan]arc fix <FINDING_ID>[/cyan] to remediate.")
    else:
        console.print(f"[green]✓ No findings detected for {display_title}. Good job![/green]\n")


def reliability_command(path: Optional[str] = typer.Argument(None, help="Target project path")) -> None:
    """Analyze code reliability, exception handling, and resource safety."""
    _run_engine_command("reliability", "Reliability Engine", path)


def security_command(path: Optional[str] = typer.Argument(None, help="Target project path")) -> None:
    """Analyze application security vulnerabilities (SQL injection, command injection, crypto)."""
    _run_engine_command("security", "Security Engine", path)


def secrets_command(path: Optional[str] = typer.Argument(None, help="Target project path")) -> None:
    """Scan for hardcoded API keys, tokens, and credentials (masked safely)."""
    _run_engine_command("secrets", "Secrets Engine", path)


def deps_command(path: Optional[str] = typer.Argument(None, help="Target project path")) -> None:
    """Analyze project dependencies, lockfiles, and wildcard version risks."""
    _run_engine_command("dependencies", "Dependency Engine", path)


def architecture_command(path: Optional[str] = typer.Argument(None, help="Target project path")) -> None:
    """Analyze modularity, circular dependencies, and architectural layer health."""
    _run_engine_command("architecture", "Architecture Engine", path)


def debt_command(path: Optional[str] = typer.Argument(None, help="Target project path")) -> None:
    """Calculate technical debt hours, remediation breakdown, and code smell distribution."""
    _run_engine_command("technical_debt", "Technical Debt Engine", path)


def test_command(path: Optional[str] = typer.Argument(None, help="Target project path")) -> None:
    """Evaluate automated test existence, test-to-source ratios, and test suite health."""
    _run_engine_command("testing", "Testing Engine", path)


def performance_command(path: Optional[str] = typer.Argument(None, help="Target project path")) -> None:
    """Identify algorithmic complexity hotspots, nested loops, and regex inefficiencies."""
    _run_engine_command("performance", "Performance Engine", path)


def ai_risk_command(path: Optional[str] = typer.Argument(None, help="Target project path")) -> None:
    """Assess composite AI & engineering compounding risk signals."""
    _run_engine_command("ai_risk", "AI Risk Engine", path)
