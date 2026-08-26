"""Validated single-file media ingest for OLDAP data documents.

The module keeps RDF metadata creation separate from binary transport while
making both operations part of one explicit CLI workflow. Media-server attach
mode is idempotent: an already attached, matching asset is verified rather
than uploaded again.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from typing import Any
from urllib.parse import quote

import requests

from oldap_tools.data_yaml import (
    DataDocument,
    DataResource,
    require_prepared_document,
)


_ASSET_ID = re.compile(r"^[A-Za-z0-9._~-]{1,128}$")


class MediaIngestError(ValueError):
    """Raised when media preflight, transport, or verification fails."""


@dataclass(frozen=True)
class MediaCopyPlan:
    """Fully resolved and integrity-checked local media copy operation."""

    project: str
    resource_iri: str
    asset_id: str
    source_path: Path
    original_name: str
    mime_type: str
    checksum: str
    ingest_profile: str
    storage_path: str = "catalogue"


@dataclass(frozen=True)
class MediaAttachResult:
    """Verified outcome of a media-server attachment."""

    resource_iri: str
    asset_id: str
    imported_now: bool
    protocol: str
    derivative_name: str
    iiif_info_url: str
    width: int | None = None
    height: int | None = None


def _scalar_property(resource: DataResource, property_iri: str) -> Any:
    """Return one scalar literal from a document property, if present."""

    values = resource.properties.get(property_iri)
    if values is None:
        return None
    if len(values) != 1 or values[0].iri is not None:
        raise MediaIngestError(
            f"Resource {resource.iri} property {property_iri} must contain "
            "exactly one literal for media ingest."
        )
    return values[0].value


def _sha256(path: Path) -> str:
    """Calculate a file SHA-256 without loading the asset into memory."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_media_copy(document: DataDocument, resource: DataResource) -> MediaCopyPlan:
    """Resolve and verify one local ``image-iiif`` media instruction.

    Args:
        document: Parsed document retaining the input file path.
        resource: Resource whose media instruction is to be prepared.

    Returns:
        A transport-ready copy plan.

    Raises:
        MediaIngestError: If the source or its RDF identity metadata disagrees.
    """

    media = resource.media
    if media is None or media.handling != "copy" or media.source.path is None:
        raise MediaIngestError(f"Resource {resource.iri} has no local copy instruction.")
    if document.source_path is None:
        raise MediaIngestError(
            "A media file can be resolved only when the document was loaded from a file."
        )
    source_path = (document.source_path.parent / media.source.path).resolve()
    if not source_path.is_file():
        raise MediaIngestError(f"Media source is not a regular file: {source_path}")

    resource_iri = resource.iri if ":" in resource.iri else f"{document.project}:{resource.iri}"
    asset_id = resource_iri.rsplit(":", 1)[-1]
    if not _ASSET_ID.fullmatch(asset_id):
        raise MediaIngestError(
            f"Resource {resource_iri} does not yield a safe media asset identifier."
        )

    original_name = _scalar_property(resource, "shared:originalName")
    mime_type = _scalar_property(resource, "shared:originalMimeType")
    expected_checksum = _scalar_property(resource, "shared:checksum")
    access_mode = _scalar_property(resource, "shared:mediaAccessMode")
    protocol = _scalar_property(resource, "shared:protocol")
    media_type = resource.properties.get("dcterms:type", ())
    media_type_iris = {value.iri for value in media_type if value.iri is not None}

    if original_name != source_path.name:
        raise MediaIngestError(
            f"Resource {resource.iri} shared:originalName is {original_name!r}, "
            f"but the source file is {source_path.name!r}."
        )
    if not isinstance(mime_type, str) or not mime_type.startswith("image/"):
        raise MediaIngestError(
            f"Resource {resource.iri} requires an image/* shared:originalMimeType."
        )
    if access_mode != "local" or protocol != "custom":
        raise MediaIngestError(
            f"Resource {resource.iri} must stage shared:mediaAccessMode=local and "
            "shared:protocol=custom before media attachment."
        )
    if "dcmitype:StillImage" not in media_type_iris and "dcmitype:Image" not in media_type_iris:
        raise MediaIngestError(
            f"Resource {resource.iri} profile image-iiif requires dcterms:type "
            "dcmitype:StillImage or dcmitype:Image."
        )

    actual_checksum = _sha256(source_path)
    if expected_checksum != actual_checksum:
        raise MediaIngestError(
            f"Resource {resource.iri} checksum mismatch: YAML has "
            f"{expected_checksum!r}, source is {actual_checksum}."
        )
    return MediaCopyPlan(
        project=document.project,
        resource_iri=resource_iri,
        asset_id=asset_id,
        source_path=source_path,
        original_name=source_path.name,
        mime_type=mime_type,
        checksum=actual_checksum,
        ingest_profile=media.ingest_profile or "",
    )


def prepare_document_media(document: DataDocument) -> tuple[MediaCopyPlan, ...]:
    """Prepare every copy instruction; reference instructions require no transfer."""

    require_prepared_document(document)
    return tuple(
        prepare_media_copy(document, resource)
        for resource in document.resources
        if resource.media is not None and resource.media.handling == "copy"
    )


