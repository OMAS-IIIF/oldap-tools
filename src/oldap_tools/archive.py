"""Thin CLI integration for the canonical :mod:`oldaplib` archive workflow.

Archive YAML parsing, validation, project resolution, preflight, and create-only
apply live exclusively in ``oldaplib``.  This module owns only CLI connection
construction and keeps the former import names available during migration.
"""

from pathlib import Path

from oldaplib.src.archive_import import (
    ArchiveImportError,
    ArchiveImportPlan,
    ArchiveUnitSpec,
    apply_archive_import,
    prepare_archive_import,
    resolve_archive_document,
)
from oldaplib.src.archive_yaml import (
    ARCHIVE_LEVELS,
    ArchiveDocument,
    archive_schema_path,
    dump_archive_yaml,
    dumps_archive_yaml,
    load_archive_yaml,
    loads_archive_yaml,
)
from oldaplib.src.objectfactory import ResourceInstanceFactory
from oldaplib.src.project import Project

from oldap_tools.connection import create_connection


# Compatibility name for callers that imported the former flattened type.
# The canonical document is intentionally nested and project-neutral.
ArchiveDefinition = ArchiveDocument


def read_archive_yaml(
    inf: Path,
    project_shortname: object | None = None,
    schema: Path | None = None,
) -> ArchiveDocument:
    """Compatibility adapter for the former file-only parser.

    ``project_shortname`` is accepted so existing callers continue to work, but
    project resolution now belongs to :func:`prepare_archive_import`.
    """

    del project_shortname
    return load_archive_yaml(inf, schema=schema)


def load_archive(
    *,
    graphdb_base: str,
    repo: str,
    user: str,
    password: str,
    project_id: str,
    inf: Path,
    dry_run: bool = True,
    graphdb_user: str | None = None,
    graphdb_password: str | None = None,
) -> ArchiveImportPlan:
    """Connect to OLDAP, preflight a YAML document, and optionally apply it.

    The authenticated user's identity and normal OLDAP permissions are used for
    every read and write.  Dry-run remains the default.
    """

    connection = create_connection(
        graphdb_base=graphdb_base,
        repo=repo,
        user=user,
        password=password,
        graphdb_user=graphdb_user,
        graphdb_password=graphdb_password,
        context_name="DEFAULT",
    )
    project = Project.read(connection, project_id, ignore_cache=True)
    document = load_archive_yaml(inf)
    factory = ResourceInstanceFactory(con=connection, project=project)
    plan = prepare_archive_import(
        factory,
        project_id,
        document,
        project_shortname=project.projectShortName,
    )
    if not dry_run:
        apply_archive_import(factory, plan)
    return plan


__all__ = [
    "ARCHIVE_LEVELS",
    "ArchiveDefinition",
    "ArchiveDocument",
    "ArchiveImportError",
    "ArchiveImportPlan",
    "ArchiveUnitSpec",
    "apply_archive_import",
    "archive_schema_path",
    "dump_archive_yaml",
    "dumps_archive_yaml",
    "load_archive",
    "load_archive_yaml",
    "loads_archive_yaml",
    "prepare_archive_import",
    "read_archive_yaml",
    "resolve_archive_document",
]
