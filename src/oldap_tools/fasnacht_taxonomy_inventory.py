"""Read-only inventory for the Fasnacht taxonomy simplification.

The module intentionally exposes no apply or update path. It reads list and
project-data graphs, combines their state with the reviewed Phase-1 mapping,
and produces an auditable report for local and production rehearsals.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Iterable

from oldaplib.src.project import Project
import yaml

from oldap_tools.connection import create_connection


SUPPORTED_MAPPING_MODES = frozenset({"exact", "broader", "review"})
SUPPORTED_SOURCE_STATES = frozenset({"active", "legacy"})
EVENT_YEAR_TITLE = re.compile(r"^Fasnacht\s+\d{4}$", re.IGNORECASE)
BOILERPLATE_EVENT_PROPERTIES = frozenset({
    "attachedToRole",
    "contributor",
    "created",
    "createdBy",
    "creator",
    "creationDate",
    "dating",
    "lastModificationDate",
    "lastModifiedBy",
    "modified",
    "name",
    "publicationStatus",
    "type",
})


@dataclass(frozen=True)
class MappingRule:
    """Expanded migration guidance for one source taxonomy node."""

    source_list: str
    source_node: str
    target_list: str | None
    target_nodes: tuple[str, ...]
    mode: str
    note: str = ""
    source_state: str = "active"


def _mapping_document(path: Path) -> dict[str, Any]:
    """Load and structurally validate a Phase-1 mapping document."""

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Taxonomy mapping must be a version-1 mapping document.")
    if not isinstance(data.get("lists"), dict):
        raise ValueError("Taxonomy mapping requires a lists mapping.")
    return data


def load_mapping(path: Path) -> dict[str, dict[str, MappingRule]]:
    """Expand grouped YAML rules into one rule per source node.

    Args:
        path: Version-1 mapping YAML.

    Returns:
        Rules keyed first by list ID and then by source node ID.

    Raises:
        ValueError: If rules are malformed, duplicated, or use an unknown mode.
    """

    document = _mapping_document(path)
    expanded: dict[str, dict[str, MappingRule]] = {}
    for list_id, list_spec in document["lists"].items():
        if not isinstance(list_spec, dict):
            raise ValueError(f'Mapping for list "{list_id}" must be an object.')
        target_list = list_spec.get("target_list")
        if target_list is not None and not isinstance(target_list, str):
            raise ValueError(f'Target list for "{list_id}" must be a string or null.')
        node_rules: dict[str, MappingRule] = {}
        for group in list_spec.get("groups", []):
            if not isinstance(group, dict):
                raise ValueError(f'Mapping group in "{list_id}" must be an object.')
            mode = group.get("mode")
            if mode not in SUPPORTED_MAPPING_MODES:
                raise ValueError(f'Unknown mapping mode "{mode}" in "{list_id}".')
            source_state = group.get("source_state", "active")
            if source_state not in SUPPORTED_SOURCE_STATES:
                raise ValueError(f'Unknown source state "{source_state}" in "{list_id}".')
            sources = group.get("source_nodes")
            targets = group.get("target_nodes")
            if not isinstance(sources, list) or not all(isinstance(value, str) and value for value in sources):
                raise ValueError(f'Mapping group in "{list_id}" requires source_nodes.')
            if not isinstance(targets, list) or not all(isinstance(value, str) and value for value in targets):
                raise ValueError(f'Mapping group in "{list_id}" requires target_nodes.')
            for source_node in sources:
                if source_node in node_rules:
                    raise ValueError(f'Duplicate mapping for "{list_id}:{source_node}".')
                node_rules[source_node] = MappingRule(
                    source_list=list_id,
                    source_node=source_node,
                    target_list=target_list,
                    target_nodes=tuple(targets),
                    mode=mode,
                    note=str(group.get("note", "")).strip(),
                    source_state=source_state,
                )
        expanded[list_id] = node_rules
    return expanded


def taxonomy_node_ids(path: Path) -> set[str]:
    """Return every node ID in a one-list OLDAP taxonomy YAML."""

    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or len(document) != 1:
        raise ValueError(f"{path} must contain exactly one taxonomy.")
    specification = next(iter(document.values()))
    if not isinstance(specification, dict):
        raise ValueError(f"{path} contains an invalid taxonomy specification.")

    result: set[str] = set()

    def visit(nodes: Any) -> None:
        if nodes is None:
            return
        if not isinstance(nodes, dict):
            raise ValueError(f"{path} contains an invalid nodes mapping.")
        for node_id, node in nodes.items():
            if node_id in result:
                raise ValueError(f'Duplicate taxonomy node ID "{node_id}" in {path}.')
            result.add(str(node_id))
            if not isinstance(node, dict):
                raise ValueError(f'Node "{node_id}" in {path} must be an object.')
            visit(node.get("nodes"))

    visit(specification.get("nodes"))
    return result


def validate_mapping_coverage(
    mapping: dict[str, dict[str, MappingRule]],
    taxonomy_paths: dict[str, Path],
) -> None:
    """Require the mapping to cover every active source node exactly once."""

    for list_id, taxonomy_path in taxonomy_paths.items():
        actual = taxonomy_node_ids(taxonomy_path)
        mapped = set(mapping.get(list_id, {}))
        missing = sorted(actual - mapped)
        allowed_legacy = {
            node_id
            for node_id, rule in mapping.get(list_id, {}).items()
            if rule.source_state == "legacy"
        }
        unknown = sorted(mapped - actual - allowed_legacy)
        if missing or unknown:
            details = []
            if missing:
                details.append(f"missing: {', '.join(missing)}")
            if unknown:
                details.append(f"unknown: {', '.join(unknown)}")
            raise ValueError(f'Incomplete mapping for "{list_id}" ({"; ".join(details)}).')


def validate_mapping_targets(
    mapping: dict[str, dict[str, MappingRule]],
    target_paths: dict[str, Path],
) -> None:
    """Require every declared target node to exist in its inactive draft list."""

    target_nodes = {
        list_id: taxonomy_node_ids(path)
        for list_id, path in target_paths.items()
    }
    for rules in mapping.values():
        for rule in rules.values():
            if not rule.target_nodes:
                continue
            if rule.target_list not in target_nodes:
                raise ValueError(f'No draft taxonomy supplied for target list "{rule.target_list}".')
            unknown = sorted(set(rule.target_nodes) - target_nodes[rule.target_list])
            if unknown:
                raise ValueError(
                    f'Unknown target node(s) for "{rule.source_list}:{rule.source_node}": '
                    f"{', '.join(unknown)}."
                )


def _sparql_literal(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_list_node_query(namespace: str, list_ids: Iterable[str]) -> str:
    """Build the read-only query that inventories all source-list nodes."""

    values = " ".join(
        f"(<{namespace}{list_id}> {_sparql_literal(list_id)} "
        f"{_sparql_literal(f'{namespace}{list_id}#')})"
        for list_id in list_ids
    )
    return f"""
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?list ?listId ?node ?nodeId ?label
WHERE {{
  GRAPH <{namespace}lists> {{
    VALUES (?list ?listId ?nodePrefix) {{ {values} }}
    ?node skos:inScheme ?list .
    BIND(STRAFTER(STR(?node), ?nodePrefix) AS ?nodeId)
    OPTIONAL {{
      ?node skos:prefLabel ?label .
      FILTER(LANG(?label) = "" || LANGMATCHES(LANG(?label), "de"))
    }}
  }}
}}
ORDER BY ?list ?nodeId
""".strip()


def build_taxonomy_usage_query(namespace: str, list_ids: Iterable[str]) -> str:
    """Build the read-only query for direct project-data node references."""

    values = " ".join(
        f"({_sparql_literal(list_id)} {_sparql_literal(f'{namespace}{list_id}#')})"
        for list_id in list_ids
    )
    return f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX schema: <https://schema.org/>
SELECT ?listId ?node ?nodeId ?resource ?property ?resourceClass ?resourceName
WHERE {{
  VALUES (?listId ?nodePrefix) {{ {values} }}
  GRAPH <{namespace}data> {{
    ?resource ?property ?node .
    FILTER(ISIRI(?node) && STRSTARTS(STR(?node), ?nodePrefix))
    BIND(STRAFTER(STR(?node), ?nodePrefix) AS ?nodeId)
    OPTIONAL {{ ?resource rdf:type ?resourceClass . }}
    OPTIONAL {{
      ?resource schema:name ?resourceName .
      FILTER(LANG(?resourceName) = "" || LANGMATCHES(LANG(?resourceName), "de"))
    }}
  }}
}}
ORDER BY ?listId ?nodeId ?resource ?property
""".strip()


