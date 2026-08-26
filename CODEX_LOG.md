# CODEX_LOG

### Update 2026-08-26 23:59
- Decisions: Treat object-property IRIs fixed by `sh:in` as ontology-controlled named individuals, not ordinary permission-readable project resources; retain full existence/type checks for every unconstrained resource link.
- Implementation: Corrected data preflight for combined `sh:class`/`sh:in` properties such as `shared:archiveLevel`, added a focused regression and documentation, updated the Poetry lock from OLDAPlib 0.7.10 to 0.7.15, and prepared oldap-tools 0.3.12.
- Open: Repeat the live Chama five-resource archive preflight, then apply/rerun and perform the separate cycle-safe Lobato Item move.
- Risks/Assumptions: Dynamic OLDAP instance construction remains authoritative for membership in the allowed-value set. The bypass applies only to the exact configured `sh:in` values; arbitrary links still require visibility and target-class verification.

### Update 2026-08-25 14:31
- Decisions: Reserve a later import extension for an explicit destination consisting of an already user-created StagingArea and selected existing StagingFolder. Do not infer or silently create staging containers during data/media import.
- Implementation: Recorded the future staging-target requirement in the stable project roadmap; no code or YAML schema was changed.
- Open: When implementing the slice, design the YAML block and validate existence, folder membership in the selected area, visibility, permissions, and retry semantics before writes.
- Risks/Assumptions: Exact field names and the transition from staging to catalogue remain deliberately undecided until the workflow is implemented and tested incrementally.

### Update 2026-08-25 12:24
- Decisions: Treat RDF resource identity as independent of mutable or repeatable descriptive facts. Preserve explicit institutional IRIs; otherwise mint a UUID-based project-local name once during offline preparation. Make the prepared document—not a title, filename, path, checksum, or a fresh rerun—the durable identity authority.
- Implementation: Added repeated `iri: auto` source placeholders, the text-preserving and atomic `data prepare` command, strict unresolved-identity guards on import/batch/media operations, distinct media asset IDs derived from the prepared resource names, same-filename regression coverage for two different binaries, CLI help, and complete format/command/context documentation.
- Open: Exercise a prepared two-file same-filename document in a future live batch when suitable duplicate source filenames are available; consider export/import round-trip conventions separately.
- Risks/Assumptions: References cannot target an unnamed `auto` resource until preparation has minted its name, so linked new records either need explicit IRIs or links added to the prepared file. The prepared file must be retained; regenerating it would create different identities.

### Update 2026-08-25 00:47
- Decisions: Treat owner inspection in SALSAH as the final acceptance gate for the first real batch vertical slice.
- Implementation: Recorded successful visual and semantic review of `IMG_1508`, `IMG_1521`, and `IMG_0171`: IIIF images render, complete metadata is present, and all expected links navigate correctly.
- Open: Choose the next bounded slice from additional Chama data, external-reference ingest, or evidence-driven generic UI refinement.
- Risks/Assumptions: No defect was found in this slice; broader asset types and larger batches remain separate tests.

### Update 2026-08-25 00:44
- Decisions: Accept actual OLDAP and media-server state as conclusive proof of batch completion and idempotence; retain the generated reports as audit evidence rather than resume authority.
- Implementation: Recorded the successful live dry-run, nine-resource apply, three HEIC attachments, and identical second apply for `chama-photographs-batch-01.yaml`. The rerun returned `metadata=existing_verified` for all nine resources and `media=existing_verified` for `IMG_1508`, `IMG_1521`, and `IMG_0171`, with no duplicate creation or upload.
- Open: Inspect the three new photographs and their KnowledgeContribution relationships in SALSAH, then decide the next bounded metadata or UI increment.
- Risks/Assumptions: Live CLI output confirms state verification; visual SALSAH inspection remains the next independent presentation check.

