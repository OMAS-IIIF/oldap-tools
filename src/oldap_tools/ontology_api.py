"""Load ontology YAML through existing OLDAP API operations.

Local preparation and remote read-only planning precede all writes. Each write
is an independent API transaction; the progress log identifies completed steps
and the first failure. There is no client-side transaction or silent GraphDB
fallback. The direct CLI remains available for administrative-only features.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from graphlib import TopologicalSorter, CycleError
import json
from pathlib import Path
import re
from typing import Any, Callable
from zipfile import ZipFile, ZIP_DEFLATED

import yaml
from rdflib import Dataset
from rdflib.exceptions import ParserError
from oldaplib.src.enums.editor import Editor
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName

from oldap_tools.api_client import ApiError, ApiOperation, OldapApiClient, api_path
from oldap_tools.lucene_api import plan_connector
from oldap_tools.list_api import plan_list, read_list_specs, read_api_lists
from oldap_tools.ontology import PROP_KEY_MAP, _as_datatype, _as_langstring, _read_yaml


_LANG_FIELDS = {"label", "comment", "name", "description"}
_SET_FIELDS = {"superclass", "languageIn", "inSet", "proposedResourceClass",
               "proposedDatatypePropertyClass", "proposedObjectPropertyClass"}


@dataclass
class OntologyApiPlan:
    """Ordered mutations plus pre-import state needed for an API backup.

    ``model_trig`` is populated only when a backup will be written. List YAML
    contains every current project taxonomy, not just those named in the input.
    """

    project: str
    operations: list[ApiOperation]
    project_before: dict | None
    model_before: dict | None
    list_yaml: dict[str, bytes] = field(default_factory=dict)
    model_trig: bytes | None = None
    connector_before: dict | None = None


def _language_values(value: Any) -> list[str] | None:
    """Normalize all CLI language forms to the API's replacement-list format."""
    langstring = _as_langstring(value)
    return [f"{text}@{lang.name.lower()}" for lang, text in langstring.items()] if langstring else None


def _property_payload(spec: dict, project: str, list_ids: set[str]) -> dict:
    """Translate YAML property keys to the API write contract (``class``).

    GET responses use ``toClass``; writes use ``class``. Explicit nulls are
    retained, and unsupported node-kind changes fail before remote mutations.
    """
    result = {}
    for key, value in spec.items():
        if key == "iri":
            continue
        if key == "node_kind":
            raise ValueError("The current OLDAP API does not support node_kind writes; use --transport direct.")
        target = "class" if key == "to_class" else PROP_KEY_MAP.get(key, key)
        if key == "to_class" and isinstance(value, str) and value.startswith("list:"):
            list_id = value.split(":", 1)[1]
            if list_id not in list_ids:
                raise ValueError(f'Unknown list reference "{value}".')
            value = f"{project}:{list_id}Node"
        if key == "datatype" and value is not None:
            value = _as_datatype(value).value
        if key == "editor" and value is not None:
            value = Editor(value).value
        if key in _LANG_FIELDS:
            value = _language_values(value)
        if key == "in" and value == []:
            raise ValueError("The current API cannot represent an empty 'in' constraint.")
        if key == "in":
            # YAML resolves bare ISO dates to Python date objects; the REST
            # contract expects lexical values interpreted using the datatype.
            value = [item.isoformat() if isinstance(item, (date, datetime)) else item for item in value]
            if any(item is None or not isinstance(item, (str, int, float, bool)) for item in value):
                raise ValueError("Values in an 'in' constraint must be scalar literals or IRI strings.")
        result[target] = value
    return result


def _equal(key: str, desired: Any, current: Any) -> bool:
    """Compare API snapshots without rewriting unordered language/set values."""
    if key == "editor":
        # YAML accepts enum names and DASH aliases; compare the same canonical
        # identifiers returned by the API, while keeping explicit null distinct.
        return (Editor(desired).value if desired is not None else None) == (
            Editor(current).value if current is not None else None
        )
    if key in _LANG_FIELDS | _SET_FIELDS:
        # The API serializes inSet literals as strings even for numeric types.
        def canonical(values):
            return {str(item).lower() if isinstance(item, bool) else str(item) for item in (values or [])}
        return canonical(desired) == canonical(current)
    return desired == current


def _changes(desired: dict, current: dict) -> dict:
    """Return only explicitly requested changes; omission preserves attributes."""
    changes = {}
    for key, value in desired.items():
        previous = current.get("toClass" if key == "class" else key)
        if key == "superclass" and "oldap:Thing" in (previous or []) and "oldap:Thing" not in (value or []):
            # ResourceClass adds this system base implicitly on construction.
            # Preserve it rather than proposing a removal on every YAML import.
            value = [*value, "oldap:Thing"]
        if _equal(key, value, previous):
            continue
        if key == "superclass" and value == []:
            value = {"del": previous} if previous else None
        elif key in _SET_FIELDS and value == []:
            value = None
        changes[key] = value
    return changes


