"""Unit tests for platform detection."""

from arc_cloud.blueprint.models import PlatformType
from arc_cloud.scanner.platforms import PlatformDetector


def test_platform_detection_mobile():
    dirs = ["android", "ios", "lib"]
    files = ["pubspec.yaml", "lib/main.dart"]
    platforms = PlatformDetector.detect(dirs, files)
    names = {p.name for p in platforms}

    assert PlatformType.ANDROID in names
    assert PlatformType.IOS in names


def test_platform_detection_web():
    dirs = ["public", "src"]
    files = ["public/index.html", "src/App.js"]
    platforms = PlatformDetector.detect(dirs, files)
    names = {p.name for p in platforms}

    assert PlatformType.WEB in names


def test_platform_detection_desktop():
    dirs = ["windows", "macos", "linux"]
    files = ["CMakeLists.txt"]
    platforms = PlatformDetector.detect(dirs, files)
    names = {p.name for p in platforms}

    assert PlatformType.WINDOWS in names
    assert PlatformType.MACOS in names
    assert PlatformType.LINUX in names
