"""Configuration loader and schema for .arccloud.yml."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field

DEFAULT_CONFIG_FILENAME = ".arccloud.yml"


class RuleConfig(BaseModel):
    enabled: bool = True
    threshold: Optional[int] = None
    severity: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)


class ScanConfig(BaseModel):
    exclude: List[str] = Field(
        default_factory=lambda: [
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
        ]
    )
    max_files: int = 20_000
    max_depth: int = 20
    max_file_size: int = 10_000_000


class OutputConfig(BaseModel):
    format: str = "terminal"  # terminal, json, sarif
    file: Optional[str] = None


class CodeQualityConfig(BaseModel):
    max_complexity: int = 10
    enabled: bool = True


class SecurityConfig(BaseModel):
    enabled: bool = False


class ReportingConfig(BaseModel):
    format: str = "terminal"


class ArcCloudConfig(BaseModel):
    """Normalized .arccloud.yml configuration model."""
    project_name: Optional[str] = None
    scan: ScanConfig = Field(default_factory=ScanConfig)
    rules: Dict[str, RuleConfig] = Field(
        default_factory=lambda: {
            "ARC001": RuleConfig(enabled=True, threshold=10)
        }
    )
    output: OutputConfig = Field(default_factory=OutputConfig)

    def __init__(
        self,
        code_quality: Optional[CodeQualityConfig] = None,
        security: Optional[SecurityConfig] = None,
        reporting: Optional[ReportingConfig] = None,
        **data: Any,
    ) -> None:
        super().__init__(**data)
        if code_quality:
            self.rules["ARC001"] = RuleConfig(
                enabled=code_quality.enabled,
                threshold=code_quality.max_complexity,
            )
        if reporting:
            self.output.format = reporting.format

    @property
    def code_quality(self) -> CodeQualityConfig:
        thresh = 10
        enab = True
        if "ARC001" in self.rules:
            if self.rules["ARC001"].threshold is not None:
                thresh = self.rules["ARC001"].threshold
            enab = self.rules["ARC001"].enabled
        return CodeQualityConfig(max_complexity=thresh, enabled=enab)

    @classmethod
    def load(cls, project_dir: Path | str, explicit_config: Optional[str | Path] = None) -> "ArcCloudConfig":
        """Loads configuration from explicit path or .arccloud.yml in project root."""
        root = Path(project_dir).resolve()
        config_path = Path(explicit_config).resolve() if explicit_config else (root / DEFAULT_CONFIG_FILENAME)

        if not config_path.exists() or not config_path.is_file():
            return cls(project_name=root.name)

        try:
            content = config_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content) or {}
            
            project_data = data.get("project", {})
            p_name = project_data.get("name") if isinstance(project_data, dict) else None

            scan_data = data.get("scan", {})
            rules_data = data.get("rules", {})
            output_data = data.get("output", {})

            parsed_rules: Dict[str, RuleConfig] = {}
            for r_id, r_spec in rules_data.items():
                if isinstance(r_spec, dict):
                    parsed_rules[r_id] = RuleConfig(**r_spec)

            return cls(
                project_name=p_name or root.name,
                scan=ScanConfig(**scan_data) if isinstance(scan_data, dict) else ScanConfig(),
                rules=parsed_rules or {"ARC001": RuleConfig(enabled=True, threshold=10)},
                output=OutputConfig(**output_data) if isinstance(output_data, dict) else OutputConfig(),
            )
        except Exception:
            return cls(project_name=root.name)

    @classmethod
    def generate_default_yaml(cls, project_name: str = "my-project") -> str:
        """Returns the default .arccloud.yml template."""
        return f"""# ARC CLOUD Project Configuration
project:
  name: {project_name}

scan:
  exclude:
    - .git
    - node_modules
    - .venv
    - venv
    - build
    - dist
    - .dart_tool
    - .gradle
    - target
    - __pycache__
  max_files: 20000
  max_depth: 20

rules:
  ARC001:
    enabled: true
    threshold: 10

output:
  format: terminal
"""


# Alias for backward and forward compatibility
ArcConfig = ArcCloudConfig
