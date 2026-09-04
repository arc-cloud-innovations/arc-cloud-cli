"""Unit tests for modular framework detection."""

from pathlib import Path
from arc_cloud.scanner.dependencies import DependencyDetector
from arc_cloud.scanner.frameworks import FrameworkRegistry, ScanContext
from arc_cloud.utils.security import SecurityManager

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _run_framework_detection(project_name: str):
    project_dir = FIXTURES_DIR / project_name
    security = SecurityManager(project_dir)

    rel_files = []
    rel_dirs = []
    for p in project_dir.rglob("*"):
        if p.is_file():
            rel_files.append(p.relative_to(project_dir).as_posix())
        elif p.is_dir():
            rel_dirs.append(p.relative_to(project_dir).as_posix())

    dep_detector = DependencyDetector(project_dir, security)
    dependencies = dep_detector.detect(rel_files)

    ctx = ScanContext(
        root_dir=project_dir,
        relative_files=rel_files,
        relative_dirs=rel_dirs,
        dependencies=dependencies,
        files_set=set(rel_files),
        security=security,
    )

    registry = FrameworkRegistry()
    return registry.detect_all(ctx)


def test_detect_flutter():
    frameworks = _run_framework_detection("flutter_project")
    names = {f.name for f in frameworks}
    assert "Flutter" in names


def test_detect_react():
    frameworks = _run_framework_detection("react_project")
    names = {f.name for f in frameworks}
    assert "React" in names


def test_detect_nextjs():
    frameworks = _run_framework_detection("nextjs_project")
    names = {f.name for f in frameworks}
    assert "Next.js" in names
    assert "React" in names


def test_detect_fastapi():
    frameworks = _run_framework_detection("fastapi_project")
    names = {f.name for f in frameworks}
    assert "FastAPI" in names


def test_detect_django():
    frameworks = _run_framework_detection("django_project")
    names = {f.name for f in frameworks}
    assert "Django" in names


def test_detect_node():
    frameworks = _run_framework_detection("node_project")
    names = {f.name for f in frameworks}
    assert "Node.js" in names


def test_detect_spring():
    frameworks = _run_framework_detection("spring_project")
    names = {f.name for f in frameworks}
    assert "Spring Boot" in names


def test_detect_dotnet():
    frameworks = _run_framework_detection("dotnet_project")
    names = {f.name for f in frameworks}
    assert ".NET" in names
