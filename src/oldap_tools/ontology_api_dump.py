"""Export API datamodels and taxonomies as a portable ontology YAML package.

All downloads and schema validation finish before publishing output. Existing
files require explicit overwrite; each file is replaced atomically and the main
ontology document is published last. No GraphDB connection is opened.
"""

from __future__ import annotations

import gzip
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

import yaml
import yamale
from oldaplib.src.enums.editor import Editor
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName

from oldap_tools.lucene_api import read_connector
from oldap_tools.api_client import OldapApiClient, api_path
from oldap_tools.list_api import read_api_lists
from oldap_tools.ontology import ATTR_TO_YAML, _as_langstring, _schema_path
from oldap_tools.ontology_api import _index


_PROPERTY_FIELDS = set(ATTR_TO_YAML) | {"datatype", "name", "description", "pattern", "order", "group", "editor"}


def _languages(value: Any) -> dict[str, str]:
    """Convert API language strings to readable YAML language mappings."""
    values = _as_langstring(value)
    return dict(sorted((language.name.lower(), str(text)) for language, text in values.items())) if values else {}


def _export_property(prop: dict, list_classes: dict[str, str]) -> dict:
    """Preserve supported property values, including false/zero and constraints.

    The YAML schema cannot represent OWL property-type extensions or annotation
    targets. Reject these explicitly instead of silently producing a lossy dump.
    """
    if prop.get("type") or prop.get("appliesToProperty"):
        raise ValueError(f"Property {prop['iri']} uses type/appliesToProperty metadata not supported by ontology YAML.")
    result = {"iri": prop["iri"]}
    for key in sorted(_PROPERTY_FIELDS):
        if key not in prop or prop[key] is None:
            continue
        value = prop[key]
        if key in {"name", "description"}:
            value = _languages(value)
        elif key == "editor":
            value = Editor(value).name
        elif key == "toClass" and value in list_classes:
            value = f"list:{list_classes[value]}"
        result[ATTR_TO_YAML.get(key, key)] = value
    return result


def api_model_to_yaml(project: dict, model: dict, list_files: dict[str, str]) -> dict:
    """Map existing API representations to the canonical ontology YAML schema.

    Includes project creation metadata, external ontology declarations,
    standalone properties and classes. Taxonomy class aliases are used only
    when the corresponding list file is part of the export. Audit timestamps,
    role configuration, instance data and Lucene connectors are not exported.
    """
    shortname = project.get("projectShortName")
    if not isinstance(shortname, str) or model.get("project") != shortname:
        raise ValueError("API project and datamodel identities do not match.")
    Xsd_NCName(shortname, validate=True)
    if any(not isinstance(project.get(key), str) or not project[key] for key in ("projectIri", "namespaceIri")):
        raise ValueError("API project response is missing its IRI or namespace.")
    project_spec = {"shortname": shortname}
    for source, target in (("projectIri", "iri"), ("namespaceIri", "namespace"), ("projectStart", "start")):
        if project.get(source) is not None:
            project_spec[target] = project[source]
    for key in ("label", "comment"):
        if project.get(key):
            project_spec[key] = _languages(project[key])
    ontology: dict[str, Any] = {"project": project_spec}
    if list_files:
        ontology["lists"] = list_files
    external = _index(model.get("externalOntologies"), "prefix", "external ontology")
    if external:
        ontology["external_ontologies"] = {}
        for prefix, spec in sorted(external.items()):
            item = {"namespace": spec["namespaceIri"]}
            for key in ("label", "comment"):
                if spec.get(key):
                    item[key] = _languages(spec[key])
            for key in ("proposedResourceClass", "proposedDatatypePropertyClass", "proposedObjectPropertyClass"):
                if spec.get(key) is not None:
                    item[key] = sorted(spec[key])
            ontology["external_ontologies"][prefix] = item
    list_classes = {f"{shortname}:{list_id}Node": list_id for list_id in list_files}
    standalone = _index(model.get("annotationProperties"), "iri", "standalone property")
    if standalone:
        ontology["standalone_properties"] = {}
        for iri, prop in sorted(standalone.items()):
            item = _export_property(prop, list_classes)
            del item["iri"]
            ontology["standalone_properties"][iri] = item
    ontology["classes"] = {}
    for iri, spec in sorted(_index(model.get("resources"), "iri", "resource").items()):
        item = {}
        for key in ("label", "comment"):
            if spec.get(key):
                item[key] = _languages(spec[key])
        if spec.get("closed") is not None:
            item["closed"] = spec["closed"]
        parents = sorted(parent for parent in spec.get("superclass", []) if parent != "oldap:Thing")
        if parents:
            item["superclass"] = parents
        props = _index(spec.get("properties"), "iri", "class property")
        item["properties"] = [_export_property(prop, list_classes) for _, prop in sorted(props.items())]
        ontology["classes"][iri] = item
    return {"ontology": ontology}


