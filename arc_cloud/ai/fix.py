"""ARC CLOUD Automated Fix Generation and Application Module."""
from __future__ import annotations

import difflib
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from arc_cloud.ai.knowledge_base import RULE_KNOWLEDGE_BASE
from arc_cloud.core.models import Finding
from arc_cloud.scanner.engine import ScannerEngine


class FindingFixer:
    """Generates patches, manages file backups, applies fixes, and re-scans for resolution."""

    @classmethod
    def generate_fix(cls, finding: Finding, root_dir: Path) -> Dict[str, Any]:
        """Generates a proposed patch and fix description for a finding."""
        target_file = (root_dir / finding.file_path).resolve()
        if not target_file.is_file():
            # Try absolute path
            target_file = Path(finding.file_path).resolve()

        if not target_file.is_file():
            raise FileNotFoundError(f"File not found: {finding.file_path}")

        original_lines = target_file.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        modified_lines = list(original_lines)
        line_idx = (finding.line - 1) if finding.line and finding.line > 0 else 0

        rule_id = finding.rule_id
        fix_description = "Refactor code pattern to address static finding."
        applied = False

        if line_idx < len(modified_lines):
            cur_line = modified_lines[line_idx]
            indent = len(cur_line) - len(cur_line.lstrip())
            indent_str = cur_line[:indent]

            # Rule-specific automated transforms
            if rule_id == "ARC-REL-001":
                # Broad exception: except Exception: pass -> except Exception as exc: # TODO: handle exc
                if "except" in cur_line and "pass" in cur_line:
                    modified_lines[line_idx] = f"{indent_str}except Exception as exc:\n{indent_str}    # ARC CLOUD: handle or log exception\n{indent_str}    pass\n"
                    fix_description = "Add explicit exception capture variable for logging/handling."
                    applied = True
                elif "except Exception:" in cur_line:
                    modified_lines[line_idx] = cur_line.replace("except Exception:", "except Exception as exc:")
                    fix_description = "Capture exception instance for diagnosis."
                    applied = True
            elif rule_id == "ARC-SEC-008":
                # Insecure HTTP -> HTTPS
                if "http://" in cur_line:
                    modified_lines[line_idx] = cur_line.replace("http://", "https://")
                    fix_description = "Upgrade insecure http:// URL to https://."
                    applied = True
            elif rule_id == "ARC-SEC-003":
                # shell=True -> shell=False
                if "shell=True" in cur_line:
                    modified_lines[line_idx] = cur_line.replace("shell=True", "shell=False")
                    fix_description = "Disable shell execution to prevent command injection."
                    applied = True
            elif rule_id == "ARC-DEP-001":
                # Unpinned wildcard * -> ^
                if '"*"' in cur_line or "'*'" in cur_line:
                    modified_lines[line_idx] = cur_line.replace('"*"', '"^1.0.0"').replace("'*'", "'^1.0.0'")
                    fix_description = "Pin wildcard dependency to compatible version range."
                    applied = True

        if not applied:
            # Generic comment annotation if specific AST transform not automated
            if line_idx < len(modified_lines):
                cur_line = modified_lines[line_idx]
                indent = len(cur_line) - len(cur_line.lstrip())
                indent_str = cur_line[:indent]
                rec_comment = f"{indent_str}# ARC-FIX ({rule_id}): {finding.recommendation or 'Review pattern'}\n"
                modified_lines.insert(line_idx, rec_comment)
                fix_description = f"Annotated code with remediation directive for {rule_id}."

        # Compute unified diff
        diff_lines = list(
            difflib.unified_diff(
                original_lines,
                modified_lines,
                fromfile=f"a/{finding.file_path}",
                tofile=f"b/{finding.file_path}",
                lineterm="",
            )
        )
        patch_str = "\n".join(diff_lines)

        return {
            "finding_id": finding.id,
            "rule_id": rule_id,
            "file_path": str(target_file),
            "fix_description": fix_description,
            "patch": patch_str,
            "original_lines": original_lines,
            "modified_lines": modified_lines,
        }

    @classmethod
    def apply_fix(cls, fix_data: Dict[str, Any]) -> Path:
        """Creates a backup file (.bak) and applies the modified lines to the target file."""
        target_file = Path(fix_data["file_path"])
        backup_file = target_file.with_suffix(target_file.suffix + ".bak")

        # 1. Create backup
        shutil.copy2(target_file, backup_file)

        # 2. Write modified content
        target_file.write_text("".join(fix_data["modified_lines"]), encoding="utf-8")
        return backup_file

    @classmethod
    def verify_resolution(cls, finding: Finding, root_dir: Path) -> bool:
        """Re-scans the target file to verify if the finding has been resolved."""
        target_file = (root_dir / finding.file_path).resolve()
        if not target_file.is_file():
            target_file = Path(finding.file_path).resolve()
        if not target_file.is_file():
            return False

        from arc_cloud.core.orchestrator import ScanOrchestrator
        orchestrator = ScanOrchestrator()
        report = orchestrator.run_scan(root_dir)
        # Check if same rule_id is still triggered on that file and line
        still_present = any(
            f.rule_id == finding.rule_id and str(f.file_path) == str(finding.file_path)
            for f in report.findings
        )
        return not still_present
