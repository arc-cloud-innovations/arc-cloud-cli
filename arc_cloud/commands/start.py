"""ARC START Live Engineering Monitor CLI Command."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import select
import sys
import termios
import time
import tty
from typing import Optional

from rich.console import Console
import typer

from arc_cloud.changes.models import ChangeSet, FileChange
from arc_cloud.core.models import FindingSeverity, HealthReport
from arc_cloud.core.orchestrator import ScanOrchestrator
from arc_cloud.monitoring.change_detector import ChangeDetector
from arc_cloud.monitoring.event_bus import EventBus, EventType, LiveEvent
from arc_cloud.monitoring.session import MonitoringSession
from arc_cloud.monitoring.watcher import FileWatcher
from arc_cloud.project.detector import ProjectDetector
from arc_cloud.project.profile import ProjectProfileBuilder
from arc_cloud.reporting.live_terminal import LiveTerminalReporter
from arc_cloud.testing.runner import TestResult, TestRunner
from arc_cloud.verification.snapshot import SnapshotManager
from arc_cloud.verification.verifier import VerificationEngine, VerificationResult

app = typer.Typer(help="Live engineering health monitoring mode.")
console = Console()


def start_command(
    path: Optional[str] = typer.Argument(None, help="Target project path to monitor (defaults to current directory)"),
    watch: bool = typer.Option(True, "--watch/--no-watch", help="Continuously monitor filesystem for changes"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose event telemetry"),
    no_tests: bool = typer.Option(False, "--no-tests", help="Disable automated test execution on change"),
    format: str = typer.Option("terminal", "--format", "-f", help="Output format (terminal or json)"),
    auto_verify: bool = typer.Option(False, "--auto-verify", help="Automatically accept changes if tests and checks pass"),
) -> None:
    """Start live engineering monitoring on a project."""
    target_path = Path(path).resolve() if path else Path.cwd()
    if not target_path.exists():
        console.print(f"[bold red]Error:[/bold red] Path does not exist: {target_path}")
        raise typer.Exit(code=1)

    json_mode = format.lower() == "json"
    event_bus = EventBus()
    reporter = LiveTerminalReporter(console=console, json_mode=json_mode)
    event_bus.subscribe_all(reporter.handle_event)

    # 1. Initialize Event Bus and Scanner
    event_bus.emit(EventType.PROJECT_STARTED, message=f"Starting monitor for {target_path.name}")
    orchestrator = ScanOrchestrator()
    initial_report = orchestrator.run_scan(target_path)
    initial_score = initial_report.health_score.overall_score
    profile = initial_report.project_profile

    # 2. Store Baseline Snapshot
    SnapshotManager.create_snapshot(target_path, initial_report)
    event_bus.emit(EventType.INITIAL_SCAN_COMPLETED, message=f"Initial scan complete. Health: {initial_score:.0f}/100")

    # 4. Initialize Subsystems
    session = MonitoringSession(
        project_name=profile.name,
        files_monitored=initial_report.project_profile.total_files or len(initial_report.findings),
        start_health=initial_score,
        current_health=initial_score,
    )
    change_detector = ChangeDetector(target_path, event_bus)
    test_runner = TestRunner(target_path)
    verifier = VerificationEngine(target_path, event_bus)

    last_report: HealthReport = initial_report
    prev_findings_dict = [
        {"rule_id": f.rule_id, "file_path": str(f.file_path), "line": f.line, "severity": f.severity.value}
        for f in initial_report.findings
    ]

    # Initial UI
    reporter.render_live_dashboard(session, initial_report, verification_status="MONITORING")

    if not watch:
        # One-shot run
        reporter.render_session_report(session)
        return

    # Change Handler Callback
    def on_file_changes(raw_changes: list[FileChange]) -> None:
        nonlocal last_report, prev_findings_dict
        if not raw_changes:
            return

        session.changes_detected += len(raw_changes)
        verifier.invalidate("File changed in project.")
        session.verification_status = "UNVERIFIED"

        change_set: ChangeSet = change_detector.process_changes(raw_changes)

        # Rescan
        event_bus.emit(EventType.SCAN_STARTED, message="Running targeted rescan...")
        session.scans_run += 1
        curr_report = orchestrator.run_scan(target_path)
        session.current_health = curr_report.health_score.overall_score

        # Check for immediate security alerts
        sec_findings = [f for f in curr_report.findings if "SEC" in f.rule_id or f.severity == FindingSeverity.CRITICAL]
        for sf in sec_findings:
            session.security_alerts += 1
            event_bus.emit(
                EventType.SECURITY_RISK_DETECTED,
                message=sf.message,
                data={"rule_id": sf.rule_id, "file_path": str(sf.file_path)},
            )

        # Run automated tests unless --no-tests
        test_passed = True
        test_errors: list[str] = []
        if not no_tests:
            event_bus.emit(EventType.TEST_STARTED, message="Running automated tests...")
            session.tests_run += 1
            test_res: TestResult = test_runner.run_tests(change_set.affected_tests if change_set.affected_tests else None)
            test_passed = test_res.success
            test_errors = test_res.errors
            event_bus.emit(
                EventType.TEST_COMPLETED,
                message=f"Tests {'PASSED' if test_passed else 'FAILED'}: {test_res.passed} passed, {test_res.failed} failed",
                data={"passed": test_res.passed, "failed": test_res.failed, "success": test_passed},
            )

        # Verification check
        ver_res: VerificationResult = verifier.verify_state(
            current_report=curr_report,
            previous_findings=prev_findings_dict,
            previous_score=last_report.health_score.overall_score,
            test_passed=test_passed,
            test_errors=test_errors,
        )

        if ver_res.is_verified:
            session.successful_changes += 1
            session.verification_status = "VERIFIED"
            # Update baseline
            prev_findings_dict = [
                {"rule_id": f.rule_id, "file_path": str(f.file_path), "line": f.line, "severity": f.severity.value}
                for f in curr_report.findings
            ]
        else:
            session.failed_changes += 1
            session.verification_status = "NOT VERIFIED"
            if ver_res.regressions_count > 0:
                session.regressions += ver_res.regressions_count
                event_bus.emit(EventType.REGRESSION_DETECTED, message=f"{ver_res.regressions_count} regression(s) detected.")

        last_report = curr_report

        # Render alerts and verification
        if curr_report.findings:
            reporter.render_problems_alert(curr_report.findings)
        reporter.render_verification_banner(ver_res)
        reporter.render_live_dashboard(session, curr_report, verification_status=session.verification_status)

    watcher = FileWatcher(root_dir=target_path, on_changes=on_file_changes, debounce_seconds=0.5)
    watcher.start()

    # Terminal Input Loop (supports hotkeys q, r, v, t, s, h, c)
    is_tty = sys.stdin.isatty()
    old_settings = None
    if is_tty:
        try:
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        except Exception:
            is_tty = False

    try:
        while True:
            if is_tty:
                rlist, _, _ = select.select([sys.stdin], [], [], 0.5)
                if rlist:
                    char = sys.stdin.read(1).lower()
                    if char == "q":
                        break
                    elif char == "r":
                        console.print("\n[cyan]🔄 Manual rescan triggered...[/cyan]")
                        last_report = orchestrator.run_scan(target_path)
                        session.scans_run += 1
                        session.current_health = last_report.health_score.overall_score
                        reporter.render_live_dashboard(session, last_report, verification_status=session.verification_status)
                    elif char == "t":
                        console.print("\n[cyan]🧪 Running automated tests...[/cyan]")
                        session.tests_run += 1
                        res = test_runner.run_tests()
                        console.print(f"Tests: {res.passed} passed, {res.failed} failed. Success: {res.success}")
                    elif char == "v":
                        console.print("\n[cyan]🔍 Running manual verification...[/cyan]")
                        ver = verifier.verify_state(last_report, prev_findings_dict, session.start_health)
                        reporter.render_verification_banner(ver)
                    elif char == "s":
                        reporter.render_live_dashboard(session, last_report, verification_status=session.verification_status)
                    elif char == "c":
                        console.clear()
                        reporter.render_live_dashboard(session, last_report, verification_status=session.verification_status)
            else:
                time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        if is_tty and old_settings:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            except Exception:
                pass
        watcher.stop()
        session.close()
        reporter.render_session_report(session)
