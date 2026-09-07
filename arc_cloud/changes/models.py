"""Change data models for live monitoring and delta analysis."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
import uuid


class ChangeType(str, Enum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    RENAMED = "RENAMED"


@dataclass
class FileChange:
    path: Path
    change_type: ChangeType
    old_path: Optional[Path] = None
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def file_name(self) -> str:
        return self.path.name


@dataclass
class ImpactedScope:
    affected_modules: List[str] = field(default_factory=list)
    affected_functions: List[str] = field(default_factory=list)
    affected_tests: List[Path] = field(default_factory=list)
    is_dependency_manifest: bool = False
    is_config_file: bool = False


@dataclass
class ChangeSet:
    change_id: str = field(default_factory=lambda: f"chg-{uuid.uuid4().hex[:8]}")
    timestamp: datetime = field(default_factory=datetime.now)
    changes: List[FileChange] = field(default_factory=list)
    files_added: List[Path] = field(default_factory=list)
    files_modified: List[Path] = field(default_factory=list)
    files_deleted: List[Path] = field(default_factory=list)
    files_renamed: List[tuple[Path, Path]] = field(default_factory=list)
    diff: str = ""
    affected_modules: List[str] = field(default_factory=list)
    affected_functions: List[str] = field(default_factory=list)
    affected_tests: List[Path] = field(default_factory=list)
    is_dependency_change: bool = False

    def to_dict(self) -> Dict[str, object]:
        return {
            "change_id": self.change_id,
            "timestamp": self.timestamp.isoformat(),
            "files_added": [str(p) for p in self.files_added],
            "files_modified": [str(p) for p in self.files_modified],
            "files_deleted": [str(p) for p in self.files_deleted],
            "files_renamed": [(str(o), str(n)) for o, n in self.files_renamed],
            "affected_modules": self.affected_modules,
            "affected_tests": [str(t) for t in self.affected_tests],
            "is_dependency_change": self.is_dependency_change,
        }
