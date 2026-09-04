"""Unit tests for language detection."""

from arc_cloud.scanner.languages import LanguageDetector


def test_language_detection_single_language():
    files = ["src/index.ts", "src/util.ts", "src/types.ts"]
    metrics = LanguageDetector.detect(files)

    assert len(metrics) == 1
    assert metrics[0].name == "TypeScript"
    assert metrics[0].files == 3
    assert metrics[0].percentage == 100.0


def test_language_detection_mixed_languages():
    files = [
        "app/main.py",
        "app/models.py",
        "app/utils.py",
        "web/index.js",
    ]
    metrics = LanguageDetector.detect(files)

    assert len(metrics) == 2
    assert metrics[0].name == "Python"
    assert metrics[0].files == 3
    assert metrics[0].percentage == 75.0

    assert metrics[1].name == "JavaScript"
    assert metrics[1].files == 1
    assert metrics[1].percentage == 25.0


def test_language_detection_empty():
    metrics = LanguageDetector.detect([])
    assert metrics == []


def test_language_detection_non_code_files():
    files = ["README.md", "LICENSE", ".gitignore", "data.json"]
    metrics = LanguageDetector.detect(files)
    assert metrics == []


def test_language_detection_all_supported_types():
    files = [
        "main.dart",
        "script.py",
        "app.js",
        "app.ts",
        "Service.java",
        "Main.kt",
        "AppDelegate.swift",
        "Program.cs",
        "engine.cpp",
        "server.go",
        "lib.rs",
        "index.php",
        "app.rb",
    ]
    metrics = LanguageDetector.detect(files)
    detected_names = {m.name for m in metrics}

    assert "Dart" in detected_names
    assert "Python" in detected_names
    assert "JavaScript" in detected_names
    assert "TypeScript" in detected_names
    assert "Java" in detected_names
    assert "Kotlin" in detected_names
    assert "Swift" in detected_names
    assert "C#" in detected_names
    assert "C++" in detected_names
    assert "Go" in detected_names
    assert "Rust" in detected_names
    assert "PHP" in detected_names
    assert "Ruby" in detected_names
