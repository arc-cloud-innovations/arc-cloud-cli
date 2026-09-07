"""Project snapshot management for tracking baseline and state transitions."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from arc_cloud.core.models import HealthReport


@dataclass
class ProjectSnapshot:
    snapshot_id: str = field(default_factory=lambda: f"snap-{uuid.uuid4().hex[:8]}")
    timestamp: datetime = field(default_factory=datetime.now)
    project_name: str = ""
    health_score: float = 100.0
    letter_grade: str = "A"
    total_files: int = 0
    file_hashes: Dict[str, str] = field(default_factory=dict)
    finding_signatures: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d


class SnapshotManager:
    """Creates, stores, and compares lightweight project snapshots without saving secrets."""

    SNAPSHOT_DIR = ".arccloud/snapshots"

    @classmethod
    def get_snapshot_dir(cls, root_dir: Path) -> Path:
        p = root_dir / cls.SNAPSHOT_DIR
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def create_snapshot(cls, root_dir: Path, report: HealthReport) -> ProjectSnapshot:
        file_hashes: Dict[str, str] = {}
        # Collect hashes of all tracked files
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in {".git", ".venv", "venv", "node_modules", "build", "dist", ".arccloud", ".arc"}]
            root_path = Path(root)
            for f in files:
                fpath = root_path / f
                if fpath.suffix in {".tmp", ".swp", ".bak", ".log", ".DS_Store"}:
                    continue
                try:
                    rel = str(fpath.relative_to(root_dir))
                    hasher = hashlib.sha256()
                    with fpath.open("rb") as fp:
                        while chunk := fp.read(65536):
                            hasher.update(chunk)
                    file_hashes[rel] = hasher.hexdigest()
                except Exception:
                    continue

        signatures = [
            {
                "rule_id": f.rule_id,
                "file_path": str(f.file_path),
                "line": f.line,
                "severity": f.severity.value,
                "engine": getattr(f, "engine", "unknown"),
            }
            for f in report.findings
        ]

        snapshot = ProjectSnapshot(
            project_name=report.project_profile.name,
            health_score=report.health_score.overall_score,
            letter_grade=report.health_score.letter_grade,
            total_files=len(file_hashes),
            file_hashes=file_hashes,
            finding_signatures=signatures,
        )

        cls.save_snapshot(root_dir, snapshot)
        return snapshot

    @classmethod
    def save_snapshot(cls, root_dir: Path, snapshot: ProjectSnapshot) -> Path:
        sdir = cls.get_snapshot_dir(root_dir)
        snap_file = sdir / f"{snapshot.snapshot_id}.json"
        snap_file.write_text(json.dumps(snapshot.to_dict(), indent=2), encoding="utf-8")
        # Also maintain latest.json pointer
        latest_file = sdir / "latest.json"
        latest_file.write_text(json.dumps(snapshot.to_dict(), indent=2), encoding="utf-8")
        return snap_file

    @classmethod
    def load_latest_snapshot(cls, root_dir: Path) -> Optional[ProjectSnapshot]:
        latest_file = cls.get_snapshot_dir(root_dir) / "latest.json"
        if not latest_file.is_file():
            return None
        try:
            data = json.loads(latest_file.read_text(encoding="utf-8"))
            return ProjectSnapshot(
                snapshot_id=data.get("snapshot_id", ""),
                timestamp=datetime.fromisoformat(data["timestamp"]),
                project_name=data.get("project_name", ""),
                health_score=float(data.get("health_score", 100.0)),
                letter_grade=data.get("letter_grade", "A"),
                total_files=int(data.get("total_files", 0)),
                file_hashes=data.get("file_hashes", {}),
                finding_signatures=data.get("finding_signatures", []),
            )
        except Exception:
            return None
