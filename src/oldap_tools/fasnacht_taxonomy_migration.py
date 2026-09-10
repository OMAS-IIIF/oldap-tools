"""Plan and execute the Fasnacht taxonomy cutover.

The migration is deliberately manifest-driven.  A connected dry-run expands
the Phase-1 mapping and reviewed Phase-2 decisions against current data.  The
resulting digest must be supplied again for apply, which prevents a migration
from running after the source data or decision rules have changed.

Apply performs the project-data, flat-list, and narrowly scoped ontology
changes as one guarded workflow. The full order and production gate are
documented in the Phase-2 runbook.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

import yaml

from oldaplib.src.cachesingleton import CacheSingletonRedis
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.project import Project

from oldap_tools.connection import create_connection
from oldap_tools.dump_project import dump_project
from oldap_tools.fasnacht_taxonomy_inventory import (
    MappingRule,
    load_mapping,
    run_fasnacht_taxonomy_inventory,
)
from oldap_tools.list_merge import load_or_merge_lists_from_yaml
from oldap_tools.ontology import validate_ontology_yaml


SUPPORTED_DECISION_STATUS = frozenset({"local-rehearsal", "approved"})
ARCHIVE_RESOURCE_CLASS_IDS = frozenset({
    "ArchiveObject",
    "CarnivalEvent",
    "ArchiveMediaObject",
})


@dataclass(frozen=True)
class ReviewMatchRule:
    """Reviewed rule for resolving usages that Phase 1 marked for review."""

    source_list: str
    source_node: str
    name_regex: str
    target_nodes: tuple[str, ...]
    expected_count: int
    rationale: str


def load_phase2_decisions(path: Path) -> dict[str, Any]:
    """Load and validate a Phase-2 decision document.

    Args:
        path: Version-1 Phase-2 YAML document.

    Returns:
        A normalized decision dictionary.

    Raises:
        ValueError: If the document is malformed or unsafe to evaluate.
    """

    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("version") != 1:
        raise ValueError("Phase-2 decisions must be a version-1 document.")
    status = document.get("status")
    if status not in SUPPORTED_DECISION_STATUS:
        raise ValueError(f'Unsupported Phase-2 decision status "{status}".')

    included_lists = document.get("included_lists")
    if not isinstance(included_lists, list) or not all(
        isinstance(value, str) and value for value in included_lists
    ):
        raise ValueError("Phase-2 decisions require included_lists.")
    if len(set(included_lists)) != len(included_lists):
        raise ValueError("Phase-2 included_lists contains duplicates.")

    approved_modes = document.get("approved_modes")
    if not isinstance(approved_modes, list) or not set(approved_modes) <= {"exact", "broader"}:
        raise ValueError("approved_modes may contain only exact and broader.")

    target_properties = document.get("target_properties")
    if not isinstance(target_properties, dict):
        raise ValueError("Phase-2 decisions require target_properties.")
    missing_properties = set(included_lists) - set(target_properties)
    if missing_properties:
        raise ValueError(
            "Missing target property for: " + ", ".join(sorted(missing_properties)) + "."
        )

    raw_rules = document.get("review_match_rules", [])
    if not isinstance(raw_rules, list):
        raise ValueError("review_match_rules must be a list.")
    normalized_rules: list[ReviewMatchRule] = []
    for raw_rule in raw_rules:
        if not isinstance(raw_rule, dict):
            raise ValueError("Each review match rule must be an object.")
        source_list = raw_rule.get("source_list")
        source_node = raw_rule.get("source_node")
        name_regex = raw_rule.get("name_regex")
        target_nodes = raw_rule.get("target_nodes")
        expected_count = raw_rule.get("expected_count")
        if source_list not in included_lists or not isinstance(source_node, str):
            raise ValueError("Review rule requires an included source_list and source_node.")
        if not isinstance(name_regex, str) or not name_regex:
            raise ValueError("Review rule requires name_regex.")
        try:
            re.compile(name_regex)
        except re.error as error:
            raise ValueError(f'Invalid review regex "{name_regex}": {error}.') from error
        if not isinstance(target_nodes, list) or not target_nodes or not all(
            isinstance(value, str) and value for value in target_nodes
        ):
            raise ValueError("Review rule requires at least one target node.")
        if not isinstance(expected_count, int) or expected_count < 0:
            raise ValueError("Review rule expected_count must be a non-negative integer.")
        normalized_rules.append(ReviewMatchRule(
            source_list=source_list,
            source_node=source_node,
            name_regex=name_regex,
            target_nodes=tuple(target_nodes),
            expected_count=expected_count,
            rationale=str(raw_rule.get("rationale", "")).strip(),
        ))

    return {
        "version": 1,
        "status": status,
        "included_lists": tuple(included_lists),
        "approved_modes": frozenset(approved_modes),
        "target_properties": dict(target_properties),
        "review_match_rules": tuple(normalized_rules),
    }


def _inventory_lists(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["listId"]: entry for entry in report.get("taxonomyLists", [])}


def _target_node_iri(namespace: str, target_list: str, target_node: str) -> str:
    return f"{namespace}{target_list}#{target_node}"


def _matched_review_rule(
    *,
    rules: tuple[ReviewMatchRule, ...],
    source_list: str,
    source_node: str,
    name: str,
) -> ReviewMatchRule | None:
    matches = [
        rule
        for rule in rules
        if rule.source_list == source_list
        and rule.source_node == source_node
        and re.search(rule.name_regex, name)
    ]
    if len(matches) > 1:
        raise ValueError(
            f'Multiple Phase-2 review rules match "{source_list}:{source_node}" / "{name}".'
        )
    return matches[0] if matches else None


def build_migration_plan(
    *,
    inventory: dict[str, Any],
    mapping: dict[str, dict[str, MappingRule]],
    decisions: dict[str, Any],
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Expand current usages into an auditable migration manifest.

    Automatic exact/broader rules and reviewed regex decisions are both
    materialized as resource IRIs in the output.  Apply is permitted only when
    the manifest has no unresolved usages and all rule counts match.
    """

    namespace = inventory["namespace"]
    inventory_lists = _inventory_lists(inventory)
    rule_counts = {rule: 0 for rule in decisions["review_match_rules"]}
    resolved: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    out_of_scope: list[dict[str, Any]] = []
    allowed_resource_classes = {
        f"{namespace}{class_id}"
        for class_id in ARCHIVE_RESOURCE_CLASS_IDS
    }

    for list_id in decisions["included_lists"]:
        if list_id not in inventory_lists:
            raise ValueError(f'Inventory does not contain included list "{list_id}".')
        for node in inventory_lists[list_id].get("nodes", []):
            if not node.get("usageCount"):
                continue
            source_node = node["nodeId"]
            mapping_rule = mapping.get(list_id, {}).get(source_node)
            for usage in node.get("usages", []):
                resource_classes = set(usage.get("classes", []))
                if (
                    not resource_classes
                    or not resource_classes <= allowed_resource_classes
                ):
                    out_of_scope.append({
                        "sourceList": list_id,
                        "sourceNode": source_node,
                        "resource": usage["resource"],
                        "property": usage["property"],
                        "name": usage.get("name", ""),
                        "resourceClasses": sorted(resource_classes),
                        "reason": (
                            "Taxonomy reference is not exclusively attached to an "
                            "ArchiveObject, CarnivalEvent, or ArchiveMediaObject."
                        ),
                    })
                    continue
                target_nodes: tuple[str, ...] = ()
                decision_kind = ""
                rationale = ""
                if (
                    mapping_rule is not None
                    and mapping_rule.mode in decisions["approved_modes"]
                    and mapping_rule.target_nodes
                ):
                    target_nodes = mapping_rule.target_nodes
                    decision_kind = mapping_rule.mode
                    rationale = mapping_rule.note
                else:
                    review_rule = _matched_review_rule(
                        rules=decisions["review_match_rules"],
                        source_list=list_id,
                        source_node=source_node,
                        name=usage.get("name", ""),
                    )
                    if review_rule is not None:
                        target_nodes = review_rule.target_nodes
                        decision_kind = "reviewed"
                        rationale = review_rule.rationale
                        rule_counts[review_rule] += 1

                if not target_nodes or mapping_rule is None or mapping_rule.target_list is None:
                    unresolved.append({
                        "sourceList": list_id,
                        "sourceNode": source_node,
                        "resource": usage["resource"],
                        "property": usage["property"],
                        "name": usage.get("name", ""),
                        "reason": "No approved automatic mapping or matching reviewed decision.",
                    })
                    continue

                target_property = decisions["target_properties"][list_id]
                target_iris = sorted({
                    _target_node_iri(namespace, mapping_rule.target_list, target_node)
                    for target_node in target_nodes
                })
                resolved.append({
                    "sourceList": list_id,
                    "sourceNode": source_node,
                    "sourceNodeIri": node["iri"],
                    "resource": usage["resource"],
                    "sourceProperty": usage["property"],
                    "targetProperty": target_property,
                    "targetNodeIris": target_iris,
                    "name": usage.get("name", ""),
                    "resourceClasses": sorted(resource_classes),
                    "decision": decision_kind,
                    "rationale": rationale,
                })

    count_errors = []
    for rule, actual_count in rule_counts.items():
        if actual_count != rule.expected_count:
            count_errors.append({
                "sourceList": rule.source_list,
                "sourceNode": rule.source_node,
                "nameRegex": rule.name_regex,
                "expectedCount": rule.expected_count,
                "actualCount": actual_count,
            })

    resolved.sort(key=lambda entry: (
        entry["sourceList"], entry["resource"], entry["sourceProperty"], entry["sourceNode"]
    ))
    unresolved.sort(key=lambda entry: (
        entry["sourceList"], entry["sourceNode"], entry["name"].casefold(), entry["resource"]
    ))
    out_of_scope.sort(key=lambda entry: (
        entry["sourceList"], entry["sourceNode"], entry["name"].casefold(), entry["resource"]
    ))
    actionable = [
        entry
        for entry in resolved
        if entry["sourceProperty"] != entry["targetProperty"]
        or entry["sourceNodeIri"] not in entry["targetNodeIris"]
        or len(entry["targetNodeIris"]) != 1
    ]
    unchanged = [entry for entry in resolved if entry not in actionable]
    digest_payload = {
        "project": inventory["project"],
        "namespace": namespace,
        "decisionStatus": decisions["status"],
        "protectedState": {
            "eventResourceCount": inventory.get("events", {}).get("eventCount", 0),
            "organisationReferenceCount": inventory_lists.get("OrganisationTaxonomy", {}).get("referenceCount", 0),
        },
        "resolved": resolved,
        "unresolved": unresolved,
        "outOfScope": out_of_scope,
        "ruleCountErrors": count_errors,
    }
    digest = hashlib.sha256(
        json.dumps(digest_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    timestamp = generated_at or datetime.now(timezone.utc)
    return {
        "version": 1,
        "generatedAt": timestamp.isoformat(),
        "mode": "dry-run",
        "project": inventory["project"],
        "namespace": namespace,
        "decisionStatus": decisions["status"],
        "protectedState": digest_payload["protectedState"],
        "digest": digest,
        "readyToApply": not unresolved and not out_of_scope and not count_errors,
        "summary": {
            "resolvedReferenceCount": len(resolved),
            "actionableReferenceCount": len(actionable),
            "unchangedReferenceCount": len(unchanged),
            "unresolvedReferenceCount": len(unresolved),
            "outOfScopeReferenceCount": len(out_of_scope),
            "ruleCountErrorCount": len(count_errors),
        },
        "actions": actionable,
        "unchanged": unchanged,
        "unresolved": unresolved,
        "outOfScope": out_of_scope,
        "ruleCountErrors": count_errors,
    }


def write_migration_plan(path: Path, plan: dict[str, Any]) -> None:
    """Write a Phase-2 plan in YAML or JSON format."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".json":
        content = json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
    elif path.suffix.lower() in {".yaml", ".yml"}:
        content = yaml.safe_dump(plan, allow_unicode=True, sort_keys=False)
    else:
        raise ValueError("Migration plan must use .json, .yaml, or .yml.")
    path.write_text(content, encoding="utf-8")


def run_fasnacht_taxonomy_migration_plan(
    *,
    graphdb_base: str,
    repo: str,
    user: str,
    password: str,
    mapping_path: Path,
    decisions_path: Path,
    project_id: str = "fasnacht",
    graphdb_user: str | None = None,
    graphdb_password: str | None = None,
) -> dict[str, Any]:
    """Build a fresh connected Phase-2 plan without changing OLDAP state."""

    mapping = load_mapping(mapping_path)
    decisions = load_phase2_decisions(decisions_path)
    inventory = run_fasnacht_taxonomy_inventory(
        graphdb_base=graphdb_base,
        repo=repo,
        user=user,
        password=password,
        mapping_path=mapping_path,
        project_id=project_id,
        graphdb_user=graphdb_user,
        graphdb_password=graphdb_password,
    )
    return build_migration_plan(
        inventory=inventory,
        mapping=mapping,
        decisions=decisions,
    )


def _iri(value: str) -> str:
    """Return a SPARQL IRI token after rejecting unsafe input."""

    if not re.fullmatch(r"(?:https?://|urn:)[^<>\s]+", value):
        raise ValueError(f'Unsafe or unsupported IRI "{value}".')
    return f"<{value}>"


def _lang_literal(value: str) -> str:
    """Convert the OLDAP list-YAML ``text@language`` form to SPARQL."""

    text, separator, language = value.rpartition("@")
    if not separator or not re.fullmatch(r"[A-Za-z]{2}(?:-[A-Za-z0-9]+)*", language):
        raise ValueError(f'Invalid language-tagged list value "{value}".')
    return f"{json.dumps(text, ensure_ascii=False)}@{language}"


def _read_flat_taxonomy(path: Path) -> tuple[str, dict[str, Any]]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or len(document) != 1:
        raise ValueError(f"{path} must contain exactly one taxonomy.")
    list_id, specification = next(iter(document.items()))
    if not isinstance(specification, dict) or not isinstance(specification.get("nodes"), dict):
        raise ValueError(f"{path} contains an invalid taxonomy.")
    for node_id, node in specification["nodes"].items():
        if not isinstance(node, dict):
            raise ValueError(f'Node "{node_id}" in {path} must be an object.')
        if node.get("nodes"):
            raise ValueError(f'Taxonomy "{list_id}" must be flat for Phase 2.')
    return str(list_id), specification


def build_data_reference_update(plan: dict[str, Any]) -> str:
    """Build the transactional SPARQL update for all actionable references."""

    graph = _iri(f"{plan['namespace']}data")
    deletes: set[tuple[str, str, str]] = set()
    inserts: set[tuple[str, str, str]] = set()
    for action in plan["actions"]:
        deletes.add((action["resource"], action["sourceProperty"], action["sourceNodeIri"]))
        for target in action["targetNodeIris"]:
            inserts.add((action["resource"], action["targetProperty"], target))

    delete_lines = "\n".join(
        f"    {_iri(subject)} {_iri(predicate)} {_iri(obj)} ."
        for subject, predicate, obj in sorted(deletes)
    )
    insert_lines = "\n".join(
        f"    {_iri(subject)} {_iri(predicate)} {_iri(obj)} ."
        for subject, predicate, obj in sorted(inserts)
    )
    return f"""
DELETE DATA {{
  GRAPH {graph} {{
{delete_lines}
  }}
}};
INSERT DATA {{
  GRAPH {graph} {{
{insert_lines}
  }}
}}
""".strip()


def build_flat_list_replacement_update(
    *,
    namespace: str,
    taxonomy_path: Path,
    contributor_iri: str,
) -> str:
    """Build a full in-place replacement for one OLDAP list's node tree.

    Stable node IRIs are retained, but list-node audit timestamps are recreated
    because the operation replaces the complete old tree in one transaction.
    """

    list_id, specification = _read_flat_taxonomy(taxonomy_path)
    list_iri = f"{namespace}{list_id}"
    node_class_iri = f"{namespace}{list_id}Node"
    list_triples = []
    for label in specification.get("label", []):
        list_triples.append(f"    {_iri(list_iri)} skos:prefLabel {_lang_literal(label)} .")
    for definition in specification.get("definition", []):
        list_triples.append(f"    {_iri(list_iri)} skos:definition {_lang_literal(definition)} .")
    list_triples.extend([
        f"    {_iri(list_iri)} dcterms:modified ?now .",
        f"    {_iri(list_iri)} dcterms:contributor {_iri(contributor_iri)} .",
    ])

    node_triples = []
    for position, (node_id, node) in enumerate(specification["nodes"].items()):
        node_iri = f"{list_iri}#{node_id}"
        left_index = position * 2 + 1
        right_index = left_index + 1
        node_triples.extend([
            f"    {_iri(node_iri)} rdf:type {_iri(node_class_iri)} ;",
            f"      skos:inScheme {_iri(list_iri)} ;",
            f"      oldap:leftIndex {left_index} ;",
            f"      oldap:rightIndex {right_index} ;",
            f"      dcterms:created ?now ;",
            f"      dcterms:creator {_iri(contributor_iri)} ;",
            f"      dcterms:modified ?now ;",
            f"      dcterms:contributor {_iri(contributor_iri)} .",
        ])
        for label in node.get("label", []):
            node_triples.append(f"    {_iri(node_iri)} skos:prefLabel {_lang_literal(label)} .")
        for definition in node.get("definition", []):
            node_triples.append(f"    {_iri(node_iri)} skos:definition {_lang_literal(definition)} .")

    inserted = "\n".join(list_triples + node_triples)
    return f"""
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX oldap: <http://oldap.org/base#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
DELETE {{
  GRAPH {_iri(f'{namespace}lists')} {{
    {_iri(list_iri)} skos:prefLabel ?oldListLabel .
    {_iri(list_iri)} skos:definition ?oldListDefinition .
    {_iri(list_iri)} dcterms:modified ?oldListModified .
    {_iri(list_iri)} dcterms:contributor ?oldListContributor .
    ?oldNode ?nodePredicate ?nodeObject .
  }}
}}
INSERT {{
  GRAPH {_iri(f'{namespace}lists')} {{
{inserted}
  }}
}}
WHERE {{
  BIND(NOW() AS ?now)
  OPTIONAL {{ GRAPH {_iri(f'{namespace}lists')} {{ {_iri(list_iri)} skos:prefLabel ?oldListLabel . }} }}
  OPTIONAL {{ GRAPH {_iri(f'{namespace}lists')} {{ {_iri(list_iri)} skos:definition ?oldListDefinition . }} }}
  OPTIONAL {{ GRAPH {_iri(f'{namespace}lists')} {{ {_iri(list_iri)} dcterms:modified ?oldListModified . }} }}
  OPTIONAL {{ GRAPH {_iri(f'{namespace}lists')} {{ {_iri(list_iri)} dcterms:contributor ?oldListContributor . }} }}
  OPTIONAL {{
    GRAPH {_iri(f'{namespace}lists')} {{
      ?oldNode skos:inScheme {_iri(list_iri)} ; ?nodePredicate ?nodeObject .
    }}
  }}
}}
""".strip()


def build_reference_verification_query(plan: dict[str, Any]) -> str:
    """Build a query returning stale sources or missing migration targets."""

    source_rows = []
    target_rows = []
    for action in plan["actions"]:
        source_rows.append(
            f"({_iri(action['resource'])} {_iri(action['sourceProperty'])} {_iri(action['sourceNodeIri'])})"
        )
        target_rows.extend(
            f"({_iri(action['resource'])} {_iri(action['targetProperty'])} {_iri(target)})"
            for target in action["targetNodeIris"]
        )
    return f"""
SELECT ?kind ?resource ?property ?value
WHERE {{
  {{
    VALUES (?resource ?property ?value) {{ {' '.join(sorted(set(source_rows)))} }}
    GRAPH {_iri(f"{plan['namespace']}data")} {{ ?resource ?property ?value . }}
    BIND("stale-source" AS ?kind)
  }}
  UNION
  {{
    VALUES (?resource ?property ?value) {{ {' '.join(sorted(set(target_rows)))} }}
    FILTER NOT EXISTS {{ GRAPH {_iri(f"{plan['namespace']}data")} {{ ?resource ?property ?value . }} }}
    BIND("missing-target" AS ?kind)
  }}
}}
LIMIT 20
""".strip()


def build_practice_model_cutover_update(namespace: str) -> str:
    """Replace the two old topic property shapes with practice property shapes.

    OLDAP refuses an incremental ResourceClass update while instances exist,
    while rebuilding the entire model is unnecessarily broad.  This focused
    model-graph update changes only the two declared property shapes and their
    OWL property declaration.
    """

    shacl_graph = _iri(f"{namespace}shacl")
    onto_graph = _iri(f"{namespace}onto")
    carnival_thing_shape = _iri(f"{namespace}CarnivalThingShape")
    media_shape = _iri(f"{namespace}ArchiveMediaObjectShape")
    topics_class = _iri(f"{namespace}CarnivalTopicsTaxonomyNode")
    practice_class = _iri(f"{namespace}CarnivalPracticeTaxonomyNode")
    practice_property = _iri(f"{namespace}carnivalPractice")
    return f"""
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
DELETE {{
  GRAPH {shacl_graph} {{
    ?classShape sh:property ?oldPropertyShape .
    ?oldPropertyShape ?predicate ?object .
  }}
}}
WHERE {{
  VALUES ?classShape {{ {carnival_thing_shape} {media_shape} }}
  GRAPH {shacl_graph} {{
    ?classShape sh:property ?oldPropertyShape .
    ?oldPropertyShape sh:path dcterms:subject ; sh:class {topics_class} ; ?predicate ?object .
  }}
}};
INSERT DATA {{
  GRAPH {shacl_graph} {{
    {carnival_thing_shape} sh:property _:carnivalThingPractice .
    _:carnivalThingPractice
      sh:path {practice_property} ;
      sh:class {practice_class} ;
      sh:name "Carnival practice"@en, "Praxis / Handlung"@de, "Pratique carnavalesque"@fr, "Pratica carnevalesca"@it ;
      sh:description "Cultural practices or forms of expression represented by this carnival thing."@en,
        "Kulturelle Praktiken oder Ausdrucksformen, die durch dieses Fasnachtsding dargestellt werden."@de,
        "Pratiques culturelles ou formes d'expression représentées par cet objet carnavalesque."@fr,
        "Pratiche culturali o forme di espressione rappresentate da questo oggetto carnevalesco."@it ;
      sh:order "3.0"^^xsd:decimal .

    {media_shape} sh:property _:mediaPractice .
    _:mediaPractice
      sh:path {practice_property} ;
      sh:class {practice_class} ;
      sh:name "Carnival practice"@en, "Praxis / Handlung"@de, "Pratique carnavalesque"@fr, "Pratica carnevalesca"@it ;
      sh:description "Cultural practices or forms of expression directly depicted or addressed by this archive media item."@en,
        "Kulturelle Praktiken oder Ausdrucksformen, die dieses Archivmedium direkt darstellt oder behandelt."@de,
        "Pratiques culturelles ou formes d'expression directement représentées ou abordées par cet objet média d'archive."@fr,
        "Pratiche culturali o forme di espressione direttamente rappresentate o trattate da questo oggetto multimediale d'archivio."@it ;
      sh:order "6.0"^^xsd:decimal .
  }}
}};
DELETE DATA {{ GRAPH {onto_graph} {{ dcterms:subject rdf:type owl:ObjectProperty . }} }};
INSERT DATA {{ GRAPH {onto_graph} {{ {practice_property} rdf:type owl:ObjectProperty . }} }}
""".replace(
        "PREFIX dcterms:",
        "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\nPREFIX dcterms:",
        1,
    ).strip()


def _bindings(result: dict[str, Any]) -> list[dict[str, Any]]:
    return result.get("results", {}).get("bindings", [])


def verify_post_cutover_state(
    *,
    connection: Any,
    plan: dict[str, Any],
    taxonomy_paths: tuple[Path, ...],
) -> None:
    """Verify exact flat lists, practice shapes, and protected data counts."""

    namespace = plan["namespace"]
    expected_lists: dict[str, set[str]] = {}
    values = []
    for path in taxonomy_paths:
        list_id, specification = _read_flat_taxonomy(path)
        expected_lists[list_id] = set(specification["nodes"])
        values.append(
            f"({_iri(f'{namespace}{list_id}')} {json.dumps(list_id)} "
            f"{json.dumps(f'{namespace}{list_id}#')})"
        )
    list_query = f"""
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?listId ?nodeId ?parent
WHERE {{
  VALUES (?list ?listId ?prefix) {{ {' '.join(values)} }}
  GRAPH {_iri(f'{namespace}lists')} {{
    ?node skos:inScheme ?list .
    BIND(STRAFTER(STR(?node), ?prefix) AS ?nodeId)
    OPTIONAL {{ ?node skos:broader ?parent . }}
  }}
}}
""".strip()
    actual_lists = {list_id: set() for list_id in expected_lists}
    parents = []
    for binding in _bindings(connection.query(list_query)):
        list_id = binding["listId"]["value"]
        actual_lists[list_id].add(binding["nodeId"]["value"])
        if "parent" in binding:
            parents.append(binding)
    if actual_lists != expected_lists or parents:
        raise ValueError(
            f"Flat-list verification failed: expected {expected_lists!r}, actual {actual_lists!r}, parents {parents!r}."
        )

    model_query = f"""
PREFIX sh: <http://www.w3.org/ns/shacl#>
SELECT ?shape ?path ?class
WHERE {{
  GRAPH {_iri(f'{namespace}shacl')} {{
    VALUES ?shape {{ {_iri(f'{namespace}CarnivalThingShape')} {_iri(f'{namespace}ArchiveMediaObjectShape')} }}
    ?shape sh:property ?propertyShape .
    ?propertyShape sh:path ?path ; sh:class ?class .
    FILTER(?path IN (<http://purl.org/dc/terms/subject>, {_iri(f'{namespace}carnivalPractice')}))
  }}
}}
""".strip()
    model_rows = _bindings(connection.query(model_query))
    expected_shapes = {
        f"{namespace}CarnivalThingShape",
        f"{namespace}ArchiveMediaObjectShape",
    }
    actual_shapes = {
        row["shape"]["value"]
        for row in model_rows
        if row["path"]["value"] == f"{namespace}carnivalPractice"
        and row["class"]["value"] == f"{namespace}CarnivalPracticeTaxonomyNode"
    }
    if actual_shapes != expected_shapes or len(model_rows) != 2:
        raise ValueError(f"Practice property-shape verification failed: {model_rows!r}.")

    event_count_query = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT (COUNT(DISTINCT ?resource) AS ?count)
WHERE {{
  GRAPH {_iri(f'{namespace}data')} {{
    ?resource rdf:type {_iri(f'{namespace}CarnivalEvent')} .
  }}
}}
""".strip()
    organisation_reference_count_query = f"""
SELECT (COUNT(*) AS ?count)
WHERE {{
  GRAPH {_iri(f'{namespace}data')} {{
    ?resource ?property ?node .
    FILTER(STRSTARTS(STR(?node), {json.dumps(f'{namespace}OrganisationTaxonomy#')}))
  }}
}}
""".strip()
    event_rows = _bindings(connection.query(event_count_query))
    organisation_rows = _bindings(connection.query(organisation_reference_count_query))
    event_count = int(event_rows[0]["count"]["value"]) if event_rows else 0
    organisation_reference_count = (
        int(organisation_rows[0]["count"]["value"]) if organisation_rows else 0
    )
    protected_expected = plan["protectedState"]
    if event_count != protected_expected["eventResourceCount"]:
        raise ValueError("Protected CarnivalEvent resource count changed during taxonomy migration.")
    if organisation_reference_count != protected_expected["organisationReferenceCount"]:
        raise ValueError("Protected OrganisationTaxonomy reference count changed during taxonomy migration.")

    topics_exists_query = f"""
PREFIX oldap: <http://oldap.org/base#>
ASK {{ GRAPH {_iri(f'{namespace}lists')} {{ {_iri(f'{namespace}CarnivalTopicsTaxonomy')} a oldap:OldapList . }} }}
""".strip()
    if connection.query(topics_exists_query).get("boolean"):
        raise ValueError("CarnivalTopicsTaxonomy still exists after the cutover.")


def apply_fasnacht_taxonomy_migration(
    *,
    graphdb_base: str,
    repo: str,
    user: str,
    password: str,
    mapping_path: Path,
    decisions_path: Path,
    ontology_path: Path,
    object_taxonomy_path: Path,
    event_taxonomy_path: Path,
    practice_taxonomy_path: Path,
    backup_path: Path,
    expected_digest: str,
    project_id: str = "fasnacht",
    allow_local_rehearsal: bool = False,
    graphdb_user: str | None = None,
    graphdb_password: str | None = None,
) -> dict[str, Any]:
    """Apply the complete local taxonomy cutover with backup and verification.

    The operation is intentionally restricted to the three decided lists.
    Organisation classification and event-resource deletion are never touched.
    """

    plan = run_fasnacht_taxonomy_migration_plan(
        graphdb_base=graphdb_base,
        repo=repo,
        user=user,
        password=password,
        mapping_path=mapping_path,
        decisions_path=decisions_path,
        project_id=project_id,
        graphdb_user=graphdb_user,
        graphdb_password=graphdb_password,
    )
    if plan["digest"] != expected_digest:
        raise ValueError(
            f"Migration digest changed: expected {expected_digest}, current {plan['digest']}. Run dry-run again."
        )
    if not plan["readyToApply"]:
        raise ValueError(
            "Migration plan has unresolved, out-of-scope, or rule-count errors."
        )
    if plan["decisionStatus"] == "local-rehearsal" and not allow_local_rehearsal:
        raise ValueError("Local-rehearsal decisions require --allow-local-rehearsal.")
    validate_ontology_yaml(inf=ontology_path)

    backup_path.parent.mkdir(parents=True, exist_ok=True)
    if backup_path.exists():
        raise ValueError(f"Backup path already exists: {backup_path}.")
    dump_project(
        project_id=project_id,
        graphdb_base=graphdb_base,
        repo=repo,
        out=backup_path,
        include_data=True,
        include_model=True,
        include_admin=True,
        include_lists=True,
        user=user,
        password=password,
        graphdb_user=graphdb_user,
        graphdb_password=graphdb_password,
    )

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
    load_or_merge_lists_from_yaml(connection, project, practice_taxonomy_path)

    update_parts = [build_data_reference_update(plan)]
    update_parts.extend([
        build_flat_list_replacement_update(
            namespace=plan["namespace"],
            taxonomy_path=path,
            contributor_iri=str(connection.userIri),
        )
        for path in (object_taxonomy_path, event_taxonomy_path)
    ])
    connection.transaction_start()
    try:
        for update in update_parts:
            connection.transaction_update(update)
        violations = _bindings(connection.transaction_query(build_reference_verification_query(plan)))
        if violations:
            raise ValueError(f"Transactional migration verification failed: {violations!r}")
        connection.transaction_commit()
    except Exception:
        connection.transaction_abort()
        raise

    connection.update_query(build_practice_model_cutover_update(plan["namespace"]))

    # Direct SPARQL list/model replacement bypasses oldaplib's object cache.
    CacheSingletonRedis().clear()
    OldapList.read(connection, project, "CarnivalTopicsTaxonomy").delete()
    CacheSingletonRedis().clear()
    violations = _bindings(connection.query(build_reference_verification_query(plan)))
    if violations:
        raise ValueError(f"Post-migration verification failed: {violations!r}")
    verify_post_cutover_state(
        connection=connection,
        plan=plan,
        taxonomy_paths=(object_taxonomy_path, event_taxonomy_path, practice_taxonomy_path),
    )

    return {
        "digest": plan["digest"],
        "backup": str(backup_path),
        "backupSha256": hashlib.sha256(backup_path.read_bytes()).hexdigest(),
        "changedReferenceCount": plan["summary"]["actionableReferenceCount"],
        "unchangedReferenceCount": plan["summary"]["unchangedReferenceCount"],
    }