def _publish_dump(directory: Path, files: dict[str, bytes], *, overwrite: bool) -> list[Path]:
    """Stage all bytes and publish files in insertion order, preserving unrelated files.

    Conflicts and symlink/non-file destinations are rejected before any export
    file is written. Existing directories are not replaced wholesale. File
    replacement is atomic, but a multi-file refresh is not a directory transaction;
    callers must avoid concurrent exporters/readers while overwriting a package.
    """
    directory = directory.expanduser().absolute()
    targets = [directory / name for name in files]
    for target in targets:
        current = target
        while current != directory.parent:
            if current.is_symlink():
                raise ValueError(f"Refusing to export through symlink: {current}")
            if current != target and current.exists() and not current.is_dir():
                raise ValueError(f"Output parent is not a directory: {current}")
            current = current.parent
        if target.exists() and (not overwrite or not target.is_file()):
            raise ValueError(f"Output already exists: {target}. Use --overwrite to replace export files.")
    directory.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".oldap-dump-", dir=directory.parent) as folder:
        stage = Path(folder)
        for name, raw in files.items():
            staged = stage / name
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(raw)
        for name, target in zip(files, targets):
            target.parent.mkdir(parents=True, exist_ok=True)
            if overwrite:
                os.replace(stage / name, target)
            else:
                # Hard-link publication also refuses a file created after preflight.
                os.link(stage / name, target)
    return targets


def dump_ontology_api(*, api_base: str, user: str, password: str, project_id: str,
                      out_dir: Path | None = None, out: Path | None = None,
                      include_taxonomies: bool = False, overwrite: bool = False, include_connectors: bool = True,
                      emit: Callable[[str], None] = print) -> Path:
    """Read and export an ontology, optionally with every taxonomy in a directory.

    Args:
        api_base: Existing OLDAP API base URL.
        user: OLDAP login user.
        password: Password supplied by the CLI or its hidden prompt.
        project_id: Project short name to export.
        out_dir: Package directory; created if missing. Uses ontology.yaml and taxonomies/.
        out: Alternative single YAML filename, optionally gzip compressed.
        include_taxonomies: Download all taxonomies; requires out_dir.
        include_connectors: Export complete native Lucene options (requires updated API).
        overwrite: Replace conflicting export files, preserving unrelated files.
        emit: Receives the final export summary.

    Returns:
        Absolute path of the written ontology YAML document.
    """
    if out_dir is not None and out is not None:
        raise ValueError("Use either --out-dir or --out, not both.")
    if include_taxonomies and out_dir is None:
        raise ValueError("--include-taxonomies requires --out-dir.")
    Xsd_NCName(project_id, validate=True)
    output = out_dir / "ontology.yaml" if out_dir is not None else out or Path("ontology.yaml")
    with OldapApiClient(api_base) as client:
        client.login(user, password)
        project = client.get_json(api_path("admin", "project", project_id))
        model = client.get_json(api_path("admin", "datamodel", project_id))
        if not isinstance(project, dict) or project.get("projectShortName") != project_id or not isinstance(model, dict):
            raise ValueError("API returned invalid project or model data.")
        if not isinstance(project.get("namespaceIri"), str) or not project["namespaceIri"]:
            raise ValueError("API project response is missing its namespace.")
        lists = read_api_lists(client, project_id, project["namespaceIri"]) if include_taxonomies else {}
        list_files = {key: f"taxonomies/{key}.yaml" for key in lists}
        document = api_model_to_yaml(project, model, list_files)
        if include_connectors:
            connector = read_connector(client, project_id)
            if connector["configuration"] is not None:
                document["ontology"]["lucene_connectors"] = {project_id: {"configuration": connector["configuration"]}}
        text = yaml.safe_dump(document, allow_unicode=True, sort_keys=False)
        yamale.validate(yamale.make_schema(str(_schema_path())), yamale.make_data(content=text))
        raw = text.encode("utf-8")
        files = {list_files[key]: value for key, value in lists.items()}
        files[output.name] = gzip.compress(raw, mtime=0) if output.suffix == ".gz" else raw
        _publish_dump(output.parent, files, overwrite=overwrite)
    result = output.expanduser().absolute()
    emit(f"Ontology written to {result}; {len(lists)} taxonomy file(s) exported.")
    return result
