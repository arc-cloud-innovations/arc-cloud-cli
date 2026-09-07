"""Live interactive terminal UI and event stream renderer for ARC START."""
from __future__ import annotations

from datetime import datetime
import json
import sys
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from arc_cloud.core.models import Finding, FindingSeverity, HealthReport
from arc_cloud.monitoring.event_bus import EventType, LiveEvent
from arc_cloud.monitoring.session import MonitoringSession
from arc_cloud.verification.health_delta import HealthDelta
from arc_cloud.verification.verifier import VerificationResult


class LiveTerminalReporter:
    """Renders real-time monitoring events, problem alerts, and status panels."""

    def __init__(self, console: Optional[Console] = None, json_mode: bool = False) -> None:
        self.console = console or Console()
        self.json_mode = json_mode
        self._recent_events: List[LiveEvent] = []

    def handle_event(self, event: LiveEvent) -> None:
        self._recent_events.append(event)
        if len(self._recent_events) > 12:
            self._recent_events.pop(0)

        if self.json_mode:
            sys.stdout.write(json.dumps(event.to_dict()) + "\n")
            sys.stdout.flush()
            return

        # Terminal specific alerts for critical events
        if event.event_type == EventType.FILE_MODIFIED or event.event_type == EventType.FILE_CREATED:
            fname = event.data.get("path", "")
            self.console.print(f"\n[bold yellow]⚠️  CODE CHANGE DETECTED[/bold yellow]")
            self.console.print(f"  [cyan]File:[/cyan]   {fname}")
            self.console.print(f"  [cyan]Change:[/cyan] {event.event_type.value}")
            self.console.print(f"  [cyan]Source:[/cyan] External editor / development tool")
            self.console.print("  [dim]ARC CLOUD is analyzing the change...[/dim]")

        elif event.event_type == EventType.DEPENDENCY_CHANGED:
            fname = event.data.get("file", "")
            self.console.print(f"\n[bold yellow]⚠️  DEPENDENCY CHANGE DETECTED[/bold yellow]")
            self.console.print(f"  [cyan]File:[/cyan] {fname}")
            self.console.print("  [dim]ARC CLOUD is checking: Compatibility, Dependency risk, Vulnerabilities...[/dim]")

        elif event.event_type == EventType.SECURITY_RISK_DETECTED:
            rule_id = event.data.get("rule_id", "ARC-SEC")
            fpath = event.data.get("file_path", "")
            self.console.print(f"\n[bold red]🚨 SECURITY RISK DETECTED[/bold red]")
            self.console.print(f"  [cyan]Rule:[/cyan]     {rule_id}")
            self.console.print(f"  [cyan]File:[/cyan]     {fpath}")
            self.console.print(f"  [cyan]Problem:[/cyan]  {event.message}")
            self.console.print(f"  [cyan]Severity:[/cyan] [bold red]CRITICAL[/bold red]")
            self.console.print("  [yellow]ARC CLOUD has NOT verified this change.[/yellow]")

        elif event.event_type == EventType.VERIFICATION_INVALIDATED:
            reason = event.data.get("reason", "Code changed after verification.")
            self.console.print(f"\n[bold yellow]⚠️  VERIFICATION INVALIDATED[/bold yellow]")
            self.console.print(f"  [cyan]Reason:[/cyan]         {reason}")
            self.console.print(f"  [cyan]Current status:[/cyan] [bold red]UNVERIFIED[/bold red]")
            self.console.print("  [dim]ARC CLOUD is analyzing the new state...[/dim]")

    def render_live_dashboard(
        self,
        session: MonitoringSession,
        current_report: Optional[HealthReport] = None,
        verification_status: str = "MONITORING",
    ) -> None:
        if self.json_mode:
            return

        framework_str = "Standard"
        if current_report and current_report.project_profile.frameworks:
            fw_names = []
            for fw in current_report.project_profile.frameworks[:2]:
                if isinstance(fw, dict):
                    fw_names.append(str(fw.get("name", "Unknown")))
                else:
                    fw_names.append(str(fw))
            if fw_names:
                framework_str = ", ".join(fw_names)

        status_color = "green" if "VERIFIED" in verification_status else "yellow"
        if "FAILED" in verification_status or "FAIL" in verification_status:
            status_color = "red"

        # Construct Header & Overview table
        table = Table.grid(padding=(0, 2))
        table.add_column("Key", style="cyan bold")
        table.add_column("Val", style="bold")

        table.add_row("Project", session.project_name)
        table.add_row("Framework", framework_str)
        table.add_row("Health", f"{session.current_health:.0f}/100")
        table.add_row("Status", f"[{status_color}]● {verification_status}[/{status_color}]")

        # Event stream lines
        event_lines: List[str] = []
        for ev in self._recent_events[-6:]:
            t_str = ev.timestamp.strftime("%H:%M:%S")
            icon = "✓" if "PASSED" in ev.event_type.value or "COMPLETED" in ev.event_type.value else "ℹ"
            if "FAIL" in ev.event_type.value or "SECURITY" in ev.event_type.value:
                icon = "🚨"
            elif "CHANGE" in ev.event_type.value or "MODIFIED" in ev.event_type.value or "CREATED" in ev.event_type.value:
                icon = "⚠️ "
            event_lines.append(f"[dim]{t_str}[/dim] {icon} {ev.message or ev.event_type.value}")

        events_content = "\n".join(event_lines) if event_lines else "[dim]No events yet... waiting for file changes.[/dim]"

        panel_content = Text()
        panel_content.append("ARC CLOUD LIVE ENGINEERING MONITOR\n", style="bold white on blue")
        panel_content.append(f"Health: {session.start_health:.0f} → {session.current_health:.0f} (Delta: {session.health_delta:+.1f})\n\n", style="bold")
        panel_content.append("Recent Live Events:\n", style="bold underline")
        panel_content.append(Text.from_markup(events_content))

        self.console.print(
            Panel(
                panel_content,
                title="[bold green]● LIVE MONITOR[/bold green]",
                subtitle="[dim]\\[q]uit \\[r]escan \\[v]erify \\[t]est \\[s]tatus \\[h]ealth \\[c]lear[/dim]",
                border_style="blue",
            )
        )

    def render_problems_alert(self, findings: List[Finding]) -> None:
        if self.json_mode or not findings:
            return

        crit = sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL)
        high = sum(1 for f in findings if f.severity == FindingSeverity.HIGH)
        med = sum(1 for f in findings if f.severity == FindingSeverity.MEDIUM)
        low = sum(1 for f in findings if f.severity == FindingSeverity.LOW)

        self.console.print(f"\n[bold yellow]⚠️  {len(findings)} PROBLEM(S) DETECTED[/bold yellow]")
        if crit:
            self.console.print(f"  [bold red]🔴 {crit} CRITICAL[/bold red]")
        if high:
            self.console.print(f"  [bold red]🔴 {high} HIGH[/bold red]")
        if med:
            self.console.print(f"  [bold orange3]🟠 {med} MEDIUM[/bold orange3]")
        if low:
            self.console.print(f"  [bold yellow]🟡 {low} LOW[/bold yellow]")

        # Show top 2 findings
        for f in findings[:2]:
            self.console.print(f"\n  [bold cyan]Problem:[/bold cyan] {f.message}")
            self.console.print(f"  [dim]File: {f.file_path}:{f.line or 1} | Rule: {f.rule_id} | Risk: {f.severity.value}[/dim]")
            if getattr(f, "recommendation", None):
                self.console.print(f"  [green]Recommendation:[/green] {f.recommendation}")

        self.console.print("  [dim]Status: [bold red]❌ NOT VERIFIED[/bold red][/dim]")
        self.console.print("  [dim]Run: [bold]arc review[/bold] or [bold]arc fix <id>[/bold] for remediation.[/dim]")

    def render_verification_banner(self, result: VerificationResult) -> None:
        if self.json_mode:
            return

        if result.is_verified:
            content = (
                f"[bold green]✓ ARC CLOUD CHANGE VERIFIED[/bold green]\n\n"
                f"Tests:           [green]✓ PASS[/green]\n"
                f"Security:        [green]✓ PASS[/green]\n"
                f"Architecture:    [green]✓ PASS[/green]\n"
                f"Regressions:     [green]✓ NONE[/green]\n"
                f"Health:          {result.health_before:.0f} → {result.health_after:.0f} ({result.health_delta:+.1f})\n\n"
                f"Status:          [bold green]VERIFIED ✓[/bold green]"
            )
            self.console.print(Panel(content, border_style="green"))
        else:
            reasons_str = "\n".join(f"• {r}" for r in result.reasons) if result.reasons else "• Unresolved findings or test failure."
            content = (
                f"[bold red]❌ ARC CLOUD VERIFICATION FAILED[/bold red]\n\n"
                f"Status:          [bold red]NOT VERIFIED[/bold red]\n"
                f"Tests:           [{'green' if result.tests_status == 'PASS' else 'red'}]{result.tests_status}[/]\n"
                f"Security:        [{'green' if result.security_status == 'PASS' else 'red'}]{result.security_status}[/]\n"
                f"Regressions:     [bold red]{result.regressions_count} detected[/bold red]\n"
                f"Health:          {result.health_before:.0f} → {result.health_after:.0f} ({result.health_delta:+.1f})\n\n"
                f"Failure Details:\n{reasons_str}"
            )
            self.console.print(Panel(content, border_style="red"))

    def render_session_report(self, session: MonitoringSession) -> None:
        if self.json_mode:
            sys.stdout.write(json.dumps(session.to_dict(), indent=2) + "\n")
            return

        t = Table(title="ARC CLOUD SESSION REPORT", show_header=False, border_style="cyan")
        t.add_column("Metric", style="cyan bold")
        t.add_column("Value", style="bold")

        t.add_row("Project", session.project_name)
        t.add_row("Session Duration", f"{session.duration_seconds}s")
        t.add_row("Files Monitored", str(session.files_monitored))
        t.add_row("Changes Detected", str(session.changes_detected))
        t.add_row("Scans Executed", str(session.scans_run))
        t.add_row("Tests Executed", str(session.tests_run))
        t.add_row("Successful Changes", str(session.successful_changes))
        t.add_row("Failed Changes", str(session.failed_changes))
        t.add_row("Security Alerts", str(session.security_alerts))
        t.add_row("Regressions", str(session.regressions))
        t.add_row("Start Health", f"{session.start_health:.0f}")
        t.add_row("Current Health", f"{session.current_health:.0f}")
        t.add_row("Health Delta", f"{session.health_delta:+.1f}")
        t.add_row("Final Status", session.verification_status)

        self.console.print("\n")
        self.console.print(Panel(t, border_style="cyan"))
