"""Platform detector for ARC CLOUD CLI."""

from __future__ import annotations

from pathlib import Path
from typing import List, Set

from arc_cloud.blueprint.models import PlatformInfo, PlatformType


class PlatformDetector:
    """Detects targeted platforms such as Android, iOS, Web, Windows, macOS, and Linux."""

    @staticmethod
    def detect(relative_dirs: List[str], relative_files: List[str]) -> List[PlatformInfo]:
        platforms: List[PlatformInfo] = []
        detected_names: Set[PlatformType] = set()

        dir_set = set(relative_dirs)
        file_set = set(relative_files)

        # 1. Android
        if any(d == "android" or d.startswith("android/") for d in dir_set) or any(
            f.endswith("AndroidManifest.xml") for f in file_set
        ):
            if PlatformType.ANDROID not in detected_names:
                platforms.append(PlatformInfo(name=PlatformType.ANDROID, source="android/ directory"))
                detected_names.add(PlatformType.ANDROID)

        # 2. iOS
        if any(d == "ios" or d.startswith("ios/") for d in dir_set) or any(
            ".xcodeproj" in f or ".xcworkspace" in f for f in file_set
        ):
            if PlatformType.IOS not in detected_names:
                platforms.append(PlatformInfo(name=PlatformType.IOS, source="ios/ directory"))
                detected_names.add(PlatformType.IOS)

        # 3. Web
        if any(d == "web" or d.startswith("web/") for d in dir_set) or any(
            f.endswith("index.html") or f.startswith("public/index.html") for f in file_set
        ):
            if PlatformType.WEB not in detected_names:
                platforms.append(PlatformInfo(name=PlatformType.WEB, source="web/ directory or index.html"))
                detected_names.add(PlatformType.WEB)

        # 4. Windows
        if any(d == "windows" or d.startswith("windows/") for d in dir_set):
            if PlatformType.WINDOWS not in detected_names:
                platforms.append(PlatformInfo(name=PlatformType.WINDOWS, source="windows/ directory"))
                detected_names.add(PlatformType.WINDOWS)

        # 5. macOS
        if any(d == "macos" or d.startswith("macos/") for d in dir_set):
            if PlatformType.MACOS not in detected_names:
                platforms.append(PlatformInfo(name=PlatformType.MACOS, source="macos/ directory"))
                detected_names.add(PlatformType.MACOS)

        # 6. Linux
        if any(d == "linux" or d.startswith("linux/") for d in dir_set):
            if PlatformType.LINUX not in detected_names:
                platforms.append(PlatformInfo(name=PlatformType.LINUX, source="linux/ directory"))
                detected_names.add(PlatformType.LINUX)

        return platforms
