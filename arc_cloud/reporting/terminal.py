"""Rich terminal renderer for ARC CLOUD health reports."""
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from arc_cloud.core.models import FindingSeverity, HealthReport


class TerminalReporter:
    """Renders HealthReport to the terminal using rich formatting."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()

    def render(self, report: HealthReport) -> None:
        c = self.console
        p = report.project_profile
        h = report.health_score
        r = report.risk_assessment

        c.print()
        c.rule("[bold cyan]ARC CLOUD — Software Engineering Health Report[/bold cyan]")
        c.print()

        # Project Info
        if isinstance(p.languages, dict):
            langs_str = ", ".join(f"{lang} ({pct}%)" for lang, pct in p.languages.items()) if p.languages else "None detected"
        elif isinstance(p.languages, list):
            langs_str = ", ".join(f"{item.get('name', 'Unknown')} ({item.get('percentage', 0)}%)" if isinstance(item, dict) else str(item) for item in p.languages) if p.languages else "None detected"
        else:
            langs_str = "None detected"

        if isinstance(p.frameworks, list):
            fworks_str = ", ".join(f.get("name", str(f)) if isinstance(f, dict) else str(f) for f in p.frameworks) if p.frameworks else "None detected"
        elif isinstance(p.frameworks, dict):
            fworks_str = ", ".join(p.frameworks.keys()) if p.frameworks else "None detected"
        else:
            fworks_str = "None detected"
        pkg_str = ", ".join(p.package_managers) if p.package_managers else "None"

        proj_table = Table.grid(padding=(0, 2))
        proj_table.add_column(style="bold white", justify="left")
        proj_table.add_column(style="green")

        proj_table.add_row("Project:", p.name)
        proj_table.add_row("Type:", p.project_type)
        proj_table.add_row("Files:", f"{p.total_files} ({p.total_loc:,} LOC, {p.source_loc:,} source LOC)")
        proj_table.add_row("Languages:", langs_str)
        proj_table.add_row("Frameworks:", fworks_str)
        proj_table.add_row("Package Mgr:", pkg_str)
        c.print(proj_table)
        c.print()

        # Health Scores
        c.rule("[bold yellow]ENGINEERING HEALTH[/bold yellow]")
        c.print()

        health_table = Table.grid(padding=(0, 2))
        health_table.add_column(style="bold white", justify="left")
        health_table.add_column()

        # Overall Health styling
        grade_color = "green" if h.grade in ("A", "B") else ("yellow" if h.grade == "C" else "red")
        health_table.add_row("Overall Health:", f"[{grade_color} bold]{h.overall_score:.0f}/100 (Grade {h.grade})[/{grade_color} bold]")
        health_table.add_row("Code Quality:", f"{h.code_quality_score:.0f}/100" if h.code_quality_score is not None else "[dim]Not analyzed[/dim]")
        health_table.add_row("Security:", f"{h.security_score:.0f}/100" if h.security_score is not None else "[dim]Not analyzed (requires ARC Security engine)[/dim]")
        health_table.add_row("Dependencies:", f"{h.dependency_score:.0f}/100" if h.dependency_score is not None else "[dim]Not analyzed[/dim]")
        health_table.add_row("Architecture:", f"{h.architecture_score:.0f}/100" if h.architecture_score is not None else "[dim]Not analyzed[/dim]")
        health_table.add_row("Technical Debt:", f"{h.technical_debt_score:.0f}/100" if h.technical_debt_score is not None else "[dim]Not analyzed[/dim]")
        c.print(health_table)
        c.print()

        # Risk Profile
        c.rule("[bold red]RISK PROFILE[/bold red]")
        c.print()

        risk_color = "red bold" if r.level in ("CRITICAL", "HIGH") else ("yellow bold" if r.level == "MEDIUM" else "green bold")
        risk_table = Table.grid(padding=(0, 2))
        risk_table.add_column(style="bold white", justify="left")
        risk_table.add_column()

        risk_table.add_row("Risk Level:", f"[{risk_color}]{r.level}[/{risk_color}]")
        risk_table.add_row("Risk Score:", f"{r.total_risk_score} points")
        risk_table.add_row("Critical:", f"[red]{r.critical_count}[/red]" if r.critical_count else "0")
        risk_table.add_row("High:", f"[bright_red]{r.high_count}[/bright_red]" if r.high_count else "0")
        risk_table.add_row("Medium:", f"[yellow]{r.medium_count}[/yellow]" if r.medium_count else "0")
        risk_table.add_row("Low:", f"[blue]{r.low_count}[/blue]" if r.low_count else "0")
        risk_table.add_row("Info:", f"[dim]{r.info_count}[/dim]" if r.info_count else "0")
        c.print(risk_table)
        c.print()

        # Findings
        c.rule(f"[bold magenta]FINDINGS ({len(report.findings)})[/bold magenta]")
        c.print()

        if not report.findings:
            c.print("  [bold green]No issues found. Codebase health is in excellent condition![/bold green]")
            c.print()
        else:
            for f in report.findings:
                sev_style = {
                    FindingSeverity.CRITICAL: "red bold",
                    FindingSeverity.HIGH: "bright_red bold",
                    FindingSeverity.MEDIUM: "yellow bold",
                    FindingSeverity.LOW: "blue",
                    FindingSeverity.INFO: "dim",
                }.get(f.severity, "white")

                c.print(f"[{sev_style}][{f.severity.value}][/{sev_style}] [bold]{f.rule_id}: {f.title}[/bold]")
                c.print(f"  [bold]File:[/bold]   {f.file_path}:{f.line}")
                c.print(f"  [bold]Detail:[/bold] {f.description}")
                if f.recommendation:
                    c.print(f"  [bold]Fix:[/bold]    [italic]{f.recommendation}[/italic]")
                if f.code_snippet:
                    c.print("  [bold]Code:[/bold]")
                    for snip_line in f.code_snippet.splitlines():
                        c.print(f"    [dim]|[/dim] {snip_line}")
                c.print()

        # Actions
        if report.actions:
            c.rule("[bold green]ACTIONS[/bold green]")
            c.print()
            for idx, action in enumerate(report.actions, 1):
                c.print(f"  {idx}. {action}")
            c.print()

        c.rule("[dim]Scan completed[/dim]")
        c.print()
