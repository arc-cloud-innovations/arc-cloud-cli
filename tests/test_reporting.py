"""Tests for Reporting layer: JSON, SARIF, and Terminal."""
import json
import pytest

from arc_cloud.core.models import (
    Finding,
    FindingCategory,
    FindingSeverity,
    HealthReport,
    HealthScore,
    ProjectProfile,
    RiskAssessment,
)
from arc_cloud.reporting.json_reporter import JSONReporter
from arc_cloud.reporting.sarif_reporter import SARIFReporter
from arc_cloud.reporting.terminal import TerminalReporter


@pytest.fixture
def sample_report() -> HealthReport:
    profile = ProjectProfile(
        name="test_project",
        root_path="/tmp/test",
        project_type="Python Backend",
        total_files=5,
        total_loc=350,
        source_loc=300,
        test_loc=50,
        languages={"Python": 100.0},
        frameworks=["FastAPI"],
        package_managers=["pip"],
    )
    score = HealthScore(
        overall_score=85.0,
        code_quality_score=85.0,
        grade="B",
        explanation="Test explanation",
    )
    risk = RiskAssessment(
        level="HIGH",
        total_risk_score=15,
        high_count=1,
    )
    finding = Finding(
        rule_id="ARC001",
        title="Excessive Function Complexity",
        description="Complexity is 16",
        category=FindingCategory.CODE_QUALITY,
        severity=FindingSeverity.HIGH,
        file_path="service.py",
        line=42,
        end_line=50,
        col=4,
        end_col=20,
        recommendation="Refactor into smaller functions",
    )
    return HealthReport(
        project_profile=profile,
        health_score=score,
        risk_assessment=risk,
        findings=[finding],
        actions=["Refactor service.py"],
    )


def test_json_reporter(sample_report: HealthReport) -> None:
    json_str = JSONReporter.render(sample_report)
    data = json.loads(json_str)
    assert data["project_profile"]["name"] == "test_project"
    assert data["health_score"]["overall_score"] == 85.0
    assert len(data["findings"]) == 1
    assert data["findings"][0]["rule_id"] == "ARC001"


def test_sarif_reporter(sample_report: HealthReport) -> None:
    sarif_str = SARIFReporter.render(sample_report)
    sarif_doc = json.loads(sarif_str)

    assert sarif_doc["version"] == "2.1.0"
    assert "runs" in sarif_doc
    run = sarif_doc["runs"][0]
    assert run["tool"]["driver"]["name"] == "ARC CLOUD"

    # Rules
    assert len(run["tool"]["driver"]["rules"]) == 1
    assert run["tool"]["driver"]["rules"][0]["id"] == "ARC001"

    # Results
    assert len(run["results"]) == 1
    result = run["results"][0]
    assert result["ruleId"] == "ARC001"
    assert result["level"] == "error"  # HIGH maps to error
    location = result["locations"][0]["physicalLocation"]
    assert location["artifactLocation"]["uri"] == "service.py"
    assert location["region"]["startLine"] == 42


def test_terminal_reporter(sample_report: HealthReport) -> None:
    from rich.console import Console
    console = Console(record=True, width=120)
    reporter = TerminalReporter(console=console)
    reporter.render(sample_report)
    text = console.export_text()

    assert "ARC CLOUD" in text
    assert "test_project" in text
    assert "Overall Health:" in text
    assert "85/100" in text
    assert "ARC001" in text
    assert "service.py:42" in text