def build_event_outgoing_query(namespace: str) -> str:
    """Build the read-only query for event titles and outgoing properties."""

    return f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX schema: <https://schema.org/>
SELECT ?event ?name ?property ?value
WHERE {{
  GRAPH <{namespace}data> {{
    ?event rdf:type <{namespace}CarnivalEvent> ; ?property ?value .
    OPTIONAL {{
      ?event schema:name ?name .
      FILTER(LANG(?name) = "" || LANGMATCHES(LANG(?name), "de"))
    }}
  }}
}}
ORDER BY ?event ?property
""".strip()


def build_event_incoming_query(namespace: str) -> str:
    """Build the read-only query for resources referring to an event."""

    return f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?event ?source ?property
WHERE {{
  GRAPH <{namespace}data> {{
    ?event rdf:type <{namespace}CarnivalEvent> .
    ?source ?property ?event .
    FILTER(?source != ?event)
  }}
}}
ORDER BY ?event ?source ?property
""".strip()


def _bindings(query_result: dict[str, Any]) -> list[dict[str, dict[str, str]]]:
    return query_result.get("results", {}).get("bindings", [])


def _value(binding: dict[str, dict[str, str]], key: str) -> str:
    return binding.get(key, {}).get("value", "").strip()


def _preferred_text(current: str, candidate: str, binding: dict[str, dict[str, str]], key: str) -> str:
    language = binding.get(key, {}).get("xml:lang", "").lower()
    if candidate and (not current or language == "de"):
        return candidate
    return current


