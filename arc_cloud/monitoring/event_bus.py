"""ARC CLOUD Live Event Bus."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class EventType(str, Enum):
    PROJECT_STARTED = "PROJECT_STARTED"
    INITIAL_SCAN_COMPLETED = "INITIAL_SCAN_COMPLETED"
    FILE_CREATED = "FILE_CREATED"
    FILE_MODIFIED = "FILE_MODIFIED"
    FILE_DELETED = "FILE_DELETED"
    FILE_RENAMED = "FILE_RENAMED"
    DEPENDENCY_CHANGED = "DEPENDENCY_CHANGED"
    SCAN_STARTED = "SCAN_STARTED"
    SCAN_COMPLETED = "SCAN_COMPLETED"
    PROBLEM_DETECTED = "PROBLEM_DETECTED"
    SECURITY_RISK_DETECTED = "SECURITY_RISK_DETECTED"
    TEST_STARTED = "TEST_STARTED"
    TEST_COMPLETED = "TEST_COMPLETED"
    REGRESSION_DETECTED = "REGRESSION_DETECTED"
    VERIFICATION_STARTED = "VERIFICATION_STARTED"
    VERIFICATION_PASSED = "VERIFICATION_PASSED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    VERIFICATION_INVALIDATED = "VERIFICATION_INVALIDATED"


@dataclass
class LiveEvent:
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "data": self.data,
        }


class EventBus:
    """Central event bus for monitoring pub/sub."""

    def __init__(self) -> None:
        self._subscribers: Dict[EventType, List[Callable[[LiveEvent], None]]] = {}
        self._all_subscribers: List[Callable[[LiveEvent], None]] = []
        self._history: List[LiveEvent] = []

    def subscribe(self, event_type: EventType, callback: Callable[[LiveEvent], None]) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def subscribe_all(self, callback: Callable[[LiveEvent], None]) -> None:
        self._all_subscribers.append(callback)

    def publish(self, event: LiveEvent) -> None:
        self._history.append(event)
        # Notify specific subscribers
        if event.event_type in self._subscribers:
            for cb in self._subscribers[event.event_type]:
                try:
                    cb(event)
                except Exception:
                    pass
        # Notify all-event subscribers
        for cb in self._all_subscribers:
            try:
                cb(event)
            except Exception:
                pass

    def emit(self, event_type: EventType, message: str = "", data: Optional[Dict[str, Any]] = None) -> LiveEvent:
        event = LiveEvent(event_type=event_type, message=message, data=data or {})
        self.publish(event)
        return event

    @property
    def history(self) -> List[LiveEvent]:
        return list(self._history)
