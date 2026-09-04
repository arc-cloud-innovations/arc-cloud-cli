"""Unit tests for dependency detection across supported ecosystems."""

from pathlib import Path
from arc_cloud.scanner.dependencies import DependencyDetector
from arc_cloud.utils.security import SecurityManager

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_flutter_dependencies():
    project_dir = FIXTURES_DIR / "flutter_project"
    security = SecurityManager(project_dir)
    detector = DependencyDetector(project_dir, security)

    deps = detector.detect(["pubspec.yaml", "lib/main.dart"])
    dep_names = {d.name: d for d in deps}

    assert "flutter" in dep_names
    assert "cupertino_icons" in dep_names
    assert "http" in dep_names
    assert "flutter_test" in dep_names

    assert dep_names["flutter_test"].type == "dev"
    assert dep_names["http"].type == "runtime"


def test_react_dependencies():
    project_dir = FIXTURES_DIR / "react_project"
    security = SecurityManager(project_dir)
    detector = DependencyDetector(project_dir, security)

    deps = detector.detect(["package.json", "src/App.tsx"])
    dep_names = {d.name: d for d in deps}

    assert "react" in dep_names
    assert "react-dom" in dep_names
    assert "typescript" in dep_names
    assert dep_names["typescript"].type == "dev"


def test_fastapi_dependencies():
    project_dir = FIXTURES_DIR / "fastapi_project"
    security = SecurityManager(project_dir)
    detector = DependencyDetector(project_dir, security)

    deps = detector.detect(["requirements.txt", "app/main.py"])
    dep_names = {d.name: d for d in deps}

    assert "fastapi" in dep_names
    assert dep_names["fastapi"].version == "==0.109.0"
    assert "uvicorn[standard]" in dep_names or "uvicorn" in dep_names
    assert "pydantic" in dep_names


def test_spring_dependencies():
    project_dir = FIXTURES_DIR / "spring_project"
    security = SecurityManager(project_dir)
    detector = DependencyDetector(project_dir, security)

    deps = detector.detect(["pom.xml"])
    dep_names = {d.name: d for d in deps}

    assert "org.springframework.boot:spring-boot-starter-web" in dep_names
    assert "org.springframework.boot:spring-boot-starter-test" in dep_names
    assert dep_names["org.springframework.boot:spring-boot-starter-test"].type == "test"


def test_dotnet_dependencies():
    project_dir = FIXTURES_DIR / "dotnet_project"
    security = SecurityManager(project_dir)
    detector = DependencyDetector(project_dir, security)

    deps = detector.detect(["SampleApp.csproj"])
    dep_names = {d.name: d for d in deps}

    assert "Microsoft.AspNetCore.OpenApi" in dep_names
    assert "Swashbuckle.AspNetCore" in dep_names
    assert dep_names["Microsoft.AspNetCore.OpenApi"].version == "8.0.2"