### Update 2026-08-25 00:38
- Decisions: Make the first live Chama batch a meaningful vertical slice rather than three isolated files: include reusable capture places, locomotive 489, and one complete KnowledgeContribution per owner annotation. Preserve the corrected Foster's filename `IMG_0171`, not the originally mistyped `IMG_1771`.
- Implementation: Added `examples/data/chama-photographs-batch-01.yaml` with nine dependency-ordered resources: Chama engine house, Chama Main Street, locomotive 489, `IMG_1508`, `IMG_1521`, `IMG_0171`, and their three contributions. Recorded titles, normalized descriptions, dates, creators, capture places, depiction links, permissions, rights notes, provenance, original annotations, uncertainties, normalization notes, local media instructions, and verified SHA-256 values. Added regression validation and documentation/context links.
- Open: Run the live batch dry-run with a report, review all nine ontology-aware plans, then apply. Rerun apply afterward to confirm every metadata and media phase reports `existing_verified`.
- Risks/Assumptions: The engine-house and Main Street place descriptions and locomotive 489 classification derive from the owner's supplied Chama knowledge. Historical hotel claims remain attributed in KnowledgeContribution uncertainty notes. The Foster's photograph retains a depicted-person review note for broader publication.

### Update 2026-08-25 00:29
- Decisions: Add multi-resource import as a resumable, sequential create-only workflow rather than an artificial all-or-nothing transaction. Preflight the complete document before writing, stop at the first operational failure, and use actual OLDAP/media state—not a local report—as resume authority.
- Implementation: Added `data import --batch` for dry-run and apply; exact verification of matching existing classes, YAML-declared properties, and role permissions; allowance for server-managed properties and the legitimate `custom` to `iiif` protocol transition; sequential metadata/media processing; first-failure stop with `not_started` remainder; JSON/YAML audit reports; CLI output; tests; and complete documentation.
- Open: Build a representative multi-image Chama YAML, run batch dry-run and apply against the live services, then rerun it to verify recovery/idempotence with real OLDAP and IIIF data.
- Risks/Assumptions: Batch order is significant and serves as the conservative dependency order; preflight rejects forward references to other new in-document resources. The workflow never edits an existing resource: mismatches fail preflight. A hidden existing IRI can still surface only when create commits. Report-write failure cannot undo a completed import; current OLDAP/media state remains authoritative.

### Update 2026-08-25 00:13
- Decisions: Keep media source, handling, and ingest profile independent; keep binaries outside YAML; enable only the fully supported local `image-iiif` copy profile while reserving stable names for future preservation, audio, video, and document workflows. Treat RDF creation and media attachment as separate recoverable service transactions.
- Implementation: Added strict `media` parsing for local files, direct URLs, IIIF Image services, and IIIF manifests; relative-path and streaming SHA-256 preflight; automatic local image ingest after one-resource create; API authentication, media-server attach mode, OLDAP delivery-field and IIIF verification; idempotent `data media-attach`; API/media CLI origins; the IMG_1520 file reference; focused tests; and complete YAML/command/connection documentation.
- Open: Run `data media-attach --dry-run` and `--apply` for the existing `chama:IMG_1520`, then inspect the IIIF image in SALSAH. Implement reserved profiles and URL-copy only with complete media-server contracts.
- Risks/Assumptions: `image-iiif` derives its default asset ID from the resource local name and uses media storage path `catalogue`. External `reference` instructions do not transfer or probe remote content; their canonical delivery facts remain explicit RDF properties. If media attachment fails after RDF creation, the resource remains and the CLI directs the operator to the idempotent recovery command.

### Update 2026-08-24 23:56
- Decisions: Make the first instance-data write path strictly create-only and limit each apply execution to exactly one resource. Do not offer generic multi-resource rollback because independent oldaplib transactions and structured `oldap:Dating` helper nodes would make compensating deletion incomplete.
- Implementation: Enabled `data import --apply`, retained dry-run as the default, repeated the complete live preflight immediately before OLDAP's transactional create, rejected multi-resource apply before writes, added explicit execution results and CLI reporting, expanded tests, and documented that metadata apply does not import media binaries.
- Open: Inspect the resulting `chama:IMG_1520` resource in SALSAH and attach the HEIC binary/IIIF service separately. Design multi-resource apply only with an explicit atomic transaction strategy.
- Risks/Assumptions: The apply path relies on `ResourceInstance.create()` for the final atomic collision and permission checks. The authenticated live apply created `chama:IMG_1520` with 13 properties and two typed references; it did not import or attach a media binary.

