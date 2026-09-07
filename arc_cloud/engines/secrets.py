"""Secret detection engine for ARC CLOUD (credentials, tokens, private keys)."""
import re
import time
from pathlib import Path
from typing import List, Optional, Pattern

from arc_cloud.core.config import ArcConfig
from arc_cloud.core.models import (
    EngineStatus,
    Finding,
    FindingCategory,
    FindingSeverity,
    ProjectProfile,
)
from arc_cloud.engines.base import BaseEngine, EngineResult

SECRET_PATTERNS: List[tuple[str, str, Pattern[str], FindingSeverity]] = [
    (
        "AWS Access Key ID",
        "ARC-SEC-001A",
        re.compile(r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}"),
        FindingSeverity.CRITICAL,
    ),
    (
        "GitHub Personal Access Token",
        "ARC-SEC-001B",
        re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,255}"),
        FindingSeverity.CRITICAL,
    ),
    (
        "Private Cryptographic Key",
        "ARC-SEC-001C",
        re.compile(r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP|PRIVATE) KEY"),
        FindingSeverity.CRITICAL,
    ),
    (
        "Hardcoded JWT Secret / Token",
        "ARC-SEC-001D",
        re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
        FindingSeverity.HIGH,
    ),
    (
        "Slack / Webhook Token",
        "ARC-SEC-001E",
        re.compile(r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*"),
        FindingSeverity.HIGH,
    ),
    (
        "Hardcoded Password or API Secret Assignment",
        "ARC-SEC-001F",
        re.compile(r"""(?i)(?:api_key|apikey|secret_key|client_secret|db_pass|password|auth_token)\s*[:=]\s*["']([^"'\s]{8,})["']"""),
        FindingSeverity.HIGH,
    ),
]


def _mask_secret(secret_str: str) -> str:
    """Masks secret string so raw credentials are never printed or exported."""
    if len(secret_str) <= 6:
        return "****"
    return secret_str[:3] + "..." + secret_str[-3:]


class SecretsEngine(BaseEngine):
    """Engine that detects exposed credentials, tokens, and private keys."""

    name = "secrets"
    version = "1.0.0"
    category = FindingCategory.SECRETS

    def is_available(self) -> bool:
        return True

    def analyze(
        self,
        project_root: Path,
        profile: ProjectProfile,
        config: Optional[ArcConfig] = None,
    ) -> EngineResult:
        start = time.perf_counter()
        findings: List[Finding] = []
        files_checked = 0

        # Scan all source files + config files
        candidate_files = set(profile.source_files + profile.config_files)

        for rel_path in candidate_files:
            abs_path = project_root / rel_path
            if not abs_path.is_file():
                continue

            # Skip binary files or lock files
            if abs_path.suffix.lower() in (".png", ".jpg", ".jpeg", ".lock", ".zip", ".tar", ".gz"):
                continue

            files_checked += 1
            try:
                content = abs_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            lines = content.splitlines()
            for idx, line in enumerate(lines, 1):
                # Ignore comment-only lines or test fixtures
                stripped = line.strip()
                if stripped.startswith(("#", "//", "/*", "*")):
                    continue

                for secret_name, rule_id, pattern, severity in SECRET_PATTERNS:
                    match = pattern.search(line)
                    if match:
                        matched_val = match.group(0)
                        # Filter out placeholders
                        if any(p in matched_val.lower() for p in ("dummy", "example", "placeholder", "your_", "todo", "xxx")):
                            continue

                        masked = _mask_secret(matched_val)
                        findings.append(
                            Finding(
                                rule_id=rule_id,
                                engine=self.name,
                                title=f"Exposed {secret_name}",
                                description=f"Potential {secret_name} detected in source code ({masked}).",
                                category=self.category,
                                severity=severity,
                                file_path=rel_path,
                                line=idx,
                                recommendation="Immediately remove credential, rotate it in the provider console, and load via environment variables or secret manager.",
                                confidence="HIGH",
                                estimated_fix_minutes=20,
                            )
                        )
                        break  # One secret per line

        elapsed_ms = (time.perf_counter() - start) * 1000.0

        return EngineResult(
            engine_name=self.name,
            status=EngineStatus.ANALYZED,
            findings=findings,
            metrics={"files_checked": files_checked, "secrets_found": len(findings)},
            execution_time_ms=elapsed_ms,
        )