def _local_name(iri: str) -> str:
    return re.split(r"[/#]", iri.rstrip("/#"))[-1]


def _event_candidates(
    outgoing_bindings: list[dict[str, dict[str, str]]],
    incoming_bindings: list[dict[str, dict[str, str]]],
    namespace: str,
) -> list[dict[str, Any]]:
    events: dict[str, dict[str, Any]] = {}
    for binding in outgoing_bindings:
        iri = _value(binding, "event")
        event = events.setdefault(iri, {"iri": iri, "name": "", "properties": {}, "incoming": set()})
        event["name"] = _preferred_text(event["name"], _value(binding, "name"), binding, "name")
        property_iri = _value(binding, "property")
        if property_iri:
            event["properties"].setdefault(property_iri, set()).add(_value(binding, "value"))

    for binding in incoming_bindings:
        iri = _value(binding, "event")
        event = events.setdefault(iri, {"iri": iri, "name": "", "properties": {}, "incoming": set()})
        event["incoming"].add((_value(binding, "source"), _value(binding, "property")))

    media_property = f"{namespace}archiveMediaObjectOf"
    report = []
    for event in events.values():
        incoming = sorted(event["incoming"])
        media_references = [entry for entry in incoming if entry[1] == media_property]
        substantive = sorted(
            property_iri
            for property_iri in event["properties"]
            if _local_name(property_iri) not in BOILERPLATE_EVENT_PROPERTIES
        )
        title_matches = bool(EVENT_YEAR_TITLE.fullmatch(event["name"]))
        review_candidate = title_matches and not incoming
        deletion_candidate = review_candidate and not substantive
        reasons = []
        if not title_matches:
            reasons.append("title is not 'Fasnacht YYYY'")
        if incoming:
            reasons.append(f"{len(incoming)} incoming reference(s)")
        if substantive:
            reasons.append(f"{len(substantive)} substantive property/properties")
        report.append({
            "iri": event["iri"],
            "name": event["name"],
            "mediaReferenceCount": len(media_references),
            "incomingReferenceCount": len(incoming),
            "incomingReferences": [
                {"source": source, "property": property_iri}
                for source, property_iri in incoming
            ],
            "substantiveProperties": substantive,
            "substantivePropertyValues": {
                property_iri: sorted(event["properties"][property_iri])
                for property_iri in substantive
            },
            "reviewCandidate": review_candidate,
            "deletionCandidate": deletion_candidate,
            "assessment": (
                "strict empty-year candidate"
                if deletion_candidate
                else "empty-year review candidate; " + "; ".join(reasons)
                if review_candidate
                else "; ".join(reasons)
            ),
        })
    return sorted(report, key=lambda entry: (entry["name"].casefold(), entry["iri"]))


