"""Unified diff and changed lines calculation for live monitoring."""
from __future__ import annotations

import difflib
from pathlib import Path
from typing import List, Optional, Tuple


class ChangeDiffer:
    """Calculates diffs and modified line ranges."""

    @staticmethod
    def get_unified_diff(
        old_content: str,
        new_content: str,
        file_path: str = "",
    ) -> str:
        """Returns a standard unified diff string."""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        )
        return "".join(diff)

    @staticmethod
    def extract_changed_line_numbers(old_content: str, new_content: str) -> List[int]:
        """Extracts 1-indexed line numbers in new_content that were added or modified."""
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        changed_lines: List[int] = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag in ("replace", "insert"):
                # j1 to j2 in new_lines are changed
                changed_lines.extend(range(j1 + 1, j2 + 1))
        return changed_lines

    @staticmethod
    def diff_files(
        old_path: Optional[Path],
        new_path: Optional[Path],
        old_content: Optional[str] = None,
    ) -> Tuple[str, List[int]]:
        """Compares previous content with the current file on disk."""
        prev = old_content or ""
        curr = ""
        if new_path and new_path.is_file():
            try:
                curr = new_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                curr = ""
        path_str = str(new_path or old_path or "unknown")
        diff = ChangeDiffer.get_unified_diff(prev, curr, path_str)
        changed = ChangeDiffer.extract_changed_line_numbers(prev, curr)
        return diff, changed
