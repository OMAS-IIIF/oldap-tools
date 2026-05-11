from pathlib import Path
from typing import Any

import tempfile
import yaml
import yamale
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.oldaplist_helpers import load_list_from_yaml
from oldaplib.src.oldaplistnode import OldapListNode
from oldaplib.src.project import Project
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName


def list_exists_in_store(con: Connection, project: Project, list_id: str) -> bool:
    from oldaplib.src.helpers.context import Context

    context = Context(name=con.context_name)
    context[project.projectShortName] = project.namespaceIri
    list_iri = f"{project.projectShortName}:{list_id}"
    sparql = context.sparql_context
    sparql += f"""
    ASK {{
        GRAPH {project.projectShortName}:lists {{
            {list_iri} a oldap:OldapList .
        }}
    }}
    """
    return con.query(sparql)["boolean"]


def _validate_yaml_lists(content: str) -> None:
    schema = yamale.make_schema(content="""
map(include('node'))
---
node:
  label: list(str(matches='^.*@[ -~]{2}$'))
  definition: list(str(matches='^.*@[ -~]{2}$'), required=False)
  nodes: map(include('node'), required=False)
""")
    yamale.validate(schema=schema, data=yamale.make_data(content=content))


def _read_yaml_lists(filepath: Path) -> dict[str, Any]:
    content = filepath.read_text(encoding="utf-8")
    _validate_yaml_lists(content)
    data = yaml.safe_load(content)
    if not isinstance(data, dict):
        raise ValueError(f'List YAML "{filepath}" must contain a top-level mapping.')
    return data


def _create_list_from_spec(con: Connection, project: Project, list_id: str, spec: dict[str, Any]) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", encoding="utf-8", delete=False) as f:
        yaml.safe_dump({list_id: spec}, f, allow_unicode=True, sort_keys=False)
        path = Path(f.name)
    try:
        load_list_from_yaml(con=con, project=project, filepath=path)
    finally:
        path.unlink(missing_ok=True)


def _index_nodes(
    nodes: list[OldapListNode] | None,
    parent_id: str | None,
    by_id: dict[str, OldapListNode],
    parent_by_id: dict[str, str | None],
    children_by_parent: dict[str | None, list[OldapListNode]],
) -> None:
    children_by_parent[parent_id] = list(nodes or [])
    for node in nodes or []:
        node_id = str(node.oldapListNodeId)
        by_id[node_id] = node
        parent_by_id[node_id] = parent_id
        _index_nodes(node.nodes, node_id, by_id, parent_by_id, children_by_parent)


def _validate_no_moves(
    yaml_nodes: dict[str, Any] | None,
    parent_id: str | None,
    by_id: dict[str, OldapListNode],
    parent_by_id: dict[str, str | None],
    seen: set[str],
) -> None:
    for node_id, spec in (yaml_nodes or {}).items():
        if node_id in seen:
            raise ValueError(f'List node "{node_id}" occurs more than once in the YAML tree.')
        seen.add(node_id)
        if not isinstance(spec, dict):
            raise ValueError(f'List node "{node_id}" must contain a mapping.')
        existing = by_id.get(node_id)
        if existing is not None:
            current_parent = parent_by_id[node_id]
            if current_parent != parent_id:
                expected = parent_id or "<root>"
                actual = current_parent or "<root>"
                raise ValueError(
                    f'List node "{node_id}" already exists under "{actual}" and cannot be moved to "{expected}".'
                )
        _validate_no_moves(spec.get("nodes"), node_id, by_id, parent_by_id, seen)


def _new_node(con: Connection, oldaplist: OldapList, node_id: str, spec: dict[str, Any]) -> OldapListNode:
    return OldapListNode(
        con=con,
        **oldaplist.info,
        oldapListNodeId=Xsd_NCName(node_id),
        prefLabel=LangString(spec.get("label")) or None,
        definition=LangString(spec.get("definition")) or None,
    )