def build_inventory_report(
    *,
    project_id: str,
    namespace: str,
    mapping: dict[str, dict[str, MappingRule]],
    node_bindings: list[dict[str, dict[str, str]]],
    usage_bindings: list[dict[str, dict[str, str]]],
    event_outgoing_bindings: list[dict[str, dict[str, str]]],
    event_incoming_bindings: list[dict[str, dict[str, str]]],
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Combine query results and mappings into a deterministic audit report."""

    nodes: dict[tuple[str, str], dict[str, Any]] = {}
    for binding in node_bindings:
        list_id = _value(binding, "listId") or _local_name(_value(binding, "list"))
        node_id = _value(binding, "nodeId")
        key = (list_id, node_id)
        node = nodes.setdefault(key, {
            "nodeId": node_id,
            "iri": _value(binding, "node"),
            "label": "",
            "usages": {},
            "presentInList": True,
        })
        node["label"] = _preferred_text(node["label"], _value(binding, "label"), binding, "label")

    for binding in usage_bindings:
        list_id = _value(binding, "listId")
        node_id = _value(binding, "nodeId")
        key = (list_id, node_id)
        node = nodes.setdefault(key, {
            "nodeId": node_id,
            "iri": _value(binding, "node"),
            "label": "",
            "usages": {},
            "presentInList": False,
        })
        usage_key = (_value(binding, "resource"), _value(binding, "property"))
        usage = node["usages"].setdefault(usage_key, {
            "resource": usage_key[0],
            "property": usage_key[1],
            "name": "",
            "classes": set(),
        })
        usage["name"] = _preferred_text(
            usage["name"], _value(binding, "resourceName"), binding, "resourceName"
        )
        resource_class = _value(binding, "resourceClass")
        if resource_class:
            usage["classes"].add(resource_class)

    lists = []
    for list_id, rules in mapping.items():
        list_nodes = []
        keys = sorted({key for key in nodes if key[0] == list_id} | {(list_id, node_id) for node_id in rules})
        for key in keys:
            node_id = key[1]
            source = nodes.get(key, {
                "nodeId": node_id,
                "iri": f"{namespace}{list_id}#{node_id}",
                "label": "",
                "usages": {},
                "presentInList": False,
            })
            rule = rules.get(node_id)
            usages = []
            for usage in source["usages"].values():
                usages.append({
                    **{key: value for key, value in usage.items() if key != "classes"},
                    "classes": sorted(usage["classes"]),
                })
            usages.sort(key=lambda entry: (entry["name"].casefold(), entry["resource"], entry["property"]))
            list_nodes.append({
                "nodeId": node_id,
                "iri": source["iri"],
                "label": source["label"],
                "presentInList": source["presentInList"],
                "mappingMode": rule.mode if rule else "unmapped",
                "sourceState": rule.source_state if rule else "unknown",
                "targetList": rule.target_list if rule else None,
                "targetNodes": list(rule.target_nodes) if rule else [],
                "mappingNote": rule.note if rule else "No Phase-1 mapping rule.",
                "usageCount": len(usages),
                "usages": usages,
            })
        lists.append({
            "listId": list_id,
            "nodeCount": len(list_nodes),
            "usedNodeCount": sum(1 for node in list_nodes if node["usageCount"]),
            "referenceCount": sum(node["usageCount"] for node in list_nodes),
            "reviewReferenceCount": sum(
                node["usageCount"] for node in list_nodes if node["mappingMode"] in {"review", "unmapped"}
            ),
            "nodes": list_nodes,
        })

    events = _event_candidates(event_outgoing_bindings, event_incoming_bindings, namespace)
    timestamp = generated_at or datetime.now(timezone.utc)
    return {
        "version": 1,
        "generatedAt": timestamp.isoformat(),
        "mode": "read-only",
        "project": project_id,
        "namespace": namespace,
        "taxonomyLists": lists,
        "events": {
            "eventCount": len(events),
            "reviewCandidateCount": sum(1 for event in events if event["reviewCandidate"]),
            "deletionCandidateCount": sum(1 for event in events if event["deletionCandidate"]),
            "items": events,
        },
    }


def write_inventory_report(path: Path, report: dict[str, Any]) -> None:
    """Write a JSON or YAML inventory report without changing OLDAP state."""

    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".json":
        content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    elif suffix in {".yaml", ".yml"}:
        content = yaml.safe_dump(report, allow_unicode=True, sort_keys=False)
    else:
        raise ValueError("Inventory report must use .json, .yaml, or .yml.")
    path.write_text(content, encoding="utf-8")


def run_fasnacht_taxonomy_inventory(
    *,
    graphdb_base: str,
    repo: str,
    user: str,
    password: str,
    mapping_path: Path,
    project_id: str = "fasnacht",
    graphdb_user: str | None = None,
    graphdb_password: str | None = None,
) -> dict[str, Any]:
    """Run the connected, strictly read-only Phase-1 inventory."""

    mapping = load_mapping(mapping_path)
    taxonomy_dir = mapping_path.parent
    source_taxonomy_paths = {
        "ObjectTaxonomy": taxonomy_dir / "ObjectTaxonomy-PrePhase2.yaml",
        "CarnivalEventTaxonomy": taxonomy_dir / "CarnivalEventTaxonomy-PrePhase2.yaml",
        "CarnivalTopicsTaxonomy": taxonomy_dir / "CarnivalTopicsTaxonomy.yaml",
        "OrganisationTaxonomy": taxonomy_dir / "OrganisationTaxonomy.yaml",
    }
    validate_mapping_coverage(mapping, {
        list_id: source_taxonomy_paths.get(list_id, taxonomy_dir / f"{list_id}.yaml")
        for list_id in mapping
    })
    validate_mapping_targets(mapping, {
        "ObjectTaxonomy": taxonomy_dir / "ObjectTaxonomy.yaml",
        "CarnivalEventTaxonomy": taxonomy_dir / "CarnivalEventTaxonomy.yaml",
        "CarnivalPracticeTaxonomy": taxonomy_dir / "CarnivalPracticeTaxonomy.yaml",
    })
    connection = create_connection(
        graphdb_base=graphdb_base,
        repo=repo,
        user=user,
        password=password,
        graphdb_user=graphdb_user,
        graphdb_password=graphdb_password,
    )
    project = Project.read(connection, project_id, ignore_cache=True)
    namespace = str(project.namespaceIri)
    list_ids = list(mapping)
    return build_inventory_report(
        project_id=project_id,
        namespace=namespace,
        mapping=mapping,
        node_bindings=_bindings(connection.query(build_list_node_query(namespace, list_ids))),
        usage_bindings=_bindings(connection.query(build_taxonomy_usage_query(namespace, list_ids))),
        event_outgoing_bindings=_bindings(connection.query(build_event_outgoing_query(namespace))),
        event_incoming_bindings=_bindings(connection.query(build_event_incoming_query(namespace))),
    )
