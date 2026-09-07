"""High-performance debounced filesystem watcher."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import threading
import time
from typing import Callable, Dict, List, Optional, Set, Tuple

from arc_cloud.changes.models import ChangeType, FileChange
from arc_cloud.project.indexer import FileIndexer

IGNORED_DIRECTORIES = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "build",
    "dist",
    ".dart_tool",
    ".gradle",
    "target",
    "__pycache__",
    "coverage",
    ".cache",
    ".arc",
    ".arccloud",
    ".idea",
    ".vscode",
}

IGNORED_EXTENSIONS = {
    ".tmp",
    ".swp",
    ".bak",
    ".pyc",
    ".zip",
    ".tar",
    ".gz",
    ".whl",
    ".log",
    ".DS_Store",
}


def compute_file_hash(path: Path) -> str:
    try:
        hasher = hashlib.sha256()
        with path.open("rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""


class FileWatcher:
    """Monitors project directory for file creations, modifications, and deletions with debouncing."""

    def __init__(
        self,
        root_dir: Path,
        on_changes: Callable[[List[FileChange]], None],
        debounce_seconds: float = 0.5,
        poll_interval: float = 0.25,
    ) -> None:
        self.root_dir = root_dir.resolve()
        self.on_changes = on_changes
        self.debounce_seconds = debounce_seconds
        self.poll_interval = poll_interval

        # State: path -> (mtime_ns, size, hash)
        self._file_state: Dict[Path, Tuple[int, int, str]] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Debounce buffer
        self._pending_changes: Dict[Path, FileChange] = {}
        self._last_event_time: float = 0.0
        self._lock = threading.Lock()

        # Load gitignore patterns if any
        self._indexer = FileIndexer(root_dir=self.root_dir)

    def _is_ignored(self, path: Path) -> bool:
        # Check parent parts against IGNORED_DIRECTORIES
        for part in path.parts:
            if part in IGNORED_DIRECTORIES:
                return True
        if path.suffix in IGNORED_EXTENSIONS or path.name.startswith(".#") or path.name.endswith("~"):
            return True
        return False

    def scan_snapshot(self) -> Dict[Path, Tuple[int, int, str]]:
        """Walks the directory and records current (mtime_ns, size, hash) for all valid files."""
        current: Dict[Path, Tuple[int, int, str]] = {}
        for root, dirs, files in os.walk(self.root_dir):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRECTORIES]
            root_path = Path(root)
            for f in files:
                fpath = root_path / f
                if self._is_ignored(fpath):
                    continue
                try:
                    stat = fpath.stat()
                    # We compute hash lazily or use size/mtime for rapid checks
                    current[fpath] = (stat.st_mtime_ns, stat.st_size, "")
                except (OSError, PermissionError):
                    continue
        return current

    def start(self) -> None:
        """Initializes state and starts watcher thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            # Build initial baseline state
            initial = self.scan_snapshot()
            for p, (mtime, size, _) in initial.items():
                # Compute hash on startup for tracked files
                h = compute_file_hash(p)
                self._file_state[p] = (mtime, size, h)

            self._thread = threading.Thread(target=self._watch_loop, daemon=True, name="ArcFileWatcher")
            self._thread.start()

    def stop(self) -> None:
        """Stops the watcher thread."""
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _watch_loop(self) -> None:
        while self._running:
            time.sleep(self.poll_interval)
            try:
                self._poll_once()
                self._check_debounce()
            except Exception:
                pass

    def _poll_once(self) -> None:
        curr_snapshot = self.scan_snapshot()
        detected_events: List[FileChange] = []

        with self._lock:
            # Check for deletions
            old_paths = set(self._file_state.keys())
            curr_paths = set(curr_snapshot.keys())

            deleted = old_paths - curr_paths
            for p in deleted:
                _, _, old_hash = self._file_state[p]
                del self._file_state[p]
                detected_events.append(
                    FileChange(
                        path=p,
                        change_type=ChangeType.DELETED,
                        old_hash=old_hash,
                    )
                )

            # Check for additions and modifications
            for p, (curr_mtime, curr_size, _) in curr_snapshot.items():
                if p not in self._file_state:
                    # New file
                    new_hash = compute_file_hash(p)
                    self._file_state[p] = (curr_mtime, curr_size, new_hash)
                    detected_events.append(
                        FileChange(
                            path=p,
                            change_type=ChangeType.ADDED,
                            new_hash=new_hash,
                        )
                    )
                else:
                    prev_mtime, prev_size, prev_hash = self._file_state[p]
                    if curr_mtime != prev_mtime or curr_size != prev_size:
                        # Potential modification, verify with hash
                        new_hash = compute_file_hash(p)
                        if new_hash != prev_hash:
                            self._file_state[p] = (curr_mtime, curr_size, new_hash)
                            detected_events.append(
                                FileChange(
                                    path=p,
                                    change_type=ChangeType.MODIFIED,
                                    old_hash=prev_hash,
                                    new_hash=new_hash,
                                )
                            )
                        else:
                            # Just touched timestamp without content change
                            self._file_state[p] = (curr_mtime, curr_size, prev_hash)

            # Queue detected events into debounce buffer
            if detected_events:
                for evt in detected_events:
                    self._pending_changes[evt.path] = evt
                self._last_event_time = time.time()

    def _check_debounce(self) -> None:
        batch_to_fire: List[FileChange] = []
        with self._lock:
            if not self._pending_changes:
                return
            if time.time() - self._last_event_time >= self.debounce_seconds:
                batch_to_fire = list(self._pending_changes.values())
                self._pending_changes.clear()

        if batch_to_fire:
            self.on_changes(batch_to_fire)
