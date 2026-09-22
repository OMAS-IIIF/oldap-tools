# CODEX_LOG

### Update 2026-09-22 23:37
- Decisions: Make operations.md the practical entry point for the API ontology workflow, with explicit transport/backup scope and recovery guidance. User confirmed all resources are visible again after the model recovery.
- Implementation: Reworked operations.md around dump/validate/preview/apply/verify, native Lucene modes, ZIP contents, partial failures, isolated restoration tests and Workbench cache freshness. Aligned README, command reference, API contracts, installation, update semantics, YAML examples, docs index and stable project context. Corrected the direct replacement command, stale connector exclusions and outdated property-removal checklist. Checked 43 relative links/anchors and shell syntax of 45 examples across nine documents; diff whitespace checks pass.
- Open: Publish matching tools/API/library releases through the normal workflow; no documentation build configuration is present in this repository.
- Risks/Assumptions: Documentation-only changes; no commands from the operational examples were executed and no runtime/data changes were made. Zero-operation planning does not imply exact taxonomy equality or completed index construction; these limits are now explicit.

### Update 2026-09-22 23:26
- Decisions: Administrative model planning/export must read GraphDB freshly after out-of-band Workbench edits; never clear all Redis databases to repair model visibility.
- Implementation: API JSON model GET and TriG download now use DataModel.read(ignore_cache=True). Two regression cases simulate deleted graphs with a stale cached model; 14 targeted API/auth/connector tests pass. Safely restarted local API. Captured complete explicit RDF before/after snapshots at /Users/rosenth/.codex/backups/oldap-fasnacht-recovery-20260922-232248; restored only fasnacht onto/shacl from the user's 23:15 API ZIP after confirming zero differences against the exported YAML. Restoration held the normal writer gate and used additive RDF import with exact graph-scope validation.
- Open: User browser acceptance; publish the API fix through normal release workflow. Workbench edits to other cached entities still require appropriate scoped invalidation.
- Risks/Assumptions: The earlier same-state roundtrip did not test external graph deletion and overstated recovery confidence. Fresh administrative reads cost additional GraphDB queries. All 27 other graph contexts are RDF-isomorphic before/after, including all 25,435 Fasnacht data triples and taxonomies. Recovered API: 16 classes; YAML replace dry-run: zero operations; Lucene: 693 entities; ArchiveObject/ArchiveMediaObject API samples read successfully. Connector configuration/index was not replaced during recovery. No global cache flush, data-graph mutation, or production change.

### Update 2026-09-22 23:06
- Decisions: Preserve complete Lucene creation options in native YAML; load remains opt-in and project-scoped. Existing shorthand and transport defaults remain supported.
- Implementation: Add native YAML configuration, lossless default dumps/--no-connectors, API create/replace planning with reviewed revisions, connector snapshots, direct export/query escaping fixes and roundtrip/conflict/compatibility tests. 126 tools tests + 8 legacy tests + 25 targeted library/API/export/auth tests passed. Live Fasnacht dump retained 16 classes, 10 taxonomies and all options of the 8-field connector; replace dry-run planned zero operations. No live connector/model writes.
- Open: Publish paired releases before use outside this local development setup; no release/version bump performed.
- Risks/Assumptions: Connector commands are not RDF transactions. Failed replacement attempts restoration but may require reindexing; administrators outside configured writer coordination must serialize changes. Installed a local, unpublished oldaplib wheel still labelled 0.7.21 in the native API Python 3.13 environment; activated with writer-gated make restart. Production unchanged.

### Update 2026-09-22 22:43
- Decisions: Default ontology dump to the existing API. Use --out-dir for YAML packages with --include-taxonomies, create missing directories and require --overwrite for conflicting export files; retain explicit direct dumps for TriG/legacy behavior.
- Implementation: Added canonical API-to-YAML serialization of project/external ontology/standalone/class metadata, relative taxonomies/<ListId>.yaml references and list class aliases. Shared validated taxonomy downloads with import planning. Downloads/schema/conflict checks precede staged per-file publication, ontology.yaml last; unrelated files remain and symlink destinations are refused. Updated CLI, documentation and context. Added export/roundtrip/file-safety tests and aligned the older credential-message test with hidden password prompting. All 127 tests across both directories and diff checks pass.
- Open: None for the requested API YAML/taxonomy export. Unsupported OWL property extensions/annotation targets fail explicitly; existing node_kind import limitations and direct-only raw TriG/Lucene export remain documented.
- Risks/Assumptions: Read-only live Fasnacht export to a temporary directory verified 16 classes, ten taxonomies and zero subsequent import-plan operations. No live data writes or changes to user model files. Per-file replacement is atomic, but refreshing an existing package is not a whole-directory transaction; avoid concurrent exports/readers while overwriting. Existing user-created API backup ZIP retained.

