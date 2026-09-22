"""Plan conservative taxonomy extensions using existing OLDAP HTTP endpoints.

Both desired and downloaded lists use the canonical list YAML format. Planning
is pure: all duplicate IDs and parent changes are rejected before any write.
Existing labels, definitions, node positions and omitted nodes are preserved.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName

from oldap_tools.api_client import ApiOperation, OldapApiClient, api_path
from oldap_tools.list_merge import _read_yaml_lists, _validate_yaml_lists
from oldap_tools.ontology import _resolve_list_path


def read_api_lists(client: OldapApiClient, project: str, namespace: str) -> dict[str, bytes]:
    """Download and validate every project taxonomy through existing API routes.

    Accept QName or full-IRI inventory entries, but reject foreign identities,
    duplicate lists and malformed YAML before callers publish files or mutate.
    """
    found = client.get_json("/admin/hlist/search", project=project)
    if not isinstance(found, list):
        raise ValueError("API returned an invalid taxonomy inventory.")
    result = {}
    for list_iri in found:
        if not isinstance(list_iri, str):
            raise ValueError("API returned an invalid taxonomy identity.")
        prefix = f"{project}:"
        if list_iri.startswith(prefix):
            list_id = list_iri[len(prefix):]
        elif list_iri.startswith(namespace):
            list_id = list_iri[len(namespace):]
        else:
            raise ValueError(f"API returned a taxonomy outside project {project}.")
        Xsd_NCName(list_id, validate=True)
        if list_id in result:
            raise ValueError(f"API returned duplicate taxonomy {list_id}.")
        raw = client.get_bytes(api_path("admin", "hlist", project, list_id, "download"))
        _validate_yaml_lists(raw.decode("utf-8"))
        data = yaml.safe_load(raw)
        if not isinstance(data, dict) or set(data) != {list_id} or not isinstance(data[list_id], dict):
            raise ValueError(f"API returned invalid YAML for list {list_id}.")
        _index_tree(data[list_id].get("nodes", {}))
        result[list_id] = raw
    return dict(sorted(result.items()))


def read_list_specs(base_dir: Path, specs: dict[str, Any]) -> dict[str, dict]:
    """Resolve local list files before network access, including multi-list files.

    A file must contain its declared list ID. Conflicting definitions of the
    same list are rejected rather than depending on file traversal order.
    """
    result: dict[str, dict] = {}
    for list_id, spec in specs.items():
        if isinstance(spec, str):
            definitions = _read_yaml_lists(_resolve_list_path(base_dir, spec))
            if list_id not in definitions:
                raise ValueError(f'List file "{spec}" does not contain "{list_id}".')
        elif isinstance(spec, dict):
            definitions = {list_id: spec}
            _validate_yaml_lists(yaml.safe_dump(definitions))
        else:
            raise ValueError(f'Invalid list specification for "{list_id}".')
        for key, definition in definitions.items():
            if key in result and result[key] != definition:
                raise ValueError(f'Conflicting definitions for list "{key}".')
            _index_tree(definition.get("nodes", {}))
            result[key] = definition
    return result


def _index_tree(nodes: dict, parent: str | None = None, *, parents: dict | None = None, children: dict | None = None) -> tuple[dict, dict]:
    """Index tree identities/parents and ordered children, rejecting duplicates."""
    if not isinstance(nodes, dict):
        raise ValueError("Taxonomy nodes must be a mapping.")
    if parents is None:
        parents, children = {}, {}
    children[parent] = list(nodes)
    for node_id, spec in nodes.items():
        Xsd_NCName(node_id, validate=True)
        if not isinstance(spec, dict):
            raise ValueError(f'List node "{node_id}" must be a mapping.')
        if node_id in parents:
            raise ValueError(f'List node "{node_id}" occurs more than once.')
        parents[node_id] = parent
        _index_tree(spec.get("nodes", {}), node_id, parents=parents, children=children)
    return parents, children


def plan_list(project: str, list_id: str, desired: dict, current: dict | None) -> list[ApiOperation]:
    """Plan list creation and ordered insertions; never rename, move or delete."""
    wanted_parents, _ = _index_tree(desired.get("nodes", {}))
    parents, children = _index_tree((current or {}).get("nodes", {}))
    for node_id, parent in wanted_parents.items():
        if node_id in parents and parents[node_id] != parent:
            raise ValueError(f'List {list_id}: node "{node_id}" cannot be moved from '
                             f'{parents[node_id] or "<root>"} to {parent or "<root>"}.')
    path = api_path("admin", "hlist", project, list_id)
    operations = []
    if current is None:
        payload = {"prefLabel": desired["label"]}
        if desired.get("definition"):
            payload["definition"] = desired["definition"]
        operations.append(ApiOperation("PUT", path, payload))

    def visit(nodes: dict, parent: str | None) -> None:
        """Place new siblings around existing anchors, then visit descendants."""
        siblings = children.setdefault(parent, [])
        previous = None
        ids = list(nodes)
        for index, (node_id, spec) in enumerate(nodes.items()):
            if node_id not in parents:
                right = next((key for key in ids[index + 1:] if key in siblings), None)
                left = previous or (siblings[-1] if right is None and siblings else None)
                if left is not None:
                    position, reference = "rightOf", left
                    insert_at = siblings.index(left) + 1
                elif right is not None:
                    position, reference = "leftOf", right
                    insert_at = siblings.index(right)
                elif parent is not None:
                    position, reference, insert_at = "belowOf", parent, 0
                else:
                    position, reference, insert_at = "root", None, 0
                payload = {"prefLabel": spec["label"], "position": position}
                if reference is not None:
                    payload["refnode"] = reference
                if spec.get("definition"):
                    payload["definition"] = spec["definition"]
                operations.append(ApiOperation("PUT", api_path("admin", "hlist", project, list_id, node_id), payload))
                siblings.insert(insert_at, node_id)
                parents[node_id] = parent
            previous = node_id
            visit(spec.get("nodes", {}), node_id)

    visit(desired.get("nodes", {}), None)
    return operations
