"""Offline, text-preserving IRI preparation for OLDAP data documents.

Preparation replaces each resource-level ``iri: auto`` scalar with a stable
project-local UUID identifier. The output document then becomes the authority
for validation, import, links, resume, and media asset identity.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Callable
from uuid import UUID, uuid4

import yaml

from oldap_tools.data_yaml import (
    AUTO_IRI,
    GENERATED_IRI_PREFIX,
    DataValidationError,
    load_data_document,
    loads_data_document,
)


UuidFactory = Callable[[], UUID]


def _mapping_value(node: yaml.MappingNode, key: str) -> yaml.Node:
    """Return a named YAML mapping value or raise a format-aware error."""

    for key_node, value_node in node.value:
        if isinstance(key_node, yaml.ScalarNode) and key_node.value == key:
            return value_node
    raise DataValidationError(f"Prepared YAML syntax is missing mapping key {key!r}.")


def _resource_iri_nodes(source: str) -> list[yaml.ScalarNode]:
    """Locate only resource-level IRI scalar nodes, never nested link values."""

    try:
        root = yaml.compose(source)
    except yaml.YAMLError as error:
        raise DataValidationError(f"Invalid YAML/JSON syntax: {error}") from error
    if not isinstance(root, yaml.MappingNode):
        raise DataValidationError("document must be a mapping.")
    data = _mapping_value(root, "data")
    if not isinstance(data, yaml.MappingNode):
        raise DataValidationError("data must be a mapping.")
    resources = _mapping_value(data, "resources")
    if not isinstance(resources, yaml.SequenceNode):
        raise DataValidationError("data.resources must be a list.")

    result: list[yaml.ScalarNode] = []
    for resource in resources.value:
        if not isinstance(resource, yaml.MappingNode):
            raise DataValidationError("Every data.resources item must be a mapping.")
        iri = _mapping_value(resource, "iri")
        if not isinstance(iri, yaml.ScalarNode):
            raise DataValidationError("Every resource iri must be a scalar.")
        result.append(iri)
    return result


def _mint_local_iri(used: set[str], uuid_factory: UuidFactory) -> str:
    """Mint a UUID-based local name not already used in the document."""

    while True:
        candidate = f"{GENERATED_IRI_PREFIX}{uuid_factory().hex}"
        if candidate not in used:
            used.add(candidate)
            return candidate


def prepare_data_source(source: str, *, uuid_factory: UuidFactory = uuid4) -> str:
    """Replace every resource-level ``iri: auto`` while preserving source text.

    Args:
        source: Complete YAML or JSON source.
        uuid_factory: Injectable UUID generator used by deterministic tests.

    Returns:
        Source text with only the placeholder scalar spans replaced.

    Raises:
        DataValidationError: If the source is invalid or contains no placeholders.
    """

    document = loads_data_document(source)
    if document.auto_iri_count == 0:
        raise DataValidationError("The document contains no resource with iri: auto.")
    nodes = _resource_iri_nodes(source)
    auto_nodes = [node for node in nodes if node.value == AUTO_IRI]
    if len(auto_nodes) != document.auto_iri_count:
        raise DataValidationError("Could not locate every resource-level iri: auto scalar.")

    used = {resource.iri for resource in document.resources if resource.iri != AUTO_IRI}
    replacements: list[tuple[int, int, str]] = []
    json_document = source.lstrip().startswith(("{", "["))
    for node in auto_nodes:
        minted = _mint_local_iri(used, uuid_factory)
        replacement = json.dumps(minted) if json_document or node.style else minted
        replacements.append((node.start_mark.index, node.end_mark.index, replacement))

    prepared = source
    for start, end, replacement in reversed(replacements):
        prepared = prepared[:start] + replacement + prepared[end:]
    verified = loads_data_document(prepared)
    if verified.auto_iri_count != 0:
        raise DataValidationError("IRI preparation left unresolved auto placeholders.")
    return prepared


def prepare_data_file(
    inf: Path,
    out: Path,
    *,
    force: bool = False,
    uuid_factory: UuidFactory = uuid4,
) -> int:
    """Prepare one input file into a distinct, stable import document.

    Args:
        inf: Source YAML or JSON path.
        out: Destination path that becomes the import authority.
        force: Permit replacing an existing destination.
        uuid_factory: Injectable UUID generator used by deterministic tests.

    Returns:
        Number of generated resource IRIs.

    Raises:
        DataValidationError: If paths, syntax, or placeholders are invalid.
    """

    if inf.resolve() == out.resolve():
        raise DataValidationError("--out must differ from --inf; preparation is explicit.")
    if inf.resolve().parent != out.resolve().parent:
        raise DataValidationError(
            "--out must be in the same directory as --inf so relative media paths "
            "retain their meaning."
        )
    if out.exists() and not force:
        raise DataValidationError(f"Output already exists: {out}; use --force to replace it.")
    try:
        source = inf.read_text(encoding="utf-8")
    except OSError as error:
        raise DataValidationError(f"Cannot read {inf}: {error}") from error
    # Load with the normal path-aware validator before text transformation.
    document = load_data_document(inf)
    prepared = prepare_data_source(source, uuid_factory=uuid_factory)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=out.parent,
            prefix=f".{out.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(prepared)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, out)
        temporary_path = None
    except OSError as error:
        raise DataValidationError(f"Cannot write {out}: {error}") from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return document.auto_iri_count
