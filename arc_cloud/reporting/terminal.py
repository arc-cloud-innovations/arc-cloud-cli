"""Rich terminal renderer for ARC CLOUD Software Engineering Health Platform."""
from typing import Optional
from rich.console import Console
from rich.table import Table

from arc_cloud.core.models import FindingSeverity, HealthReport


class TerminalReporter:
    """Renders HealthReport to the terminal matching ARC CLOUD platform design."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()

    def render(self, report: HealthReport) -> None:
        c = self.console
        p = report.project_profile
        h = report.health_score
        r = report.risk_assessment

        c.print()
        c.rule("[bold cyan]ARC CLOUD — SOFTWARE ENGINEERING HEALTH[/bold cyan]")
        c.print()

        # 1. PROJECT
        c.print("[bold white]PROJECT[/bold white]")
        c.print(f"Name:  [bold cyan]{p.name}[/bold cyan]")
        c.print(f"Type:  [green]{p.project_type}[/green]")
        c.print(f"Files: {p.total_files:,} ({p.total_loc:,} LOC, {p.source_loc:,} source LOC)")
        c.print()

        c.print("[bold white]Languages:[/bold white]")
        if isinstance(p.languages, dict):
            for lang, pct in p.languages.items():
                c.print(f"  {lang:<16} {pct:>5.1f}%")
        elif isinstance(p.languages, list):
            for item in p.languages:
                if isinstance(item, dict):
                    name = item.get("name", "Unknown")
                    pct = item.get("percentage", 0.0)
                    c.print(f"  {name:<16} {pct:>5.1f}%")
        else:
            c.print("  [dim]None detected[/dim]")
        c.print()

        # 2. ENGINEERING HEALTH
        c.rule("[bold yellow]ENGINEERING HEALTH[/bold yellow]")
        c.print()

        grade_color = "green bold" if h.grade in ("A", "B") else ("yellow bold" if h.grade == "C" else "red bold")
        c.print(f"Overall Health:       [{grade_color}]{h.overall_score:.0f}/100 (Grade {h.grade})[/{grade_color}]")
        c.print()

        # 10 Engine breakdown table
        engines_display = [
            ("Code Quality", h.code_quality),
            ("Reliability", h.reliability),
            ("Security", h.security),
            ("Dependencies", h.dependencies),
            ("Secrets", h.secrets),
            ("Architecture", h.architecture),
            ("Technical Debt", h.technical_debt),
            ("Testing", h.testing),
            ("Performance", h.performance),
        ]

        table = Table.grid(padding=(0, 3))
        table.add_column(style="bold white", width=22)
        table.add_column()

        for label, val in engines_display:
            if val is not None:
                clr = "green" if val >= 80 else ("yellow" if val >= 65 else "red")
                table.add_row(label, f"[{clr}]{val}[/{clr}]")
            else:
                table.add_row(label, "[dim]NOT ANALYZED[/dim]")

        # AI Code Risk
        if h.ai_risk:
            ai_clr = "red bold" if h.ai_risk == "HIGH" else ("yellow" if h.ai_risk == "MEDIUM" else "green")
            table.add_row("AI Code Risk", f"[{ai_clr}]{h.ai_risk}[/{ai_clr}]")

        c.print(table)
        c.print()
        c.print(f"[dim]Analysis Coverage:[/dim] [bold cyan]{h.analysis_coverage}[/bold cyan]")
        c.print()

        # 3. RISK PROFILE
        c.rule("[bold red]RISK PROFILE[/bold red]")
        c.print()

        risk_color = "red bold" if r.level in ("CRITICAL", "HIGH") else ("yellow bold" if r.level == "MEDIUM" else "green bold")
        c.print(f"Risk Level:  [{risk_color}]{r.level}[/{risk_color}]")
        c.print(f"Risk Score:  {r.total_risk_score} points")
        c.print(f"Critical:    [red]{r.critical_count}[/red]")
        c.print(f"High:        [bright_red]{r.high_count}[/bright_red]")
        c.print(f"Medium:      [yellow]{r.medium_count}[/yellow]")
        c.print(f"Low:         [blue]{r.low_count}[/blue]")
        c.print(f"Info:        [dim]{r.info_count}[/dim]")
        c.print()

        # 4. TOP FINDINGS
        if report.findings:
            c.rule(f"[bold magenta]TOP FINDINGS ({len(report.findings)})[/bold magenta]")
            c.print()
            # Show up to top 7 findings
            for f in report.findings[:7]:
                sev_style = {
                    FindingSeverity.CRITICAL: "red bold",
                    FindingSeverity.HIGH: "bright_red bold",
                    FindingSeverity.MEDIUM: "yellow bold",
                    FindingSeverity.LOW: "blue",
                    FindingSeverity.INFO: "dim",
                }.get(f.severity, "white")

                c.print(f"[{sev_style}][{f.severity.value}] {f.rule_id}:[/{sev_style}] [bold]{f.title}[/bold]")
                c.print(f"  File:   {f.file_path}:{f.line}")
                c.print(f"  Detail: {f.description}")
                if f.recommendation:
                    c.print(f"  Fix:    [italic]{f.recommendation}[/italic]")
                c.print()

        # 5. RECOMMENDED ACTIONS
        if report.actions:
            c.rule("[bold green]RECOMMENDED ACTIONS[/bold green]")
            c.print()
            for idx, action in enumerate(report.actions, 1):
                c.print(f"  {idx}. {action}")
            c.print()

        c.rule("[dim]ARC CLOUD: SCAN → UNDERSTAND → PRIORITIZE → FIX → VERIFY[/dim]")
        c.print()
