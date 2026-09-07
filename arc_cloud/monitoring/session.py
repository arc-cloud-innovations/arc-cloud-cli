"""Monitoring session telemetry and lifecycle tracking."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class MonitoringSession:
    project_name: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    files_monitored: int = 0
    changes_detected: int = 0
    scans_run: int = 0
    tests_run: int = 0
    successful_changes: int = 0
    failed_changes: int = 0
    security_alerts: int = 0
    regressions: int = 0
    start_health: float = 100.0
    current_health: float = 100.0
    unverified_changes: int = 0
    verification_status: str = "UNVERIFIED"

    @property
    def health_delta(self) -> float:
        return round(self.current_health - self.start_health, 1)

    @property
    def duration_seconds(self) -> float:
        end = self.end_time or datetime.now()
        return round((end - self.start_time).total_seconds(), 1)

    def close(self) -> None:
        self.end_time = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "files_monitored": self.files_monitored,
            "changes_detected": self.changes_detected,
            "scans_run": self.scans_run,
            "tests_run": self.tests_run,
            "successful_changes": self.successful_changes,
            "failed_changes": self.failed_changes,
            "security_alerts": self.security_alerts,
            "regressions": self.regressions,
            "start_health": self.start_health,
            "current_health": self.current_health,
            "health_delta": self.health_delta,
            "unverified_changes": self.unverified_changes,
            "final_status": self.verification_status,
        }
