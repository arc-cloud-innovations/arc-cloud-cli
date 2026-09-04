"""Security checks and boundaries for ARC CLOUD CLI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple

# Sensitive files whose content must NEVER be read or inspected
SENSITIVE_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".env.test",
    ".env.staging",
    "id_rsa",
    "id_rsa.pub",
    "id_ed25519",
    "id_ecdsa",
    ".netrc",
    "credentials.json",
    "service-account.json",
    "secret.key",
}

SENSITIVE_PREFIXES = (
    ".env.",
)

# Standard ignored directory names
DEFAULT_IGNORED_DIRS = {
    ".git",
    ".github",  # can contain workflows, but usually excluded from source scan or scanned selectively
    ".svn",
    ".hg",
    "node_modules",
    ".venv",
    "venv",
    "ENV",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".dart_tool",
    "build",
    "dist",
    "target",
    ".gradle",
    ".idea",
    ".vscode",
    ".next",
    ".nuxt",
    "out",
    "bin",
    "obj",
    ".turbo",
    ".cache",
}


class SecurityError(Exception):
    """Raised when a security constraint or boundary is violated."""
    pass


class SecurityManager:
    """Enforces sandboxing and security constraints for static scanning."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir.resolve()

    def is_safe_path(self, path: Path) -> bool:
        """Ensure the path resolves within the project root (prevents path traversal and symlink escapes)."""
        try:
            resolved = path.resolve()
            return self.root_dir in resolved.parents or resolved == self.root_dir
        except (OSError, RuntimeError, PermissionError):
            return False

    def is_sensitive_file(self, path: Path) -> bool:
        """Checks if a file might contain secrets or environment variables."""
        name = path.name.lower()
        if name in SENSITIVE_FILENAMES:
            return True
        for prefix in SENSITIVE_PREFIXES:
            if name.startswith(prefix):
                return True
        return False

    def is_symlink_escape(self, path: Path) -> bool:
        """Detects if a symlink points outside the project root."""
        if not path.is_symlink():
            return False
        try:
            target = path.resolve()
            return not (self.root_dir in target.parents or target == self.root_dir)
        except (OSError, RuntimeError, PermissionError):
            return True

    def safe_read_text(self, file_path: Path, max_bytes: int = 1_000_000) -> str:
        """Safely read manifest/config text content up to max_bytes, refusing sensitive files."""
        if self.is_sensitive_file(file_path):
            raise SecurityError(f"Access to sensitive file '{file_path.name}' is strictly blocked.")

        if not self.is_safe_path(file_path):
            raise SecurityError(f"Path traversal detected for file '{file_path}'.")

        if self.is_symlink_escape(file_path):
            raise SecurityError(f"Symlink escape detected for '{file_path}'.")

        try:
            size = file_path.stat().st_size
            if size > max_bytes:
                raise SecurityError(f"File '{file_path.name}' exceeds safe size limit ({size} > {max_bytes} bytes).")
            return file_path.read_text(encoding="utf-8", errors="replace")
        except UnicodeDecodeError:
            return file_path.read_text(encoding="latin-1", errors="replace")
        except PermissionError as exc:
            raise PermissionError(f"Permission denied reading '{file_path.name}': {exc}") from exc