### Update 2026-08-24 23:47
- Decisions: Keep version-1 instance import strictly create-only and read-only; delegate ontology constraints to oldaplib's dynamic resource classes instead of duplicating SHACL/model rules in oldap-tools, and reject `--apply` explicitly.
- Implementation: Added `data import --dry-run` with live project/class/property resolution, inherited constraint and cardinality validation, typed link and forward-reference checks, role lookup, `ADMIN_CREATE` verification, visible collision detection, concise plans, full documentation, and focused orchestration/error tests.
- Open: Decide whether the next increment should add a reviewed create-only apply mode or first exercise the format with more multi-resource Chama data.
- Risks/Assumptions: A resource hidden from the authenticated user is indistinguishable from a missing resource during read-only checks, so a later create could still discover a hidden IRI collision. The authenticated `IMG_1520` live preflight passed against the Chama project with 13 properties and two typed references; no data was written.

### Update 2026-08-24 23:36
- Decisions: Introduce a small, project-neutral, versioned instance-data interchange format before implementing imports; keep literals and IRI references explicit, keep every property value as a list, and make all purely local validators credential-free.
- Implementation: Added version-1 YAML/JSON parsing and structural validation, duplicate-key and ambiguity checks, the offline `data validate` command, a complete `IMG_1520` Chama example, command/format documentation, centralized credential enforcement for connected commands, and focused YAML, JSON, CLI, and regression tests.
- Open: Add ontology-aware `data import --dry-run` preflight that resolves the live project model, properties, cardinalities, references, roles, and create/conflict status before any write mode is considered.
- Risks/Assumptions: Version-1 local validation does not prove that a project, class, property, role, or linked resource exists; ontology-dependent values such as `oldap:Dating` shorthand are deferred to the future preflight. No OLDAP/GraphDB data was written and `IMG_1520` was not imported.

### Update 2026-08-10 21:35
- Decisions: Retain the existing archive CLI surface and dry-run default while moving every reusable archive YAML concern to oldaplib.
- Implementation: Replaced the former combined parser/importer with a thin connection adapter, removed the duplicate archive Yamale schema, retained a documented `read_archive_yaml` transition adapter, updated documentation/context, and added three focused CLI/centralization tests.
- Open: Exercise the adapter against a running development GraphDB after downstream installation of the working oldaplib version.
- Risks/Assumptions: Repository tests use the sibling oldaplib through `PYTHONPATH` until a future release; no release, commit, push, deployment, or GraphDB write was performed.

### Update 2026-08-03 12:07
- Decisions: Use recursive project-neutral YAML as the canonical manual archive-tree format; allow multiple roots and additive attachment below an explicit existing parent while keeping version 1 strictly create-only and dry-run by default.
- Implementation: Added the bundled Yamale schema, semantic parser/normalizer, stable project-IRI mapping, collision and parent preflight, parent-first creation with best-effort rollback, `archive validate` and `archive load` commands, unit tests, a two-fonds example, and complete format/command documentation.
- Open: Run `archive load --apply` against a running development GraphDB and inspect the created role assignments and tree in FasnachtsPage; design the Staging-to-YAML generator as a separate follow-up.
- Risks/Assumptions: The local GraphDB dry-run could not complete because port 7200 was not running. Version 1 deliberately relies on the authenticated user's normal default OLDAP roles and does not update, merge, move, or delete any existing archive unit.

### Update 2026-07-31 23:26
- Decisions: Provide the existing-StagingArea backfill as an idempotent OLDAP CLI operation rather than raw SQL/SPARQL, and make dry-run the safe default.
- Implementation: Added `staging ensure-mobile-folder` with explicit-area or all-area selection, hierarchy/duplicate validation, `DATA_VIEW` assignment for the StagingArea default role, focused plan tests, and concise CLI reporting.
- Open: Run the command against the test GraphDB with its concrete StagingArea IRI, inspect the dry-run output, and rerun with `--apply`.
- Risks/Assumptions: Live GraphDB execution was not performed because no credentials or target IRI were supplied; local unit tests and CLI help validation pass.

