"""The 'explain' command for ARC CLOUD CLI."""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from arc_cloud.ai.explain import FindingExplainer
from arc_cloud.ai.knowledge_base import RULE_KNOWLEDGE_BASE
from arc_cloud.core.orchestrator import ScanOrchestrator
from arc_cloud.rules.registry import RuleRegistry
from arc_cloud.verification.verifier import BaselineVerifier

console = Console()
err_console = Console(stderr=True)


def explain_command(
    target: Optional[str] = typer.Argument(
        None,
        help="Finding ID (e.g. arc-f-123) or Rule ID (e.g. ARC001, ARC-SEC-002). If omitted, lists all rules.",
    ),
    list_rules: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List all available rules and descriptions.",
    ),
) -> None:
    """Explain a finding or rule with root-cause analysis, side effects, and remediation guidance."""
    registry = RuleRegistry()

    if not target or list_rules:
        # Display list of rules
        table = Table(title="ARC CLOUD Static Analysis Rules", box=None, padding=(0, 2))
        table.add_column("Rule ID", style="bold cyan", no_wrap=True)
        table.add_column("Category", style="yellow", no_wrap=True)
        table.add_column("Default Severity", style="magenta", no_wrap=True)
        table.add_column("Title", style="white")

        for r in registry.get_all():
            table.add_row(r.rule_id, r.category.value, r.default_severity.value, r.title)

        console.print()
        console.print(table)
        console.print()
        console.print("Run [bold cyan]arc explain <RULE_ID_OR_FINDING_ID>[/bold cyan] to see in-depth remediation guidance.")
        return

    target_id = target.strip()

    # 1. Registered Rule in registry
    rule = registry.get(target_id)
    if rule:
        console.print()
        console.rule(f"[bold cyan]ARC CLOUD Rule Explanation: {rule.rule_id}[/bold cyan]")
        console.print()

        meta_table = Table.grid(padding=(0, 2))
        meta_table.add_column(style="bold white")
        meta_table.add_column()
        meta_table.add_row("Title:", f"[bold]{rule.title}[/bold]")
        meta_table.add_row("Category:", f"[yellow]{rule.category.value}[/yellow]")
        meta_table.add_row("Default Severity:", f"[magenta]{rule.default_severity.value}[/magenta]")
        console.print(Panel(meta_table, title="Rule Details", border_style="cyan"))
        console.print()

        console.print("[bold cyan]Description:[/bold cyan]")
        console.print(f"  {rule.description}\n")

        if rule.why_it_matters:
            console.print("[bold yellow]Why It Matters:[/bold yellow]")
            console.print(f"  {rule.why_it_matters}\n")

        console.print("[bold green]Recommendation & Remediation:[/bold green]")
        console.print(f"  {rule.recommendation}\n")

        if rule.example_bad:
            console.print("[bold red]Anti-Pattern Example:[/bold red]")
            console.print(Syntax(rule.example_bad, "python", theme="monokai", line_numbers=True))
            console.print()

        if rule.example_good:
            console.print("[bold green]Recommended Pattern Example:[/bold green]")
            console.print(Syntax(rule.example_good, "python", theme="monokai", line_numbers=True))
            console.print()
        return

    # 2. Rule in Knowledge Base
    if target_id in RULE_KNOWLEDGE_BASE:
        explanation = FindingExplainer.explain_rule(target_id)
        _render_explanation(explanation)
        return

    # 3. Otherwise, treat target as a Finding ID: search current repository scan and baseline
    found_finding = None
    baseline = BaselineVerifier.load_baseline(Path.cwd())
    if baseline:
        for f_data in baseline.get("findings", []):
            if f_data.get("id") == target_id:
                from arc_cloud.core.models import Finding, FindingSeverity
                found_finding = Finding(
                    id=f_data["id"],
                    rule_id=f_data["rule_id"],
                    file_path=Path(f_data["file_path"]),
                    line=f_data.get("line"),
                    message=f_data["message"],
                    severity=FindingSeverity(f_data["severity"]),
                    engine=f_data.get("engine", "code_quality"),
                )
                break

    if not found_finding:
        try:
            report = ScanOrchestrator().run_scan(Path.cwd())
            for f in report.findings:
                if f.id == target_id:
                    found_finding = f
                    break
        except Exception:
            pass

    if found_finding:
        explanation = FindingExplainer.explain_rule(found_finding.rule_id, finding=found_finding)
        _render_explanation(explanation)
        return

    # Partial match fallback
    for rid in RULE_KNOWLEDGE_BASE:
        if target_id.lower() in rid.lower():
            explanation = FindingExplainer.explain_rule(rid)
            _render_explanation(explanation)
            return

    err_console.print(f"[bold red]✗ Error:[/bold red] Unknown rule ID '{target_id}'.")
    err_console.print("Tip: Run [cyan]arc explain --list[/cyan] to view all supported rules.")
    raise typer.Exit(code=2)


def _render_explanation(exp: dict) -> None:
    """Renders comprehensive explanation matching Section 13 specification."""
    console.print()
    title_str = exp.get("title", exp.get("rule_id", "ARC Rule"))
    console.rule(f"[bold cyan]ARC CLOUD Explanation: {title_str}[/bold cyan]")
    console.print()

    # Meta panel
    meta_table = Table.grid(padding=(0, 2))
    meta_table.add_column(style="bold white")
    meta_table.add_column()
    meta_table.add_row("Rule ID:", f"[cyan]{exp.get('rule_id')}[/cyan]")
    meta_table.add_row("Engine:", f"[yellow]{exp.get('engine', 'code_quality').capitalize()}[/yellow]")
    if exp.get("finding_id"):
        meta_table.add_row("Finding ID:", f"[bold magenta]{exp['finding_id']}[/bold magenta]")
        meta_table.add_row("Location:", f"{exp.get('file_path')}:{exp.get('line') or 1}")
    meta_table.add_row("Provider:", f"[green]{exp.get('provider')}[/green]")
    console.print(Panel(meta_table, title="Diagnostic Overview", border_style="cyan"))
    console.print()

    # Root cause
    console.print("[bold cyan]1. Root Cause Explanation:[/bold cyan]")
    console.print(f"   {exp.get('root_cause')}\n")

    # Why it is a problem / Why it matters
    console.print("[bold yellow]2. Why It Matters:[/bold yellow]")
    console.print(f"   {exp.get('impact')}\n")

    # Risk if not fixed
    console.print("[bold red]3. What Happens If Not Fixed:[/bold red]")
    console.print(f"   {exp.get('risk_if_not_fixed')}\n")

    # Step-by-step remediation guide
    console.print("[bold green]4. Step-by-Step Remediation Guide:[/bold green]")
    for step in exp.get("remediation_steps", []):
        console.print(f"   • {step}")
    console.print()

    # Code before / after
    if exp.get("code_before"):
        console.print("[bold red]Code Before (Issue):[/bold red]")
        console.print(Syntax(exp["code_before"], "python", theme="monokai", line_numbers=True))
        console.print()

    if exp.get("code_after"):
        console.print("[bold green]Code After (Remediation):[/bold green]")
        console.print(Syntax(exp["code_after"], "python", theme="monokai", line_numbers=True))
        console.print()

    # Potential side effects
    if exp.get("side_effects"):
        console.print("[bold magenta]5. Potential Side Effects of Fix:[/bold magenta]")
        console.print(f"   {exp.get('side_effects')}\n")

    # Suggested test
    if exp.get("suggested_test"):
        console.print("[bold blue]6. Suggested Test to Verify Fix:[/bold blue]")
        console.print(f"   {exp.get('suggested_test')}\n")
