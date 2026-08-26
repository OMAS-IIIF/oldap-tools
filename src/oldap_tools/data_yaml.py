"""Versioned, project-neutral YAML/JSON documents for OLDAP instance data.

Version 1 models resource identity, class, property values, role permissions,
and optional media-ingest instructions. It distinguishes RDF references from
literal values and represents every property as a list, so API response
container conventions do not leak into the interchange format.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping
from urllib.parse import urlparse

import yaml


DATA_FORMAT_VERSION = 1
AUTO_IRI = "auto"
GENERATED_IRI_PREFIX = "resource_"
DATA_PERMISSIONS = frozenset(
    {
        "DATA_RESTRICTED",
        "DATA_VIEW",
        "DATA_EXTEND",
        "DATA_UPDATE",
        "DATA_DELETE",
        "DATA_PERMISSIONS",
    }
)
RESERVED_PROPERTIES = frozenset({"rdf:type", "oldap:attachedToRole"})
MEDIA_SOURCE_TYPES = frozenset({"file", "url", "iiif-image", "iiif-manifest"})
MEDIA_HANDLING_MODES = frozenset({"copy", "reference"})
KNOWN_INGEST_PROFILES = frozenset(
    {
        "preserve-original",
        "image-iiif",
        "audio-access",
        "video-access",
        "document-access",
        "document-iiif",
    }
)
# Only profiles backed by a complete, verified oldap-mediaserver workflow are
# enabled. Known future names remain reserved so their semantics cannot drift.
ENABLED_INGEST_PROFILES = frozenset({"image-iiif"})

_LOCAL_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9._-]*$")
_QNAME = re.compile(r"^[A-Za-z_][A-Za-z0-9._-]*:[^\s:][^\s]*$")
_ABSOLUTE_IRI = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:\S+$")
_LANGUAGE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")


class DataValidationError(ValueError):
    """Raised when an OLDAP data document is structurally or semantically invalid."""


class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that refuses silently overwritten mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise DataValidationError(f"Duplicate mapping key {key!r}.")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


LiteralScalar = str | int | float | bool


@dataclass(frozen=True)
class DataValue:
    """One explicit IRI reference or literal property value."""

    iri: str | None = None
    value: LiteralScalar | None = None
    language: str | None = None
    datatype: str | None = None


@dataclass(frozen=True)
class MediaSource:
    """One portable media source declaration.

    Exactly one location field is populated according to ``source_type``.
    """

    source_type: str
    path: str | None = None
    url: str | None = None
    info_url: str | None = None
    manifest_url: str | None = None


@dataclass(frozen=True)
class MediaInstruction:
    """Operational media handling attached to one RDF resource declaration."""

    source: MediaSource
    handling: str
    ingest_profile: str | None = None


@dataclass(frozen=True)
class DataResource:
    """One resource declaration in a data document."""

    iri: str
    resource_class: str
    properties: Mapping[str, tuple[DataValue, ...]]
    permissions: Mapping[str, str]
    media: MediaInstruction | None = None


@dataclass(frozen=True)
class DataDocument:
    """Validated version-1 data document independent of a live OLDAP project."""

    version: int
    project: str
    resources: tuple[DataResource, ...]
    source_path: Path | None = None

    @property
    def auto_iri_count(self) -> int:
        """Return the number of resources awaiting offline IRI preparation."""

        return sum(resource.iri == AUTO_IRI for resource in self.resources)


def require_prepared_document(document: DataDocument) -> None:
    """Reject unresolved auto identities before any live or media operation."""

    if document.auto_iri_count:
        raise DataValidationError(
            f"Document contains {document.auto_iri_count} unresolved iri: auto "
            "placeholder(s); run 'oldap-tools data prepare' first and import its output."
        )


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise DataValidationError(f"{path} must be a mapping with string keys.")
    return value


def _exact_keys(
    mapping: Mapping[str, Any],
    path: str,
    required: set[str],
    optional: frozenset[str] | set[str] = frozenset(),
) -> None:
    missing = required - mapping.keys()
    unknown = mapping.keys() - required - optional
    if missing:
        raise DataValidationError(f"{path} is missing: {', '.join(sorted(missing))}.")
    if unknown:
        raise DataValidationError(f"{path} has unknown keys: {', '.join(sorted(unknown))}.")


def _identifier(value: Any, path: str, *, local_allowed: bool) -> str:
    if not isinstance(value, str) or not value:
        raise DataValidationError(f"{path} must be a non-empty string identifier.")
    if _QNAME.fullmatch(value) or _ABSOLUTE_IRI.fullmatch(value):
        return value
    if local_allowed and _LOCAL_NAME.fullmatch(value):
        return value
    expected = (
        "a local name, QName, or absolute IRI"
        if local_allowed
        else "a QName or absolute IRI"
    )
    raise DataValidationError(f"{path} must be {expected}; received {value!r}.")


def _parse_value(raw: Any, path: str) -> DataValue:
    item = _mapping(raw, path)
    has_iri = "iri" in item
    has_value = "value" in item
    if has_iri == has_value:
        raise DataValidationError(f"{path} must contain exactly one of 'iri' and 'value'.")
    if has_iri:
        _exact_keys(item, path, {"iri"})
        return DataValue(iri=_identifier(item["iri"], f"{path}.iri", local_allowed=False))

    _exact_keys(item, path, {"value"}, {"language", "datatype"})
    value = item["value"]
    if value is None or not isinstance(value, (str, int, float, bool)):
        raise DataValidationError(f"{path}.value must be a non-null JSON scalar.")
    language = item.get("language")
    datatype = item.get("datatype")
    if language is not None and datatype is not None:
        raise DataValidationError(f"{path} cannot declare both language and datatype.")
    if language is not None:
        if not isinstance(value, str):
            raise DataValidationError(f"{path}.language is allowed only for string values.")
        if not isinstance(language, str) or not _LANGUAGE.fullmatch(language):
            raise DataValidationError(f"{path}.language is not a supported language tag.")
        language = language.lower()
    if datatype is not None:
        datatype = _identifier(datatype, f"{path}.datatype", local_allowed=False)
    return DataValue(value=value, language=language, datatype=datatype)


def _web_url(value: Any, path: str) -> str:
    """Validate a non-credential-bearing HTTP(S) URL."""

    if not isinstance(value, str) or not value:
        raise DataValidationError(f"{path} must be a non-empty HTTP(S) URL.")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise DataValidationError(f"{path} must be an absolute HTTP(S) URL.")
    if parsed.username is not None or parsed.password is not None:
        raise DataValidationError(f"{path} must not contain credentials.")
    return value


def _parse_media_source(raw: Any, path: str) -> MediaSource:
    """Parse one discriminated local, HTTP, or IIIF media source."""

    item = _mapping(raw, path)
    source_type = item.get("type")
    if source_type not in MEDIA_SOURCE_TYPES:
        allowed = ", ".join(sorted(MEDIA_SOURCE_TYPES))
        raise DataValidationError(f"{path}.type must be one of {allowed}.")

    location_key = {
        "file": "path",
        "url": "url",
        "iiif-image": "info_url",
        "iiif-manifest": "manifest_url",
    }[source_type]
    _exact_keys(item, path, {"type", location_key})
    location = item[location_key]
    if source_type == "file":
        if not isinstance(location, str) or not location.strip():
            raise DataValidationError(f"{path}.path must be a non-empty relative path.")
        if Path(location).is_absolute():
            raise DataValidationError(
                f"{path}.path must be relative to the YAML/JSON document."
            )
        return MediaSource(source_type=source_type, path=location)
    location = _web_url(location, f"{path}.{location_key}")
    if source_type == "iiif-image" and not urlparse(location).path.endswith("/info.json"):
        raise DataValidationError(f"{path}.info_url must identify an IIIF info.json.")
    return MediaSource(source_type=source_type, **{location_key: location})


def _parse_media(raw: Any, path: str) -> MediaInstruction:
    """Parse and cross-check one media workflow instruction."""

    item = _mapping(raw, path)
    _exact_keys(item, path, {"source", "handling"}, {"ingest_profile"})
    source = _parse_media_source(item["source"], f"{path}.source")
    handling = item["handling"]
    if handling not in MEDIA_HANDLING_MODES:
        allowed = ", ".join(sorted(MEDIA_HANDLING_MODES))
        raise DataValidationError(f"{path}.handling must be one of {allowed}.")
    profile = item.get("ingest_profile")

    if handling == "copy":
        if source.source_type != "file":
            raise DataValidationError(
                f"{path}: version 1 currently supports copy only from a local file."
            )
        if profile is None:
            raise DataValidationError(f"{path}.ingest_profile is required for copy.")
        if profile not in KNOWN_INGEST_PROFILES:
            allowed = ", ".join(sorted(KNOWN_INGEST_PROFILES))
            raise DataValidationError(
                f"{path}.ingest_profile is unknown; reserved names are {allowed}."
            )
        if profile not in ENABLED_INGEST_PROFILES:
            raise DataValidationError(
                f"{path}.ingest_profile {profile!r} is reserved but not implemented."
            )
    else:
        if source.source_type == "file":
            raise DataValidationError(
                f"{path}: a local file must use handling 'copy'."
            )
        if profile is not None:
            raise DataValidationError(
                f"{path}.ingest_profile must be omitted for handling 'reference'."
            )
    return MediaInstruction(source=source, handling=handling, ingest_profile=profile)


def _parse_resource(raw: Any, index: int) -> DataResource:
    path = f"data.resources[{index}]"
    item = _mapping(raw, path)
    _exact_keys(item, path, {"iri", "class", "properties"}, {"permissions", "media"})
    iri = _identifier(item["iri"], f"{path}.iri", local_allowed=True)
    resource_class = _identifier(item["class"], f"{path}.class", local_allowed=False)

    raw_properties = _mapping(item["properties"], f"{path}.properties")
    properties: dict[str, tuple[DataValue, ...]] = {}
    for property_iri, raw_values in raw_properties.items():
        _identifier(property_iri, f"{path}.properties key", local_allowed=False)
        if property_iri in RESERVED_PROPERTIES:
            raise DataValidationError(
                f"{path}.properties.{property_iri} is reserved; use "
                f"{'class' if property_iri == 'rdf:type' else 'permissions'} instead."
            )
        if not isinstance(raw_values, list) or not raw_values:
            raise DataValidationError(
                f"{path}.properties.{property_iri} must be a non-empty list."
            )
        properties[property_iri] = tuple(
            _parse_value(raw_value, f"{path}.properties.{property_iri}[{value_index}]")
            for value_index, raw_value in enumerate(raw_values)
        )

    raw_permissions = _mapping(item.get("permissions", {}), f"{path}.permissions")
    permissions: dict[str, str] = {}
    for role_iri, permission in raw_permissions.items():
        _identifier(role_iri, f"{path}.permissions role", local_allowed=False)
        if permission not in DATA_PERMISSIONS:
            allowed = ", ".join(sorted(DATA_PERMISSIONS))
            raise DataValidationError(
                f"{path}.permissions.{role_iri} must be one of {allowed}."
            )
        permissions[role_iri] = permission

    return DataResource(
        iri=iri,
        resource_class=resource_class,
        properties=properties,
        permissions=permissions,
        media=_parse_media(item["media"], f"{path}.media") if "media" in item else None,
    )


def loads_data_document(source: str) -> DataDocument:
    """Parse and validate a YAML or JSON OLDAP data document.

    Args:
        source: Complete UTF-8 YAML or JSON text.

    Returns:
        A normalized version-1 document.

    Raises:
        DataValidationError: If syntax, structure, or local semantics are invalid.
    """

    try:
        raw = yaml.load(source, Loader=_UniqueKeyLoader)
    except DataValidationError:
        raise
    except yaml.YAMLError as error:
        raise DataValidationError(f"Invalid YAML/JSON syntax: {error}") from error
    root = _mapping(raw, "document")
    _exact_keys(root, "document", {"data"})
    data = _mapping(root["data"], "data")
    _exact_keys(data, "data", {"version", "project", "resources"})
    if type(data["version"]) is not int or data["version"] != DATA_FORMAT_VERSION:
        raise DataValidationError(
            f"data.version must be the integer {DATA_FORMAT_VERSION}."
        )
    project = _identifier(data["project"], "data.project", local_allowed=True)
    if ":" in project or _ABSOLUTE_IRI.fullmatch(project):
        raise DataValidationError("data.project must be an OLDAP project shortname.")
    raw_resources = data["resources"]
    if not isinstance(raw_resources, list) or not raw_resources:
        raise DataValidationError("data.resources must be a non-empty list.")
    resources = tuple(
        _parse_resource(item, index) for index, item in enumerate(raw_resources)
    )
    # Repeated ``auto`` placeholders are intentionally allowed before the
    # explicit preparation phase assigns each resource a stable unique IRI.
    identities = [resource.iri for resource in resources if resource.iri != AUTO_IRI]
    duplicates = sorted({iri for iri in identities if identities.count(iri) > 1})
    if duplicates:
        raise DataValidationError(
            f"data.resources contains duplicate identities: {', '.join(duplicates)}."
        )
    return DataDocument(version=DATA_FORMAT_VERSION, project=project, resources=resources)


def load_data_document(path: Path) -> DataDocument:
    """Read and validate a UTF-8 YAML or JSON OLDAP data document.

    Args:
        path: Input file path.

    Returns:
        A normalized version-1 document.

    Raises:
        DataValidationError: If the file cannot be read or is invalid.
    """

    try:
        source = path.read_text(encoding="utf-8")
    except OSError as error:
        raise DataValidationError(f"Cannot read {path}: {error}") from error
    document = loads_data_document(source)
    return DataDocument(
        version=document.version,
        project=document.project,
        resources=document.resources,
        source_path=path.resolve(),
    )
