# Tools merge preparation — 2026-11-03

Local checkpoint on `migration/jena`, not a 1.0 release or deployment approval.
Follow the [coordinated release plan](../../oldap-setup/docs/jena-1.0-merge-plan.md).

## Reviewed scope

- Portable YAML fulltext fields, offline namespace/path planning, explicit API
  activation with revision/authorization preflight, final activation order and
  snapshot/dump preservation. Future projects can supply their own fields.
- Explicit Jena project dump/load routing, native RDF 1.2 graph transfer, atomic
  file replacement and pre/post-import cache handling. Administrative accounts,
  binary media and index configuration remain outside this bounded transfer.
- Canonical Fasnacht archive assignment and isPartOf direction; explicit null
  removes legacy inverse axioms during incremental imports. Data conversion is
  a separate documented migration, not implied by loading YAML.
- Disabled legacy package/image publication targets and retained migration docs.

Existing public `dump_project`/`load_project` arguments are unchanged. Ontology
API helpers add optional keyword-only `fulltext_mode` or `search_backend`; old
calls retain defaults. The CLI adds `ontology fulltext-plan`, `--fulltext` and
`--search-backend`. No harvester call-site change is required by these additions;
harvester Jena compatibility remains a separate release gate.

The existing split between offline planning, authenticated API operations and
native administrative transfer remains proportionate. No further architectural
blocker was found in the reviewed migration changes. Model/list/index activation
is intentionally a sequence of API transactions, not a global transaction;
failed final activation must not imply rollback of earlier writes.

## Corrections and validation

Two regressions failed before correction and pass afterward:

1. GraphDB project commands imported the Jena transport while selecting their
   backend, even with an older library lacking that module. Import now occurs
   only inside the selected Jena dump/load operation.
2. A dump exactly within the JSON request limit could exceed the loader's native
   file limit because of its metadata header. Both byte sizes are checked before
   replacing the destination, preserving an existing backup on failure.

All 171 tests in `tests` and `test`, plus seven subtests, pass with socket
connect/connect_ex blocked. No shared GraphDB, Jena or Redis is accessed.
Poetry metadata validation and wheel build pass. Extracting the wheel outside
this checkout verifies the new modules/schema and nine-field offline CLI plan.
Existing Typer/RDFLib/Poetry deprecation warnings remain.

The preceding sibling API full probe passes 162 normal-speed integration checks,
including actual Tools CLI imports, index activation/no-op replay and gzip native
project transfer. It predates the two boundary corrections above; these have
focused offline regressions, not a new full live-service run.

## Remaining release gates

Package/runtime/bump version remains 0.3.22. Do not republish this changed package
under that existing version. Its `oldaplib ^0.7.18` dependency and lock must be
updated with coordinated 1.0 packaging. Extracted-wheel checks use installed
current sibling library dependencies and are not clean 1.x distribution evidence.

The native transfer limit remains 262144 bytes; imports append, and repeated
blank-node imports are not idempotent. Do not treat this command as the production
backup/restore or GraphDB conversion procedure. Existing direct administration
commands remain GraphDB-specific unless explicitly documented otherwise.

The committed merge simulation against the locally fetched `origin/main` is
clean; refresh remote refs again before actual merging. No main merge, remote
push, tag, package/image publication or home/production update occurs here.