def _request_json(
    method: str,
    url: str,
    *,
    token: str | None = None,
    timeout: int = 900,
    **kwargs: Any,
) -> dict[str, Any]:
    """Send one authenticated HTTP request and require a JSON object."""

    headers = dict(kwargs.pop("headers", {}))
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.request(
            method, url, headers=headers, timeout=timeout, **kwargs
        )
    except requests.RequestException as error:
        raise MediaIngestError(f"{method} {url} failed: {error}") from error
    if not response.ok:
        raise MediaIngestError(
            f"{method} {url} returned HTTP {response.status_code}: {response.text}"
        )
    try:
        payload = response.json()
    except ValueError as error:
        raise MediaIngestError(f"{method} {url} returned invalid JSON.") from error
    if not isinstance(payload, dict):
        raise MediaIngestError(f"{method} {url} returned a non-object JSON response.")
    return payload


def authenticate_media_user(api_base: str, user: str, password: str) -> str:
    """Obtain the OLDAP Bearer token accepted by oldap-mediaserver."""

    login = _request_json(
        "POST",
        f"{api_base.rstrip('/')}/admin/auth/{quote(user, safe='')}",
        json={"password": password},
        timeout=60,
    )
    token = login.get("accessToken") or login.get("token")
    if not isinstance(token, str) or not token:
        raise MediaIngestError("OLDAP authentication returned no access token.")
    return token


def _read_mediaobject(api_base: str, token: str, resource_iri: str) -> dict[str, Any]:
    """Read a MediaObject through OLDAP's capability-issuing endpoint."""

    return _request_json(
        "GET",
        f"{api_base.rstrip('/')}/data/mediaobject/iri/{quote(resource_iri, safe='')}",
        token=token,
        timeout=60,
    )


def _response_scalar(record: dict[str, Any], key: str) -> Any:
    value = record.get(key)
    if isinstance(value, list):
        if len(value) != 1:
            raise MediaIngestError(f"OLDAP returned multiple values for {key}.")
        return value[0]
    return value


def attach_media_copy(
    plan: MediaCopyPlan,
    *,
    api_base: str,
    media_base: str,
    token: str,
) -> MediaAttachResult:
    """Attach or idempotently verify one prepared image media asset."""

    before = _read_mediaobject(api_base, token, plan.resource_iri)
    existing_asset_id = _response_scalar(before, "shared:assetId")
    imported_now = False
    if existing_asset_id is None:
        with plan.source_path.open("rb") as source_handle:
            response = _request_json(
                "POST",
                f"{media_base.rstrip('/')}/upload",
                token=token,
                data={
                    "projectId": plan.project,
                    "path": plan.storage_path,
                    "identifier": plan.asset_id,
                    "targetFormat": "tiff",
                    "existingResourceIri": plan.resource_iri,
                },
                files={
                    "file": (plan.original_name, source_handle, plan.mime_type),
                },
            )
        if response.get("attachedToExistingResource") is not True:
            raise MediaIngestError("Media server did not confirm attachment to the resource.")
        imported_now = True
    elif existing_asset_id != plan.asset_id:
        raise MediaIngestError(
            f"Resource {plan.resource_iri} is already bound to unexpected asset "
            f"{existing_asset_id!r}."
        )

    record = _read_mediaobject(api_base, token, plan.resource_iri)
    expected = {
        "shared:assetId": plan.asset_id,
        "shared:originalName": plan.original_name,
        "shared:originalMimeType": plan.mime_type,
        "shared:checksum": plan.checksum,
        "shared:mediaAccessMode": "local",
        "shared:protocol": "iiif",
        "shared:derivativeName": "master.tif",
        "shared:path": f"{plan.project}/image/{plan.storage_path}",
    }
    mismatches = {
        key: {"expected": value, "actual": _response_scalar(record, key)}
        for key, value in expected.items()
        if _response_scalar(record, key) != value
    }
    if mismatches:
        raise MediaIngestError(f"OLDAP media verification failed: {mismatches!r}")

    server_url = _response_scalar(record, "shared:serverUrl")
    media_token = record.get("token")
    if not isinstance(server_url, str) or not isinstance(media_token, str):
        raise MediaIngestError("OLDAP returned no IIIF server URL or media capability.")
    service_id = f"{server_url.rstrip('/')}/{quote(plan.asset_id, safe='')}"
    info_url = f"{service_id}/info.json"
    info = _request_json("GET", info_url, params={"token": media_token}, timeout=60)
    if info.get("id") != service_id:
        raise MediaIngestError("IIIF info.json returned an unexpected service identifier.")
    return MediaAttachResult(
        resource_iri=plan.resource_iri,
        asset_id=plan.asset_id,
        imported_now=imported_now,
        protocol="iiif",
        derivative_name="master.tif",
        iiif_info_url=info_url,
        width=info.get("width") if isinstance(info.get("width"), int) else None,
        height=info.get("height") if isinstance(info.get("height"), int) else None,
    )


def run_media_attach(
    document: DataDocument,
    *,
    api_base: str,
    media_base: str,
    user: str,
    password: str,
    apply: bool,
) -> tuple[MediaCopyPlan, tuple[MediaAttachResult, ...]]:
    """Preflight or attach exactly one document-declared local media file."""

    plans = prepare_document_media(document)
    if len(document.resources) != 1 or len(plans) != 1:
        raise MediaIngestError(
            "data media-attach requires exactly one resource with one local copy instruction."
        )
    token = authenticate_media_user(api_base, user, password)
    # Reading proves that the target exists, is visible, and is a MediaObject.
    _read_mediaobject(api_base, token, plans[0].resource_iri)
    if not apply:
        return plans[0], ()
    return plans[0], (
        attach_media_copy(
            plans[0], api_base=api_base, media_base=media_base, token=token
        ),
    )
