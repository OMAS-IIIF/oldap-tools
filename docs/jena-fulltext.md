# Jena fulltext configuration

oldap-tools 1.x accepts a portable `ontology.fulltext` section.
It is validated using the same oldaplib helper as the Jena query adapter.
Offline planning does not activate an index. API imports can explicitly activate
the configuration with `--fulltext apply`, after backend/revision preflight.

## Development environment

Install the declared oldap-tools dependencies with Poetry. Released oldaplib
1.x includes the Jena adapter; a migration branch is no longer required.

For coordinated development against a sibling library checkout, an editable
environment is also supported:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -e . -e ../oldaplib pytest
```

Select `.venv/bin/python` in PyCharm. An editable sibling remains a local
development choice; published dependencies and the lockfile use released packages.

## YAML and offline commands

```yaml
ontology:
  project:
    shortname: example
    namespace: https://example.org/model/
  fulltext:
    fields:
      title: [schema:name]
      representedTitle: [example:represents, schema:name]
```

`project.namespace` is mandatory for offline fulltext preparation. Predicates
may be full IRIs, built-in OLDAP QNames or QNames declared through
`ontology.external_ontologies.<prefix>.namespace`. Conflicting namespace
bindings are rejected. Fields require a nonempty list of forward predicates;
unknown prefixes, empty fields, invalid names and unknown options are errors.
Project prefixes cannot leak between successive documents.

```sh
.venv/bin/oldap-tools ontology validate -i examples/ontology/fasnacht-jena.yaml
.venv/bin/oldap-tools ontology fulltext-plan -i examples/ontology/fasnacht-jena.yaml
```

The second command writes deterministic JSON to stdout: project ID, full data
graph IRI, full field paths and deduplicated `indexed_predicates`. Redirect stdout
to a file to save a review artifact. This is a desired configuration report, not
a server configuration file, executable deployment plan or live index status.
Neither command uses credentials, HTTP, GraphDB, Fuseki or Redis.

The Fasnacht example contains all nine field names from the current
`fasnacht/fasnacht-onto.yaml`, including `archiveMediaObjectText` for derived
PDF text. It is a configuration-only example, not a replacement ontology.
The migration ontology also contains the separately reviewed canonical
relationship changes; these are not applied to a running GraphDB by this example.

## Semantics and activation boundary

The terminal predicate of each path is indexed. Earlier predicates are joined
against current data at query time. Thus `representedTitle` indexes `schema:name`
and follows `example:represents` when searching. Aliases can share an indexed
predicate. Paths stay within the project's data graph. The normal Jena adapter checks access to the returned root resource and
requires DATA_VIEW on each referenced resource along the path, using current
asserted role memberships and RDF 1.2 grants. An annotation without its
membership edge is insufficient. Paths through ungranted embedded nodes are
not implicitly authorized by ownership of the root; configure a root text
property or explicitly readable resources instead.

Do not mix `fulltext` with `lucene_connectors`. Native GraphDB type restrictions,
language filters, analyzers and other connector options are not translated.
The portable field map alone does not establish full GraphDB search parity.
The Jena adapter supports words, nonleading wildcards and quoted phrases.
Unquoted words require all words within the configured field, across literal
values and independent of order. Quoted phrases match one indexed value.
Separate fields retain explicit AND/OR filters; arbitrary Lucene syntax remains
unsupported.

Direct `ontology load` rejects portable fulltext. API imports reject it by default;
use `--fulltext apply` to explicitly request activation. With `--dry-run`, this
reads and plans but does not rebuild. The API must support a backend-bound Jena
connection and current ADMIN_MODEL/ADMIN_OLDAP checks. Default GraphDB API
connections return 503, never a misleading absent-index response.

```sh
.venv/bin/oldap-tools --api http://localhost:8000 --user USER ontology load \
  -i ontology.yaml --fulltext apply --dry-run
.venv/bin/oldap-tools --api http://localhost:8000 --user USER ontology load \
  -i ontology.yaml --fulltext apply
.venv/bin/oldap-tools --api http://localhost:8000 --user USER ontology dump demo \
  --out ontology-export.yaml
```

API dumps default to Jena and include portable fulltext fields. Use
`--search-backend graphdb` explicitly when exporting from a legacy GraphDB API.
The explicit legacy `--transport direct` dump keeps its GraphDB default.
`--no-connectors` deliberately omits search configuration for either backend;
it is not a complete search-configuration backup. A failed Jena endpoint never
silently falls back to GraphDB or drops the fields.

These commands require a Jena-enabled API; choosing an export mode does not
switch the server's backend. A new project must be created first, then its ontology imported.
Preflight resolves authoritative namespace and reads index state before any
model/list writes. Activation is the final operation, guarded by the reviewed
revision. Unchanged configuration does not rebuild. API snapshots include
`fulltext.json`, including explicit absence. Dumps preserve full predicate paths
in the portable YAML section without querying GraphDB connectors.

Model/list writes remain independent API transactions. A final activation failure
does not undo earlier successful writes; the error reports committed progress.
No automatic mutation replay or automatic snapshot restore is performed.

See [the public API contract](../../oldap-api/doc/jena-fulltext-api.md) and
[the lifecycle report](../../oldaplib/docs/migration/jena-fulltext-activation.md). Do not emulate activation by posting
the portable configuration to the GraphDB Lucene endpoint. Public API and
oldaplib function signatures have not changed in this step.

## Verification

```sh
.venv/bin/python -m pytest --noconftest tests/test_fulltext_api.py tests/test_fulltext.py tests/test_ontology_api.py -q
```

The complete offline suite passes 173 tests and seven subtests (2026-11-10),
with socket connections blocked. Coverage includes namespace/path expansion,
alias deduplication, malformed configurations, offline CLI use, the current
Fasnacht field example and rejection before API authentication/direct connection.
New tests cover backend/permission preflight failures with zero mutations, final
activation order, no retry after uncertainty, snapshot state, unchanged replay
and portable dump/load parity. Existing API import/native connector tests remain
green. Real backend authorization/rebuild is exercised by the sibling library
probe; the tools model/list endpoints remain fixtures in these offline tests.

## Existing Fasnacht files

`fasnacht/fasnacht-onto.yaml` and its ten referenced taxonomy files were refreshed
from the production Jena API on 2026-11-10. The snapshot includes 16 classes and
nine managed fulltext fields, replacing the legacy GraphDB connector section.
Its local list paths retain the existing sibling-file layout. A read-only import
plan against production contains zero operations, including no index rebuild;
see [verification receipt](fasnacht-production-ontology-20261110.json).

The snapshot follows production project metadata, including its 2026-02-08 start
date and current labels; it is not a merge of production and older local proposals.
YAML ordering, language-string representation and formatting are normalized by
the exporter. Handwritten comments are not part of an API export.
`examples/ontology/fasnacht-jena.yaml` remains a fulltext-only example.

To refresh the current model including its fields and taxonomy files, export
from the target API:

```sh
oldap-tools --api https://api.example.org --user USER ontology dump fasnacht \
  --out-dir export/fasnacht --include-taxonomies
oldap-tools --api https://api.example.org --user USER ontology load \
  -i export/fasnacht/ontology.yaml --fulltext apply --dry-run
```

Review the plan before omitting `--dry-run`. Existing GraphDB type/language/analyzer
options must not be mechanically renamed to portable fields.
