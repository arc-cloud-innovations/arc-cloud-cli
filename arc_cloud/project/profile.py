"""ProjectProfile builder synthesizing FileIndexer and ProjectDetector results."""

from __future__ import annotations

from pathlib import Path

from arc_cloud.core.models import ProjectProfile
from arc_cloud.project.detector import ProjectDetector
from arc_cloud.project.indexer import FileIndexer
from arc_cloud.utils.security import SecurityManager


class ProjectProfileBuilder:
    """Constructs a normalized ProjectProfile for any software project."""

    @staticmethod
    def build(
        root_dir: Path | str,
        project_name: str | None = None,
        exclude_dirs: list[str] | None = None,
        max_files: int = 20_000,
        max_depth: int = 20,
    ) -> ProjectProfile:
        path = Path(root_dir).resolve()
        name = project_name or path.name

        indexer = FileIndexer(
            root_dir=path,
            exclude_dirs=exclude_dirs,
            max_files=max_files,
            max_depth=max_depth,
        )
        index_result = indexer.index()

        security = SecurityManager(path)
        detector = ProjectDetector(path, security)
        intel = detector.detect(
            all_files=index_result.all_files,
            relative_dirs=list(index_result.project_tree.keys()),
        )

        return ProjectProfile(
            project_name=name,
            root_path=str(path),
            languages=intel["languages"],
            primary_language=intel["primary_language"],
            frameworks=intel["frameworks"],
            package_managers=intel["package_managers"],
            build_systems=intel["build_systems"],
            project_type=intel["project_type"],
            source_files=index_result.source_files,
            test_files=index_result.test_files,
            config_files=index_result.config_files,
            dependency_files=index_result.dependency_files,
            file_count=index_result.total_files,
            line_count=index_result.total_lines,
            source_line_count=index_result.source_lines,
            test_line_count=index_result.test_lines,
            project_tree=index_result.project_tree,
        )
