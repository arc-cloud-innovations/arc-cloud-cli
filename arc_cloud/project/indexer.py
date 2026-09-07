"""File Indexer for ARC CLOUD Software Engineering Health Platform."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set

from arc_cloud.utils.security import DEFAULT_IGNORED_DIRS, SecurityManager

SOURCE_EXTENSIONS = {
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx",
    ".dart", ".java", ".kt", ".kts", ".swift",
    ".cs", ".cpp", ".cc", ".cxx", ".c", ".h", ".hpp",
    ".go", ".rs", ".php", ".rb",
}

CONFIG_EXTENSIONS_OR_NAMES = {
    "package.json", "tsconfig.json", "pyproject.toml", "requirements.txt",
    "Pipfile", "pom.xml", "build.gradle", "settings.gradle", "pubspec.yaml",
    "Dockerfile", "docker-compose.yml", ".gitignore", ".arccloud.yml",
}


@dataclass
class IndexedFilesResult:
    root_path: Path
    all_files: List[str] = field(default_factory=list)
    source_files: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    dependency_files: List[str] = field(default_factory=list)
    total_files: int = 0
    total_lines: int = 0
    source_lines: int = 0
    test_lines: int = 0
    project_tree: Dict[str, List[str]] = field(default_factory=dict)
    ignored_directories: Set[str] = field(default_factory=set)
    warnings: List[str] = field(default_factory=list)


class FileIndexer:
    """Discovers project files, categorizes code/tests/configs, and calculates line counts."""

    def __init__(
        self,
        root_dir: Path,
        exclude_dirs: List[str] | None = None,
        max_files: int = 20_000,
        max_depth: int = 20,
        max_file_size: int = 10_000_000,
    ):
        self.root_dir = root_dir.resolve()
        self.max_files = max_files
        self.max_depth = max_depth
        self.max_file_size = max_file_size
        self.ignored_dirs = set(DEFAULT_IGNORED_DIRS)
        if exclude_dirs:
            self.ignored_dirs.update(exclude_dirs)
        self.security = SecurityManager(self.root_dir)

    def index(self) -> IndexedFilesResult:
        result = IndexedFilesResult(root_path=self.root_dir)

        if not self.root_dir.exists():
            raise FileNotFoundError(f"Directory not found: '{self.root_dir}'")
        if not self.root_dir.is_dir():
            raise NotADirectoryError(f"Path is not a directory: '{self.root_dir}'")

        gitignore_patterns = self._load_gitignore()
        visited_inodes: Set[int] = set()

        try:
            visited_inodes.add(self.root_dir.stat().st_ino)
        except (OSError, PermissionError) as exc:
            result.warnings.append(f"Permission error accessing root: {exc}")
            return result

        stack = [(self.root_dir, 0)]

        while stack:
            current_dir, current_depth = stack.pop()

            if current_depth > self.max_depth:
                rel = current_dir.relative_to(self.root_dir).as_posix()
                result.warnings.append(f"Max depth reached at '{rel}'. Subdirectories skipped.")
                continue

            try:
                with os.scandir(current_dir) as entries:
                    for entry in entries:
                        entry_path = Path(entry.path)

                        # Symlink safety
                        if entry.is_symlink():
                            if self.security.is_symlink_escape(entry_path):
                                result.warnings.append(f"Symlink escape skipped: '{entry.name}'")
                                continue

                        if entry.is_dir(follow_symlinks=False):
                            dir_name = entry.name
                            if dir_name in self.ignored_dirs or dir_name.startswith("."):
                                result.ignored_directories.add(dir_name)
                                continue

                            rel_dir = entry_path.relative_to(self.root_dir).as_posix()
                            if self._is_gitignored(rel_dir, gitignore_patterns, is_dir=True):
                                result.ignored_directories.add(dir_name)
                                continue

                            try:
                                ino = entry.stat(follow_symlinks=False).st_ino
                                if ino in visited_inodes:
                                    continue
                                visited_inodes.add(ino)
                            except (OSError, PermissionError):
                                pass

                            stack.append((entry_path, current_depth + 1))

                        elif entry.is_file(follow_symlinks=False):
                            if result.total_files >= self.max_files:
                                result.warnings.append(f"Maximum files limit ({self.max_files}) reached.")
                                break

                            rel_file = entry_path.relative_to(self.root_dir).as_posix()

                            if self._is_gitignored(rel_file, gitignore_patterns, is_dir=False):
                                continue

                            try:
                                size = entry.stat(follow_symlinks=False).st_size
                                if size > self.max_file_size:
                                    continue
                            except (OSError, PermissionError):
                                continue

                            result.all_files.append(rel_file)
                            result.total_files += 1

                            # Update directory tree
                            parent_rel = entry_path.parent.relative_to(self.root_dir).as_posix()
                            if parent_rel not in result.project_tree:
                                result.project_tree[parent_rel] = []
                            result.project_tree[parent_rel].append(entry.name)

                            # Categorization & Line Counting
                            ext = entry_path.suffix.lower()
                            name = entry_path.name.lower()
                            is_test = self._is_test_file(rel_file, name)
                            is_source = ext in SOURCE_EXTENSIONS and not is_test
                            is_config = name in CONFIG_EXTENSIONS_OR_NAMES or ext in (".json", ".yaml", ".yml", ".toml")
                            is_dep = name in ("package.json", "requirements.txt", "pyproject.toml", "pubspec.yaml", "pom.xml", "build.gradle", "Pipfile") or ext == ".csproj"

                            if is_test:
                                result.test_files.append(rel_file)
                            if is_source:
                                result.source_files.append(rel_file)
                            if is_config:
                                result.config_files.append(rel_file)
                            if is_dep:
                                result.dependency_files.append(rel_file)

                            lines = self._count_lines(entry_path)
                            result.total_lines += lines
                            if is_source:
                                result.source_lines += lines
                            elif is_test:
                                result.test_lines += lines

            except PermissionError as exc:
                rel = current_dir.relative_to(self.root_dir).as_posix()
                result.warnings.append(f"Permission denied accessing '{rel}': {exc}")
            except OSError as exc:
                rel = current_dir.relative_to(self.root_dir).as_posix()
                result.warnings.append(f"OS error accessing '{rel}': {exc}")

        return result

    def _is_test_file(self, rel_path: str, file_name: str) -> bool:
        """Determines if a file is a test specification or test suite."""
        parts = rel_path.lower().split("/")
        if any(p in ("test", "tests", "spec", "specs", "__tests__") for p in parts[:-1]):
            return True
        return (
            file_name.startswith("test_")
            or file_name.endswith("_test.py")
            or file_name.endswith(".test.js")
            or file_name.endswith(".test.ts")
            or file_name.endswith(".spec.js")
            or file_name.endswith(".spec.ts")
            or file_name.endswith("_test.dart")
            or file_name.endswith("test.java")
        )

    def _count_lines(self, file_path: Path) -> int:
        """Counts text lines safely without loading excessive bytes into memory."""
        try:
            with open(file_path, "rb") as f:
                lines = 0
                for line in f:
                    lines += 1
                return lines
        except Exception:
            return 0

    def _load_gitignore(self) -> List[str]:
        """Loads simple gitignore glob patterns if .gitignore exists."""
        patterns: List[str] = []
        gi = self.root_dir / ".gitignore"
        if gi.exists() and gi.is_file():
            try:
                for line in gi.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.append(line.rstrip("/"))
            except Exception:
                pass
        return patterns

    def _is_gitignored(self, rel_path: str, patterns: List[str], is_dir: bool = False) -> bool:
        """Glob-aware matching of gitignore patterns."""
        import fnmatch
        parts = rel_path.split("/")
        file_name = parts[-1]
        for pattern in patterns:
            pattern = pattern.rstrip("/")
            if pattern in parts:
                return True
            if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(rel_path, pattern):
                return True
            if any(fnmatch.fnmatch(part, pattern) for part in parts):
                return True
        return False
