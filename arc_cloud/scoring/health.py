"""Health score calculation engine for ARC CLOUD Software Engineering Health Platform."""
from typing import Dict, List, Optional, Union

from arc_cloud.core.models import (
    EngineStatus,
    Finding,
    FindingCategory,
    HealthScore,
    ProjectProfile,
)
from arc_cloud.engines.base import EngineResult
from arc_cloud.scoring.severity import get_severity_deduction

ENGINE_NAMES = [
    "code_quality",
    "reliability",
    "security",
    "dependencies",
    "secrets",
    "architecture",
    "technical_debt",
    "testing",
    "performance",
    "ai_risk",
]


class HealthEngine:
    """Computes holistic health scores across all 10 engineering health dimensions."""

    @staticmethod
    def calculate(
        findings: List[Finding],
        profile: Optional[ProjectProfile] = None,
        engine_results: Optional[Dict[str, EngineResult]] = None,
    ) -> HealthScore:
        engine_scores: Dict[str, Optional[int]] = {}
        engine_statuses: Dict[str, str] = {}
        results_map = engine_results or {}

        # 1. Process each of the 10 engineering health engines
        for name in ENGINE_NAMES:
            res = results_map.get(name)
            if res is None:
                # If only findings were passed without explicit engine results:
                # Check if this engine has findings or is code_quality
                cat_name = "dependency" if name == "dependencies" else name
                engine_findings = [f for f in findings if f.category.value == cat_name or f.engine == name]
                if name == "code_quality" or engine_findings:
                    score = HealthEngine._score_from_findings(engine_findings)
                    engine_scores[name] = score
                    engine_statuses[name] = EngineStatus.ANALYZED.value
                else:
                    engine_scores[name] = None
                    engine_statuses[name] = EngineStatus.NOT_ANALYZED.value
            else:
                if res.status == EngineStatus.ANALYZED:
                    if res.score is not None:
                        engine_scores[name] = max(0, min(100, int(res.score)))
                    else:
                        engine_scores[name] = HealthEngine._score_from_findings(res.findings)
                    engine_statuses[name] = EngineStatus.ANALYZED.value
                elif res.status == EngineStatus.UNSUPPORTED:
                    engine_scores[name] = None
                    engine_statuses[name] = EngineStatus.UNSUPPORTED.value
                elif res.status == EngineStatus.ERROR:
                    engine_scores[name] = None
                    engine_statuses[name] = EngineStatus.ERROR.value
                else:
                    engine_scores[name] = None
                    engine_statuses[name] = EngineStatus.NOT_ANALYZED.value

        # 2. Determine AI Risk rating
        ai_risk_res = results_map.get("ai_risk")
        ai_risk_rating: Optional[str] = None
        if ai_risk_res and ai_risk_res.status == EngineStatus.ANALYZED:
            ai_risk_rating = ai_risk_res.metrics.get("risk_level", "LOW")

        # 3. Compute overall score strictly from ANALYZED scores (excluding ai_risk if categorical)
        analyzed_scores = [
            score for eng, score in engine_scores.items()
            if score is not None and eng != "ai_risk"
        ]

        if analyzed_scores:
            overall_health = int(round(sum(analyzed_scores) / len(analyzed_scores)))
        else:
            overall_health = 100

        analyzed_count = sum(1 for st in engine_statuses.values() if st == EngineStatus.ANALYZED.value)
        total_count = len(ENGINE_NAMES)
        coverage_str = f"{analyzed_count}/{total_count} engines analyzed"

        # 4. Grade assignment
        if overall_health >= 90:
            grade = "A"
        elif overall_health >= 80:
            grade = "B"
        elif overall_health >= 70:
            grade = "C"
        elif overall_health >= 60:
            grade = "D"
        else:
            grade = "F"

        dimension_summaries = []
        for eng, score in engine_scores.items():
            if score is not None and eng != "ai_risk":
                eng_disp = eng.replace("_", " ").title()
                dimension_summaries.append(f"{eng_disp} ({float(score):.1f}/100)")

        dims_text = ": " + ", ".join(dimension_summaries) if dimension_summaries else ""
        explanation = (
            f"Overall health ({overall_health}/100, Grade {grade}) derived from {coverage_str}{dims_text}. "
            f"Only actively analyzed dimensions are scored to prevent misleading metrics."
        )

        return HealthScore(
            overall_health=overall_health,
            code_quality=engine_scores.get("code_quality"),
            reliability=engine_scores.get("reliability"),
            security=engine_scores.get("security"),
            dependencies=engine_scores.get("dependencies"),
            secrets=engine_scores.get("secrets"),
            architecture=engine_scores.get("architecture"),
            technical_debt=engine_scores.get("technical_debt"),
            testing=engine_scores.get("testing"),
            performance=engine_scores.get("performance"),
            ai_risk=ai_risk_rating,
            engine_statuses=engine_statuses,
            analysis_coverage=coverage_str,
            analyzed_count=analyzed_count,
            total_engines_count=total_count,
            grade=grade,
            explanation=explanation,
            status_dimensions=engine_statuses,
        )

    @staticmethod
    def _score_from_findings(findings: List[Finding]) -> int:
        """Calculates 0-100 score by deducting weighted points from 100 base."""
        deductions = sum(get_severity_deduction(f.severity) for f in findings)
        return max(0, min(100, int(round(100.0 - deductions))))
