"""Configuration file detector for ARC CLOUD CLI."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from arc_cloud.blueprint.models import ConfigFileInfo

# Recognized configuration patterns and categories
KNOWN_CONFIG_PATTERNS = [
    (r"^pubspec\.ya?ml$", "package", "Dart/Flutter Package Spec"),
    (r"^package\.json$", "package", "Node.js Package Manifest"),
    (r"^tsconfig.*\.json$", "build", "TypeScript Configuration"),
    (r"^next\.config\.[mc]?[jt]s$", "framework", "Next.js Configuration"),
    (r"^vite\.config\.[mc]?[jt]s$", "build", "Vite Configuration"),
    (r"^requirements.*\.txt$", "package", "Python Requirements"),
    (r"^pyproject\.toml$", "package", "Python Project Configuration"),
    (r"^Pipfile(\.lock)?$", "package", "Pipenv Manifest"),
    (r"^pom\.xml$", "build", "Maven Build Descriptor"),
    (r"^(build|settings)\.gradle(\.kts)?$", "build", "Gradle Build Script"),
    (r"^.*\.csproj$", "build", "C# Project Configuration"),
    (r"^.*\.sln$", "build", ".NET Solution File"),
    (r"^(Dockerfile.*|docker-compose.*\.ya?ml)$", "container", "Docker Configuration"),
    (r"^\.gitignore$", "git", "Git Ignore Rules"),
    (r"^README(\.md|\.rst|\.txt)?$", "documentation", "Project Documentation"),
]


class ConfigDetector:
    """Detects important configuration and manifest files in the project."""

    @staticmethod
    def detect(relative_files: List[str]) -> List[ConfigFileInfo]:
        detected: List[ConfigFileInfo] = []
        seen_paths = set()

        for rel_file in relative_files:
            file_name = Path(rel_file).name
            for pattern, cat, _desc in KNOWN_CONFIG_PATTERNS:
                if re.match(pattern, file_name, re.IGNORECASE):
                    if rel_file not in seen_paths:
                        seen_paths.add(rel_file)
                        detected.append(
                            ConfigFileInfo(
                                path=rel_file,
                                name=file_name,
                                type=cat,
                            )
                        )
                    break

        return sorted(detected, key=lambda c: (c.type, c.path))