### Update 2026-07-26 23:54
- Decisions: Stabilize the Fasnacht wizard's ontology package around independent ArchiveMediaObjects, multi-valued direct topics and associated organisations, Agent-based creators, optional representation roles, original-content dating, and optional StagingArea default rights with CC BY-ND as the initial instance value.
- Implementation: Activated the replacement ObjectTaxonomy wording, sharpened four topic labels without changing their IDs, added ArchiveMediaObject `dcterms:subject` and `fasnacht:associatedOrganisation`, clarified optional target links and creator/dating descriptions, and added optional `fasnacht:defaultRights` to StagingArea. Updated the ObjectTaxonomy migration document with verified IRI construction and the list-replacement constraint.
- Open: Reload the revised ontology after this change, populate existing StagingAreas with `L-CreativeCommons:CC_BY-ND`, verify the replacement ObjectTaxonomy state and all object-type references in GraphDB, and decide the final Rädäbäng type.
- Risks/Assumptions: The current loader cannot move existing list nodes during merge, and ontology `--mode replace` does not replace lists; the ObjectTaxonomy hierarchy therefore requires an explicit backed-up list replacement. No GraphDB data or deployment was changed in this step.

### Update 2026-07-23 12:10
- Decisions: Keep the existing `CarnivalTopicsTaxonomy` list identifier while drafting a replacement in a separate, inactive file; model shared archive facets as themes, practices, and cultural expressions instead of duplicating organisation, object, event, or media types.
- Implementation: Added `fasnacht/CarnivalTopicsTaxonomyNew.yaml` with seven extensible top-level domains, 41 child topics, and English, German, French, and Italian labels and definitions throughout; left the current taxonomy and ontology reference unchanged.
- Open: Review the vocabulary against representative photographs, agree stable node IDs and scope notes, then decide whether to point `fasnacht-onto.yaml` at the new file and migrate or remove test references.
- Risks/Assumptions: The draft is syntactically valid and fully multilingual, but its cultural terminology and translations still require domain review before production use.

### Update 2026-07-16 12:27
- Decisions: Treat external ontology definitions as required YAML roundtrip metadata while leaving deprecated standalone-property behavior unchanged.
- Implementation: Added canonical serialization of external ontology namespaces, labels, comments, and proposed class/property names to `ontology dump`; verified that `ontology load` consumes the emitted fields; added focused unit and integrated YAML-export tests and documented the behavior.
- Open: Run a live dump/load roundtrip against GraphDB to confirm the exported Fasnacht `foaf` reference in the deployment environment.
- Risks/Assumptions: Update mode remains patch-oriented and does not delete external ontologies omitted from YAML; replace mode recreates exactly those present in YAML.

### Update 2026-07-15 21:54
- Decisions: Keep the administrative CLI on direct GraphDB authentication and prevent JWT signing secrets from being distributed to CLI installations.
- Implementation: Added a shared connection factory using `issue_access_token=False`, migrated all command connection sites, raised the `oldaplib` requirement to 0.7.1, added focused factory tests, and documented the authentication boundary and migration plan.
- Open: Publish `oldaplib 0.7.1`, resolve the lockfile against that release, and run representative live read/write commands in the deployment environment.
- Risks/Assumptions: The direct mode depends on the new `oldaplib.Connection` option and intentionally leaves `Connection.token` unset.

### Update 2026-06-05 23:51
- Decisions: Make ontology update attribute comparison tolerate missing OLDAP attributes instead of relying on oldaplib value-object comparison against `None`.
- Implementation: Added `_values_equal()` and routed `_set_attr()` through it so `LangString` and similar values are only compared after explicit `None` handling.
- Open: Rerun the live `ontology load` command against GraphDB to confirm the next update phase completes in the user's repository state.
- Risks/Assumptions: Local verification covers the failing comparison path; the live update may expose further model-specific issues after this first crash is removed.

