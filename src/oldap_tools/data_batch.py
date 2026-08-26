"""Resumable, create-only batch execution for instance-data documents.

The complete document is validated before the first write. Resources are then
processed sequentially and execution stops at the first failure, leaving a
clear, recoverable prefix. A later run verifies existing metadata against the
YAML and resumes with the first incomplete resource.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

import yaml

from oldaplib.src.objectfactory import ResourceInstanceFactory
from oldaplib.src.project import Project

from oldap_tools.connection import create_connection
from oldap_tools.data_import import (
    DataImportPreflight,
    DataImportPreflightError,
    create_data_resource,
    prepare_data_import,
)
from oldap_tools.data_yaml import DataDocument, require_prepared_document
from oldap_tools.media_ingest import (
    MediaIngestError,
    attach_media_copy,
    authenticate_media_user,
    prepare_document_media,
)


@dataclass(frozen=True)
class BatchResourceResult:
    """Outcome for one resource in document order."""

    iri: str
    metadata_status: str
    media_status: str
    error: str | None = None


@dataclass(frozen=True)
class BatchImportExecution:
    """Complete dry-run or apply result suitable for audit serialization."""

    project: str
    mode: str
    succeeded: bool
    resources: tuple[BatchResourceResult, ...]


def _pending_result(iri: str) -> BatchResourceResult:
    return BatchResourceResult(
        iri=iri,
        metadata_status="not_started",
        media_status="not_started",
    )


def _validate_batch_order(plan: DataImportPreflight) -> None:
    """Require newly referenced in-document resources before dependants."""

    by_iri = {resource.iri: (index, resource) for index, resource in enumerate(plan.resources)}
    for index, resource in enumerate(plan.resources):
        for reference in resource.reference_iris:
            target = by_iri.get(reference)
            if target is None:
                continue
            target_index, target_resource = target
            if target_resource.disposition == "create" and target_index >= index:
                raise DataImportPreflightError(
                    f"Batch order is unsafe: {resource.iri} references new resource "
                    f"{reference}, which must appear earlier in data.resources."
                )


def execute_batch_import(
    connection: Any,
    factory: ResourceInstanceFactory,
    document: DataDocument,
    *,
    apply: bool,
    api_base: str,
    media_base: str,
    user: str,
    password: str,
) -> tuple[DataImportPreflight, BatchImportExecution]:
    """Preflight a whole document and optionally process it sequentially.

    Raises during the whole-document preflight, before any write. During apply,
    operational failures are recorded on the affected resource and remaining
    resources are marked ``not_started``.
    """

    require_prepared_document(document)
    media_plans = prepare_document_media(document)
    media_by_iri = {plan.resource_iri: plan for plan in media_plans}
    plan = prepare_data_import(
        connection,
        factory,
        document,
        allow_existing=True,
    )
    _validate_batch_order(plan)

    if not apply:
        results = tuple(
            BatchResourceResult(
                iri=item.iri,
                metadata_status=(
                    "would_create" if item.disposition == "create" else "existing_verified"
                ),
                media_status=(
                    "would_attach"
                    if item.iri in media_by_iri
                    else "reference"
                    if resource.media is not None
                    else "not_declared"
                ),
            )
            for resource, item in zip(document.resources, plan.resources, strict=True)
        )
        return plan, BatchImportExecution(
            project=plan.project,
            mode="dry-run",
            succeeded=True,
            resources=results,
        )

    token = None
    if media_plans:
        # Authenticate before the first metadata write. Media service failures
        # after this point remain per-resource and resumable.
        token = authenticate_media_user(api_base, user, password)

    results: list[BatchResourceResult] = []
    stopped = False
    for resource, item in zip(document.resources, plan.resources, strict=True):
        if stopped:
            results.append(_pending_result(item.iri))
            continue

        metadata_status = "existing_verified"
        if item.disposition == "create":
            try:
                create_data_resource(connection, factory, document, resource)
                metadata_status = "created"
            except Exception as error:
                results.append(
                    BatchResourceResult(
                        iri=item.iri,
                        metadata_status="failed",
                        media_status="not_started",
                        error=str(error),
                    )
                )
                stopped = True
                continue

        if resource.media is None:
            results.append(
                BatchResourceResult(item.iri, metadata_status, "not_declared")
            )
            continue
        if resource.media.handling == "reference":
            results.append(BatchResourceResult(item.iri, metadata_status, "reference"))
            continue

        media_plan = media_by_iri[item.iri]
        try:
            if token is None:  # Defensive invariant; media plans authenticated above.
                raise MediaIngestError("Media authentication is unavailable.")
            media_result = attach_media_copy(
                media_plan,
                api_base=api_base,
                media_base=media_base,
                token=token,
            )
            media_status = "attached" if media_result.imported_now else "existing_verified"
            results.append(BatchResourceResult(item.iri, metadata_status, media_status))
        except Exception as error:
            results.append(
                BatchResourceResult(
                    iri=item.iri,
                    metadata_status=metadata_status,
                    media_status="failed",
                    error=str(error),
                )
            )
            stopped = True

    return plan, BatchImportExecution(
        project=plan.project,
        mode="apply",
        succeeded=not stopped,
        resources=tuple(results),
    )


def run_batch_import(
    *,
    graphdb_base: str,
    repo: str,
    user: str,
    password: str,
    document: DataDocument,
    apply: bool,
    api_base: str,
    media_base: str,
    graphdb_user: str | None = None,
    graphdb_password: str | None = None,
) -> tuple[DataImportPreflight, BatchImportExecution]:
    """Connect once and execute a resumable batch import."""

    connection = create_connection(
        graphdb_base=graphdb_base,
        repo=repo,
        user=user,
        password=password,
        graphdb_user=graphdb_user,
        graphdb_password=graphdb_password,
        context_name="DEFAULT",
    )
    project = Project.read(connection, document.project, ignore_cache=True)
    factory = ResourceInstanceFactory(con=connection, project=project)
    return execute_batch_import(
        connection,
        factory,
        document,
        apply=apply,
        api_base=api_base,
        media_base=media_base,
        user=user,
        password=password,
    )


def write_batch_report(path: Path, execution: BatchImportExecution) -> None:
    """Write an audit report as JSON or YAML using the filename suffix."""

    payload = {
        "batch_import": {
            "project": execution.project,
            "mode": execution.mode,
            "succeeded": execution.succeeded,
            "resources": [asdict(resource) for resource in execution.resources],
        }
    }
    suffix = path.suffix.lower()
    if suffix == ".json":
        content = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    elif suffix in {".yaml", ".yml"}:
        content = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    else:
        raise ValueError("Batch report must use a .json, .yaml, or .yml suffix.")
    try:
        path.write_text(content, encoding="utf-8")
    except OSError as error:
        raise ValueError(f"Cannot write batch report {path}: {error}") from error
