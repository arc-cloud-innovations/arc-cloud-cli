"""AI and Verification Commands: fix, plan, review, verify."""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from arc_cloud.ai.fix import FindingFixer
from arc_cloud.ai.plan import RemediationPlanner
from arc_cloud.ai.review import CodeReviewer
from arc_cloud.core.models import Finding
from arc_cloud.core.orchestrator import ScanOrchestrator
from arc_cloud.verification.verifier import BaselineVerifier

console = Console()
err_console = Console(stderr=True)


def fix_command(
    finding_id: str = typer.Argument(..., help="ID of the finding to remediate (e.g. arc-f-123)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview proposed patch without writing to file."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Apply fix automatically without prompt."),
) -> None:
    """Generate and apply an automated fix patch for a finding with automatic backup and re-scan."""
    root_dir = Path.cwd()

    # Find the finding in current scan
    try:
        report = ScanOrchestrator().run_scan(root_dir)
    except Exception as exc:
        err_console.print(f"[bold red]✗ Scan Error:[/bold red] {exc}")
        raise typer.Exit(code=3)

    target_finding: Optional[Finding] = None
    for f in report.findings:
        if f.id == finding_id or finding_id.lower() in f.id.lower():
            target_finding = f
            break

    if not target_finding:
        err_console.print(f"[bold red]✗ Error:[/bold red] Finding ID '{finding_id}' not found in current project scan.")
        raise typer.Exit(code=2)

    console.print()
    console.rule(f"[bold cyan]ARC CLOUD Automated Fix: {target_finding.id}[/bold cyan]")
    console.print()

    try:
        fix_data = FindingFixer.generate_fix(target_finding, root_dir)
    except Exception as exc:
        err_console.print(f"[bold red]✗ Fix Error:[/bold red] Could not generate patch: {exc}")
        raise typer.Exit(code=3)

    console.print(f"[bold white]Target File:[/bold white] [cyan]{fix_data['file_path']}[/cyan]")
    console.print(f"[bold white]Rule ID:[/bold white] [yellow]{fix_data['rule_id']}[/yellow]")
    console.print(f"[bold white]Action:[/bold white] {fix_data['fix_description']}\n")

    if fix_data["patch"]:
        console.print("[bold cyan]Proposed Patch (git diff):[/bold cyan]")
        console.print(Syntax(fix_data["patch"], "diff", theme="monokai"))
        console.print()
    else:
        console.print("[yellow]No automated file diff generated; manual refactoring recommended.[/yellow]")
        return

    if dry_run:
        console.print("[bold yellow]--dry-run enabled: No changes applied to file.[/bold yellow]\n")
        return

    # Confirm if not -y
    if not yes:
        confirm = typer.confirm("Apply this patch to your file? (A .bak backup file will be created)", default=True)
        if not confirm:
            console.print("[dim]Fix cancelled by user.[/dim]\n")
            return

    # Apply fix
    try:
        backup_path = FindingFixer.apply_fix(fix_data)
        console.print(f"[bold green]✓ Fix applied![/bold green] Backup saved to [dim]{backup_path}[/dim]")
    except Exception as exc:
        err_console.print(f"[bold red]✗ Apply Error:[/bold red] Failed to write changes: {exc}")
        raise typer.Exit(code=3)

    # Re-scan to verify resolution
    console.print("[dim]Re-scanning project to verify finding resolution...[/dim]")
    resolved = FindingFixer.verify_resolution(target_finding, root_dir)
    if resolved:
        console.print(f"[bold green]✓ Verified:[/bold green] Finding {target_finding.id} ({target_finding.rule_id}) is resolved!\n")
    else:
        console.print(f"[yellow]Notice: Finding {target_finding.id} still requires further manual refactoring.[/yellow]\n")


def plan_command(
    path: Optional[str] = typer.Argument(None, help="Target project path (defaults to current directory)"),
) -> None:
    """Generate a prioritized, sprint-ready remediation plan (P0 Immediate, P1 Short-term, P2 Long-term)."""
    target_path = Path(path).resolve() if path else Path.cwd()
    if not target_path.exists() or not target_path.is_dir():
        err_console.print(f"[bold red]✗ Error:[/bold red] Path not found: {target_path}")
        raise typer.Exit(code=2)

    try:
        report = ScanOrchestrator().run_scan(target_path)
    except Exception as exc:
        err_console.print(f"[bold red]✗ Scan Error:[/bold red] {exc}")
        raise typer.Exit(code=3)

    plan = RemediationPlanner.generate_plan(report)

    console.print()
    console.rule(f"[bold cyan]ARC CLOUD Engineering Remediation Plan — {plan['project_name']}[/bold cyan]")
    console.print()

    console.print(f"Overall Health Score: [bold cyan]{plan['overall_health_score']:.0f}/100[/bold cyan]")
    console.print(f"Total Estimated Engineering Time: [bold yellow]{plan['total_estimated_hours']} hours[/bold yellow]\n")

    summary = plan["summary"]
    s_table = Table.grid(padding=(0, 2))
    s_table.add_column(style="bold")
    s_table.add_column()
    s_table.add_row("[red]P0 Immediate (Critical/Security/Secrets):[/red]", f"{summary['p0_count']} items")
    s_table.add_row("[yellow]P1 Short-Term (High/Reliability/Arch):[/yellow]", f"{summary['p1_count']} items")
    s_table.add_row("[blue]P2 Long-Term (Debt/Testing/Quality):[/blue]", f"{summary['p2_count']} items")
    console.print(Panel(s_table, title="Work Breakdown", border_style="cyan"))
    console.print()

    def print_section(title: str, tasks: list, color: str):
        if not tasks:
            return
        console.print(f"[{color}][bold]{title}[/bold] ({len(tasks)} tasks)[/{color}]")
        t_table = Table(box=None, padding=(0, 1))
        t_table.add_column("Task ID", style="bold cyan")
        t_table.add_column("Rule", style="yellow")
        t_table.add_column("Location", style="white")
        t_table.add_column("Action", style="white")
        t_table.add_column("Est. Time", style="bold green")

        for t in tasks:
            t_table.add_row(t["id"], t["rule_id"], t["location"], t["action"], f"{t['estimated_minutes']}m")
        console.print(t_table)
        console.print()

    print_section("P0: Immediate Action Required", plan["p0_immediate"], "red")
    print_section("P1: Short-Term Sprint Priorities", plan["p1_short_term"], "yellow")
    print_section("P2: Long-Term Architecture & Health Goals", plan["p2_long_term"], "blue")

    console.print("[dim]Tip: Run [cyan]arc explain <TASK_ID>[/cyan] or [cyan]arc fix <TASK_ID>[/cyan] on individual items.[/dim]\n")


def review_command(
    path: Optional[str] = typer.Argument(None, help="Target project repository"),
    staged: bool = typer.Option(False, "--staged", "-s", help="Review staged changes only."),
) -> None:
    """Pre-commit AI code review of uncommitted or staged changes to flag regressions."""
    target_path = Path(path).resolve() if path else Path.cwd()
    if not target_path.exists() or not target_path.is_dir():
        err_console.print(f"[bold red]✗ Error:[/bold red] Target path not found: {target_path}")
        raise typer.Exit(code=2)

    console.print()
    console.rule("[bold cyan]ARC CLOUD Pre-Commit Code Review[/bold cyan]")
    console.print()

    res = CodeReviewer.review_changes(target_path, staged_only=staged)

    if res["changed_files_count"] > 0:
        console.print(f"Reviewing [bold]{res['changed_files_count']}[/bold] modified files from git diff:")
        for cf in res["changed_files"]:
            console.print(f"  • [cyan]{cf}[/cyan]")
        console.print()
    else:
        console.print("[dim]No git diff detected or not a git repository; running review on all source files.[/dim]\n")

    findings = res["findings"]
    if findings:
        console.print(f"[bold red]✗ {len(findings)} potential regressions detected in modified files:[/bold red]\n")
        table = Table(box=None, padding=(0, 1))
        table.add_column("Rule", style="yellow")
        table.add_column("Severity", style="bold")
        table.add_column("Location", style="white")
        table.add_column("Message")

        for f in findings:
            sev_style = "red" if f.severity.value in ("critical", "high") else "yellow"
            table.add_row(f.rule_id, f"[{sev_style}]{f.severity.value.upper()}[/{sev_style}]", f"{f.file_path}:{f.line or 1}", f.message)
        console.print(table)
        console.print()
        console.print("[bold red]Review failed: Fix issues before committing.[/bold red]\n")
        raise typer.Exit(code=1)
    else:
        console.print("[bold green]✓ Clean review: No static regressions detected in changed files. Ready to commit![/bold green]\n")


def verify_command(
    path: Optional[str] = typer.Argument(None, help="Target project path"),
    update_baseline: bool = typer.Option(False, "--update-baseline", "-u", help="Save current scan as new baseline."),
) -> None:
    """Compare current scan against previous baseline (.arc/baseline.json) and report trends."""
    target_path = Path(path).resolve() if path else Path.cwd()
    if not target_path.exists() or not target_path.is_dir():
        err_console.print(f"[bold red]✗ Error:[/bold red] Target path not found: {target_path}")
        raise typer.Exit(code=2)

    console.print()
    console.rule("[bold cyan]ARC CLOUD Baseline Verification & Trend[/bold cyan]")
    console.print()

    try:
        res = BaselineVerifier.verify(target_path, save_as_new_baseline=update_baseline)
    except Exception as exc:
        err_console.print(f"[bold red]✗ Verification Error:[/bold red] {exc}")
        raise typer.Exit(code=3)

    if res.get("is_initial_run"):
        console.print(f"[bold green]✓ Initial baseline created and stored in .arc/baseline.json[/bold green]")
        console.print(f"Health Score: [bold cyan]{res['health_score']:.0f}/100[/bold cyan] (Grade {res['letter_grade']})")
        console.print(f"Tracked Findings: [bold]{res['current_findings_count']}[/bold]\n")
        console.print("Run [cyan]arc verify[/cyan] in future runs to see new, fixed, and remaining findings trend.")
        return

    # Trend Summary
    delta = res["score_delta"]
    if delta > 0:
        delta_str = f"[bold green]+{delta:.1f} (IMPROVED)[/bold green]"
    elif delta < 0:
        delta_str = f"[bold red]{delta:.1f} (DEGRADED)[/bold red]"
    else:
        delta_str = "[yellow]0.0 (UNCHANGED)[/yellow]"

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold white")
    table.add_column()
    table.add_row("Previous Health Score:", f"{res['previous_score']:.0f}/100 ({res['previous_grade']})")
    table.add_row("Current Health Score:", f"{res['current_score']:.0f}/100 ({res['current_grade']})")
    table.add_row("Health Score Trend:", delta_str)
    table.add_row("Fixed Findings:", f"[bold green]-{res['fixed_count']}[/bold green]")
    table.add_row("New Findings:", f"[bold red]+{res['new_count']}[/bold red]")
    table.add_row("Remaining Findings:", f"{res['remaining_count']}")

    console.print(Panel(table, title="Verification Delta", border_style="cyan"))
    console.print()

    if res["new_findings"]:
        console.print(f"[bold red]New Findings ({res['new_count']}):[/bold red]")
        for nf in res["new_findings"]:
            console.print(f"  • [red]+[/red] [{nf.severity.value.upper()}] [yellow]{nf.rule_id}[/yellow] at {nf.file_path}:{nf.line or 1} - {nf.message}")
        console.print()

    if res["fixed_findings"]:
        console.print(f"[bold green]Resolved Findings ({res['fixed_count']}):[/bold green]")
        for ff in res["fixed_findings"]:
            console.print(f"  • [green]✓[/green] [{ff['severity'].upper()}] [yellow]{ff['rule_id']}[/yellow] at {ff['file_path']}:{ff.get('line') or 1}")
        console.print()

    if update_baseline:
        console.print("[dim]Baseline updated with latest scan results in .arc/baseline.json[/dim]\n")
