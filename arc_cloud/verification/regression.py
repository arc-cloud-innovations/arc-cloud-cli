"""Regression detection comparing current scan against previous state."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from arc_cloud.core.models import Finding, FindingSeverity, HealthReport


@dataclass
class RegressionReport:
    has_regression: bool = False
    new_findings: List[Finding] = field(default_factory=list)
    fixed_findings: List[Dict[str, Any]] = field(default_factory=list)
    new_critical_count: int = 0
    new_high_count: int = 0
    health_dropped: bool = False
    score_delta: float = 0.0
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_regression": self.has_regression,
            "new_findings_count": len(self.new_findings),
            "fixed_findings_count": len(self.fixed_findings),
            "new_critical_count": self.new_critical_count,
            "new_high_count": self.new_high_count,
            "health_dropped": self.health_dropped,
            "score_delta": self.score_delta,
            "reasons": self.reasons,
        }


class RegressionDetector:
    """Detects whether recent code changes introduced regressions."""

    @classmethod
    def check_regression(
        cls,
        current_report: HealthReport,
        previous_findings: List[Dict[str, Any]],
        previous_score: float,
    ) -> RegressionReport:
        report = RegressionReport()
        report.score_delta = round(current_report.health_score.overall_score - previous_score, 1)

        prev_sigs = {
            f"{f.get('rule_id')}:{f.get('file_path')}:{f.get('line') or 1}": f
            for f in previous_findings
        }
        curr_sigs = {
            f"{f.rule_id}:{f.file_path}:{f.line or 1}": f
            for f in current_report.findings
        }

        # Identify newly introduced findings
        new_keys = set(curr_sigs.keys()) - set(prev_sigs.keys())
        fixed_keys = set(prev_sigs.keys()) - set(curr_sigs.keys())

        report.new_findings = [curr_sigs[k] for k in new_keys]
        report.fixed_findings = [prev_sigs[k] for k in fixed_keys]

        for nf in report.new_findings:
            if nf.severity == FindingSeverity.CRITICAL:
                report.new_critical_count += 1
            elif nf.severity == FindingSeverity.HIGH:
                report.new_high_count += 1

        if report.new_critical_count > 0:
            report.has_regression = True
            report.reasons.append(f"Introduced {report.new_critical_count} new CRITICAL severity finding(s).")

        if report.new_high_count > 0:
            report.has_regression = True
            report.reasons.append(f"Introduced {report.new_high_count} new HIGH severity finding(s).")

        if report.score_delta < -5.0:
            report.health_dropped = True
            report.has_regression = True
            report.reasons.append(f"Health score dropped significantly by {report.score_delta} points.")

        return report
