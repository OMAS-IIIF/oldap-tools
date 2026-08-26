# oldap-tools Project Context

`oldap-tools` is a Python CLI package for managing selected OLDAP project assets. It can dump and load project data, load and dump hierarchical lists, validate ontology YAML, load or dump OLDAP ontology data models, create archive trees from validated YAML, and validate versioned project instance data.

## Repository State

- Package source lives in `src/oldap_tools/`.
- User documentation lives in `docs/`.
- Example and active Fasnacht project definitions live in `fasnacht/`.
- The package is managed with Poetry and exposes the `oldap-tools` console script.
- Connection construction is centralized in `src/oldap_tools/connection.py`; normal CLI operations use `oldaplib`'s trusted direct mode without issuing access tokens or requiring JWT signing secrets. Media ingest authenticates through oldap-api because oldap-mediaserver correctly requires a short-lived user Bearer token.
- Local validators for ontologies, archive trees, and instance data do not require credentials; connected commands validate that both OLDAP user and password were supplied.
- The current worktree may contain user-created artifacts; do not reset or remove unrelated files.

## Architecture

- `cli.py` defines the Typer command surface.
- `connection.py` is the single boundary for authenticated direct GraphDB connections.
- `load_project.py`, `dump_project.py`, and `delete_projectdata.py` handle project graph operations.
- `load_list.py`, `dump_list.py`, and `list_merge.py` handle hierarchical OLDAP lists.
- `ontology.py`, `graph_helpers.py`, and `schemas/ontology_schema.yaml` implement ontology YAML validation/loading/dumping support.
- `archive.py` is a thin CLI/connection adapter around the canonical archive YAML document, schema, validation, preflight, and create-only import implementation in `oldaplib`; no archive schema or parser is duplicated in this repository. YAML IDs map deterministically to project IRIs, multiple roots are allowed, and an external attachment point requires `DATA_UPDATE` in addition to project `ADMIN_CREATE` for new units.
- `data_yaml.py` defines version 1 of the project-neutral instance-data YAML/JSON format. Property values are always lists and explicitly distinguish literal values from IRI references. Optional media instructions independently declare source (`file`, `url`, `iiif-image`, or `iiif-manifest`), handling (`copy` or `reference`), and an ingest profile. Incoming records may use repeated `iri: auto` placeholders, but no live operation accepts unresolved identities.
- `data_prepare.py` performs the one-time offline identity step. It replaces only resource-level `iri: auto` scalars with UUID-based project-local names, preserves YAML comments and formatting or JSON syntax, writes atomically to a distinct same-directory file, and makes that prepared document the durable import authority. Identity is never derived from titles, filenames, paths, or checksums; repeated filenames therefore remain harmless metadata.
- `data_import.py` implements the live preflight and strict create-only apply. It delegates datatype, allowed-value, and cardinality validation to dynamic oldaplib resource classes, then verifies ordinary resource links, target classes, roles, `ADMIN_CREATE`, and visible IRI collisions. Object-property IRIs fixed by `sh:in`, including Shared archive-level named individuals, are validated as controlled vocabulary and are not incorrectly looked up in a project data graph. Apply is limited to one resource, repeats preflight immediately before OLDAP's transactional create, and never updates, overwrites, or deletes RDF.
- The current Poetry lock resolves OLDAPlib 0.7.15.
- `media_ingest.py` owns local media path resolution, streaming SHA-256 checks, API authentication, oldap-mediaserver attach mode, and delivery/IIIF verification. `image-iiif` is the first enabled copy profile; the documented audio, video, document, and preserve-only names remain reserved. `data media-attach` is the idempotent completion/recovery path because RDF creation and binary attachment are separate service transactions.
- `data_batch.py` implements resumable multi-resource import. It preflights the complete document before writing, verifies matching existing resources from actual OLDAP state, processes in YAML order, stops at the first failure, and emits optional JSON/YAML audit reports. It remains create-only: existing mismatches are errors, never updates.
- `examples/data/chama-photographs-batch-01.yaml` is the first end-to-end-proven batch package: public `IMG_1508`, `IMG_1521`, and corrected `IMG_0171` HEIC photographs; three complete KnowledgeContributions; Chama engine-house and Main Street places; and locomotive 489. Its nine resources were created successfully, all three images attached through IIIF, an identical second apply verified every metadata and media phase without writes, and owner inspection in SALSAH confirmed that all data and links are present and correct.
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
- `chama:IMG_1520` has been attached successfully and is visible through its 4032x3024 IIIF service in SALSAH.
- Add copy implementations for URL sources and the reserved audio, video, document, and preserve-original ingest profiles only when their server-side contracts can be fully verified.
- Later extend instance-data YAML with an explicit staging destination for imports into a user-created existing `StagingArea` and selected existing `StagingFolder`. The importer must resolve and validate the area/folder relationship, visibility, and required write permissions; it must not silently create or infer staging containers. Keep the exact YAML keys and lifecycle semantics open until this slice is implemented.
- Select the next bounded vertical slice: either package the remaining already-annotated Chama records, exercise an external-reference media source, or refine one generic SALSAH presentation issue discovered through broader data use.
- Exercise the archive YAML importer against a running development GraphDB, then add a Staging-tree generator that emits the same canonical YAML rather than creating a second import path.
- Maintain `fasnacht/fasnachts-onto.md` as concise technical model documentation.
- Maintain laienfreundliche Fasnacht object documentation in `fasnacht/objekte/` for domain experts who do not work with data modeling concepts.
