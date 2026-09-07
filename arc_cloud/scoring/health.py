"""Health score calculation engine for ARC CLOUD."""
from typing import List, Optional

from arc_cloud.core.models import Finding, FindingCategory, HealthScore, ProjectProfile
from arc_cloud.scoring.severity import get_severity_deduction


class HealthEngine:
    """Computes holistic health scores across active engineering dimensions."""

    @staticmethod
    def calculate(findings: List[Finding], profile: Optional[ProjectProfile] = None) -> HealthScore:
        # Filter findings by category
        cq_findings = [f for f in findings if f.category == FindingCategory.CODE_QUALITY]

        # Calculate Code Quality Score
        cq_deductions = sum(get_severity_deduction(f.severity) for f in cq_findings)
        code_quality_score = max(0.0, min(100.0, round(100.0 - cq_deductions, 1)))

        # In MVP, only Code Quality is actively analyzed.
        # Other categories are explicitly None (not analyzed) to prevent fake metrics.
        overall_score = code_quality_score

        # Determine Letter Grade
        if overall_score >= 90.0:
            grade = "A"
        elif overall_score >= 80.0:
            grade = "B"
        elif overall_score >= 70.0:
            grade = "C"
        elif overall_score >= 60.0:
            grade = "D"
        else:
            grade = "F"

        # Generate transparent explanation
        if cq_findings:
            explanation = (
                f"Overall health ({overall_score}/100, Grade {grade}) is determined from "
                f"Code Quality ({code_quality_score}/100, {len(cq_findings)} finding(s), "
                f"-{cq_deductions} pts deduction). Security, Dependencies, Architecture, "
                "and Technical Debt were not analyzed."
            )
        else:
            explanation = (
                f"Overall health ({overall_score}/100, Grade {grade}) with 0 findings in "
                "active Code Quality checks. Security, Dependencies, Architecture, "
                "and Technical Debt were not analyzed."
            )

        return HealthScore(
            overall_score=overall_score,
            code_quality_score=code_quality_score,
            security_score=None,
            dependency_score=None,
            architecture_score=None,
            technical_debt_score=None,
            grade=grade,
            explanation=explanation,
        )
