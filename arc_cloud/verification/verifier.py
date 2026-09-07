"""ARC CLOUD Baseline Tracking and Verification Engine."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from arc_cloud.core.models import FindingSeverity, HealthReport
from arc_cloud.core.orchestrator import ScanOrchestrator
from arc_cloud.monitoring.event_bus import EventBus, EventType
from arc_cloud.verification.health_delta import HealthDelta, HealthDeltaCalculator
from arc_cloud.verification.regression import RegressionDetector, RegressionReport


@dataclass
class VerificationResult:
    verification_id: str = field(default_factory=lambda: f"ver-{uuid.uuid4().hex[:8]}")
    status: str = "NOT_VERIFIED"  # VERIFIED | NOT_VERIFIED
    health_before: float = 100.0
    health_after: float = 100.0
    health_delta: float = 0.0
    new_findings_count: int = 0
    resolved_findings_count: int = 0
    regressions_count: int = 0
    tests_status: str = "PASS"
    security_status: str = "PASS"
    architecture_status: str = "PASS"
    timestamp: datetime = field(default_factory=datetime.now)
    verified_files: List[str] = field(default_factory=list)
    verified_hashes: Dict[str, str] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)

    @property
    def is_verified(self) -> bool:
        return self.status == "VERIFIED"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d


class VerificationEngine:
    """Manages the verification state, validity, and invalidation lifecycle."""

    def __init__(self, root_dir: Path, event_bus: Optional[EventBus] = None) -> None:
        self.root_dir = root_dir.resolve()
        self.event_bus = event_bus or EventBus()
        self.last_verification: Optional[VerificationResult] = None

    def verify_state(
        self,
        current_report: HealthReport,
        previous_findings: List[Dict[str, Any]],
        previous_score: float,
        test_passed: bool = True,
        test_errors: Optional[List[str]] = None,
    ) -> VerificationResult:
        self.event_bus.emit(EventType.VERIFICATION_STARTED, message="Running verification checks...")

        # 1. Regression check
        regression = RegressionDetector.check_regression(
            current_report=current_report,
            previous_findings=previous_findings,
            previous_score=previous_score,
        )

        # 2. Health Delta
        delta = HealthDeltaCalculator.calculate(
            before_score=previous_score,
            problems_before=len(previous_findings),
            current_report=current_report,
            has_regressions=regression.has_regression,
            test_passed=test_passed,
        )

        # 3. Security check
        crit_sec = [
            f for f in current_report.findings
            if f.severity in (FindingSeverity.CRITICAL, FindingSeverity.HIGH) and "SEC" in f.rule_id
        ]
        has_critical_security = len(crit_sec) > 0

        # Determine pass / fail
        passed = (
            test_passed
            and not regression.has_regression
            and not has_critical_security
            and current_report.health_score.overall_score >= 50.0
        )

        reasons = list(regression.reasons)
        if not test_passed:
            reasons.append("Automated test suite failed or had errors.")
            if test_errors:
                reasons.extend(test_errors[:2])
        if has_critical_security:
            reasons.append(f"{len(crit_sec)} critical/high security vulnerability(ies) active.")

        status = "VERIFIED" if passed else "NOT_VERIFIED"

        # Compute file hashes for verification validity
        hashes = self._collect_hashes()

        result = VerificationResult(
            status=status,
            health_before=previous_score,
            health_after=current_report.health_score.overall_score,
            health_delta=delta.score_delta,
            new_findings_count=len(regression.new_findings),
            resolved_findings_count=len(regression.fixed_findings),
            regressions_count=regression.new_critical_count + regression.new_high_count,
            tests_status="PASS" if test_passed else "FAIL",
            security_status=delta.security_status,
            architecture_status=delta.architecture_status,
            verified_files=list(hashes.keys()),
            verified_hashes=hashes,
            reasons=reasons,
        )

        self.last_verification = result

        if passed:
            self.event_bus.emit(
                EventType.VERIFICATION_PASSED,
                message=f"Change Verified! Health: {previous_score} -> {result.health_after}",
                data=result.to_dict(),
            )
        else:
            self.event_bus.emit(
                EventType.VERIFICATION_FAILED,
                message=f"Verification Failed! Status: NOT VERIFIED. Reasons: {', '.join(reasons)}",
                data=result.to_dict(),
            )

        return result

    def check_validity(self) -> bool:
        """Returns False and invalidates if files changed since last verification."""
        if not self.last_verification or self.last_verification.status != "VERIFIED":
            return False

        current_hashes = self._collect_hashes()
        if current_hashes != self.last_verification.verified_hashes:
            self.invalidate("Project files changed after verification.")
            return False
        return True

    def invalidate(self, reason: str = "Files modified after verification.") -> None:
        if self.last_verification and self.last_verification.status == "VERIFIED":
            self.last_verification.status = "NOT_VERIFIED"
            self.event_bus.emit(
                EventType.VERIFICATION_INVALIDATED,
                message=f"Verification Invalidated: {reason}",
                data={"reason": reason},
            )

    def _collect_hashes(self) -> Dict[str, str]:
        hashes: Dict[str, str] = {}
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in {".git", ".venv", "venv", "node_modules", "build", "dist", ".arccloud", ".arc"}]
            root_path = Path(root)
            for f in files:
                if f.endswith((".tmp", ".swp", ".bak", ".log", ".DS_Store")):
                    continue
                fpath = root_path / f
                try:
                    rel = str(fpath.relative_to(self.root_dir))
                    h = hashlib.sha256()
                    with fpath.open("rb") as fp:
                        while chunk := fp.read(65536):
                            h.update(chunk)
                    hashes[rel] = h.hexdigest()
                except Exception:
                    continue
        return hashes


class BaselineVerifier:
    """Compares current scan results against a stored baseline in .arc/baseline.json."""

    BASELINE_DIR = ".arc"
    BASELINE_FILE = "baseline.json"

    @classmethod
    def get_baseline_path(cls, root_dir: Path) -> Path:
        return root_dir / cls.BASELINE_DIR / cls.BASELINE_FILE

    @classmethod
    def save_baseline(cls, root_dir: Path, report: HealthReport) -> Path:
        base_path = cls.get_baseline_path(root_dir)
        base_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "project_name": report.project_profile.name,
            "scanned_at": report.scanned_at.isoformat(),
            "health_score": report.health_score.overall_score,
            "letter_grade": report.health_score.letter_grade,
            "findings": [
                {
                    "id": f.id,
                    "rule_id": f.rule_id,
                    "file_path": str(f.file_path),
                    "line": f.line,
                    "message": f.message,
                    "severity": f.severity.value,
                    "engine": getattr(f, "engine", "code_quality"),
                }
                for f in report.findings
            ],
        }
        base_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return base_path

    @classmethod
    def load_baseline(cls, root_dir: Path) -> Optional[Dict[str, Any]]:
        base_path = cls.get_baseline_path(root_dir)
        if not base_path.is_file():
            return None
        try:
            return json.loads(base_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    @classmethod
    def verify(cls, root_dir: Path, save_as_new_baseline: bool = False) -> Dict[str, Any]:
        """Runs scan and calculates diff with stored baseline."""
        orchestrator = ScanOrchestrator()
        current_report = orchestrator.run_scan(root_dir)
        baseline = cls.load_baseline(root_dir)

        curr_findings_keys = {
            f"{f.rule_id}:{f.file_path}:{f.line or 1}": f for f in current_report.findings
        }

        if baseline is None:
            # First run: initialize baseline
            cls.save_baseline(root_dir, current_report)
            return {
                "is_initial_run": True,
                "health_score": current_report.health_score.overall_score,
                "letter_grade": current_report.health_score.letter_grade,
                "current_findings_count": len(current_report.findings),
                "new_findings": [],
                "fixed_findings": [],
                "remaining_findings": current_report.findings,
                "trend": "baseline_initialized",
                "score_delta": 0.0,
                "report": current_report,
            }

        prev_findings = baseline.get("findings", [])
        prev_findings_keys = {
            f"{pf['rule_id']}:{pf['file_path']}:{pf.get('line') or 1}": pf for pf in prev_findings
        }

        # Calculate Diff
        new_keys = set(curr_findings_keys.keys()) - set(prev_findings_keys.keys())
        fixed_keys = set(prev_findings_keys.keys()) - set(curr_findings_keys.keys())
        remaining_keys = set(curr_findings_keys.keys()) & set(prev_findings_keys.keys())

        new_findings = [curr_findings_keys[k] for k in new_keys]
        fixed_findings = [prev_findings_keys[k] for k in fixed_keys]
        remaining_findings = [curr_findings_keys[k] for k in remaining_keys]

        prev_score = baseline.get("health_score", 100.0)
        curr_score = current_report.health_score.overall_score
        score_delta = round(curr_score - prev_score, 1)

        if score_delta > 0:
            trend = "improved"
        elif score_delta < 0:
            trend = "degraded"
        else:
            trend = "unchanged"

        if save_as_new_baseline:
            cls.save_baseline(root_dir, current_report)

        return {
            "is_initial_run": False,
            "previous_score": prev_score,
            "current_score": curr_score,
            "score_delta": score_delta,
            "trend": trend,
            "previous_grade": baseline.get("letter_grade", "A"),
            "current_grade": current_report.health_score.letter_grade,
            "new_count": len(new_findings),
            "fixed_count": len(fixed_findings),
            "remaining_count": len(remaining_findings),
            "new_findings": new_findings,
            "fixed_findings": fixed_findings,
            "remaining_findings": remaining_findings,
            "report": current_report,
        }
