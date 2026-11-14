# Reification YAML — stage 2 acceptance

Implemented locally on `codex/reification-properties` in oldap-tools, with
small integration corrections in the sibling oldaplib and oldap-api branches.
No dependency pin, published artifact, service or live ontology was changed.
Use the matching sibling sources for development.

The [YAML contract](ontology-yaml.md#reifier-shapes-stage-2) and complete
[Travel example](../examples/ontology/travel-reification.yaml) cover definitions,
property-use references, explicit false/removal and incremental field merging.
The four-stage authority remains the library's
[working plan](../../oldaplib/docs/reification-properties-plan.md).

## Implementation boundaries

- `ontology_reification.py` performs shared read-only merging and reference
  validation; both transports retain their existing persistence mechanisms.
- `ontology.py` builds/synchronizes ReifierShape definitions, preflights before
  project/list/model mutations, and exports definitions and attachments.
- `ontology_api.py` plans shape CRUD, orders attachments/removals, preserves
  omission and uses fresh state to avoid duplicate work on replay.
- `ontology_api_dump.py` preserves definitions in YAML. Its internal preflight
  adapter tolerates unrelated legacy annotation metadata; public exports still
  reject unsupported metadata rather than lose it.
- Library fixes preserve numeric zero constraints and avoid prefix-only OWL
  updates for SHACL-only edits. API property-update allowlists now include the
  new fields; shape replacement preserves absent `uniqueLang` instead of adding
  the legacy implicit false default.

Inherited policies are checked against fresh local/shared model snapshots.
Concurrent schema writers remain unsupported. In-use checks and foreign
references outside the fetched models are ultimately enforced by the store.
Imports are not atomic across the whole YAML document. No instance annotation
CRUD, instance YAML support or search support is included.

## Verification

The complete offline tools suite passes: **199 tests and seven subtests**,
including six sibling-source integration cases. The focused library/API
regression suite passes **84 tests**. Integration cases use the actual library
and Flask routes, first against isolated RDFLib and then against pinned Jena
6.2.0/TDB2 through the diagnostic JSON-line bridge. Python network connections
are blocked during acceptance; no HTTP listener or live Redis is used.

Coverage includes YAML -> library/API -> RDF -> YAML, unchanged replay,
shape field changes, false and zero values, explicit reference/shape deletion,
shared references, invalid input before writes, ordered partial-apply recovery,
legacy compatibility, Fasnacht fixtures and API backup contents.

From the sibling oldaplib checkout:

```sh
PYTHONPATH=.:../oldap-tools:../oldap-tools/src:../oldap-api \
OLDAP_TEST_FUSEKI_JAR=/path/to/apache-jena-fuseki-6.2.0/fuseki-server.jar \
OLDAP_TEST_JAVA_HOME=/opt/homebrew/opt/openjdk@25 \
../oldap-api/.venv/bin/python -m pytest \
  ../oldap-tools/tests ../oldap-tools/test -q
```

The jar's enforced SHA-256 is
`2c92c598e65ab69d99820052e05f4277ed1d77980a8845f87545ad35b71a76ee`.
Without the native environment variable, Jena cases are explicitly skipped;
sibling-source integration also requires oldap-api and the library test helpers.
Temporary test-owned TDB2 directories are used. This verifies generated queries
and API view behavior, not remote HTTP authentication/deployment acceptance.

[Acceptance receipt and source hashes](reification-stage2-results.json).

Next: stage 3 instance annotation lifecycle and validation.
