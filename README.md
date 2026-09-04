# ARC CLOUD CLI

[![CI Tests](https://github.com/ARC-CLOUD/arc-cloud-cli/actions/workflows/tests.yml/badge.svg)](https://github.com/ARC-CLOUD/arc-cloud-cli/actions/workflows/tests.yml)
[![PyPI version](https://img.shields.io/pypi/v/arc-cloud.svg)](https://pypi.org/project/arc-cloud/)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

> **ARC CLOUD CLI** is a local Software X-Ray tool that analyzes a software project and generates a structured Software Blueprint containing detected languages, frameworks, platforms, dependencies, configuration and project structure.

---

## Privacy & Security Guarantee

```text
ARC CLOUD CLI performs project scanning locally.
Your source code is not uploaded to ARC CLOUD during local scanning.
```

- **100% Offline & Local**: Scanning runs entirely on your local machine without sending your code to any cloud server or LLM API.
- **Zero Code Execution**: Manifests and code files are statically inspected. The scanner never executes project code or runs package managers (`npm install`, `pip install`, `flutter pub get`, `gradle`, `cargo`, etc.).
- **Secret Protection**: Files matching `.env`, `.env.*`, `credentials.json`, `id_rsa`, `*.key`, and secret patterns are never read, printed, or exported.
- **No AI / LLM Requirement**: Deterministic, rule-based static analysis engine.

---

## Installation

### Recommended: `pipx` (Globally Available)
Install once globally and run from any project directory:
```bash
pipx install arc-cloud
```

### Standard `pip`
```bash
pip install arc-cloud
```

### Development Installation
```bash
git clone https://github.com/ARC-CLOUD/arc-cloud-cli.git
cd arc-cloud-cli
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

---

## Usage

### 1. Scan Current Project Directory
Navigate to any project on your computer and run:
```bash
cd my-project
arc scan
```

### 2. Scan a Specific Project Path
```bash
arc scan ./my-project
arc scan /absolute/path/to/project
```

### 3. Output as Raw JSON
Stream the normalized Software Blueprint JSON directly to stdout for scripting or piping into `jq`:
```bash
arc scan --json
arc scan ./my-project --json | jq .project
```

### 4. Export Blueprint to File
```bash
arc scan --output blueprint.json
```

### 5. Check CLI Version & Help
```bash
arc --version
arc --help
```

---

## Supported Technologies

### Programming Languages
- **Dart** (`.dart`)
- **Python** (`.py`, `.pyi`, `.pyw`)
- **JavaScript** (`.js`, `.mjs`, `.cjs`, `.jsx`)
- **TypeScript** (`.ts`, `.mts`, `.cts`, `.tsx`)
- **Java** (`.java`)
- **Kotlin** (`.kt`, `.kts`)
- **Swift** (`.swift`)
- **C#** (`.cs`, `.csx`)
- **C++ / C** (`.cpp`, `.cc`, `.cxx`, `.hpp`, `.h`, `.c`)
- **Go** (`.go`)
- **Rust** (`.rs`)
- **PHP** (`.php`)
- **Ruby** (`.rb`)

### Frameworks & Ecosystems
- **Flutter**: `pubspec.yaml`, Flutter SDK dependencies, Dart files, Android/iOS directories.
- **React**: `package.json`, `react` dependencies, JSX/TSX components.
- **Next.js**: `package.json`, `next` dependencies, `next.config.*`, App/Pages router.
- **Node.js**: `package.json`, JavaScript/TypeScript server signals.
- **FastAPI**: `requirements.txt`, `pyproject.toml`, `fastapi` dependencies.
- **Django**: `requirements.txt`, `manage.py`, `django` dependencies.
- **Spring Boot**: `pom.xml`, `build.gradle`, Spring starter dependencies.
- **.NET**: `*.csproj`, `*.sln`, SDK indicators.

### Platforms Detected
- **Android**, **iOS**, **Web**, **Windows**, **macOS**, **Linux**

### Project Classifications
- **Mobile Application**, **Web Application**, **Backend**, **Full Stack**, **Desktop Application**, **Library**, **CLI Application**, **Unknown**

---

## CLI Commands Reference

| Command | Description |
| :--- | :--- |
| `arc scan [PATH]` | Perform static project analysis and generate Software Blueprint (defaults to current directory) |
| `arc --version` | Display the installed CLI version |
| `arc --help` | Display general help and command options |

Options for `arc scan`:
- `--json`, `-j`: Output the normalized Software Blueprint as raw JSON to stdout.
- `--output`, `-o <FILE>`: Save the normalized Software Blueprint JSON to a specified file.
- `--max-files <INT>`: Maximum number of files to inspect (default: 20,000).
- `--max-depth <INT>`: Maximum directory recursion depth (default: 20).

---

## Software Blueprint JSON Specification

The Software Blueprint uses schema version `1.0`:

```json
{
  "schema_version": "1.0",
  "scanner": {
    "name": "ARC CLOUD CLI",
    "version": "0.1.0",
    "timestamp": "2026-09-04T12:00:00Z",
    "duration_seconds": 0.04,
    "files_scanned": 128
  },
  "project": {
    "name": "my_project",
    "type": "Mobile Application",
    "root_path": "/path/to/my_project",
    "description": null
  },
  "languages": [
    {
      "name": "Dart",
      "files": 45,
      "percentage": 88.2
    }
  ],
  "frameworks": [
    {
      "name": "Flutter",
      "version": "3.19.0",
      "category": "Mobile",
      "confidence": 1.0
    }
  ],
  "platforms": [
    {
      "name": "Android",
      "source": "android/ directory"
    },
    {
      "name": "iOS",
      "source": "ios/ directory"
    }
  ],
  "dependencies": [
    {
      "name": "cupertino_icons",
      "version": "^1.0.6",
      "source": "pubspec.yaml",
      "type": "runtime"
    }
  ],
  "configuration_files": [
    {
      "path": "pubspec.yaml",
      "name": "pubspec.yaml",
      "type": "package"
    }
  ],
  "structure": {
    "areas": [
      {
        "name": "source",
        "paths": ["lib"]
      },
      {
        "name": "tests",
        "paths": ["test"]
      }
    ],
    "total_files": 128,
    "total_directories": 14,
    "ignored_directories": [".git", ".dart_tool"]
  },
  "architecture": {
    "patterns": ["Layered / Modular Architecture"],
    "details": {
      "test_suite_detected": true
    }
  },
  "warnings": []
}
```

---

## Development & Testing

Run all tests:
```bash
pytest -v
```

Run test coverage:
```bash
pytest --cov=arc_cloud --cov-report=term-missing
```

Build the distribution packages:
```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

---

## Release Process

### 1. TestPyPI Publishing
```bash
twine upload -r testpypi dist/*
```
Verify the TestPyPI package:
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ arc-cloud
arc --version
```

### 2. Production PyPI Publishing
When authorized by the project owner:
```bash
git tag v0.1.0
git push origin v0.1.0
```
GitHub Actions will run tests, build distribution wheels, and publish to production PyPI via PyPI Trusted Publishing.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
