"""Health delta calculator between scan states."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from arc_cloud.core.models import FindingSeverity, HealthReport


@dataclass
class HealthDelta:
    before_score: float
    after_score: float
    score_delta: float
    problems_before: int
    problems_after: int
    problems_delta: int
    severity_breakdown: Dict[str, int] = field(default_factory=dict)
    security_status: str = "PASS"
    tests_status: str = "PASS"
    architecture_status: str = "PASS"
    regression_status: str = "NONE"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "before_score": self.before_score,
            "after_score": self.after_score,
            "score_delta": self.score_delta,
            "problems_before": self.problems_before,
            "problems_after": self.problems_after,
            "problems_delta": self.problems_delta,
            "severity_breakdown": self.severity_breakdown,
            "security_status": self.security_status,
            "tests_status": self.tests_status,
            "architecture_status": self.architecture_status,
            "regression_status": self.regression_status,
        }


class HealthDeltaCalculator:
    """Calculates granular health and metric transitions."""

    @classmethod
    def calculate(
        cls,
        before_score: float,
        problems_before: int,
        current_report: HealthReport,
        has_regressions: bool = False,
        test_passed: bool = True,
    ) -> HealthDelta:
        after_score = current_report.health_score.overall_score
        score_delta = round(after_score - before_score, 1)

        problems_after = len(current_report.findings)
        problems_delta = problems_after - problems_before

        sev_counts: Dict[str, int] = {}
        for f in current_report.findings:
            sev_counts[f.severity.value] = sev_counts.get(f.severity.value, 0) + 1

        sec_findings = [f for f in current_report.findings if f.severity in (FindingSeverity.CRITICAL, FindingSeverity.HIGH) and "SEC" in f.rule_id]
        security_status = "FAIL" if sec_findings else "PASS"

        arch_findings = [f for f in current_report.findings if "ARCH" in f.rule_id]
        arch_status = "WARNING" if arch_findings else "PASS"

        return HealthDelta(
            before_score=before_score,
            after_score=after_score,
            score_delta=score_delta,
            problems_before=problems_before,
            problems_after=problems_after,
            problems_delta=problems_delta,
            severity_breakdown=sev_counts,
            security_status=security_status,
            tests_status="PASS" if test_passed else "FAIL",
            architecture_status=arch_status,
            regression_status="DETECTED" if has_regressions else "NONE",
        )
