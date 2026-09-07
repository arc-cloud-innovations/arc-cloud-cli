"""Risk calculation engine for ARC CLOUD findings."""
from typing import List

from arc_cloud.core.models import Finding, FindingSeverity, RiskAssessment
from arc_cloud.scoring.severity import get_severity_weight


class RiskEngine:
    """Computes risk points and severity profiles from findings."""

    @staticmethod
    def assess(findings: List[Finding]) -> RiskAssessment:
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0
        info_count = 0
        total_risk_score = 0

        for f in findings:
            weight = get_severity_weight(f.severity)
            total_risk_score += weight

            if f.severity == FindingSeverity.CRITICAL:
                critical_count += 1
            elif f.severity == FindingSeverity.HIGH:
                high_count += 1
            elif f.severity == FindingSeverity.MEDIUM:
                medium_count += 1
            elif f.severity == FindingSeverity.LOW:
                low_count += 1
            elif f.severity == FindingSeverity.INFO:
                info_count += 1

        if total_risk_score >= 30 or critical_count >= 3:
            level = "CRITICAL"
        elif total_risk_score >= 15 or critical_count >= 1 or high_count >= 2:
            level = "HIGH"
        elif total_risk_score >= 5 or high_count >= 1 or medium_count >= 2:
            level = "MEDIUM"
        elif total_risk_score > 0:
            level = "LOW"
        else:
            level = "NONE"

        return RiskAssessment(
            level=level,
            total_risk_score=total_risk_score,
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            info_count=info_count,
        )
