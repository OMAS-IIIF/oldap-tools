import gzip
import json
import logging
from datetime import datetime
from importlib import resources
from pathlib import Path
from typing import Any

import typer
import yaml
import yamale
from oldaplib.src.cachesingleton import CacheSingletonRedis
from oldaplib.src.connection import Connection
from oldaplib.src.datamodel import DataModel
from oldaplib.src.dtypes.languagein import LanguageIn
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.editor import Editor
from oldaplib.src.enums.externalontologyattr import ExternalOntologyAttr
from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.enums.resourceclassattr import ResClassAttribute
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.externalontology import ExternalOntology
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNotFound
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.oldaplist_helpers import ListFormat, dump_list_to
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.xsd.xsd_decimal import Xsd_decimal
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName

from oldap_tools.dump_project import dump_project
from oldap_tools.connection import create_connection
from oldap_tools.list_merge import (
    list_exists_in_store,
    load_or_merge_list_from_spec,
    load_or_merge_lists_from_yaml,
)

log = logging.getLogger(__name__)


PROP_KEY_MAP = {
    "subproperty_of": "subPropertyOf",
    "to_class": "toClass",
    "node_kind": "nodeKind",
    "language_in": "languageIn",
    "unique_lang": "uniqueLang",
    "in": "inSet",
    "min_length": "minLength",
    "max_length": "maxLength",
    "min_exclusive": "minExclusive",
    "min_inclusive": "minInclusive",
    "max_exclusive": "maxExclusive",
    "max_inclusive": "maxInclusive",
    "less_than": "lessThan",
    "less_than_or_equals": "lessThanOrEquals",
    "inverse_of": "inverseOf",
    "equivalent_property": "equivalentProperty",
    "min_count": "minCount",
    "max_count": "maxCount",
}

ATTR_TO_YAML = {
    "subPropertyOf": "subproperty_of",
    "toClass": "to_class",
    "nodeKind": "node_kind",
    "languageIn": "language_in",
    "uniqueLang": "unique_lang",
    "inSet": "in",
    "minLength": "min_length",
    "maxLength": "max_length",
    "minExclusive": "min_exclusive",
    "minInclusive": "min_inclusive",
    "maxExclusive": "max_exclusive",
    "maxInclusive": "max_inclusive",
    "lessThan": "less_than",
    "lessThanOrEquals": "less_than_or_equals",
    "inverseOf": "inverse_of",
    "equivalentProperty": "equivalent_property",
    "minCount": "min_count",
    "maxCount": "max_count",
}


def _schema_path() -> Path:
    return Path(str(resources.files("oldap_tools") / "schemas" / "ontology_schema.yaml"))


def validate_ontology_yaml(inf: Path, schema: Path | None = None) -> None:
    schema_file = schema or _schema_path()
    try:
        schema_obj = yamale.make_schema(str(schema_file))
        data = yamale.make_data(str(inf))
        yamale.validate(schema=schema_obj, data=data)
    except Exception as err:
        log.error(f"ERROR: YAML validation failed: {err}")
        raise typer.Exit(code=1)


def _read_yaml(inf: Path) -> dict[str, Any]:
    validate_ontology_yaml(inf)
    with inf.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or not isinstance(data.get("ontology"), dict):
        log.error("ERROR: Ontology YAML must contain a top-level 'ontology' mapping.")
        raise typer.Exit(code=1)
    return data["ontology"]


