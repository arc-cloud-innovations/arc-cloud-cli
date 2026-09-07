"""Technical Debt Engine for ARC CLOUD."""
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from arc_cloud.core.config import ArcConfig
from arc_cloud.core.models import (
    EngineStatus,
    Finding,
    FindingCategory,
    FindingSeverity,
    ProjectProfile,
)
from arc_cloud.engines.base import BaseEngine, EngineResult


class TechnicalDebtEngine(BaseEngine):
    """Calculates estimated technical debt remediation effort based on measurable findings."""

    name = "technical_debt"
    version = "1.0.0"
    category = FindingCategory.TECHNICAL_DEBT

    def is_available(self) -> bool:
        return True

    def analyze(
        self,
        project_root: Path,
        profile: ProjectProfile,
        config: Optional[ArcConfig] = None,
    ) -> EngineResult:
        start = time.perf_counter()
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        # Technical debt calculations are aggregated across all findings in the orchestrator
        return EngineResult(
            engine_name=self.name,
            status=EngineStatus.ANALYZED,
            findings=[],
            metrics={
                "estimated_debt_hours": 0,
                "breakdown": {},
                "note": "Estimated technical debt is computed from aggregate active findings.",
            },
            execution_time_ms=elapsed_ms,
        )

    @staticmethod
    def calculate_debt_from_findings(findings: List[Finding]) -> Dict[str, Any]:
        """Calculates remediation time in hours grouped by category."""
        breakdown_mins: Dict[str, int] = {
            "complexity": 0,
            "security": 0,
            "architecture": 0,
            "testing": 0,
            "duplication": 0,
            "general": 0,
        }

        for f in findings:
            mins = f.estimated_fix_minutes
            if mins <= 0:
                mins = 15

            if f.rule_id in ("ARC001", "ARC002", "ARC003", "ARC007"):
                breakdown_mins["complexity"] += mins
            elif f.rule_id == "ARC004":
                breakdown_mins["duplication"] += mins
            elif f.category in (FindingCategory.SECURITY, FindingCategory.SECRETS):
                breakdown_mins["security"] += mins
            elif f.category == FindingCategory.ARCHITECTURE:
                breakdown_mins["architecture"] += mins
            elif f.category == FindingCategory.TESTING:
                breakdown_mins["testing"] += mins
            else:
                breakdown_mins["general"] += mins

        total_mins = sum(breakdown_mins.values())
        total_hours = round(total_mins / 60.0, 1)

        breakdown_hours = {
            k: round(v / 60.0, 1) for k, v in breakdown_mins.items() if v > 0
        }

        return {
            "total_hours": total_hours,
            "total_minutes": total_mins,
            "breakdown_hours": breakdown_hours,
        }
