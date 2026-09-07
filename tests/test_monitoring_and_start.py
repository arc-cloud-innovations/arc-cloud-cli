"""Tests for live monitoring subsystem, event bus, watcher, runner, and start command."""
from __future__ import annotations

import json
from pathlib import Path
import time

from typer.testing import CliRunner

from arc_cloud.changes.diff import ChangeDiffer
from arc_cloud.changes.impact import ImpactAnalyzer
from arc_cloud.changes.models import ChangeType, FileChange
from arc_cloud.main import app
from arc_cloud.monitoring.change_detector import ChangeDetector
from arc_cloud.monitoring.event_bus import EventBus, EventType, LiveEvent
from arc_cloud.monitoring.session import MonitoringSession
from arc_cloud.monitoring.watcher import FileWatcher
from arc_cloud.reporting.live_terminal import LiveTerminalReporter
from arc_cloud.testing.runner import TestResult, TestRunner
from arc_cloud.verification.health_delta import HealthDeltaCalculator
from arc_cloud.verification.regression import RegressionDetector
from arc_cloud.verification.snapshot import SnapshotManager
from arc_cloud.verification.verifier import VerificationEngine

runner = CliRunner()


def test_event_bus_pub_sub() -> None:
    bus = EventBus()
    received: list[LiveEvent] = []

    bus.subscribe(EventType.FILE_MODIFIED, lambda ev: received.append(ev))
    bus.emit(EventType.FILE_MODIFIED, message="file edited", data={"file": "foo.py"})
    bus.emit(EventType.FILE_CREATED, message="file added")

    assert len(received) == 1
    assert received[0].message == "file edited"
    assert len(bus.history) == 2


def test_diff_and_changed_lines() -> None:
    old_c = "def hello():\n    return 1\n"
    new_c = "def hello():\n    # greeting\n    return 42\n"

    diff = ChangeDiffer.get_unified_diff(old_c, new_c, "test.py")
    lines = ChangeDiffer.extract_changed_line_numbers(old_c, new_c)

    assert "greeting" in diff
    assert len(lines) > 0


def test_impact_analyzer(tmp_path: Path) -> None:
    src_file = tmp_path / "services" / "auth_service.dart"
    src_file.parent.mkdir(parents=True, exist_ok=True)
    src_file.write_text("class AuthService {}", encoding="utf-8")

    test_file = tmp_path / "test" / "auth_service_test.dart"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("void main() {}", encoding="utf-8")

    scope = ImpactAnalyzer.analyze_file(tmp_path, src_file)
    assert test_file in scope.affected_tests
    assert not scope.is_dependency_manifest

    manifest = tmp_path / "pubspec.yaml"
    manifest.write_text("name: my_app", encoding="utf-8")
    m_scope = ImpactAnalyzer.analyze_file(tmp_path, manifest)
    assert m_scope.is_dependency_manifest


def test_change_detector_and_rename(tmp_path: Path) -> None:
    bus = EventBus()
    detector = ChangeDetector(tmp_path, bus)

    f1 = tmp_path / "old.py"
    f2 = tmp_path / "new.py"
    f2.write_text("print('hello')", encoding="utf-8")

    raw = [
        FileChange(path=f1, change_type=ChangeType.DELETED, old_hash="abc123hash"),
        FileChange(path=f2, change_type=ChangeType.ADDED, new_hash="abc123hash"),
    ]

    cs = detector.process_changes(raw)
    assert len(cs.files_renamed) == 1
    assert cs.files_renamed[0] == (f1, f2)


def test_file_watcher_debouncing(tmp_path: Path) -> None:
    events_received: list[list[FileChange]] = []

    def on_chg(batch: list[FileChange]) -> None:
        events_received.append(batch)

    watcher = FileWatcher(root_dir=tmp_path, on_changes=on_chg, debounce_seconds=0.15, poll_interval=0.05)
    watcher.start()

    test_file = tmp_path / "live.py"
    test_file.write_text("a = 1\n", encoding="utf-8")

    # Wait for debounce
    time.sleep(0.4)
    watcher.stop()

    assert len(events_received) >= 1
    paths = [c.path for batch in events_received for c in batch]
    assert test_file in paths


def test_test_runner_detection_and_parsing(tmp_path: Path) -> None:
    runner_tool = TestRunner(tmp_path)
    assert runner_tool.detect_framework() is None

    # Simulate Python project
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    detected = runner_tool.detect_framework()
    assert detected in ("pytest", "unittest")

    # Output parser
    p, f, errs = runner_tool._parse_output("pytest", "12 passed, 2 failed in 0.4s", returncode=1)
    assert p == 12
    assert f == 2

    p2, f2, _ = runner_tool._parse_output("flutter", "00:03 +45 -1: Some tests failed", returncode=1)
    assert p2 == 45
    assert f2 == 1


def test_snapshot_creation_and_loading(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    from arc_cloud.core.orchestrator import ScanOrchestrator

    report = ScanOrchestrator().run_scan(tmp_path)
    snapshot = SnapshotManager.create_snapshot(tmp_path, report)

    assert snapshot.total_files >= 1
    assert "main.py" in snapshot.file_hashes

    loaded = SnapshotManager.load_latest_snapshot(tmp_path)
    assert loaded is not None
    assert loaded.snapshot_id == snapshot.snapshot_id


def test_verification_engine_and_invalidation(tmp_path: Path) -> None:
    file_p = tmp_path / "app.py"
    file_p.write_text("def run():\n    return True\n", encoding="utf-8")

    from arc_cloud.core.orchestrator import ScanOrchestrator

    report = ScanOrchestrator().run_scan(tmp_path)
    bus = EventBus()
    verifier = VerificationEngine(tmp_path, bus)

    # Initial verification passes
    result = verifier.verify_state(
        current_report=report,
        previous_findings=[],
        previous_score=100.0,
        test_passed=True,
    )
    assert result.is_verified
    assert verifier.check_validity() is True

    # Mutate file -> validity check should fail and invalidate verification!
    file_p.write_text("def run():\n    return False # mutated\n", encoding="utf-8")
    is_valid = verifier.check_validity()
    assert is_valid is False
    assert verifier.last_verification.status == "NOT_VERIFIED"


def test_live_terminal_reporter_output() -> None:
    reporter = LiveTerminalReporter(json_mode=True)
    ev = LiveEvent(event_type=EventType.SCAN_COMPLETED, message="Scan done")
    # Should not raise exception
    reporter.handle_event(ev)

    session = MonitoringSession(project_name="test_proj")
    reporter.render_session_report(session)


def test_cli_start_no_watch(tmp_path: Path) -> None:
    (tmp_path / "index.py").write_text("x = 10\n", encoding="utf-8")
    res = runner.invoke(app, ["start", str(tmp_path), "--no-watch"])
    assert res.exit_code == 0
    assert "ARC CLOUD" in res.stdout
    assert "LIVE MONITOR" in res.stdout or "SESSION REPORT" in res.stdout
