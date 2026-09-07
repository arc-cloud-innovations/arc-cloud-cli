"""ARC CLOUD Baseline Tracking and Verification Engine."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from arc_cloud.core.models import HealthReport
from arc_cloud.core.orchestrator import ScanOrchestrator


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