### Update 2026-09-22 22:34
- Decisions: Prompt for omitted OLDAP passwords at the shared connected-command boundary, with hidden terminal input; retain explicit --password for automation.
- Implementation: connection_config requires --user, prompts with hide_input=True and replaces the frozen configuration in memory. Updated help, README, connection documentation and context. Regression coverage verifies hidden input, EOF abort before connection, explicit-password bypass, and prompt-free offline validation/help; all 39 API/CLI tests and diff checks pass.
- Open: None for the password prompt.
- Risks/Assumptions: No credential persistence, API/library changes or live operations. Interactive prompting is restricted to commands that invoke connection_config.

### Update 2026-09-22 22:29
- Decisions: Keep strict pre-write backup validation; fix malformed model serialization at its OLDAPLIB source instead of bypassing validation or rewriting downloads in the client.
- Implementation: Wrap RDFLib syntax/parser failures in a concise CLI-compatible error with export line and no-writes status. Added invalid-export regression; 36 API tests pass. Corrected sibling OLDAPLIB external ontology/empty-class TriG serialization and ontology rdf:type, with three focused library tests. Built and installed an unpublished 0.7.21 wheel into the actual launchd Python 3.13 API runtime and used guarded make restart.
- Open: User may rerun the import without --dry-run; nine planned changes remain. Publish a normal new OLDAPLIB release before distributing the server-side fixes beyond this local environment.
- Risks/Assumptions: Original failure was before any import mutation or backup creation. Read-only verification against the restarted local API successfully parsed 1,524 RDF triples and created/checked a temporary 45,368-byte ZIP with all ten taxonomies; no ontology changes applied. No new API routes, production deployment or PyPI publication. Snapshot retains the previously documented recovery limitations.

### Update 2026-09-22 22:17
- Decisions: Treat YAML editor aliases and API DASH identifiers as the same value, avoiding spurious updates on every ontology import.
- Implementation: Normalize editor payloads and comparisons through the existing Editor enum; preserve null removal and reject invalid names before writes. Added regression tests for equivalent aliases, actual changes and null/invalid values; all 35 API tests and diff checks pass. Updated the API contract documentation.
- Open: Repeat the user's live dry-run; if current editor settings already match, its 33 operations should reduce to nine (one archiveUnit addition and eight order changes).
- Risks/Assumptions: The pasted dry-run does not include previous editor values, so the exact remaining count requires a fresh read. No live writes performed.

### Update 2026-09-22 22:11
- Decisions: Make ontology load an oldap-api client by default, retaining explicit --transport direct for administration. Preserve omitted class properties unless --remove-unused is supplied; respect the existing conservative class-in-use guard. No oldap-api/oldaplib changes or new dependencies.
- Implementation: Added authenticated HTTP session/refresh transport, read-only ontology and taxonomy planning, dependency-ordered class creation, YAML-to-API field translation, guarded removals, --dry-run, per-request progress/failure reporting and exclusive API ZIP snapshots. Updated direct synchronization defaults and public documentation/context. 111 tests pass across the two test directories (including 32 new API contract/failure tests and direct-removal regression); current Fasnacht YAML prepares offline with 16 classes and 10 lists; CLI help and diff checks pass.
- Open: Rehearse create/replay/extend/remove and recovery on a disposable development project against the deployed API. API graph replacement, Lucene administration and node_kind writes remain unsupported; other CLI commands retain their existing transports.
- Risks/Assumptions: API operations commit independently; no concurrent schema writers, automatic rollback or ambiguous-write retries. ZIP snapshots are API exports, not raw graph backups or project-load inputs. The existing API reports class-in-use as a specific HTTP 500 message; unknown errors stop execution. No live data changes, deployment, package publication or Git commit performed.

### Update 2026-09-13 22:48
- Decisions: Make docker-build self-sufficient when the tagged oldap-tools release has not yet been published to PyPI; only confirmed HTTP 404 authorizes automatic publication.
- Implementation: Added documented ensure-pypi-release prerequisite and stdlib helper with tag/package agreement, registry timeout/error handling, fresh temporary build artifacts, Poetry publication and bounded visibility polling. Six isolated tests and Make dry-run/diff checks pass.
- Open: Real publication/build on the user's next make docker-build; existing Poetry PyPI credentials required.
- Risks/Assumptions: No real upload, Docker build, version bump, commit or push performed during verification. Existing PyPI versions remain immutable and are reused; stale local dist files are never published.