def _index(items: Any, key: str, description: str) -> dict[str, dict]:
    """Validate API collection identities instead of treating malformed data as empty."""
    if not isinstance(items, list):
        raise ValueError(f"API returned an invalid {description} collection.")
    result = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get(key), str) or item[key] in result:
            raise ValueError(f"API returned an invalid or duplicate {description} identity.")
        result[item[key]] = item
    return result


def _require_property_type(payload: dict, iri: str) -> None:
    """Reject incomplete new definitions before any planned mutation runs."""
    if bool(payload.get("class")) == bool(payload.get("datatype")):
        raise ValueError(f"New property {iri} requires exactly one of datatype or to_class.")


def prepare_api_ontology(inf: Path) -> tuple[dict, dict]:
    """Validate input and all referenced list files locally before authentication."""
    ontology = _read_yaml(inf)
    project = ontology["project"]["shortname"]
    Xsd_NCName(project, validate=True)
    lists = read_list_specs(inf.parent, ontology.get("lists") or {})
    for list_id in lists:
        Xsd_NCName(list_id, validate=True)
    for iri, spec in (ontology.get("standalone_properties") or {}).items():
        Xsd_QName(iri, validate=True)
        _property_payload(spec, project, set(lists))
    for iri, spec in (ontology.get("classes") or {}).items():
        Xsd_QName(iri, validate=True)
        seen = set()
        for prop in spec.get("properties", []):
            prop_iri = prop.get("iri")
            if not prop_iri or prop_iri in seen:
                raise ValueError(f"Class {iri} has a missing or duplicate property IRI.")
            Xsd_QName(prop_iri, validate=True)
            seen.add(prop_iri)
            _property_payload(prop, project, set(lists))
    return ontology, lists


