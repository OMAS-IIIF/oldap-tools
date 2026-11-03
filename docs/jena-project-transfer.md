# Scoped project graph transfer on Jena

The existing `project dump` / `project load` commands now select a native Jena
path when `OLDAP_BACKEND=jena`. GraphDB remains the default. Their Python
signatures and CLI argument names are unchanged. This is a bounded migration
facility, not a complete production backup/restore system.

## Included and excluded state

This step transfers the selected `data`, `shacl`, `onto` and `lists` graphs.
Both ends must already have the same project short name and namespace registered.
Target roles/users, base/shared ontologies and server policy must be provisioned
separately. Raw access requires current `ADMIN_OLDAP` on `oldap:SystemProject`;
project writers cannot use it to bypass individual resource permissions.

Jena dumps currently require `--no-admin`. The existing GraphDB administrative
restore can delete/recreate users; that behavior is deliberately not enabled on
Jena. Legacy GraphDB files are rejected before connecting. Conversion of an
existing RDF-star dataset into the intended OLDAP RDF 1.2 permission model is a
separate migration step, not an implicit text replacement.

No binary media, managed fulltext configuration, deployment policy, transaction
receipts or default graph is included. This file alone is **not a complete
project backup**. Existing ontology/fulltext API backups remain separate.
Active Jena indexes receive imported data through the ordinary dataset write
path, but the transfer does not activate or restore field configurations.

## Usage

Use the migration checkout's existing private Jena connection environment
(`OLDAP_JENA_URL`, service/bootstrap/fulltext credentials and authentication
settings), with `OLDAP_BACKEND=jena`. GraphDB URL/repository options do not
redirect that backend-bound connection. Configure the same archive policy and
durable writer coordination as the server when archive coordination is enabled.
Keep object-cache and coordination Redis databases separate.

```sh
oldap-tools --user administrator project dump myproject --no-admin --out myproject.trig.gz
oldap-tools --user administrator project load --inf myproject.trig.gz
```

The normal hidden password prompt applies. Existing `--no-data`, `--no-model`
and `--no-lists` flags select the graph subset. A native dump contains a versioned
comment header recording the project and selected graph parts, followed by TriG.
No new public function parameters or harvester changes are required.

## Integrity and transaction behavior

- Jena parses/writes RDF 1.2 natively. All selected graphs are serialized together,
  preserving blank nodes shared across graphs and RDF triple terms in grants.
- Export sees one snapshot (or the caller's active transaction). A complete file
  replaces the destination atomically; failures preserve the previous file.
- Import parses the entire payload and validates every graph before writing.
  Foreign, administrative, reserved and default graphs are refused. The target
  namespace determines scope; names are never rewritten.
- Import **appends** inside the existing resource transaction boundary. An outer
  failure rolls back the import too. It does not clear/replace target graphs,
  retry updates or claim that importing the same blank nodes twice is idempotent.
- The CLI checks/clears the object cache before import and clears it after commit.
  A post-commit cache failure explicitly reports that RDF committed and must not
  be reimported. Concurrent application/cache traffic remains a separate gate;
  perform this administrative migration with writers/readers quiesced.

The experimental service accepts at most 262144 bytes per JSON request. Dumps
that cannot fit that envelope are refused instead of silently split into
non-atomic chunks. The exporter checks both the JSON request and the native file including its
metadata header, so accepted dumps fit the loader too. Compression does not
remove this limit. Parsing/export use
memory; streaming and large-dataset acceptance remain open.

## Acceptance

Acceptance passes 154 integration checks (145 previous plus 9 transfer checks),
14 library tests and 17 tools tests. Native import also updates the configured
fulltext index, and outer rollback restores both RDF and searchable text.

See sibling `oldap-api/doc/jena-project-transfer-results.json` for retained owned
integration results. The fixture uses a dedicated registered project, shared
blank nodes across data/list graphs, language literals and real RDF 1.2 grants.
The real CLI writes a gzip dump and loads it into cleared owned graphs. Additional
checks cover current root authorization, joined rollback and invalid graph/input
refusal. A socket-only Redis owned by the test supplies actual CLI cache clearing;
the user's Redis and existing development projects are not selected.

The general HTTP export-job endpoints and binary archives are separate workflows
and are not made production-ready by this raw graph transfer step.
