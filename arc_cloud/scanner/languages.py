"""Language detector for ARC CLOUD CLI."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Dict, List, Set

from arc_cloud.blueprint.models import LanguageMetric

# Map file extensions to programming languages
EXTENSION_LANGUAGE_MAP: Dict[str, str] = {
    # Dart
    ".dart": "Dart",
    # Python
    ".py": "Python",
    ".pyi": "Python",
    ".pyw": "Python",
    # JavaScript
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".jsx": "JavaScript",
    # TypeScript
    ".ts": "TypeScript",
    ".mts": "TypeScript",
    ".cts": "TypeScript",
    ".tsx": "TypeScript",
    # Java
    ".java": "Java",
    # Kotlin
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    # Swift
    ".swift": "Swift",
    # C#
    ".cs": "C#",
    ".csx": "C#",
    # C++
    ".cpp": "C++",
    ".cxx": "C++",
    ".cc": "C++",
    ".hpp": "C++",
    ".hxx": "C++",
    ".h": "C/C++",
    ".c": "C",
    # Go
    ".go": "Go",
    # Rust
    ".rs": "Rust",
    # PHP
    ".php": "PHP",
    # Ruby
    ".rb": "Ruby",
}


class LanguageDetector:
    """Detects programming languages based on file extensions and project structure."""

    @staticmethod
    def detect(relative_files: List[str]) -> List[LanguageMetric]:
        """Calculates file counts and percentages for each detected programming language."""
        counts: Counter[str] = Counter()

        for rel_file in relative_files:
            ext = Path(rel_file).suffix.lower()
            if ext in EXTENSION_LANGUAGE_MAP:
                lang = EXTENSION_LANGUAGE_MAP[ext]
                counts[lang] += 1

        total_code_files = sum(counts.values())
        if total_code_files == 0:
            return []

        results: List[LanguageMetric] = []
        # Sort by file count descending, then name ascending
        for lang, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
            pct = round((count / total_code_files) * 100.0, 1)
            results.append(LanguageMetric(name=lang, files=count, percentage=pct))

        return results
