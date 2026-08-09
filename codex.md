# oldap-tools Project Context

`oldap-tools` is a Python CLI package for managing selected OLDAP project assets. It can dump and load project data, load and dump hierarchical lists, validate ontology YAML, load or dump OLDAP ontology data models, and create archive trees from validated YAML.

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
- `archive.py` and `schemas/archive_schema.yaml` implement project-neutral recursive archive YAML validation, OLDAP preflight, and create-only loading. YAML IDs map deterministically to project IRIs; multiple roots are allowed, and a new root may attach below an explicit existing ArchiveUnit. Existing resources are never merged, updated, moved, or deleted.
- The Fasnacht model is declared in `fasnacht/fasnacht-onto.yaml` with companion taxonomies in YAML files in the same folder.
- Existing Fasnacht StagingAreas can be reconciled with the application-managed `Mobile` folder through `oldap-tools staging ensure-mobile-folder`. The command is idempotent, validates the `top` hierarchy, defaults to dry-run, and writes only when `--apply` is supplied.
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
- Exercise the archive YAML importer against a running development GraphDB, then add a Staging-tree generator that emits the same canonical YAML rather than creating a second import path.
- Maintain `fasnacht/fasnachts-onto.md` as concise technical model documentation.
- Maintain laienfreundliche Fasnacht object documentation in `fasnacht/objekte/` for domain experts who do not work with data modeling concepts.
