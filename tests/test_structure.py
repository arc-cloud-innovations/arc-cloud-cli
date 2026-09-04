"""Unit tests for directory structure analyzer."""

from arc_cloud.scanner.structure import StructureAnalyzer


def test_structure_classification():
    dirs = [
        "src",
        "src/components",
        "tests",
        "tests/unit",
        "docs",
        "assets",
        "assets/images",
        "android",
        "config",
    ]

    info = StructureAnalyzer.analyze(
        relative_dirs=dirs,
        total_files=42,
        total_dirs=len(dirs),
        ignored_dirs={"node_modules", ".git"},
    )

    area_map = {a.name: a.paths for a in info.areas}

    assert "source" in area_map
    assert "src" in area_map["source"]

    assert "tests" in area_map
    assert "tests" in area_map["tests"]

    assert "documentation" in area_map
    assert "docs" in area_map["documentation"]

    assert "assets" in area_map
    assert "platform" in area_map
    assert "configuration" in area_map

    assert info.total_files == 42
    assert "node_modules" in info.ignored_directories