def plan_ontology_api(client: OldapApiClient, ontology: dict, lists: dict, *, remove_unused: bool = False, connector_mode: str = "skip") -> OntologyApiPlan:
    """Read remote state and plan a complete incremental import without writes.

    New classes are created in superclass order before their properties, allowing
    property references between classes regardless of YAML declaration order. Omitted
    standalone properties/classes are never deleted. With remove_unused, only
    omitted properties of explicitly supplied class property sets are candidates.
    """
    project_spec = ontology["project"]
    project = project_spec["shortname"]
    root = api_path("admin", "datamodel", project)
    project_path = api_path("admin", "project", project)
    current_project = client.get_json(project_path, missing_ok=True)
    operations: list[ApiOperation] = []
    if current_project is None:
        missing = [key for key in ("iri", "namespace", "start") if not project_spec.get(key)]
        if missing:
            raise ValueError(f"New project {project} requires {', '.join(missing)}.")
        payload = {"projectIri": project_spec["iri"], "namespaceIri": project_spec["namespace"]}
        for key in ("label", "comment"):
            if project_spec.get(key) is not None:
                payload[key] = _language_values(project_spec[key])
        operations.append(ApiOperation("PUT", project_path, payload))
        # Existing project creation ignores projectStart without projectEnd.
        # The existing modification endpoint correctly sets the requested date.
        operations.append(ApiOperation("POST", project_path, {"projectStart": str(project_spec["start"])}))
        current_model = None
    else:
        if not isinstance(current_project, dict) or current_project.get("projectShortName") != project:
            raise ValueError("API project response does not match the requested project.")
        for yaml_key, api_key in (("iri", "projectIri"), ("namespace", "namespaceIri")):
            if yaml_key in project_spec and project_spec[yaml_key] != current_project.get(api_key):
                raise ValueError(f"Project {yaml_key} differs from the API target; refusing to load into a different project.")
        current_model = client.get_json(root, missing_ok=True)
    if current_model is None:
        operations.append(ApiOperation("PUT", root))
    elif not isinstance(current_model, dict) or current_model.get("project") != project:
        raise ValueError("API datamodel response does not match the requested project.")
    model = current_model or {"resources": [], "annotationProperties": [], "externalOntologies": []}
    classes = _index(model.get("resources"), "iri", "resource")
    standalone = _index(model.get("annotationProperties"), "iri", "standalone property")
    external = _index(model.get("externalOntologies"), "prefix", "external ontology")

    current_lists: dict[str, dict] = {}
    list_yaml: dict[str, bytes] = {}
    if current_project is not None:
        list_yaml = read_api_lists(client, project, current_project["namespaceIri"])
        current_lists = {list_id: yaml.safe_load(raw)[list_id] for list_id, raw in list_yaml.items()}
    for list_id, spec in lists.items():
        operations.extend(plan_list(project, list_id, spec, current_lists.get(list_id)))

    for prefix, spec in (ontology.get("external_ontologies") or {}).items():
        Xsd_NCName(prefix, validate=True)
        payload = {"namespaceIri": spec["namespace"]}
        for key in ("label", "comment"):
            if key in spec:
                payload[key] = _language_values(spec[key])
        for old, new in (("resource_classes", "proposedResourceClass"),
                         ("datatype_properties", "proposedDatatypePropertyClass"),
                         ("object_properties", "proposedObjectPropertyClass")):
            if new in spec or old in spec:
                payload[new] = spec.get(new, spec.get(old))
        previous = external.get(prefix)
        if previous is not None:
            if previous.get("namespaceIri") != spec["namespace"]:
                raise ValueError(f"Changing namespace of existing external ontology {prefix} is not supported.")
            payload = _changes(payload, previous)
        if payload:
            operations.append(ApiOperation("POST" if previous is not None else "PUT",
                                           api_path("admin", "datamodel", project, "extonto", prefix), payload))

    wanted_classes = ontology.get("classes") or {}
    # Constructors enforce OLDAP system inheritance. Keep superclass assignment
    # in creation and sort local dependencies; properties follow all identities.
    dependencies = {iri: {parent for parent in spec.get("superclass", []) if parent in wanted_classes}
                    for iri, spec in wanted_classes.items()}
    try:
        class_order = list(TopologicalSorter(dependencies).static_order())
    except CycleError as error:
        raise ValueError("Ontology superclass definitions contain a cycle.") from error
    for iri in class_order:
        spec = wanted_classes[iri]
        if iri not in classes:
            payload = {key: _language_values(spec[key]) if key in _LANG_FIELDS else spec[key]
                       for key in ("label", "comment", "closed", "superclass") if key in spec and spec[key] is not None}
            operations.append(ApiOperation("PUT", api_path("admin", "datamodel", project, iri), payload))

    for iri, spec in (ontology.get("standalone_properties") or {}).items():
        payload = _property_payload(spec, project, set(lists))
        previous = standalone.get(iri)
        if previous is None:
            _require_property_type(payload, iri)
        else:
            payload = _changes(payload, previous)
        if payload:
            operations.append(ApiOperation("POST" if previous is not None else "PUT",
                                           api_path("admin", "datamodel", project, "property", iri), payload))

    removals = []
    for iri, spec in wanted_classes.items():
        previous = classes.get(iri)
        attributes = {key: _language_values(spec[key]) if key in _LANG_FIELDS else spec[key]
                      for key in ("label", "comment", "closed", "superclass") if key in spec}
        if previous is None:
            attributes = {}
        else:
            attributes = _changes(attributes, previous)
        if attributes.get("closed", False) is None:
            raise ValueError("The existing API cannot remove a class's closed attribute; use true or false.")
        if attributes:
            operations.append(ApiOperation("POST", api_path("admin", "datamodel", project, iri), attributes))
        old_properties = _index(previous.get("properties") if previous else [], "iri", "class property")
        wanted = set()
        for prop in spec.get("properties", []):
            prop_iri = prop["iri"]
            wanted.add(prop_iri)
            payload = _property_payload(prop, project, set(lists))
            old_prop = old_properties.get(prop_iri)
            if old_prop is None:
                _require_property_type(payload, prop_iri)
            else:
                payload = _changes(payload, old_prop)
            if payload:
                operations.append(ApiOperation("POST" if old_prop is not None else "PUT",
                                               api_path("admin", "datamodel", project, iri, prop_iri), payload))
        if remove_unused and "properties" in spec:
            for prop_iri, old_prop in old_properties.items():
                if prop_iri not in wanted:
                    # Never garbage-collect another project's or standalone definitions.
                    if prop_iri in standalone or old_prop.get("projectid") != project:
                        continue
                    removals.append(ApiOperation("DELETE", api_path("admin", "datamodel", project, iri, prop_iri), remove_unused=True))
    operations.extend(removals)
    connector_operation, connector_before = plan_connector(client, ontology, current_project, connector_mode)
    if connector_operation is not None:
        operations.append(connector_operation)
    for operation in operations:
        try:
            json.dumps(operation.payload, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{operation.path}: payload cannot be represented as JSON: {error}") from error
    return OntologyApiPlan(project, operations, current_project, current_model, list_yaml, connector_before=connector_before)


def write_api_backup(client: OldapApiClient, plan: OntologyApiPlan, out: Path) -> None:
    """Write a new ZIP snapshot before mutations; never overwrite a prior backup.

    The archive contains project/datamodel JSON, API-exported model TriG and
    all taxonomy YAML. It is an inspection/recovery snapshot, not a raw GraphDB
    backup accepted by ``project load``. Download/parse failures prevent apply.
    """
    if out.suffix.lower() != ".zip":
        raise ValueError("API backups require a .zip filename (direct backups use .trig.gz).")
    if plan.model_before is not None:
        plan.model_trig = client.get_bytes(api_path("admin", "datamodel", plan.project, "download"))
        try:
            Dataset().parse(data=plan.model_trig, format="trig")
        except (SyntaxError, ParserError, ValueError) as error:
            # RDFLib BadSyntax has no standard SyntaxError message, which also
            # breaks Typer/Rich traceback rendering. Report the backup boundary
            # explicitly and keep the original parser failure as the cause.
            line = getattr(error, "lines", None)
            location = f" at line {line + 1}" if isinstance(line, int) else ""
            raise ValueError(
                f"API model export contains invalid TriG{location}. "
                "Backup validation failed; no import operations were executed. "
                "Fix the server export before retrying."
            ) from error
    out = out.expanduser()
    # Exclusive create protects previous backups, including same-second invocations.
    with out.open("xb") as handle:
        try:
            with ZipFile(handle, "w", compression=ZIP_DEFLATED) as archive:
                archive.writestr("manifest.json", json.dumps({"format": "oldap-tools-api-snapshot", "version": 1,
                    "project": plan.project, "created": datetime.now().astimezone().isoformat(),
                    "includesInstanceData": False, "rawGraphBackup": False}, indent=2))
                if plan.connector_before is not None:
                    archive.writestr("lucene.json", json.dumps(plan.connector_before, ensure_ascii=False, indent=2))
                archive.writestr("project.json", json.dumps(plan.project_before, ensure_ascii=False, indent=2))
                archive.writestr("datamodel.json", json.dumps(plan.model_before, ensure_ascii=False, indent=2))
                if plan.model_trig is not None:
                    archive.writestr("model.trig", plan.model_trig)
                for list_id, raw in plan.list_yaml.items():
                    archive.writestr(f"lists/{list_id}.yaml", raw)
        except Exception:
            out.unlink(missing_ok=True)
            raise


def apply_ontology_plan(client: OldapApiClient, plan: OntologyApiPlan, emit: Callable[[str], None]) -> tuple[int, int]:
    """Execute once in order; preserve explicit in-use refusals, stop on other errors.

    Returns the number of successful and refused-removal operations. A server
    error is never assumed to mean 'in use' based on status alone.
    """
    completed = skipped = 0
    for index, operation in enumerate(plan.operations, 1):
        label = f"[{index}/{len(plan.operations)}] {operation.method} {operation.path}"
        try:
            client.apply(operation)
        except ApiError as error:
            if operation.remove_unused and error.status == 500 and re.fullmatch(r'Cannot update: resource "[^"]+" is in use', error.detail):
                skipped += 1
                emit(f"KEEP {label}: server reports class in use.")
                continue
            raise ApiError(f"Import stopped after {completed} successful operation(s), {skipped} preserved removal(s). "
                           f"Failed {label}. {error} Earlier successful operations remain committed.",
                           status=error.status, detail=error.detail) from error
        completed += 1
        emit(f"OK {label}")
    return completed, skipped


def load_ontology_api(*, api_base: str, user: str, password: str, inf: Path,
                      remove_unused: bool = False, dry_run: bool = False, connector_mode: str = "skip",
                      backup: bool = True, backup_out: Path | None = None,
                      emit: Callable[[str], None] = print) -> OntologyApiPlan:
    """Validate, authenticate, plan, back up and incrementally load ontology YAML.

    Dry-run authenticates and reads live state but makes no model/list writes
    and creates no backup. API credentials/repository selection belong to the
    configured server; no GraphDB address or password is consumed by this path.
    """
    inf = inf.expanduser().resolve()
    ontology, lists = prepare_api_ontology(inf)
    if backup_out is not None and backup_out.suffix.lower() != ".zip":
        raise ValueError("API backups require a .zip filename.")
    with OldapApiClient(api_base) as client:
        client.login(user, password)
        plan = plan_ontology_api(client, ontology, lists, remove_unused=remove_unused, connector_mode=connector_mode)
        emit(f"Planned {len(plan.operations)} API operation(s) for {plan.project}.")
        if dry_run:
            for operation in plan.operations:
                emit(f"{operation.method} {operation.path} " + json.dumps(operation.payload, ensure_ascii=False))
            return plan
        if not plan.operations:
            emit("Ontology, taxonomies and requested connectors already match the requested values.")
            return plan
        if backup:
            out = backup_out or Path(f"{plan.project}-api-backup-{datetime.now():%Y%m%d-%H%M%S-%f}.zip")
            write_api_backup(client, plan, out)
            emit(f"API snapshot written to {out}")
        completed, skipped = apply_ontology_plan(client, plan, emit)
        emit(f"Completed {completed} API operation(s); preserved {skipped} in-use property removal(s).")
        return plan
