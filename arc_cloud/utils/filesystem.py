"""Safe, sandboxed filesystem traversal for ARC CLOUD CLI."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set

from arc_cloud.utils.security import DEFAULT_IGNORED_DIRS, SecurityManager


@dataclass
class ScanWalkResult:
    """Results of walking a project directory tree."""
    root_path: Path
    files: List[Path] = field(default_factory=list)
    relative_files: List[str] = field(default_factory=list)
    directories: List[Path] = field(default_factory=list)
    relative_dirs: List[str] = field(default_factory=list)
    ignored_directories_encountered: Set[str] = field(default_factory=set)
    warnings: List[str] = field(default_factory=list)
    total_files_found: int = 0
    total_dirs_found: int = 0


class SafeProjectWalker:
    """Iterates through a project's directory tree under strict security and resource limits."""

    def __init__(
        self,
        root_dir: Path,
        max_files: int = 20_000,
        max_depth: int = 20,
        max_file_size: int = 10_000_000,  # 10 MB limit for any single file
        custom_ignored_dirs: Set[str] | None = None,
    ):
        self.root_dir = root_dir.resolve()
        self.max_files = max_files
        self.max_depth = max_depth
        self.max_file_size = max_file_size
        self.ignored_dirs = set(DEFAULT_IGNORED_DIRS)
        if custom_ignored_dirs:
            self.ignored_dirs.update(custom_ignored_dirs)
        self.security = SecurityManager(self.root_dir)

    def walk(self) -> ScanWalkResult:
        result = ScanWalkResult(root_path=self.root_dir)

        if not self.root_dir.exists():
            raise FileNotFoundError(f"Project directory '{self.root_dir}' does not exist.")

        if not self.root_dir.is_dir():
            raise NotADirectoryError(f"Target path '{self.root_dir}' is not a directory.")

        visited_inodes: Set[int] = set()

        try:
            root_stat = self.root_dir.stat()
            visited_inodes.add(root_stat.st_ino)
        except (OSError, PermissionError) as exc:
            result.warnings.append(f"Permission error accessing root directory: {exc}")
            return result

        # Stack contains (current_dir_path, current_depth)
        stack = [(self.root_dir, 0)]

        while stack:
            current_dir, current_depth = stack.pop()

            if current_depth > self.max_depth:
                rel = current_dir.relative_to(self.root_dir)
                result.warnings.append(
                    f"⚠ Maximum directory depth ({self.max_depth}) exceeded at '{rel}'. Subdirectories skipped."
                )
                continue

            try:
                with os.scandir(current_dir) as entries:
                    for entry in entries:
                        entry_path = Path(entry.path)

                        # Symlink safety check
                        if entry.is_symlink():
                            if self.security.is_symlink_escape(entry_path):
                                result.warnings.append(
                                    f"⚠ Symlink escape skipped: '{entry_path.name}' points outside project root."
                                )
                                continue

                        if entry.is_dir(follow_symlinks=False):
                            dir_name = entry.name
                            if dir_name in self.ignored_dirs or dir_name.startswith("."):
                                result.ignored_directories_encountered.add(dir_name)
                                continue

                            try:
                                dir_stat = entry.stat(follow_symlinks=False)
                                if dir_stat.st_ino in visited_inodes:
                                    # Prevent cyclic symlinks or hardlink loops
                                    continue
                                visited_inodes.add(dir_stat.st_ino)
                            except (OSError, PermissionError):
                                pass

                            rel_dir = entry_path.relative_to(self.root_dir).as_posix()
                            result.directories.append(entry_path)
                            result.relative_dirs.append(rel_dir)
                            result.total_dirs_found += 1

                            stack.append((entry_path, current_depth + 1))

                        elif entry.is_file(follow_symlinks=False):
                            if len(result.files) >= self.max_files:
                                if "⚠ File count limit reached" not in str(result.warnings):
                                    result.warnings.append(
                                        f"⚠ Maximum file limit ({self.max_files}) reached. Skipping remaining files."
                                    )
                                break

                            try:
                                size = entry.stat(follow_symlinks=False).st_size
                                if size > self.max_file_size:
                                    result.warnings.append(
                                        f"⚠ File '{entry.name}' exceeds maximum file size ({size} > {self.max_file_size} bytes). Skipped."
                                    )
                                    continue
                            except (OSError, PermissionError):
                                pass

                            rel_file = entry_path.relative_to(self.root_dir).as_posix()
                            result.files.append(entry_path)
                            result.relative_files.append(rel_file)
                            result.total_files_found += 1

            except PermissionError as exc:
                rel = current_dir.relative_to(self.root_dir)
                result.warnings.append(f"⚠ Permission denied accessing directory '{rel}': {exc}")
            except OSError as exc:
                rel = current_dir.relative_to(self.root_dir)
                result.warnings.append(f"⚠ OS error accessing '{rel}': {exc}")

        return result