def _insert_node(
    con: Connection,
    oldaplist: OldapList,
    node_id: str,
    spec: dict[str, Any],
    parent_node: OldapListNode | None,
    left_sibling: OldapListNode | None,
    right_sibling: OldapListNode | None,
) -> OldapListNode:
    node = _new_node(con, oldaplist, node_id, spec)
    if left_sibling is not None:
        node.insert_node_right_of(left_sibling)
    elif right_sibling is not None:
        node.insert_node_left_of(right_sibling)
    elif parent_node is not None:
        node.insert_node_below_of(parent_node)
    else:
        node.create_root_node()
    return node


def _merge_nodes(
    con: Connection,
    oldaplist: OldapList,
    yaml_nodes: dict[str, Any] | None,
    parent_id: str | None,
    by_id: dict[str, OldapListNode],
    parent_by_id: dict[str, str | None],
    children_by_parent: dict[str | None, list[OldapListNode]],
) -> None:
    if not yaml_nodes:
        return

    siblings = children_by_parent.setdefault(parent_id, [])
    parent_node = by_id[parent_id] if parent_id is not None else None
    previous_yaml_sibling: OldapListNode | None = None

    for index, (node_id, spec) in enumerate(yaml_nodes.items()):
        if not isinstance(spec, dict):
            raise ValueError(f'List node "{node_id}" must contain a mapping.')

        existing = by_id.get(node_id)
        if existing is not None:
            previous_yaml_sibling = existing
            _merge_nodes(con, oldaplist, spec.get("nodes"), node_id, by_id, parent_by_id, children_by_parent)
            continue

        later_yaml_ids = list(yaml_nodes.keys())[index + 1:]
        right_sibling = next(
            (
                candidate
                for candidate_id in later_yaml_ids
                if (candidate := by_id.get(candidate_id)) is not None and candidate in siblings
            ),
            None,
        )
        left_sibling = previous_yaml_sibling
        if left_sibling is None and right_sibling is None and siblings:
            left_sibling = siblings[-1]
        node = _insert_node(con, oldaplist, node_id, spec, parent_node, left_sibling, right_sibling)
        by_id[node_id] = node
        parent_by_id[node_id] = parent_id

        if right_sibling is not None:
            siblings.insert(siblings.index(right_sibling), node)
        else:
            siblings.append(node)
        if parent_node is not None and parent_node.nodes is None:
            parent_node.nodes = siblings

        previous_yaml_sibling = node
        _merge_nodes(con, oldaplist, spec.get("nodes"), node_id, by_id, parent_by_id, children_by_parent)


def merge_list_from_spec(con: Connection, project: Project, list_id: str, spec: dict[str, Any]) -> OldapList:
    if not isinstance(spec, dict):
        raise ValueError(f'Invalid list specification for "{list_id}"')
    oldaplist = OldapList.read(con=con, project=project, oldapListId=list_id)
    by_id: dict[str, OldapListNode] = {}
    parent_by_id: dict[str, str | None] = {}
    children_by_parent: dict[str | None, list[OldapListNode]] = {}
    _index_nodes(oldaplist.nodes, None, by_id, parent_by_id, children_by_parent)
    _validate_no_moves(spec.get("nodes"), None, by_id, parent_by_id, set())
    _merge_nodes(con, oldaplist, spec.get("nodes"), None, by_id, parent_by_id, children_by_parent)
    return OldapList.read(con=con, project=project, oldapListId=list_id)


def load_or_merge_list_from_spec(con: Connection, project: Project, list_id: str, spec: dict[str, Any]) -> OldapList:
    if list_exists_in_store(con, project, list_id):
        return merge_list_from_spec(con, project, list_id, spec)
    _create_list_from_spec(con, project, list_id, spec)
    return OldapList.read(con=con, project=project, oldapListId=list_id)


def load_or_merge_lists_from_yaml(con: Connection, project: Project, filepath: Path) -> list[OldapList]:
    lists = _read_yaml_lists(filepath)
    return [
        load_or_merge_list_from_spec(con=con, project=project, list_id=list_id, spec=spec)
        for list_id, spec in lists.items()
    ]