### Update 2026-09-11 00:42
- Decisions: Require oldaplib 0.7.18 as the minimum runtime dependency for coordinated archive writes and recovery; a locally updated lock alone is insufficient for downstream package installs.
- Implementation: Updated dependency floor and refreshed lock; 72 tests pass across tests/ and test/. Restored the missing CarnivalEventTaxonomy-PrePhase2.yaml fixture from HEAD without changing the active taxonomy. Package build metadata requires oldaplib >=0.7.18,<0.8.0. Source version is 0.3.12 while the latest reachable tag is v0.3.11; align release/tag and publish PyPI before Docker build.
- Open: User Git consolidation, versioned publication and inspection of newly built Docker images before production activation.
- Risks/Assumptions: Existing unrelated work/staged deletions retained. No commit, tag, push, PyPI publication, Docker rebuild or production write. Package builds are local verification artifacts.

### Update 2026-09-03 00:04
- Decisions: Support progressive media description by separating recognisable object/event categories from the identity of a concrete linked ArchiveObject or CarnivalEvent. Keep both direct classifications optional and multi-valued.
- Implementation: Added `fasnacht:representedObjectType` and `fasnacht:representedEventType` to ArchiveMediaObject, targeting ObjectTaxonomy and CarnivalEventTaxonomy respectively, with multilingual labels and definitions that explicitly avoid asserting a concrete resource identity; updated model documentation and stable context.
- Open: Load the additive ontology update locally, expose both fields in media editing and the guided Wizard, prefill new concrete targets from direct categories, and combine direct plus linked types in public search with conflict handling.
- Risks/Assumptions: Existing data remains valid and unchanged. Direct values may become redundant or conflict with subsequently linked resources, so the application must surface rather than silently overwrite such cases.

### Update 2026-09-02 23:58
- Decisions: Model represented carnival actor/formation types as a dedicated media-content taxonomy rather than reusing the entity-oriented OrganisationTaxonomy. Keep the field optional and multi-valued.
- Implementation: Added the flat ten-node `CarnivalGroupingTaxonomy`, registered it in the Fasnacht ontology, and added the multi-valued `fasnacht:carnivalGrouping` link to ArchiveMediaObject with multilingual labels and definitions; documented its separation from named organisations, authorship, deposit, and custody.
- Open: Load the additive ontology/list update locally, then expose the new field in archive media forms, the guided Wizard, public detail/search facets, and optional OrganisationTaxonomy-based suggestions.
- Risks/Assumptions: No instance receives a grouping automatically. Suggested mappings from a named organisation must remain user-controlled, particularly for the legacy combined Artist/Business category.

### Update 2026-09-02 21:32
- Decisions: Allow archival objects, but not carnival events, to be placed directly in the archive structure. Keep placement optional and constrain each ArchiveObject to at most one ArchiveUnit.
- Implementation: Added `fasnacht:archiveUnit` to `fasnacht:ArchiveObject` with `max_count: 1`, targeting `shared:ArchiveUnit` and declared as the inverse of the existing generic `schema:about` archive relation; updated the technical model documentation and stable project context.
- Open: Load the additive ontology update locally, then extend archive placement, object creation/editing, export, and frontend workflows in a separate implementation slice.
- Risks/Assumptions: Existing ArchiveObjects remain valid because no `min_count` was introduced. No instance data is assigned automatically by this ontology-only change.

### Update 2026-08-31 22:40
- Decisions: Accept the successful digest-bound production cutover after its internal invariant checks and independently validate the immediate pre-cutover backup before declaring the data migration complete.
- Implementation: Production applied digest `a2ea33a59866a8b73695e07a8ab901ea8d9dc65c1e8c3edcc6969f4659e0b295`, changing 138 of 231 archive references. Apply verified exact flat lists, practice shapes, zero legacy/out-of-scope references, Topics removal, and unchanged counts of 88 CarnivalEvents and 30 Organisation references. The 495 KiB pre-cutover backup parses as 27,165 TriG triples across shacl/onto/lists/data and has SHA-256 `7dc8525f928acb5d7e9306ae40e02209d0e6f60d8dd58841107a152fdff522bb`.
- Open: Deploy the matching FasnachtsPage taxonomy build and smoke-test public/admin archive workflows; separately decide Organisation grouping and the 67 described yearly-event candidates.
- Risks/Assumptions: Archive editing remained frozen during apply. Aktuelles, EventAnnouncement, Story, and MediaLibraryObject resources were excluded by class and zero out-of-scope references were present. Keep the verified backup until post-deployment acceptance is complete.

