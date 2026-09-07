"""AI Code Risk Engine for ARC CLOUD (observable engineering signals)."""
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


class AIRiskEngine(BaseEngine):
    """Evaluates composite code risk signals (complexity + missing tests + security exposure)."""

    name = "ai_risk"
    version = "1.0.0"
    category = FindingCategory.AI_CODE_RISK

    def is_available(self) -> bool:
        return True

    def analyze(
        self,
        project_root: Path,
        profile: ProjectProfile,
        config: Optional[ArcConfig] = None,
    ) -> EngineResult:
        start = time.perf_counter()
        signals: List[str] = []
        findings: List[Finding] = []

        # Signal 1: Test-to-source ratio
        source_count = len(profile.source_files)
        test_count = len(profile.test_files)
        if source_count > 10 and test_count == 0:
            signals.append("Zero automated test suites for extensive codebase")
        elif source_count > 20 and (test_count / source_count) < 0.15:
            signals.append("Low test-to-source file ratio (< 15%)")

        # Signal 2: Security-sensitive packages without corresponding tests
        untested_sensitive: List[str] = []
        test_stems = {Path(t).stem.lower().replace("test_", "").replace("_test", "") for t in profile.test_files}
        for src in profile.source_files:
            stem = Path(src).stem.lower()
            if any(k in stem for k in ("auth", "security", "token", "payment", "crypto")):
                if stem not in test_stems:
                    untested_sensitive.append(src)

        if untested_sensitive:
            signals.append(f"Untested security-sensitive components ({len(untested_sensitive)} files)")

        # Determine composite risk level
        if len(signals) >= 2:
            risk_level = "HIGH"
            severity = FindingSeverity.HIGH
        elif len(signals) == 1:
            risk_level = "MEDIUM"
            severity = FindingSeverity.MEDIUM
        else:
            risk_level = "LOW"
            severity = FindingSeverity.LOW

        if risk_level in ("HIGH", "MEDIUM"):
            findings.append(
                Finding(
                    rule_id="ARC-AIRISK-001",
                    engine=self.name,
                    title=f"Elevated Engineering Risk ({risk_level})",
                    description=f"Observable risk signals detected: {'; '.join(signals)}.",
                    category=self.category,
                    severity=severity,
                    file_path="project",
                    line=1,
                    recommendation="Perform focused human code review and augment test coverage before deploying to production.",
                    confidence="HIGH",
                    estimated_fix_minutes=60,
                )
            )

        elapsed_ms = (time.perf_counter() - start) * 1000.0

        return EngineResult(
            engine_name=self.name,
            status=EngineStatus.ANALYZED,
            findings=findings,
            metrics={"risk_level": risk_level, "signals": signals},
            execution_time_ms=elapsed_ms,
        )