def _resolve_relative_path(base_dir: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _resolve_list_path(base_dir: Path, value: str) -> Path:
    path = _resolve_relative_path(base_dir, value)
    if path.exists():
        return path
    fallback = (base_dir / Path(value).name).resolve()
    if fallback.exists():
        return fallback
    return path


def _as_langstring(value: Any) -> LangString | None:
    if value is None:
        return None
    if isinstance(value, LangString):
        return value
    if isinstance(value, str):
        return LangString([value])
    if isinstance(value, list):
        return LangString(value)
    if isinstance(value, dict):
        return LangString([f"{text}@{lang}" for lang, text in value.items() if text is not None])
    raise ValueError(f"Cannot convert {value!r} to LangString")


def _as_datatype(value: str | None) -> XsdDatatypes | None:
    if value is None:
        return None
    try:
        return XsdDatatypes(value)
    except ValueError:
        return XsdDatatypes[value]


def _resolve_class(value: str | None, lists: dict[str, OldapList]) -> Xsd_QName | None:
    if value is None:
        return None
    if value.startswith("list:"):
        list_id = value.split(":", 1)[1]
        if list_id not in lists:
            raise ValueError(f'Unknown list reference "{value}"')
        return lists[list_id].node_classIri
    return Xsd_QName(value)


def _property_kwargs(spec: dict[str, Any], lists: dict[str, OldapList]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    for yaml_key, value in spec.items():
        if yaml_key == "iri" or value is None:
            continue
        key = PROP_KEY_MAP.get(yaml_key, yaml_key)
        match key:
            case "datatype":
                kwargs[key] = _as_datatype(value)
            case "toClass":
                kwargs[key] = _resolve_class(value, lists)
            case "name" | "description":
                kwargs[key] = _as_langstring(value)
            case "languageIn":
                kwargs[key] = LanguageIn(value)
            case "editor":
                kwargs[key] = Editor(value)
            case "minCount" | "maxCount" | "minLength" | "maxLength":
                kwargs[key] = Xsd_integer(value)
            case "order":
                kwargs[key] = Xsd_decimal(value)
            case _:
                kwargs[key] = Xsd_QName(value) if isinstance(value, str) and ":" in value and key not in {"pattern"} else value
    return kwargs


def _build_property(con: Connection, project: Project, spec: dict[str, Any], lists: dict[str, OldapList]) -> PropertyClass:
    iri = spec.get("iri")
    if not iri:
        raise ValueError("Every inline property needs an 'iri'.")
    return PropertyClass(
        con=con,
        project=project,
        property_class_iri=Xsd_QName(iri),
        **_property_kwargs(spec, lists),
    )


def _load_lists(con: Connection, project: Project, base_dir: Path, lists_spec: dict[str, Any] | None) -> dict[str, OldapList]:
    loaded: dict[str, OldapList] = {}
    for list_id, spec in (lists_spec or {}).items():
        if isinstance(spec, str):
            path = _resolve_list_path(base_dir, spec)
            if not path.exists():
                raise ValueError(
                    f'List file "{spec}" for "{list_id}" was not found relative to "{base_dir}" '
                    f'or as "{Path(spec).name}" in that directory.'
                )
            yaml_lists = load_or_merge_lists_from_yaml(con=con, project=project, filepath=path)
            loaded_list = next((item for item in yaml_lists if str(item.oldapListId) == list_id), None)
            if loaded_list is None:
                if list_exists_in_store(con, project, list_id):
                    loaded_list = OldapList.read(con=con, project=project, oldapListId=list_id)
                else:
                    raise ValueError(f'List file "{spec}" does not contain list "{list_id}".')
            loaded[list_id] = loaded_list
        elif isinstance(spec, dict):
            loaded[list_id] = load_or_merge_list_from_spec(con=con, project=project, list_id=list_id, spec=spec)
        else:
            raise ValueError(f'Invalid list specification for "{list_id}"')
        if not list_exists_in_store(con, project, list_id):
            raise ValueError(f'List "{list_id}" was loaded, but no triples were found in {project.projectShortName}:lists.')
    return loaded


def _read_or_create_project(con: Connection, project_spec: dict[str, Any]) -> Project:
    shortname = project_spec["shortname"]
    try:
        return Project.read(con, shortname, ignore_cache=True)
    except OldapErrorNotFound:
        missing = [key for key in ("iri", "namespace", "start") if not project_spec.get(key)]
        if missing:
            raise ValueError(f'Project "{shortname}" does not exist and YAML is missing: {", ".join(missing)}')
        project = Project(
            con=con,
            projectIri=project_spec["iri"],
            projectShortName=shortname,
            namespaceIri=NamespaceIRI(project_spec["namespace"]),
            projectStart=Xsd_date(str(project_spec["start"])),
            label=_as_langstring(project_spec.get("label")),
            comment=_as_langstring(project_spec.get("comment")),
        )
        project.create()
        return project


def _build_external_ontology(con: Connection, project: Project, prefix: str, spec: dict[str, Any]) -> ExternalOntology:
    resource_classes = spec.get("proposedResourceClass", spec.get("resource_classes", []))
    datatype_properties = spec.get("proposedDatatypePropertyClass", spec.get("datatype_properties", []))
    object_properties = spec.get("proposedObjectPropertyClass", spec.get("object_properties", []))
    return ExternalOntology(
        con=con,
        projectShortName=project.projectShortName,
        prefix=Xsd_NCName(prefix),
        namespaceIri=NamespaceIRI(spec["namespace"]),
        label=_as_langstring(spec.get("label")),
        comment=_as_langstring(spec.get("comment")),
        proposedResourceClass=set(resource_classes or []),
        proposedDatatypePropertyClass=set(datatype_properties or []),
        proposedObjectPropertyClass=set(object_properties or []),
    )


def _ontology_context(project: Project, ontology: dict[str, Any]) -> Context:
    context = Context(name="OLDAP_TOOLS_ONTOLOGY")
    context[project.projectShortName] = project.namespaceIri
    project_spec = ontology.get("project") or {}
    if project_spec.get("shortname") and project_spec.get("namespace"):
        context[project_spec["shortname"]] = project_spec["namespace"]
    for prefix, spec in (ontology.get("external_ontologies") or {}).items():
        if spec.get("namespace"):
            context[prefix] = spec["namespace"]
    return context


def _qname_to_iri(context: Context, value: str) -> str:
    if value.startswith(("http://", "https://", "urn:")):
        return value
    return str(context.qname2iri(Xsd_QName(value)))


def _lucene_field_name_from_property(value: str | list[str] | dict[str, Any]) -> str:
    if isinstance(value, str):
        prop = value
    elif isinstance(value, list) and value:
        if len(value) > 1:
            raise ValueError(
                "Lucene field specifications with multi-step chains need an explicit field name."
            )
        prop = value[-1]
    elif isinstance(value, dict):
        if value.get("fieldName"):
            return str(value["fieldName"])
        chain = value.get("chain", value.get("propertyChain"))
        if isinstance(chain, str):
            prop = chain
        elif isinstance(chain, list) and chain:
            if len(chain) > 1:
                raise ValueError(
                    "Lucene field specifications with multi-step chains need an explicit field name."
                )
            prop = chain[-1]
        else:
            raise ValueError("Lucene field specification needs a chain/propertyChain.")
    else:
        raise ValueError(f'Invalid Lucene field specification "{value}"')

    if prop.startswith(("http://", "https://", "urn:")):
        return prop.rstrip("/#").rsplit("/", 1)[-1].rsplit("#", 1)[-1].rsplit(":", 1)[-1]
    return Xsd_QName(prop).fragment


def _lucene_field_defaults(field_name: str, spec: str | list[str] | dict[str, Any], context: Context) -> dict[str, Any]:
    if isinstance(spec, str):
        field_spec: dict[str, Any] = {"chain": [spec]}
    elif isinstance(spec, list):
        field_spec = {"chain": spec}
    elif isinstance(spec, dict):
        field_spec = spec
    else:
        raise ValueError(f'Invalid Lucene field specification for "{field_name}"')

    chain = field_spec.get("chain", field_spec.get("propertyChain"))
    if isinstance(chain, str):
        chain = [chain]
    if not chain:
        raise ValueError(f'Lucene field "{field_name}" needs a chain/propertyChain.')

    result = {
        "fieldName": field_name,
        "propertyChain": [_qname_to_iri(context, item) for item in chain],
        "indexed": True,
        "stored": True,
        "analyzed": True,
        "multivalued": True,
        "ignoreInvalidValues": False,
        "facet": False,
    }
    for key in ("indexed", "stored", "analyzed", "multivalued", "ignoreInvalidValues", "facet"):
        if key in field_spec:
            result[key] = field_spec[key]
    return result


def _build_lucene_payload(name: str, spec: dict[str, Any], context: Context) -> dict[str, Any]:
    fields = spec.get("fields") or {}
    if isinstance(fields, dict):
        field_items = fields.items()
    elif isinstance(fields, list):
        field_items = ((_lucene_field_name_from_property(field_spec), field_spec) for field_spec in fields)
    else:
        raise ValueError(f'Lucene connector "{name}" fields must be a mapping or list.')
    payload = {
        "fields": [_lucene_field_defaults(field_name, field_spec, context) for field_name, field_spec in field_items],
        "languages": spec.get("languages", ["en", "de", "fr", "it"]),
        "types": [_qname_to_iri(context, item) for item in spec.get("types", [])],
        "readonly": False,
        "detectFields": False,
        "importGraph": False,
        "skipInitialIndexing": False,
        "boostProperties": [],
        "stripMarkup": False,
    }
    if not payload["types"]:
        raise ValueError(f'Lucene connector "{name}" needs at least one type.')
    for key in ("readonly", "detectFields", "importGraph", "skipInitialIndexing", "boostProperties", "stripMarkup"):
        if key in spec:
            payload[key] = spec[key]
    return payload


def _merge_lucene_payloads(connector_name: str, payloads: list[dict[str, Any]]) -> dict[str, Any]:
    if not payloads:
        raise ValueError(f'Lucene connector "{connector_name}" needs at least one specification.')

    merged = {
        "fields": [],
        "languages": [],
        "types": [],
        "readonly": False,
        "detectFields": False,
        "importGraph": False,
        "skipInitialIndexing": False,
        "boostProperties": [],
        "stripMarkup": False,
    }
    fields_by_name: dict[str, dict[str, Any]] = {}
    for payload in payloads:
        for item in payload["types"]:
            if item not in merged["types"]:
                merged["types"].append(item)
        for item in payload["languages"]:
            if item not in merged["languages"]:
                merged["languages"].append(item)
        for field in payload["fields"]:
            field_name = field["fieldName"]
            existing = fields_by_name.get(field_name)
            if existing is not None:
                if existing != field:
                    raise ValueError(f'Lucene field "{field_name}" is defined more than once with different settings.')
                continue
            fields_by_name[field_name] = field
            merged["fields"].append(field)
        for key in ("readonly", "detectFields", "importGraph", "skipInitialIndexing", "stripMarkup"):
            if payload[key] != merged[key] and merged[key] is not False:
                raise ValueError(f'Lucene connector setting "{key}" has conflicting values.')
            merged[key] = payload[key]
        for item in payload["boostProperties"]:
            if item not in merged["boostProperties"]:
                merged["boostProperties"].append(item)

    if not merged["types"]:
        raise ValueError(f'Lucene connector "{connector_name}" needs at least one type.')
    if not merged["fields"]:
        raise ValueError(f'Lucene connector "{connector_name}" needs at least one field.')
    return merged


def _lucene_connector_exists(con: Connection, connector_name: str) -> bool:
    sparql = f"""
    PREFIX luc: <http://www.ontotext.com/connectors/lucene#>
    ASK {{
        ?connector luc:listConnectors "inst:{connector_name}" .
    }}
    """
    return con.query(sparql)["boolean"]


def _drop_lucene_connector(con: Connection, connector_name: str) -> None:
    sparql = f"""
    PREFIX luc: <http://www.ontotext.com/connectors/lucene#>
    PREFIX inst: <http://www.ontotext.com/connectors/lucene/instance#>
    INSERT DATA {{
        inst:{connector_name} luc:dropConnector [] .
    }}
    """
    con.update_query(sparql)


def _create_lucene_connector(con: Connection, connector_name: str, payload: dict[str, Any]) -> None:
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
    sparql = f"""
    PREFIX luc: <http://www.ontotext.com/connectors/lucene#>
    PREFIX inst: <http://www.ontotext.com/connectors/lucene/instance#>
    INSERT DATA {{
        inst:{connector_name} luc:createConnector '''{payload_json}''' .
    }}
    """
    print(sparql)
    con.update_query(sparql)


def _read_lucene_connector_payload(con: Connection, connector_name: str) -> dict[str, Any] | None:
    if not _lucene_connector_exists(con, connector_name):
        return None
    sparql = f"""
    PREFIX luc: <http://www.ontotext.com/connectors/lucene#>
    PREFIX inst: <http://www.ontotext.com/connectors/lucene/instance#>
    SELECT ?options
    WHERE {{
        inst:{connector_name} luc:listOptionValues ?options .
    }}
    """
    result = con.query(sparql)
    bindings = result.get("results", {}).get("bindings", [])
    if not bindings:
        return None
    value = bindings[0].get("options", {}).get("value")
    if not value:
        return None
    return json.loads(value)


def _iri_to_yaml_ref(context: Context, value: str) -> str:
    qname = context.iri2qname(value, validate=False)
    return str(qname) if qname is not None else value


def _lucene_field_yaml(field: dict[str, Any], context: Context) -> tuple[str | None, Any]:
    field_name = field["fieldName"]
    chain = [_iri_to_yaml_ref(context, item) for item in field.get("propertyChain", [])]
    if not chain:
        raise ValueError(f'Lucene field "{field_name}" has no propertyChain.')

    defaults = {
        "indexed": True,
        "stored": True,
        "analyzed": True,
        "multivalued": True,
        "ignoreInvalidValues": False,
        "facet": False,
    }
    extras = {key: field[key] for key, value in defaults.items() if key in field and field[key] != value}

    if len(chain) == 1:
        auto_name = _lucene_field_name_from_property(chain[0])
        if field_name == auto_name and not extras:
            return None, chain[0]
        if not extras:
            return field_name, chain[0]
        return field_name, {"chain": chain[0], **extras}

    return field_name, {"chain": chain, **extras}


def _dump_lucene_connector(con: Connection, project: Project) -> dict[str, Any] | None:
    connector_name = str(project.projectShortName)
    payload = _read_lucene_connector_payload(con, connector_name)
    if not payload:
        return None

    context = Context(name="OLDAP_TOOLS_ONTOLOGY_DUMP")
    context[project.projectShortName] = project.namespaceIri

    spec: dict[str, Any] = {
        "types": [_iri_to_yaml_ref(context, item) for item in payload.get("types", [])],
    }
    defaults = {
        "languages": ["en", "de", "fr", "it"],
        "readonly": False,
        "detectFields": False,
        "importGraph": False,
        "skipInitialIndexing": False,
        "boostProperties": [],
        "stripMarkup": False,
    }
    for key, default in defaults.items():
        if key in payload and payload[key] != default:
            spec[key] = payload[key]

    field_list: list[Any] = []
    field_map: dict[str, Any] = {}
    use_field_map = False
    for field in payload.get("fields", []):
        field_name, field_spec = _lucene_field_yaml(field, context)
        if field_name is None:
            field_list.append(field_spec)
            if use_field_map:
                field_map[_lucene_field_name_from_property(field_spec)] = field_spec
        else:
            if not use_field_map:
                field_map.update({_lucene_field_name_from_property(item): item for item in field_list})
                use_field_map = True
            field_map[field_name] = field_spec
    if use_field_map:
        spec["fields"] = field_map
    else:
        spec["fields"] = field_list

    return {connector_name: spec}


def _apply_lucene_connectors(con: Connection, project: Project, ontology: dict[str, Any], mode: str) -> None:
    if mode == "skip":
        return
    if mode not in {"replace", "create"}:
        raise ValueError('Connector mode must be "skip", "replace", or "create".')
    context = _ontology_context(project, ontology)
    connector_specs = ontology.get("lucene_connectors") or {}
    if not connector_specs:
        return
    connector_name = str(project.projectShortName)
    payload = _merge_lucene_payloads(
        connector_name,
        [_build_lucene_payload(name, spec, context) for name, spec in connector_specs.items()],
    )
    exists = _lucene_connector_exists(con, connector_name)
    if exists and mode == "create":
        raise ValueError(f'Lucene connector "{connector_name}" already exists.')
    if mode == "replace":
        for old_connector_name in connector_specs.keys():
            if old_connector_name != connector_name and _lucene_connector_exists(con, old_connector_name):
                _drop_lucene_connector(con, old_connector_name)
        if exists:
            _drop_lucene_connector(con, connector_name)
    if not exists or mode == "replace":
        _create_lucene_connector(con, connector_name, payload)


def _build_resource_class(
    con: Connection,
    project: Project,
    iri: str,
    spec: dict[str, Any],
    lists: dict[str, OldapList],
) -> ResourceClass:
    properties = [_build_property(con, project, prop, lists) for prop in spec.get("properties", [])]
    kwargs: dict[str, Any] = {
        "label": _as_langstring(spec.get("label")),
        "comment": _as_langstring(spec.get("comment")),
        "closed": spec.get("closed"),
        "properties": properties,
    }
    if spec.get("superclass"):
        kwargs["superclass"] = [Xsd_QName(x) for x in spec["superclass"]]
    return ResourceClass(con=con, project=project, owlclass_iri=Xsd_QName(iri), **kwargs)


def _build_datamodel(con: Connection, project: Project, ontology: dict[str, Any], lists: dict[str, OldapList]) -> DataModel:
    extontos = [
        _build_external_ontology(con, project, prefix, spec)
        for prefix, spec in (ontology.get("external_ontologies") or {}).items()
    ]
    propclasses = [
        _build_property(con, project, {"iri": iri} | spec, lists)
        for iri, spec in (ontology.get("standalone_properties") or {}).items()
    ]
    resclasses = [
        _build_resource_class(con, project, iri, spec, lists)
        for iri, spec in (ontology.get("classes") or {}).items()
    ]
    return DataModel(con=con, project=project, extontos=extontos, propclasses=propclasses, resclasses=resclasses)


def _values_equal(current: Any, desired: Any) -> bool:
    """Return whether OLDAP attribute values are semantically unchanged.

    Some oldaplib value objects, notably `LangString`, assume that comparison
    operands have the same internal structure. Handling `None` before delegating
    to those value objects keeps update mode stable for missing attributes.
    """
    if current is None or desired is None:
        return current is desired
    return current == desired


def _set_attr(obj: Any, attr: Any, value: Any) -> None:
    """Update an OLDAP model attribute only when its value changed."""
    current = obj.get(attr)
    if not _values_equal(current, value):
        obj[attr] = value


def _sync_property(existing: PropertyClass, desired_spec: dict[str, Any], lists: dict[str, OldapList]) -> None:
    desired = _property_kwargs(desired_spec, lists)
    for attr in PropClassAttr:
        fragment = attr.value.fragment
        if fragment == "type":
            continue
        yaml_key = ATTR_TO_YAML.get(fragment, fragment)
        if fragment in desired:
            _set_attr(existing, attr, desired[fragment])
        elif yaml_key in desired_spec or fragment in desired_spec:
            _set_attr(existing, attr, None)


def _sync_resource(existing: ResourceClass, desired_spec: dict[str, Any], desired: ResourceClass, lists: dict[str, OldapList]) -> None:
    for attr, key in ((ResClassAttribute.LABEL, "label"), (ResClassAttribute.COMMENT, "comment"), (ResClassAttribute.CLOSED, "closed")):
        if key in desired_spec:
            _set_attr(existing, attr, desired.get(attr))
    if "superclass" in desired_spec:
        _set_attr(existing, ResClassAttribute.SUPERCLASS, desired.get(ResClassAttribute.SUPERCLASS))

    if "properties" not in desired_spec:
        return

    desired_iris = {Xsd_QName(prop["iri"]) for prop in desired_spec["properties"]}
    for prop_spec in desired_spec["properties"]:
        prop_iri = Xsd_QName(prop_spec["iri"])
        current_prop = existing.get(prop_iri)
        if current_prop is None:
            existing[prop_iri] = _build_property(existing._con, existing._project, prop_spec, lists)
        else:
            _sync_property(current_prop, prop_spec, lists)
    for prop_iri, _prop in list(existing.properties_items()):
        if prop_iri not in desired_iris:
            del existing[prop_iri]


def _apply_update(con: Connection, project: Project, ontology: dict[str, Any], lists: dict[str, OldapList]) -> None:
    try:
        model = DataModel.read(con, project, ignore_cache=True)
    except OldapErrorNotFound:
        model = DataModel(con=con, project=project)
        model.create()
        model = DataModel.read(con, project, ignore_cache=True)

    for prefix, spec in (ontology.get("external_ontologies") or {}).items():
        key = Xsd_QName(project.projectShortName, prefix)
        desired = _build_external_ontology(con, project, prefix, spec)
        existing = model.get(key)
        if existing is None:
            model[key] = desired
        elif isinstance(existing, ExternalOntology):
            external_attrs = (
                (ExternalOntologyAttr.LABEL, ("label",)),
                (ExternalOntologyAttr.COMMENT, ("comment",)),
                (ExternalOntologyAttr.PROPOSED_RESOURCE_CLASS, ("proposedResourceClass", "resource_classes")),
                (ExternalOntologyAttr.PROPOSED_DATATYPE_PROPERTY_CLASS, ("proposedDatatypePropertyClass", "datatype_properties")),
                (ExternalOntologyAttr.PROPOSED_OBJECT_PROPERTY_CLASS, ("proposedObjectPropertyClass", "object_properties")),
            )
            for attr, yaml_keys in external_attrs:
                if any(yaml_key in spec for yaml_key in yaml_keys):
                    _set_attr(existing, attr, desired.get(attr))

    for iri, spec in (ontology.get("standalone_properties") or {}).items():
        key = Xsd_QName(iri)
        spec_with_iri = {"iri": iri} | spec
        existing = model.get(key)
        if existing is None:
            model[key] = _build_property(con, project, spec_with_iri, lists)
        elif isinstance(existing, PropertyClass):
            _sync_property(existing, spec_with_iri, lists)

    for iri, spec in (ontology.get("classes") or {}).items():
        key = Xsd_QName(iri)
        desired = _build_resource_class(con, project, iri, spec, lists)
        existing = model.get(key)
        if existing is None:
            model[key] = desired
        elif isinstance(existing, ResourceClass):
            _sync_resource(existing, spec, desired, lists)
    model.update()


def _connect(
    graphdb_base: str,
    repo: str,
    user: str,
    password: str,
    graphdb_user: str | None,
    graphdb_password: str | None,
) -> Connection:
    return create_connection(
        graphdb_base=graphdb_base,
        repo=repo,
        graphdb_user=graphdb_user,
        graphdb_password=graphdb_password,
        user=user,
        password=password,
        context_name="DEFAULT",
    )


def _backup_path(project_id: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path(f"{project_id}-model-backup-{stamp}.trig.gz")


def load_ontology(
    *,
    graphdb_base: str,
    repo: str,
    inf: Path,
    user: str,
    password: str,
    mode: str,
    connector_mode: str,
    backup: bool,
    backup_out: Path | None,
    graphdb_user: str | None = None,
    graphdb_password: str | None = None,
) -> None:
    inf = inf.expanduser().resolve()
    ontology = _read_yaml(inf)
    con = _connect(graphdb_base, repo, user, password, graphdb_user, graphdb_password)
    try:
        project = _read_or_create_project(con, ontology["project"])
        if backup:
            out = backup_out or _backup_path(str(project.projectShortName))
            dump_project(
                project_id=str(project.projectShortName),
                graphdb_base=graphdb_base,
                repo=repo,
                out=out,
                include_data=False,
                include_model=True,
                include_admin=False,
                include_lists=True,
                user=user,
                password=password,
                graphdb_user=graphdb_user,
                graphdb_password=graphdb_password,
            )
            typer.echo(f"Backup written to {out}")

        lists = _load_lists(con, project, inf.parent, ontology.get("lists"))
        if mode == "replace":
            try:
                DataModel.read(con, project, ignore_cache=True).delete()
            except OldapErrorNotFound:
                pass
            model = _build_datamodel(con, project, ontology, lists)
            model.create()
        elif mode == "update":
            _apply_update(con, project, ontology, lists)
        else:
            raise ValueError(f'Unknown mode "{mode}"')
        _apply_lucene_connectors(con, project, ontology, connector_mode)
        CacheSingletonRedis().clear()
    except (OldapError, ValueError) as err:
        log.error(f"ERROR: Failed to load ontology: {err}")
        raise typer.Exit(code=1)


def _plain(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, LangString):
        return {lang.name.lower(): str(text) for lang, text in value.items()}
    if isinstance(value, (Xsd_QName, Xsd_NCName, NamespaceIRI, XsdDatatypes, Editor)):
        return str(value)
    if isinstance(value, (Xsd_integer, Xsd_decimal)):
        return int(value) if isinstance(value, Xsd_integer) else float(value)
    if isinstance(value, set):
        return sorted(_plain(x) for x in value)
    if hasattr(value, "toRdf"):
        return str(value)
    if isinstance(value, dict):
        return {str(_plain(k)): _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(x) for x in value]
    return value


def _dump_property(prop: PropertyClass) -> dict[str, Any]:
    result = {"iri": str(prop.property_class_iri)}
    for attr, value in prop._attributes.items():
        if attr == PropClassAttr.TYPE:
            continue
        key = ATTR_TO_YAML.get(attr.value.fragment, attr.value.fragment)
        result[key] = _plain(value)
    return result


def _dump_external_ontology(ontology: ExternalOntology) -> dict[str, Any]:
    """Serialize an OLDAP external-ontology reference to canonical YAML.

    The prefix is used as the key in the surrounding ``external_ontologies``
    mapping. This function therefore emits the namespace and all mutable
    metadata needed by :func:`_build_external_ontology` for a lossless YAML
    export/import roundtrip.

    Args:
        ontology: External ontology loaded as part of a project data model.

    Returns:
        YAML-compatible external ontology metadata.
    """
    result: dict[str, Any] = {
        "namespace": str(ontology.get(ExternalOntologyAttr.NAMESPACE_IRI)),
    }
    for attr, key in (
        (ExternalOntologyAttr.LABEL, "label"),
        (ExternalOntologyAttr.COMMENT, "comment"),
    ):
        value = ontology.get(attr)
        if value:
            result[key] = _plain(value)

    for attr, key in (
        (ExternalOntologyAttr.PROPOSED_RESOURCE_CLASS, "proposedResourceClass"),
        (ExternalOntologyAttr.PROPOSED_DATATYPE_PROPERTY_CLASS, "proposedDatatypePropertyClass"),
        (ExternalOntologyAttr.PROPOSED_OBJECT_PROPERTY_CLASS, "proposedObjectPropertyClass"),
    ):
        value = ontology.get(attr)
        if value:
            result[key] = sorted(str(item) for item in value)
    return result


def _dump_resource(res: ResourceClass) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for attr, value in res.attributes_items():
        if attr == ResClassAttribute.SUPERCLASS:
            vals = [str(x) for x in value.keys() if str(x) != "oldap:Thing"]
            if vals:
                result["superclass"] = vals
        else:
            result[attr.value.fragment] = _plain(value)
    props = [_dump_property(prop) for _iri, prop in res.properties_items()]
    if props:
        result["properties"] = props
    return result


def _list_ids(con: Connection, project: Project) -> list[str]:
    context = Context(name=con.context_name)
    context[project.projectShortName] = project.namespaceIri
    sparql = context.sparql_context
    sparql += f"""
    SELECT ?list
    FROM {project.projectShortName}:lists
    WHERE {{
        ?list a oldap:OldapList .
    }}
    ORDER BY ?list
    """
    res = QueryProcessor(context, con.query(sparql))
    list_ids: list[str] = []
    for row in res:
        list_iri = str(row["list"])
        qname = context.iri2qname(list_iri, validate=False)
        if qname is not None:
            list_iri = str(qname)
        list_ids.append(list_iri.split(":", 1)[1] if ":" in list_iri else list_iri)
    return list_ids


def _dump_taxonomies(con: Connection, project: Project, out: Path) -> dict[str, str]:
    out_dir = out.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, str] = {}
    for list_id in _list_ids(con, project):
        filename = f"{list_id}.yaml"
        yaml_text = dump_list_to(
            con=con,
            project=project,
            oldapListId=list_id,
            listformat=ListFormat.YAML,
            ignore_cache=True,
        )
        (out_dir / filename).write_text(yaml_text, encoding="utf-8")
        result[list_id] = filename
    return result


def dump_ontology(
    *,
    graphdb_base: str,
    repo: str,
    project_id: str,
    out: Path,
    fmt: str,
    user: str,
    password: str,
    include_taxonomies: bool = False,
    graphdb_user: str | None = None,
    graphdb_password: str | None = None,
) -> None:
    if fmt not in {"yaml", "trig"}:
        log.error("ERROR: Output format must be 'yaml' or 'trig'.")
        raise typer.Exit(code=1)
    if fmt == "trig":
        dump_project(
            project_id=project_id,
            graphdb_base=graphdb_base,
            repo=repo,
            out=out,
            include_data=False,
            include_model=True,
            include_admin=False,
            include_lists=True,
            user=user,
            password=password,
            graphdb_user=graphdb_user,
            graphdb_password=graphdb_password,
        )
        return

    con = _connect(graphdb_base, repo, user, password, graphdb_user, graphdb_password)
    try:
        project = Project.read(con, project_id)
        model = DataModel.read(con, project, ignore_cache=True)
    except OldapError as err:
        log.error(f"ERROR: Failed to dump ontology: {err}")
        raise typer.Exit(code=1)

    doc: dict[str, Any] = {
        "ontology": {
            "project": {
                "shortname": str(project.projectShortName),
                "iri": str(project.projectIri),
                "namespace": str(project.namespaceIri),
            },
        }
    }
    external_ontologies: dict[str, Any] = {}
    for qname in model.get_extontos():
        external_ontology = model[qname]
        prefix = str(external_ontology.get(ExternalOntologyAttr.PREFIX))
        external_ontologies[prefix] = _dump_external_ontology(external_ontology)
    if external_ontologies:
        doc["ontology"]["external_ontologies"] = external_ontologies
    if include_taxonomies:
        lists = _dump_taxonomies(con, project, out)
        if lists:
            doc["ontology"]["lists"] = lists
    doc["ontology"]["classes"] = {}
    for qname in model.get_resclasses():
        doc["ontology"]["classes"][str(qname)] = _dump_resource(model[qname])
    lucene_connectors = _dump_lucene_connector(con, project)
    if lucene_connectors:
        doc["ontology"]["lucene_connectors"] = lucene_connectors
    if out.suffix == ".gz":
        with gzip.open(out, "wt", encoding="utf-8") as f:
            yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)
    else:
        with out.open("w", encoding="utf-8") as f:
            yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)
