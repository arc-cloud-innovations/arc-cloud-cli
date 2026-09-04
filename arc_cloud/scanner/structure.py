"""Directory and project structure analyzer for ARC CLOUD CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set

from arc_cloud.blueprint.models import StructureArea, StructureInfo

# Functional directory classifications
STRUCTURE_MAP: Dict[str, Set[str]] = {
    "source": {"src", "lib", "app", "packages", "core", "pkg", "cmd"},
    "tests": {"test", "tests", "spec", "specs", "__tests__"},
    "configuration": {"config", "configs", ".config", "conf"},
    "assets": {"assets", "res", "public", "static", "media", "resources"},
    "platform": {"android", "ios", "web", "windows", "macos", "linux"},
    "documentation": {"doc", "docs", "documentation"},
    "build": {"build", "dist", "out", "target", "bin"},
}


class StructureAnalyzer:
    """Analyzes the top-level and first-level directory hierarchy."""

    @staticmethod
    def analyze(
        relative_dirs: List[str],
        total_files: int,
        total_dirs: int,
        ignored_dirs: Set[str],
    ) -> StructureInfo:
        area_paths: Dict[str, List[str]] = {area: [] for area in STRUCTURE_MAP}

        for rel_dir in relative_dirs:
            parts = Path(rel_dir).parts
            first_level = parts[0].lower()

            for area, names in STRUCTURE_MAP.items():
                if first_level in names:
                    if len(parts) <= 2:  # Capture up to depth 2 for concise summary
                        if rel_dir not in area_paths[area]:
                            area_paths[area].append(rel_dir)

        areas: List[StructureArea] = []
        for area_name, paths in area_paths.items():
            if paths:
                areas.append(StructureArea(name=area_name, paths=sorted(paths)))

        return StructureInfo(
            areas=areas,
            total_files=total_files,
            total_directories=total_dirs,
            ignored_directories=sorted(list(ignored_dirs)),
        )
