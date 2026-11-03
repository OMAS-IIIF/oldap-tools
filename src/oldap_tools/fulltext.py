"""Offline preparation of portable Jena fulltext configuration.

Field validation is shared with oldaplib's query adapter. This module resolves
ontology namespaces and reports index requirements; it never activates an index.
"""
from copy import deepcopy
from typing import Any

from oldaplib.src.helpers.context import Context
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName


def plan_fulltext(ontology: dict[str, Any]) -> dict[str, Any]:
    """Resolve a YAML fulltext section into a reviewable, JSON-safe plan.

    Args:
        ontology: Inner ontology mapping, including project namespace, optional
            external_ontologies and fulltext.fields.
    Returns:
        Project, data graph, resolved field paths and unique indexed predicates.
        This describes a desired configuration, not the state of a live index.
    Raises:
        ValueError: Missing namespace/configuration or mixed backend formats.
        OldapError: Invalid field, namespace or predicate identifier.
    """
    # Lazy import keeps legacy GraphDB commands usable with released oldaplib.
    try:
        from oldaplib.src.helpers.jena_fulltext import jena_fulltext_fields
    except ImportError as error:
        raise ValueError("Fulltext planning requires the migration/jena version of oldaplib.") from error
    if 'fulltext' not in ontology:
        raise ValueError("Ontology has no fulltext section.")
    if 'lucene_connectors' in ontology:
        raise ValueError("Use either fulltext or lucene_connectors, not both in one ontology.")
    project = ontology['project']
    shortname = project['shortname']
    Xsd_NCName(shortname, validate=True)
    if not project.get('namespace'):
        raise ValueError("Offline fulltext planning requires project.namespace.")
    # Context is a named singleton. Copy the untouched baseline so prefixes from
    # one YAML file cannot leak into the next project's validation.
    context = deepcopy(Context(name='OLDAP_TOOLS_FULLTEXT_BASE'))
    namespaces = {shortname: project['namespace']}
    for prefix, spec in (ontology.get('external_ontologies') or {}).items():
        if prefix in namespaces and namespaces[prefix] != spec['namespace']:
            raise ValueError(f"Conflicting namespace for {prefix}.")
        namespaces[prefix] = spec['namespace']
    for prefix, namespace in namespaces.items():
        if context.get(prefix) is not None and str(context[prefix]) != namespace:
            raise ValueError(f"Namespace conflicts with the built-in prefix {prefix}.")
        context[prefix] = namespace
    fields = jena_fulltext_fields(ontology['fulltext'], context)
    return {
        'project': shortname,
        'graph': str(context[shortname]) + 'data',
        'fields': {name: [str(predicate) for predicate in path]
                   for name, path in sorted(fields.items())},
        'indexed_predicates': sorted({str(path[-1]) for path in fields.values()}),
    }


def require_supported_fulltext_import(ontology: dict[str, Any]) -> None:
    """Reject unsupported index administration before any import reads/writes.

    Direct imports and API imports without explicit fulltext apply use this
    guard. Never silently discard configuration or send it to a GraphDB endpoint.
    """
    if 'fulltext' in ontology:
        raise ValueError(
            "Fulltext activation is not yet supported by this import mode; use API transport with --fulltext apply. "
            "Use ontology fulltext-plan to review the configuration offline; "
            "no ontology changes have been applied."
        )
