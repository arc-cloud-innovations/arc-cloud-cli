"""Severity weights and utilities for ARC CLOUD scoring."""
from arc_cloud.core.models import FindingSeverity

SEVERITY_WEIGHTS = {
    FindingSeverity.CRITICAL: 10,
    FindingSeverity.HIGH: 5,
    FindingSeverity.MEDIUM: 2,
    FindingSeverity.LOW: 1,
    FindingSeverity.INFO: 0,
}

SEVERITY_DEDUCTIONS = {
    FindingSeverity.CRITICAL: 20.0,
    FindingSeverity.HIGH: 10.0,
    FindingSeverity.MEDIUM: 5.0,
    FindingSeverity.LOW: 1.0,
    FindingSeverity.INFO: 0.0,
}


def get_severity_weight(severity: FindingSeverity) -> int:
    """Return risk point weight for a severity level."""
    return SEVERITY_WEIGHTS.get(severity, 0)


def get_severity_deduction(severity: FindingSeverity) -> float:
    """Return score point deduction for a severity level."""
    return SEVERITY_DEDUCTIONS.get(severity, 0.0)
