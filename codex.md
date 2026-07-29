# oldap-tools Project Context

`oldap-tools` is a Python CLI package for managing selected OLDAP project assets. It can dump and load project data, load and dump hierarchical lists, validate ontology YAML, and load or dump OLDAP ontology data models.

## Repository State

- Package source lives in `src/oldap_tools/`.
- User documentation lives in `docs/`.
- Example and active Fasnacht project definitions live in `fasnacht/`.
- The package is managed with Poetry and exposes the `oldap-tools` console script.
- Connection construction is centralized in `src/oldap_tools/connection.py`; the CLI uses `oldaplib`'s trusted direct mode without issuing access tokens or requiring JWT signing secrets.
- The current worktree may contain user-created artifacts; do not reset or remove unrelated files.

## Architecture

- `cli.py` defines the Typer command surface.
- `connection.py` is the single boundary for authenticated direct GraphDB connections.
- `load_project.py`, `dump_project.py`, and `delete_projectdata.py` handle project graph operations.
- `load_list.py`, `dump_list.py`, and `list_merge.py` handle hierarchical OLDAP lists.
- `ontology.py`, `graph_helpers.py`, and `schemas/ontology_schema.yaml` implement ontology YAML validation/loading/dumping support.
- The Fasnacht model is declared in `fasnacht/fasnacht-onto.yaml` with companion taxonomies in YAML files in the same folder.
- Fasnacht archive metadata is media-first: `ArchiveMediaObject.archiveMediaObjectOf` is optional, direct media topics and associated organisations are supported, and `representationRole` uses `MediumRepresentationTaxonomy`. `dcterms:creator` targets `fasnacht:Agent` for both archive objects and media, while `contributingAgent` remains separate provenance metadata.
- `fasnacht:StagingArea` has optional `fasnacht:defaultRights` pointing to `CreativeCommons`; the agreed initial data value is `L-CreativeCommons:CC_BY-ND` and must be populated on StagingArea instances separately from the ontology definition.
- The replacement `fasnacht/ObjectTaxonomy.yaml` classifies archive material types and retains 21 legacy node IDs. The former hierarchy is preserved as `ObjectTaxonomy-OLD.yaml`; `ObjectTaxonomy-MigrationMapping.md` documents unresolved Rädäbäng records and the explicit list-replacement requirement because list merge does not move existing nodes.

## Development Style

- Prefer small, explicit Python modules and clear Typer command implementations.
- Keep YAML data-model files as the source of truth for project models.
- Update Markdown documentation whenever public CLI behavior, ontology semantics, or model conventions change.
- Use structured docstrings for public Python APIs and concise inline comments where behavior is not obvious.

## Current Roadmap

- Keep the OLDAP ontology/list tooling stable and documented.
- Maintain `fasnacht/fasnachts-onto.md` as concise technical model documentation.
- Maintain laienfreundliche Fasnacht object documentation in `fasnacht/objekte/` for domain experts who do not work with data modeling concepts.
