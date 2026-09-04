"""Blueprint generator and serializer for ARC CLOUD CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from arc_cloud.blueprint.models import (
    ArchitectureSummary,
    Blueprint,
    ConfigFileInfo,
    DependencyInfo,
    FrameworkMetric,
    LanguageMetric,
    PlatformInfo,
    ProjectInfo,
    ProjectType,
    ScannerMetadata,
    StructureInfo,
)


class BlueprintGenerator:
    """Generates a standardized Software Blueprint v1.0."""

    @staticmethod
    def create(
        project_name: str,
        project_type: ProjectType,
        root_path: str,
        languages: List[LanguageMetric],
        frameworks: List[FrameworkMetric],
        platforms: List[PlatformInfo],
        dependencies: List[DependencyInfo],
        configuration_files: List[ConfigFileInfo],
        structure: StructureInfo,
        architecture: ArchitectureSummary,
        warnings: List[str],
        duration_seconds: float,
        files_scanned: int,
        scanner_version: str = "0.1.0",
        description: Optional[str] = None,
    ) -> Blueprint:
        scanner = ScannerMetadata(
            name="ARC CLOUD CLI",
            version=scanner_version,
            duration_seconds=round(duration_seconds, 3),
            files_scanned=files_scanned,
        )

        project = ProjectInfo(
            name=project_name,
            type=project_type,
            root_path=root_path,
            description=description,
        )

        return Blueprint(
            schema_version="1.0",
            scanner=scanner,
            project=project,
            languages=languages,
            frameworks=frameworks,
            platforms=platforms,
            dependencies=dependencies,
            configuration_files=configuration_files,
            structure=structure,
            architecture=architecture,
            warnings=warnings,
        )

    @staticmethod
    def to_json(blueprint: Blueprint, indent: int = 2) -> str:
        """Serialize the blueprint model to a formatted JSON string."""
        return blueprint.model_dump_json(indent=indent)

    @staticmethod
    def to_dict(blueprint: Blueprint) -> Dict[str, Any]:
        """Serialize the blueprint model to a Python dictionary."""
        return blueprint.model_dump(mode="json")

    @staticmethod
    def save_to_file(blueprint: Blueprint, output_path: str | Path) -> Path:
        """Write the blueprint JSON to a specified file path."""
        path = Path(output_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(BlueprintGenerator.to_json(blueprint), encoding="utf-8")
        return path
