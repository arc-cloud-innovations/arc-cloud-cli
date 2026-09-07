"""Tests for RiskEngine and HealthEngine scoring."""
import pytest

from arc_cloud.core.models import (
    Finding,
    FindingCategory,
    FindingSeverity,
    ProjectProfile,
)
from arc_cloud.scoring.health import HealthEngine
from arc_cloud.scoring.risk import RiskEngine


def test_risk_engine_empty_findings() -> None:
    assessment = RiskEngine.assess([])
    assert assessment.total_risk_score == 0
    assert assessment.level == "NONE"
    assert assessment.critical_count == 0


def test_risk_engine_weights_and_levels() -> None:
    findings = [
        Finding(
            rule_id="ARC001",
            title="Complexity",
            description="High complexity",
            category=FindingCategory.CODE_QUALITY,
            severity=FindingSeverity.HIGH,
            file_path="foo.py",
            line=10,
        ),
        Finding(
            rule_id="ARC001",
            title="Complexity",
            description="Medium complexity",
            category=FindingCategory.CODE_QUALITY,
            severity=FindingSeverity.MEDIUM,
            file_path="bar.py",
            line=20,
        ),
    ]

    assessment = RiskEngine.assess(findings)
    # High: 5, Medium: 2 -> Total = 7
    assert assessment.total_risk_score == 7
    assert assessment.high_count == 1
    assert assessment.medium_count == 1
    assert assessment.level == "MEDIUM"


def test_health_engine_calculation() -> None:
    # 0 findings -> 100/100 Grade A
    empty_health = HealthEngine.calculate([])
    assert empty_health.overall_score == 100.0
    assert empty_health.grade == "A"
    assert empty_health.code_quality_score == 100.0
    assert empty_health.security_score is None  # explicitly unanalyzed
    assert empty_health.dependency_score is None

    # Finding with HIGH severity (-10 pts deduction)
    findings = [
        Finding(
            rule_id="ARC001",
            title="Complexity",
            description="High complexity",
            category=FindingCategory.CODE_QUALITY,
            severity=FindingSeverity.HIGH,
            file_path="foo.py",
            line=10,
        )
    ]
    health = HealthEngine.calculate(findings)
    assert health.overall_score == 90.0
    assert health.grade == "A"
    assert health.code_quality_score == 90.0
    assert "Code Quality (90.0/100" in health.explanation
