"""End-to-end scanner and CLI tests."""

import json
import os
import tempfile
from pathlib import Path
import pytest
from typer.testing import CliRunner

from arc_cloud.blueprint.models import ProjectType
from arc_cloud.main import app
from arc_cloud.scanner.engine import ScannerEngine
from arc_cloud.utils.security import SecurityError, SecurityManager

FIXTURES_DIR = Path(__file__).parent / "fixtures"
runner = CliRunner()


def test_scan_flutter_fixture():
    engine = ScannerEngine()
    blueprint = engine.scan(FIXTURES_DIR / "flutter_project")

    assert blueprint.project.type == ProjectType.MOBILE
    assert any(l.name == "Dart" for l in blueprint.languages)
    assert any(f.name == "Flutter" for f in blueprint.frameworks)
    assert any(p.name.value == "Android" for p in blueprint.platforms)
    assert any(p.name.value == "iOS" for p in blueprint.platforms)
    assert len(blueprint.dependencies) > 0


def test_scan_react_fixture():
    engine = ScannerEngine()
    blueprint = engine.scan(FIXTURES_DIR / "react_project")

    assert blueprint.project.type == ProjectType.WEB
    assert any(l.name == "TypeScript" for l in blueprint.languages)
    assert any(f.name == "React" for f in blueprint.frameworks)
    assert len(blueprint.dependencies) > 0


def test_scan_nextjs_fixture():
    engine = ScannerEngine()
    blueprint = engine.scan(FIXTURES_DIR / "nextjs_project")

    assert blueprint.project.type == ProjectType.FULL_STACK
    assert any(f.name == "Next.js" for f in blueprint.frameworks)


def test_scan_fastapi_fixture():
    engine = ScannerEngine()
    blueprint = engine.scan(FIXTURES_DIR / "fastapi_project")

    assert blueprint.project.type == ProjectType.BACKEND
    assert any(l.name == "Python" for l in blueprint.languages)
    assert any(f.name == "FastAPI" for f in blueprint.frameworks)
    assert "Containerized (Docker)" in blueprint.architecture.patterns


def test_scan_django_fixture():
    engine = ScannerEngine()
    blueprint = engine.scan(FIXTURES_DIR / "django_project")

    assert blueprint.project.type == ProjectType.BACKEND
    assert any(f.name == "Django" for f in blueprint.frameworks)


def test_scan_node_fixture():
    engine = ScannerEngine()
    blueprint = engine.scan(FIXTURES_DIR / "node_project")

    assert blueprint.project.type == ProjectType.BACKEND
    assert any(f.name == "Node.js" for f in blueprint.frameworks)


def test_scan_spring_fixture():
    engine = ScannerEngine()
    blueprint = engine.scan(FIXTURES_DIR / "spring_project")

    assert blueprint.project.type == ProjectType.BACKEND
    assert any(f.name == "Spring Boot" for f in blueprint.frameworks)
    assert any(l.name == "Java" for l in blueprint.languages)


def test_scan_dotnet_fixture():
    engine = ScannerEngine()
    blueprint = engine.scan(FIXTURES_DIR / "dotnet_project")

    assert blueprint.project.type == ProjectType.BACKEND
    assert any(f.name == ".NET" for f in blueprint.frameworks)
    assert any(l.name == "C#" for l in blueprint.languages)


def test_scan_invalid_path():
    engine = ScannerEngine()
    with pytest.raises(FileNotFoundError):
        engine.scan("/path/that/does/not/exist_12345")


def test_scan_file_instead_of_directory():
    engine = ScannerEngine()
    file_path = FIXTURES_DIR / "flutter_project" / "pubspec.yaml"
    with pytest.raises(NotADirectoryError):
        engine.scan(file_path)


def test_scan_empty_directory():
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = ScannerEngine()
        blueprint = engine.scan(tmp_dir)
        assert blueprint.scanner.files_scanned == 0
        assert any("empty" in w.lower() for w in blueprint.warnings)


def test_security_sensitive_file_blocking():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        env_file = tmp_path / ".env"
        env_file.write_text("DATABASE_PASSWORD=secret123")

        security = SecurityManager(tmp_path)
        assert security.is_sensitive_file(env_file)
        with pytest.raises(SecurityError):
            security.safe_read_text(env_file)


def test_security_symlink_escape_blocking():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        external_dir = tempfile.mkdtemp()
        try:
            symlink_target = Path(external_dir) / "secret.txt"
            symlink_target.write_text("sensitive")

            link_path = tmp_path / "escape_link"
            os.symlink(symlink_target, link_path)

            security = SecurityManager(tmp_path)
            assert security.is_symlink_escape(link_path)
            with pytest.raises(SecurityError):
                security.safe_read_text(link_path)
        finally:
            import shutil
            shutil.rmtree(external_dir, ignore_errors=True)


def test_scan_limits_max_files():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        # Create 10 dummy files
        for i in range(10):
            (tmp_path / f"file_{i}.py").write_text("print(1)")

        engine = ScannerEngine(max_files=3)
        blueprint = engine.scan(tmp_path)
        assert blueprint.scanner.files_scanned <= 3
        assert any("Maximum file limit" in w for w in blueprint.warnings)


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ARC CLOUD CLI" in result.output
    assert "scan" in result.output


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "arc" in result.output
    assert "0.1.0" in result.output


def test_cli_scan_json():
    target = str(FIXTURES_DIR / "react_project")
    result = runner.invoke(app, ["scan", target, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["project"]["name"] == "react_project"
    assert data["schema_version"] == "1.0"


def test_cli_scan_output_file():
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_file = Path(tmp_dir) / "blueprint.json"
        target = str(FIXTURES_DIR / "fastapi_project")
        result = runner.invoke(app, ["scan", target, "-o", str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert data["project"]["name"] == "fastapi_project"
