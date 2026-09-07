"""Testing Intelligence Engine for ARC CLOUD."""
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


class TestingEngine(BaseEngine):
    """Analyzes test presence, test-to-source ratios, and critical untested modules."""

    name = "testing"
    version = "1.0.0"
    category = FindingCategory.TESTING

    def is_available(self) -> bool:
        return True

    def analyze(
        self,
        project_root: Path,
        profile: ProjectProfile,
        config: Optional[ArcConfig] = None,
    ) -> EngineResult:
        start = time.perf_counter()
        findings: List[Finding] = []

        source_count = len(profile.source_files)
        test_count = len(profile.test_files)
        ratio = round(test_count / max(1, source_count), 2)

        # Check for critical untested components
        test_names = {Path(t).stem.lower().replace("test_", "").replace("_test", "") for t in profile.test_files}
        critical_untested: List[str] = []

        for src in profile.source_files:
            src_stem = Path(src).stem.lower()
            if any(crit in src_stem for crit in ("auth", "payment", "crypto", "security", "token", "billing")):
                if src_stem not in test_names:
                    critical_untested.append(src)
                    findings.append(
                        Finding(
                            rule_id="ARC-TEST-001",
                            engine=self.name,
                            title="Missing Tests for Critical Module",
                            description=f"Security/business-critical module '{src}' has no matching unit test suite.",
                            category=self.category,
                            severity=FindingSeverity.HIGH,
                            file_path=src,
                            line=1,
                            recommendation="Add comprehensive automated unit and integration tests covering happy and error paths.",
                            confidence="HIGH",
                            estimated_fix_minutes=45,
                        )
                    )

        # Honest coverage detection
        coverage_status = "NOT MEASURED"
        coverage_files = [".coverage", "coverage.json", "lcov.info", "coverage/lcov.info"]
        has_coverage = any((project_root / cf).is_file() for cf in coverage_files)
        if has_coverage:
            coverage_status = "Measured (Telemetry present)"

        elapsed_ms = (time.perf_counter() - start) * 1000.0

        metrics: Dict[str, Any] = {
            "source_files_count": source_count,
            "test_files_count": test_count,
            "test_source_ratio": ratio,
            "coverage": coverage_status,
            "critical_untested_count": len(critical_untested),
            "critical_untested_modules": critical_untested[:5],
        }

        # Calculate score
        score = 100.0
        if profile.total_lines > 50 and source_count > 2 and test_count == 0:
            score = 50.0
        elif source_count > 2 and ratio < 0.2:
            score = 70.0
        elif source_count > 2 and ratio < 0.5:
            score = 85.0

        score = max(0.0, score - (len(critical_untested) * 10))

        return EngineResult(
            engine_name=self.name,
            status=EngineStatus.ANALYZED,
            score=score,
            findings=findings,
            metrics=metrics,
            execution_time_ms=elapsed_ms,
        )
