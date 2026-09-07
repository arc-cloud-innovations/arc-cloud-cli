"""Tests for the standalone HTML report generator."""
from pathlib import Path
import tempfile
import pytest

from arc_cloud.core.models import HealthReport
from arc_cloud.core.orchestrator import ScanOrchestrator
from arc_cloud.reporting.html_reporter import HTMLReporter


def test_html_reporter_generates_valid_html() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "service.py").write_text("def work(): pass\n", encoding="utf-8")
        report = ScanOrchestrator().run_scan(p)

        reporter = HTMLReporter(report)
        html_text = reporter.render()

        assert "<!DOCTYPE html>" in html_text
        assert "ARC CLOUD" in html_text
        assert "HEALTH REPORT" in html_text
        assert "Engineering Health Matrix (10 Engines)" in html_text
        assert "Risk Profile Breakdown" in html_text
        assert "Technical Debt &amp; Prioritized Actions" in html_text or "Technical Debt" in html_text
        assert "filterFindings()" in html_text
        assert "@media print" in html_text

        # Test writing to file
        out_html = p / "report.html"
        reporter.write_to_file(out_html)
        assert out_html.is_file()
        assert out_html.stat().st_size > 500