### Update 2026-08-31 22:30
- Decisions: Treat a verified full production backup as a hard precondition and do not retry the failed apply until the standalone authenticated export succeeds.
- Implementation: Diagnosed the first production apply as failing in the pre-mutation raw RDF4J graph export; no backup file was created and the mutation phase was never entered. Raw graph exports now forward the configured GraphDB Basic Auth pair, reject partial credentials, report the failed graph and HTTP status, and have focused regression coverage.
- Open: Run a new standalone read-only production project dump, verify its gzip/TriG integrity and SHA-256 locally, then rerun the digest-guarded apply with a distinct new backup path.
- Risks/Assumptions: The two successful connection messages and missing backup file locate the failure after read-only plan generation but before the first migration write. No retry is authorized until backup verification passes.

### Update 2026-08-31 22:10
- Decisions: Classify the production-only archive object `Plagge` as Requisite and accept the production-only ClubHistory reference under social cohesion; retain `Launch Kooperation` as the archive CarnivalEvent evidenced by its class and ArchiveMediaObject link.
- Implementation: Added an explicit approved production decisions file with production-bound expected counts and rationale. The file is separate from the local rehearsal decisions and must be named explicitly for both connected plan and apply. Plan output and apply rejection now also name out-of-scope reference failures explicitly.
- Open: Generate the final connected production plan, review its zero-error manifest and digest, then obtain a separate apply authorization and maintenance-window confirmation.
- Risks/Assumptions: Approval covers taxonomy mapping decisions, not execution. Any production data change after the inventory changes the digest or guarded counts and forces a new review.

### Update 2026-08-31 21:55
- Decisions: Restrict the taxonomy cutover to the archive domain. Only exclusively typed ArchiveObject, CarnivalEvent, and ArchiveMediaObject resources may enter a migration action; NewsItem, EventAnnouncement, Story, MediaLibraryObject, and mixed/unknown types are protected.
- Implementation: Added class evidence to every planned action and a fail-closed `outOfScope` manifest section, digest input, readiness condition, summary count, regression test, and production-runbook boundary. The production inventory currently contains zero out-of-scope references among the three migrated taxonomies.
- Open: Resolve the production-only `Plagge` classification, approve production-specific review counts, regenerate the connected plan, and review its new digest before any write.
- Risks/Assumptions: `Launch Kooperation` is demonstrably an archive CarnivalEvent with one ArchiveMediaObject incoming link and no NewsItem, EventAnnouncement, Story, or MediaLibraryObject link in the production inventory; its editorial title alone does not determine its target event type.

### Update 2026-08-31 18:45
- Decisions: Treat Organisation taxonomy usages and CarnivalEvent resources as protected migration invariants, alongside exact flat-list contents and the two intended practice property shapes.
- Implementation: Added these values to the digest-bound plan and made apply fail after cutover if list nodes/parents, practice SHACL shapes, organisation-reference count, event-resource count, or Topics removal differ from the reviewed plan.
- Open: Regenerate the production plan after its inventory so the protected production counts are included in the approved digest.
- Risks/Assumptions: Organisation protection counts RDF references rather than distinct resources, ensuring multiple assignments on one resource cannot disappear unnoticed.

### Update 2026-08-31 18:40
- Decisions: Activate the flat Object/Event vocabularies and a separate multi-valued Practice vocabulary locally, retain stable compatible node IRIs, require digest-bound resource manifests and a complete backup, exclude Organisation and event-resource deletion, and use a narrow SHACL/OWL property cutover instead of rebuilding the in-use model.
- Implementation: Added reviewed count-guarded local decisions, dry-run/apply CLI commands, flat-list replacement, transactional reference migration/verification, practice model cutover, tests, active ontology/list sources, and the Phase-2 runbook. The local cutover changed 134 of 227 in-scope references, left 93 stable, produced 12/15/4 flat nodes, removed Topics, and verified zero legacy references, 10 practice values, 30 unchanged organisation references, and 87 unchanged events.
- Open: Generate and review a production inventory and production-specific `approved` decisions file, rehearse exact graph restoration in that environment, obtain the operator's digest/maintenance-window approval, then run the production command. Separately review the 67 described but unreferenced yearly events and resolve the grouping model.
- Risks/Assumptions: Nine generically titled local image records are an explicit Bild rehearsal assumption. A discarded generic `ontology load --mode replace` attempt exposed an OLDAPLIB SPARQL-generation failure after clearing the local model graphs; only those graphs were restored from the full backup before the narrow verified cutover. Production must use the migration command and must not use generic model replace.

