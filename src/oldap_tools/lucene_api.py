"""Native Lucene configuration transport and read-only import planning."""

import hashlib
import json
from types import SimpleNamespace
from oldap_tools.api_client import ApiOperation, OldapApiClient, api_path
from oldap_tools.ontology import _ontology_context, _build_lucene_payload, _merge_lucene_payloads


def read_connector(client: OldapApiClient, project: str) -> dict:
    """Read an explicit configuration/absence envelope; never hide missing routes."""
    state = client.get_json(api_path("admin", "lucene", project))
    if not isinstance(state, dict) or state.get("name") != project or not {"configuration", "revision"} <= state.keys():
        raise ValueError("API returned an invalid Lucene connector response.")
    configuration = state["configuration"]
    if configuration is not None and not isinstance(configuration, dict):
        raise ValueError("API returned an invalid Lucene configuration.")
    raw = json.dumps(configuration, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    revision = hashlib.sha256(raw.encode("utf-8")).hexdigest() if configuration is not None else None
    if state["revision"] != revision:
        raise ValueError("API returned an inconsistent Lucene configuration revision.")
    return state


def plan_connector(client: OldapApiClient, ontology: dict, project_before: dict | None,
                   mode: str) -> tuple[ApiOperation | None, dict | None]:
    """Prepare one project-scoped mutation, preserving native options verbatim.

    Legacy shorthand groups still merge into the project-named connector. Native
    configuration is exclusive, avoiding lossy merges of advanced GraphDB options.
    Skip does not read connector endpoints, preserving older API compatibility.
    """
    if mode not in {"skip", "create", "replace"}:
        raise ValueError("Connector mode must be skip, create or replace.")
    specs = ontology.get("lucene_connectors") or {}
    if mode == "skip" or not specs:
        return None, None
    if len(specs) > 1 and any("configuration" in spec for spec in specs.values()):
        raise ValueError("Native Lucene configuration must be the only connector specification.")
    project = ontology["project"]["shortname"]
    namespace = ontology["project"].get("namespace") or (project_before or {}).get("namespaceIri")
    context = _ontology_context(SimpleNamespace(projectShortName=project, namespaceIri=namespace), ontology)
    desired = _merge_lucene_payloads(project, [_build_lucene_payload(name, spec, context) for name, spec in specs.items()])
    if not desired.get("types") or not (desired.get("fields") or desired.get("detectFields") is True):
        raise ValueError("Lucene configuration needs types and fields (or detectFields).")
    # A new project's connector is read after project creation by the endpoint;
    # create semantics still reject an already existing connector of the same name.
    state = read_connector(client, project) if project_before else {"name": project, "configuration": None, "revision": None}
    if mode == "create" and state["configuration"] is not None:
        raise ValueError(f'Lucene connector "{project}" already exists; use --connectors replace.')
    if mode == "replace" and desired == state["configuration"]:
        return None, state
    return ApiOperation("PUT", api_path("admin", "lucene", project),
                        {"mode": mode, "configuration": desired, "expectedRevision": state["revision"]}), state
