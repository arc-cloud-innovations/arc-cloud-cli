"""Automated test framework detection and execution engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import List, Optional


@dataclass
class TestResult:
    __test__ = False
    framework: str
    passed: int = 0
    failed: int = 0
    duration: float = 0.0
    success: bool = True
    output: str = ""
    errors: List[str] = field(default_factory=list)
    command_executed: str = ""

    @property
    def total(self) -> int:
        return self.passed + self.failed


class TestRunner:
    """Detects project test runner and executes targeted or suite tests safely."""
    __test__ = False

    def __init__(self, root_dir: Path, timeout_seconds: float = 60.0) -> None:
        self.root_dir = root_dir.resolve()
        self.timeout_seconds = timeout_seconds

    def detect_framework(self) -> Optional[str]:
        """Detects the primary testing framework of the project."""
        # Flutter
        if (self.root_dir / "pubspec.yaml").is_file():
            content = (self.root_dir / "pubspec.yaml").read_text(encoding="utf-8", errors="ignore")
            if "flutter_test:" in content or "flutter:" in content:
                if shutil.which("flutter"):
                    return "flutter"

        # Python
        if (self.root_dir / "pytest.ini").is_file() or (self.root_dir / "pyproject.toml").is_file():
            if shutil.which("pytest") or (self.root_dir / ".venv" / "bin" / "pytest").is_file():
                return "pytest"
            return "unittest"
        if any(self.root_dir.glob("test_*.py")) or (self.root_dir / "tests").is_dir():
            return "pytest" if (shutil.which("pytest") or (self.root_dir / ".venv" / "bin" / "pytest").is_file()) else "unittest"

        # Node / JS
        pkg_json = self.root_dir / "package.json"
        if pkg_json.is_file():
            try:
                import json
                data = json.loads(pkg_json.read_text(encoding="utf-8"))
                scripts = data.get("scripts", {})
                if "test" in scripts:
                    return "npm"
            except Exception:
                pass

        # Gradle / Android / Java
        if (self.root_dir / "gradlew").is_file() or (self.root_dir / "build.gradle").is_file():
            return "gradle"

        # Cargo (Rust)
        if (self.root_dir / "Cargo.toml").is_file() and shutil.which("cargo"):
            return "cargo"

        # Go
        if (self.root_dir / "go.mod").is_file() and shutil.which("go"):
            return "go"

        return None

    def run_tests(self, target_files: Optional[List[Path]] = None) -> TestResult:
        framework = self.detect_framework()
        if not framework:
            return TestResult(
                framework="none",
                success=True,
                output="No automated test framework detected for this project.",
            )

        cmd = self._build_command(framework, target_files)
        if not cmd:
            return TestResult(
                framework=framework,
                success=True,
                output=f"No runnable test command constructed for {framework}.",
            )

        start = time.time()
        try:
            res = subprocess.run(
                cmd,
                cwd=str(self.root_dir),
                shell=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            duration = round(time.time() - start, 2)
            stdout = res.stdout + "\n" + res.stderr
            passed, failed, errors = self._parse_output(framework, stdout, res.returncode)

            return TestResult(
                framework=framework,
                passed=passed,
                failed=failed,
                duration=duration,
                success=(res.returncode == 0 and failed == 0),
                output=stdout.strip(),
                errors=errors,
                command_executed=" ".join(cmd),
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                framework=framework,
                failed=1,
                duration=self.timeout_seconds,
                success=False,
                output="Test run timed out.",
                errors=["Test execution exceeded timeout limit."],
                command_executed=" ".join(cmd),
            )
        except Exception as e:
            return TestResult(
                framework=framework,
                failed=1,
                duration=round(time.time() - start, 2),
                success=False,
                output=str(e),
                errors=[f"Failed to execute tests: {e}"],
                command_executed=" ".join(cmd),
            )

    def _build_command(self, framework: str, target_files: Optional[List[Path]]) -> List[str]:
        if framework == "flutter":
            base = ["flutter", "test"]
            if target_files:
                base.extend([str(p.relative_to(self.root_dir)) if p.is_relative_to(self.root_dir) else str(p) for p in target_files])
            return base

        if framework == "pytest":
            # Prefer local virtualenv pytest if exists
            local_pytest = self.root_dir / ".venv" / "bin" / "pytest"
            exe = str(local_pytest) if local_pytest.is_file() else (shutil.which("pytest") or "pytest")
            cmd = [exe, "-q"]
            if target_files:
                cmd.extend([str(p) for p in target_files])
            return cmd

        if framework == "unittest":
            return ["python", "-m", "unittest", "discover"]

        if framework == "npm":
            return ["npm", "test", "--", "--watchAll=false"] if shutil.which("npm") else []

        if framework == "gradle":
            gradlew = self.root_dir / "gradlew"
            return [str(gradlew), "test"] if gradlew.is_file() else ["gradle", "test"]

        if framework == "cargo":
            return ["cargo", "test"]

        if framework == "go":
            return ["go", "test", "./..."]

        return []

    def _parse_output(self, framework: str, output: str, returncode: int) -> tuple[int, int, List[str]]:
        passed = 0
        failed = 0
        errors: List[str] = []

        if framework in ("pytest", "unittest"):
            # e.g. "15 passed, 2 failed in 0.5s" or "81 passed in 0.80s"
            p_match = re.search(r"(\d+)\s+passed", output)
            f_match = re.search(r"(\d+)\s+failed", output)
            if p_match:
                passed = int(p_match.group(1))
            if f_match:
                failed = int(f_match.group(1))
            if returncode != 0 and failed == 0 and passed == 0:
                failed = 1
                errors.append(output[-300:] if len(output) > 300 else output)

        elif framework == "flutter":
            # e.g. "00:02 +142: All tests passed!" or "00:03 +139 -3: Some tests failed."
            all_match = re.search(r"\+(\d+)(?:\s+-(\d+))?:", output)
            if all_match:
                passed = int(all_match.group(1))
                failed = int(all_match.group(2)) if all_match.group(2) else 0
            if "All tests passed" in output and failed == 0 and passed == 0:
                passed = 1
            elif returncode != 0 and failed == 0:
                failed = 1

        else:
            if returncode == 0:
                passed = 1
            else:
                failed = 1
                errors.append(output[-300:] if len(output) > 300 else output)

        return passed, failed, errors