### Update 2026-05-26 22:21
- Decisions: Include `fasnacht:CarnivalEvent` in the Fasnacht archive Lucene connector so public full-text search covers event descriptions and titles.
- Implementation: Added `fasnacht:CarnivalEvent` to `fasnacht_archive.types` in `fasnacht/fasnacht-onto.yaml`; existing archive title fields already use `schema:name`.
- Open: Recreate or reload the GraphDB Lucene connector and verify public archive search against event descriptions such as "Nationalismus".
- Risks/Assumptions: Assumes the OLDAP connector generator maps this YAML type list directly to the GraphDB Lucene `types` array.

### Update 2026-05-26 18:12
- Decisions: Made project dump bypass Redis object-cache reads for admin objects because cached serialized OLDAP objects can outlive oldaplib object-layout changes.
- Implementation: Added a `dump_project` docstring and passed `ignore_cache=True` to `Project.read`, `User.read`, and `Role.read` during project export.
- Open: VM should either use a rebuilt `oldap-tools` image containing this change or clear Redis as an immediate workaround.
- Risks/Assumptions: Live GraphDB dump was not run locally; verification covered imports and Python compilation only.

### Update 2026-05-26 18:05
- Decisions: Kept the oldaplib upgrade scoped to dependency metadata and environment synchronization; no oldap-tools source API changes were required by the checked import and validation paths.
- Implementation: Verified `pyproject.toml` and `poetry.lock` target `oldaplib 0.6.11`, ran `poetry install` to update the local virtual environment from `0.5.2` to `0.6.11`, and checked imports, CLI startup, Python compilation, and Fasnacht ontology YAML validation.
- Open: GraphDB-backed commands (`project`, `lists`, `ontology load/dump`, `system`) still need live integration testing against a running repository.
- Risks/Assumptions: Local checks cover static/import and schema-validation compatibility only; runtime OLDAP semantic changes may surface only during live GraphDB operations.

### Update 2026-05-13 20:59
- Decisions: Added the required repository context files before changing project documentation.
- Implementation: Created `codex.md` as stable project context and initialized this technical work log.
- Open: Fasnacht object documentation still needs to be added and linked.
- Risks/Assumptions: Project context is intentionally concise and should be expanded only for strategic repository changes.

### Update 2026-05-13 21:00
- Decisions: Kept `fasnachts-onto.md` as the concise technical overview and added separate layperson-oriented object pages under `fasnacht/objekte/`.
- Implementation: Added one Markdown page per documented Fasnacht class, linked them from `fasnachts-onto.md`, and emphasized why `ArchiveObject` and `ArchiveMediaObject` must remain separate.
- Open: No model/YAML changes were made; future ontology changes should update both the concise and object-level documentation where relevant.
- Risks/Assumptions: The documentation treats `schema:NewsArticle` as a technical base class and directs normal editorial use to `NewsItem`.

### Update 2026-05-13 21:01
- Decisions: Clarified that `FasnachtUser.memberOfOrganisation` currently points to the organisation taxonomy, not to a concrete organisation resource.
- Implementation: Adjusted the `FasnachtUser` and `Organisation` layperson pages to avoid overstating the current model relationship.
- Open: None.
- Risks/Assumptions: If the user model later needs a direct link to `fasnacht:Organisation`, both YAML and documentation should be updated together.

### Update 2026-05-14 00:49
- Decisions: Kept the Fasnacht ontology changes minimal and corrected only inconsistent references introduced by the new CarnivalThing/Event structure.
- Implementation: Added the missing target class for `fasnacht:eventLocation`, made `fasnacht:currentLocation` a subproperty of the existing `fasnacht:location`, and updated Lucene archive title fields to use inherited `schema:name`.
- Open: A live ontology load against GraphDB should still be rerun with the user’s credentials/environment.
- Risks/Assumptions: The YAML validator cannot catch all OLDAP semantic issues; the fixes are based on local schema checks and static ontology consistency checks.

### Update 2026-05-18 02:20
- Decisions: Converted Fasnacht object documentation links to Pandoc-friendly global section IDs so separate Markdown files can be merged into one document.
- Implementation: Added explicit `{#sec:...}` IDs to object documentation headings, replaced file-based Markdown links with anchor links, updated the `fasnachts-onto.md` object link list, and added a recommended Pandoc merge order.
- Open: None.
- Risks/Assumptions: Internal links assume the object documentation files are included in the same Pandoc document as the anchor targets.
