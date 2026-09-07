"""Tests for FileIndexer and project intelligence."""
from pathlib import Path
import tempfile
import pytest

from arc_cloud.project.indexer import FileIndexer


def test_file_indexer_basic() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Create files
        (root / "main.py").write_text("def main():\n    print('hello')\n", encoding="utf-8")
        (root / "test_main.py").write_text("def test_main():\n    assert True\n", encoding="utf-8")
        (root / "config.json").write_text("{\"key\": \"value\"}\n", encoding="utf-8")
        (root / "requirements.txt").write_text("requests==2.28.1\n", encoding="utf-8")

        indexer = FileIndexer(root_dir=root)
        result = indexer.index()

        assert "main.py" in result.all_files
        assert "main.py" in result.source_files
        assert "test_main.py" in result.test_files
        assert "config.json" in result.config_files
        assert "requirements.txt" in result.dependency_files

        assert result.total_files == 4
        assert result.total_lines > 0
        assert result.source_lines > 0


def test_file_indexer_ignores_vendor_and_gitignore() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Ignored by default
        node_modules = root / "node_modules" / "pkg"
        node_modules.mkdir(parents=True)
        (node_modules / "index.js").write_text("console.log('hi');\n", encoding="utf-8")

        # Ignored by gitignore
        (root / ".gitignore").write_text("ignored_folder/\n*.secret\n", encoding="utf-8")
        ignored_dir = root / "ignored_folder"
        ignored_dir.mkdir()
        (ignored_dir / "secret.py").write_text("secret = 1\n", encoding="utf-8")
        (root / "app.secret").write_text("token\n", encoding="utf-8")

        # Regular file
        (root / "app.py").write_text("x = 1\n", encoding="utf-8")

        indexer = FileIndexer(root_dir=root)
        result = indexer.index()

        assert "app.py" in result.all_files
        assert not any("node_modules" in p for p in result.all_files)
        assert not any("ignored_folder" in p for p in result.all_files)
        assert not any("app.secret" in p for p in result.all_files)