### Update 2026-08-31 17:17
- Decisions: Prepare the expert-requested flat Fasnacht vocabularies additively and keep every active list and ontology reference unchanged during Phase 1. Retain compatible node IDs, model practice as a separate multi-valued draft list, keep DCMI media forms, treat `Objekt` as an ArchiveObject workflow, and block organisation migration pending expert clarification.
- Implementation: Added inactive flat Object/Event/Practice HList drafts, a complete grouped source-to-target mapping, a SELECT-only `fasnacht taxonomy-inventory` command with JSON/YAML reporting, orphan-node detection, mapping coverage/target validation, two-stage empty-year review/strict candidates with substantive evidence, focused tests, and Phase-1 documentation. The successful local run reported 119/87/21/30 references across Object/Event/Topics/Organisation, 67 empty-year review candidates, and no strict deletion candidate.
- Open: Review the completed local inventory and run the same report in production; resolve referenced review cases, approve broader/practice mappings, clarify the grouping model and `Ehrung`, and design the backed-up list-replacement cutover before any apply operation exists.
- Risks/Assumptions: Labels and translations are working drafts requiring domain review. `OrganisationTaxonomy` is intentionally untouched. The local inventory found referenced legacy nodes `CarnivalEventTaxonomy:HistorischAnderes` and `OrganisationTaxonomy:Stamm`, now explicitly mapped to review. OLDAP list-node IDs are virtual and the inventory derives them from their list-specific node IRI. The inventory never writes to OLDAP; an event candidate is only a report item and still requires human approval before deletion.

### Update 2026-08-29 00:28
- Decisions: Treat an object property targeting `oldap:Role` as an administrative reference, not an ordinary project-data link. Reuse the existing authoritative `Role.read` boundary and role cache rather than adding a StagingArea-specific exception.
- Implementation: Routed `shared:stagingDefaultRole` and every future `oldap:Role`-targeting property through administrative role resolution; retained normal project visibility/type checks for all other object links; added positive and missing-role regressions; and documented the YAML preflight contract. All 17 focused data-import and batch tests pass, Python compilation is clean, and no GraphDB-backed test was run.
- Open: Rerun the five-resource Chama staging dry-run, then apply and verify idempotency only after a clean preflight.
- Risks/Assumptions: OLDAP roles remain instances of the exact administrative class `oldap:Role`; the special resolution intentionally does not apply to unrelated project resources. This change is backward-compatible and performs no writes during preflight.

### Update 2026-08-27 23:46
- Decisions: Treat `to_class` changes as ordinary supported ontology updates; keep the fix in generic `oldap-tools` synchronization rather than adding a Chama-specific workaround or requiring destructive model replacement.
- Implementation: Normalized the OLDAP `sh:class`/`sh:in` fragments to their `toClass`/`inSet` constructor keys during property synchronization and ontology dumping. Added regressions proving `chama:Agent` is replaced by `chama:Person` and dumps use canonical `to_class`; documented the update behavior. Seven unittest cases, Python compilation, and Chama ontology validation pass.
- Open: Rerun the backed-up Chama ontology update with this working tree, then verify GraphDB reports `chama:Person` and refresh the SALSAH Story creation form.
- Risks/Assumptions: The failed earlier update left live `sh:class chama:Agent` unchanged, as confirmed directly in GraphDB. The correction is generic and backward-compatible, but must be rerun once to repair that live value.

### Update 2026-08-27 14:14
- Decisions: Interpret omitted or empty instance `permissions` as delegation to OLDAPLIB's authenticated-user default roles, not as an explicit empty `oldap:attachedToRole` assertion. Verify roles on resumable reruns only when YAML declared them.
- Implementation: Stopped passing empty permission mappings into dynamic resource constructors, made existing-resource role comparison conditional on declared permissions, documented the optional-field semantics, and added a regression covering construction plus resumable verification. All 47 unit tests and Python compilation pass.
- Open: Rerun the interrupted Chama map batch; the first three resources should verify as existing while the digital representation and map work continue from actual OLDAP state.
- Risks/Assumptions: An authenticated user with no default roles can create a resource without YAML-declared roles only if OLDAPLIB supports that state; normal deployments should configure intentional default roles or declare permissions explicitly. Omitted permissions deliberately do not constrain later permission changes.

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
