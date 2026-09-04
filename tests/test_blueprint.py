"""Unit tests for Software Blueprint models and generator."""

import json
from arc_cloud.blueprint.generator import BlueprintGenerator
from arc_cloud.blueprint.models import (
    ArchitectureSummary,
    Blueprint,
    ConfigFileInfo,
    DependencyInfo,
    FrameworkMetric,
    LanguageMetric,
    PlatformInfo,
    PlatformType,
    ProjectType,
    StructureArea,
    StructureInfo,
)


def test_blueprint_serialization():
    blueprint = BlueprintGenerator.create(
        project_name="test_app",
        project_type=ProjectType.MOBILE,
        root_path="/tmp/test_app",
        languages=[
            LanguageMetric(name="Dart", files=50, percentage=100.0)
        ],
        frameworks=[
            FrameworkMetric(name="Flutter", version="3.19.0", category="Mobile")
        ],
        platforms=[
            PlatformInfo(name=PlatformType.ANDROID, source="android/")
        ],
        dependencies=[
            DependencyInfo(name="flutter", version="sdk: flutter", source="pubspec.yaml", type="runtime")
        ],
        configuration_files=[
            ConfigFileInfo(path="pubspec.yaml", name="pubspec.yaml", type="package")
        ],
        structure=StructureInfo(
            areas=[StructureArea(name="source", paths=["lib"])],
            total_files=50,
            total_directories=5,
            ignored_directories=[".git"],
        ),
        architecture=ArchitectureSummary(patterns=["MVC"]),
        warnings=[],
        duration_seconds=0.123,
        files_scanned=50,
    )

    json_str = BlueprintGenerator.to_json(blueprint)
    data = json.loads(json_str)

    assert data["schema_version"] == "1.0"
    assert data["scanner"]["name"] == "ARC CLOUD CLI"
    assert data["project"]["name"] == "test_app"
    assert data["project"]["type"] == "Mobile Application"
    assert len(data["languages"]) == 1
    assert data["languages"][0]["name"] == "Dart"
    assert data["scanner"]["files_scanned"] == 50

    # Ensure round-trip validation works
    reloaded = Blueprint.model_validate_json(json_str)
    assert reloaded.project.name == "test_app"
    assert reloaded.schema_version == "1.0"
