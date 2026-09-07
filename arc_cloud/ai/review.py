"""ARC CLOUD Pre-Commit and Git Diff Code Review Module."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from arc_cloud.core.orchestrator import ScanOrchestrator
from arc_cloud.core.models import Finding


class CodeReviewer:
    """Reviews uncommitted or staged changes via git diff to catch regressions before commit."""

    @classmethod
    def review_changes(cls, root_dir: Path, staged_only: bool = False) -> Dict[str, Any]:
        """Runs scan on the project and filters findings matching modified files/lines."""
        # 1. Get changed files from git
        cmd = ["git", "diff", "--name-only"]
        if staged_only:
            cmd.append("--cached")

        try:
            res = subprocess.run(cmd, cwd=root_dir, capture_output=True, text=True, check=True)
            changed_files = {line.strip() for line in res.stdout.splitlines() if line.strip()}
        except Exception:
            # Fallback if not a git repository or git fails: review all files
            changed_files = set()

        orchestrator = ScanOrchestrator()
        report = orchestrator.run_scan(root_dir)

        relevant_findings: List[Finding] = []
        for f in report.findings:
            f_str = str(f.file_path)
            # If git changed_files detected, filter by changed files
            if changed_files:
                if any(f_str.endswith(cf) or cf.endswith(f_str) for cf in changed_files):
                    relevant_findings.append(f)
            else:
                relevant_findings.append(f)

        return {
            "root_dir": str(root_dir),
            "is_git_repo": bool(changed_files or Path(root_dir / ".git").exists()),
            "changed_files_count": len(changed_files),
            "changed_files": sorted(list(changed_files)),
            "new_regressions_count": len(relevant_findings),
            "findings": relevant_findings,
            "passed": len(relevant_findings) == 0,
        }
