"""ChangeDetector turns raw file changes into structured ChangeSets and emits events."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from arc_cloud.changes.diff import ChangeDiffer
from arc_cloud.changes.impact import ImpactAnalyzer
from arc_cloud.changes.models import ChangeSet, ChangeType, FileChange
from arc_cloud.monitoring.event_bus import EventBus, EventType


class ChangeDetector:
    """Processes file change events, builds ChangeSets, and notifies the event bus."""

    def __init__(self, root_dir: Path, event_bus: Optional[EventBus] = None) -> None:
        self.root_dir = root_dir.resolve()
        self.event_bus = event_bus or EventBus()

    def process_changes(self, raw_changes: List[FileChange]) -> ChangeSet:
        change_set = ChangeSet()
        combined_diffs: List[str] = []

        # Detect potential renames (a deleted file whose hash matches an added file)
        deleted_by_hash = {c.old_hash: c for c in raw_changes if c.change_type == ChangeType.DELETED and c.old_hash}
        processed_deletions = set()

        for c in raw_changes:
            if c.change_type == ChangeType.ADDED and c.new_hash in deleted_by_hash:
                # Rename detected
                del_c = deleted_by_hash[c.new_hash]
                processed_deletions.add(del_c.path)
                change_set.files_renamed.append((del_c.path, c.path))
                c.change_type = ChangeType.RENAMED
                c.old_path = del_c.path
                self.event_bus.emit(
                    EventType.FILE_RENAMED,
                    message=f"Renamed: {del_c.path.name} -> {c.path.name}",
                    data={"old_path": str(del_c.path), "new_path": str(c.path)},
                )
            elif c.change_type == ChangeType.ADDED:
                change_set.files_added.append(c.path)
                self.event_bus.emit(
                    EventType.FILE_CREATED,
                    message=f"Created: {c.path.name}",
                    data={"path": str(c.path)},
                )
            elif c.change_type == ChangeType.MODIFIED:
                change_set.files_modified.append(c.path)
                self.event_bus.emit(
                    EventType.FILE_MODIFIED,
                    message=f"Modified: {c.path.name}",
                    data={"path": str(c.path)},
                )
            elif c.change_type == ChangeType.DELETED:
                if c.path not in processed_deletions:
                    change_set.files_deleted.append(c.path)
                    self.event_bus.emit(
                        EventType.FILE_DELETED,
                        message=f"Deleted: {c.path.name}",
                        data={"path": str(c.path)},
                    )

            change_set.changes.append(c)

            # Analyze impact per file
            if c.path.is_file():
                impact = ImpactAnalyzer.analyze_file(self.root_dir, c.path)
                change_set.affected_modules.extend(impact.affected_modules)
                change_set.affected_tests.extend(impact.affected_tests)
                if impact.is_dependency_manifest:
                    change_set.is_dependency_change = True
                    self.event_bus.emit(
                        EventType.DEPENDENCY_CHANGED,
                        message=f"Dependency manifest modified: {c.path.name}",
                        data={"file": str(c.path)},
                    )

        # Deduplicate modules and tests
        change_set.affected_modules = sorted(list(set(change_set.affected_modules)))
        change_set.affected_tests = sorted(list(set(change_set.affected_tests)))
        change_set.diff = "\n".join(combined_diffs)
        return change_set
