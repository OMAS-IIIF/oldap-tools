# CODEX_LOG

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
