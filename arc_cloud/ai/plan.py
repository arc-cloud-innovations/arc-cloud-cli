"""ARC CLOUD Prioritized Remediation Plan Generator."""
from __future__ import annotations

from typing import Any, Dict, List
from arc_cloud.core.models import Finding, FindingSeverity, HealthReport


class RemediationPlanner:
    """Creates a prioritized, sprint-ready engineering remediation plan."""

    @classmethod
    def generate_plan(cls, report: HealthReport) -> Dict[str, Any]:
        p0_findings: List[Finding] = []
        p1_findings: List[Finding] = []
        p2_findings: List[Finding] = []

        total_minutes = 0

        for f in report.findings:
            est = getattr(f, "estimated_fix_minutes", 30) or 30
            total_minutes += est
            engine = getattr(f, "engine", "").lower()
            sev = f.severity

            # P0: Critical security or secrets, or any critical finding
            if sev == FindingSeverity.CRITICAL or engine == "secrets" or (engine == "security" and sev in (FindingSeverity.CRITICAL, FindingSeverity.HIGH)):
                p0_findings.append(f)
            # P1: High reliability, architecture, or high findings
            elif sev == FindingSeverity.HIGH or engine in ("reliability", "architecture"):
                p1_findings.append(f)
            # P2: Medium/low tech debt, testing, performance, code quality
            else:
                p2_findings.append(f)

        total_hours = round(total_minutes / 60.0, 1)

        def to_task(f: Finding) -> Dict[str, Any]:
            return {
                "id": f.id,
                "rule_id": f.rule_id,
                "engine": getattr(f, "engine", "code_quality"),
                "severity": f.severity.value,
                "location": f"{f.file_path}:{f.line or 1}",
                "message": f.message,
                "action": f.recommendation or "Refactor code pattern.",
                "estimated_minutes": getattr(f, "estimated_fix_minutes", 30) or 30,
            }

        return {
            "project_name": report.project_profile.name,
            "overall_health_score": report.health_score.overall_score,
            "total_estimated_hours": total_hours,
            "summary": {
                "p0_count": len(p0_findings),
                "p1_count": len(p1_findings),
                "p2_count": len(p2_findings),
                "total_tasks": len(report.findings),
            },
            "p0_immediate": [to_task(f) for f in p0_findings],
            "p1_short_term": [to_task(f) for f in p1_findings],
            "p2_long_term": [to_task(f) for f in p2_findings],
        }
