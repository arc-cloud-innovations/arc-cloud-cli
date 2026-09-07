"""ARC004: Duplicate Code / Repeated Logic Rule."""
from typing import Dict, List

from arc_cloud.core.models import Finding, FindingCategory, FindingSeverity
from arc_cloud.rules.base import BaseRule, RuleContext


class ARC004DuplicateCodeRule(BaseRule):
    """Detects repeated identical blocks of code within the same file."""

    rule_id = "ARC004"
    title = "Duplicate Code"
    category = FindingCategory.CODE_QUALITY
    default_severity = FindingSeverity.MEDIUM
    description = (
        "Duplicate blocks of code increase maintenance overhead and defect probability when changes are not synchronized."
    )
    recommendation = "Extract duplicate logic into a shared helper function or utility module."
    why_it_matters = "Duplication violates the DRY (Don't Repeat Yourself) principle."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        findings: List[Finding] = []
        if not context.file_content:
            return findings

        raw_lines = context.file_content.splitlines()
        # Clean lines: strip whitespace and ignore empty or comment lines
        cleaned = [line.strip() for line in raw_lines]
        block_size = 6  # Minimum identical consecutive lines to flag

        if len(cleaned) < block_size * 2:
            return findings

        seen_blocks: Dict[str, int] = {}
        reported_lines: set[int] = set()

        for idx in range(len(cleaned) - block_size + 1):
            window = cleaned[idx : idx + block_size]
            # Skip if mostly empty or trivial (e.g. just braces or passes)
            meaningful_lines = [l for l in window if l and not l.startswith("#") and len(l) > 3]
            if len(meaningful_lines) < 4:
                continue

            block_signature = "\n".join(window)
            line_num = idx + 1

            if block_signature in seen_blocks:
                orig_line = seen_blocks[block_signature]
                if line_num not in reported_lines and (line_num - orig_line) >= block_size:
                    findings.append(
                        Finding(
                            rule_id=self.rule_id,
                            engine="code_quality",
                            title=self.title,
                            description=f"Duplicate code block of {block_size} lines matching lines {orig_line}-{orig_line + block_size - 1}.",
                            category=self.category,
                            severity=self.default_severity,
                            file_path=context.relative_path,
                            line=line_num,
                            end_line=line_num + block_size - 1,
                            recommendation=self.recommendation,
                            confidence="MEDIUM",
                            estimated_fix_minutes=30,
                        )
                    )
                    reported_lines.add(line_num)
            else:
                seen_blocks[block_signature] = line_num

        return findings
