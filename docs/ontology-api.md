# Ontology Loading and Dumping Through OLDAP API

`ontology load` uses `oldap-api` by default. It reads YAML and referenced taxonomy
files locally, authenticates with the existing API, reads the current model and
lists, and sends only the required changes. GraphDB credentials, addresses and
repository options are not used by this transport. The API server selects its
repository and enforces OLDAP permissions for the authenticated user.

```bash
oldap-tools --api https://api.example.org --user "$OLDAP_USER" \
  ontology load --inf ontology.yaml --dry-run

oldap-tools --api https://api.example.org --user "$OLDAP_USER" \
  ontology load --inf ontology.yaml
```

`--dry-run` authenticates and performs reads, prints the planned methods, paths
and JSON bodies, and neither applies project/model/list/connector mutations nor writes a backup.
When `--password` is omitted, the CLI prompts without terminal echo.
It is a change preview, not proof that all server-side permission, datatype and
in-use checks will pass. Those checks remain authoritative at execution time.

## Incremental Changes and Removal

By default, omitted classes, standalone properties and class properties are
preserved. Explicitly supplied values update the corresponding attributes;
supported explicit `null` values remove attributes such as `max_count`.
Taxonomies retain existing nodes, labels and definitions and insert new nodes.
Duplicate node IDs and attempted parent changes fail before any writes.

```bash
oldap-tools --api https://api.example.org --user "$OLDAP_USER" \
  ontology load --inf ontology.yaml --remove-unused --dry-run
```

`--remove-unused` requests removal of existing class properties omitted from an
explicit `properties` list. Without a `properties` key, no removals are planned;
`properties: []` explicitly makes all eligible properties candidates. Removal
requests run after additions and updates. Standalone and foreign-project
property definitions are not garbage-collected.

The existing API delegates deletion to OLDAPLIB. Its in-use guard is conservative:
a class with instances can prevent removal even when the individual property has
no values. The client recognizes the existing API's specific class-in-use refusal,
prints `KEEP`, and continues. It does not interpret arbitrary HTTP 500 responses
as safe refusals. This option is not a global unused-RDF-predicate cleanup, does
not delete instance values, and does not bypass library checks. Direct transport
also requires this option to remove omitted class properties; its library refusal
aborts the direct update rather than continuing individual API operations.

## API Contracts

The importer reuses the project, model and taxonomy endpoints and adds connector
administration through `GET`/`PUT /admin/lucene/<project>`. The model JSON read
and TriG download must include the cache-freshness fix described below. The server's
OLDAPLIB must include the TriG export fixes verified on 2026-09-22: external
ontology exports embed triples rather than SPARQL updates, propertyless classes
terminate their OWL statements, and ontology declarations use `rdf:type`.
The local API has these fixes in an unpublished 0.7.21 development wheel; the
version number alone does not establish that another installation includes them.
Malformed model exports abort backup validation before any import writes, with
a concise error identifying the export line when available.

| Operation | API route |
| --- | --- |
| Login / refresh | `POST /admin/auth/<user>`, `POST /admin/auth/refresh` |
| Project read / create / start date | `GET`, `PUT`, `POST /admin/project/<project>` |
| Model read / create | `GET`, `PUT /admin/datamodel/<project>` |
| Class create / modify | `PUT`, `POST /admin/datamodel/<project>/<class>` |
| Class property create / modify / remove | `PUT`, `POST`, `DELETE /admin/datamodel/<project>/<class>/<property>` |
| Standalone property create / modify | `PUT`, `POST /admin/datamodel/<project>/property/<property>` |
| External ontology create / modify | `PUT`, `POST /admin/datamodel/<project>/extonto/<prefix>` |
| Taxonomy inventory | `GET /admin/hlist/search?project=<project>` |
| Taxonomy/node creation | `PUT /admin/hlist/<project>/<list>[/<node>]` |
| Connector configuration read / create / replace | `GET`, `PUT /admin/lucene/<project>` |
| Model/taxonomy export | `GET /admin/datamodel/<project>/download`, `GET /admin/hlist/<project>/<list>/download` |

The adapter translates snake-case YAML fields and language mappings to the
existing JSON contract. Property writes use `class`, while reads return `toClass`.
Editor aliases such as `TEXT_FIELD` are normalized to `dash:TextFieldEditor`
before comparison and writes, so equivalent spellings do not generate changes.
`list:<ListId>` becomes `<project>:<ListId>Node`. New classes are created in local
superclass dependency order before property relations are added. Implicit
`oldap:Thing` inheritance is preserved. New projects require `iri`, `namespace`
and `start`; the existing project modification route sets the start date because
the creation route currently ignores it when no end date is supplied.

## Backups and Failure Handling

Before the first write, the default API backup creates a new
`<project>-api-backup-<timestamp>.zip` containing:

- `manifest.json`: format version, project, timestamp and snapshot scope;
- `project.json` and `datamodel.json`: pre-import API representations (null for absent objects);
- `model.trig`: the existing API's model export, when a model exists;
- `lists/<ListId>.yaml`: all existing project taxonomies, including unmentioned lists;
- `lucene.json`: the reviewed connector envelope when YAML connector instructions
  are handled with `create` or `replace`, including null configuration for absence.

Use `--backup-out before-change.zip` to choose a name. Existing files are never
overwritten. Download, parsing or file-write failures prevent mutation. No backup
is written for a dry-run or an unchanged plan. `--no-backup` explicitly disables it.

**This ZIP is an API snapshot, not a raw GraphDB backup.** It contains no instance
data, roles or full administrative graphs; list exports do not preserve all RDF
audit metadata. It cannot be passed to `project load`, and no automatic ZIP restore
is provided. For exact graph restoration, retain a separate direct `project dump`
backup as described in [Operations](operations.md).

Each API mutation is a separate server transaction. Earlier successful requests
remain committed after a later failure. The CLI prints every successful step and
the failed method/path with the completed count. It never retries ambiguous
network failures or silently falls back to GraphDB. Inspect live state with a new
dry-run before resuming. Do not run concurrent schema editors/importers: planning
and backups are sequential reads, not an atomic snapshot or an optimistic lock.

Access tokens and refresh cookies stay in one in-memory HTTP session. The client
refreshes before expiry using the existing cookie endpoint; secure refresh cookies
require HTTPS. Failed refresh/authentication stops the run. Credentials and tokens
are not written into snapshots or progress messages.

## Dump a Portable YAML Package

`ontology dump` also uses the API by default. Supply a directory for a package
that includes every project taxonomy; missing directories are created:

```bash
oldap-tools --api http://localhost:8000 --user rosenth \
  ontology dump fasnacht --out-dir ./export/fasnacht --include-taxonomies
```

The omitted password is prompted without terminal echo. Output layout:

```text
export/fasnacht/
  ontology.yaml
  taxonomies/
    CreativeCommons.yaml
    ObjectTaxonomy.yaml
    ...
```

`ontology.yaml` contains project metadata, external ontology declarations,
standalone properties, resource classes and the project connector configuration
when present. Its `ontology.lists` entries use
relative `taxonomies/<ListId>.yaml` paths. Properties targeting exported taxonomy
node classes use `to_class: list:<ListId>`. The whole directory can be moved and
loaded without editing paths:

```bash
oldap-tools --api http://localhost:8000 --user rosenth \
  ontology load --inf ./export/fasnacht/ontology.yaml --connectors replace --dry-run
```

An unchanged representable model should plan zero operations. This roundtrip was
verified against the local Fasnacht API with 16 classes and ten taxonomies.
The YAML package is an editable model definition, not an exact RDF/audit backup:
instance data, roles and audit timestamps are excluded. Lucene configuration is included by default.
Unsupported nonempty OWL property-type extensions/annotation targets are rejected
rather than silently lost. The existing `node_kind` import limitation still applies
to models whose API representation exports that field.

Use `--out model.yaml` (or `.yaml.gz`) for a single YAML file without taxonomies;
the default single filename is `ontology.yaml`. `--out` and `--out-dir` are mutually
exclusive; API `--include-taxonomies` requires `--out-dir`.

Existing export files cause an error unless `--overwrite` is given. All downloads,
schema checks and destination conflict checks finish before file publication.
Files are staged and published atomically one by one, with `ontology.yaml` last.
An overwrite preserves unrelated files, including old taxonomies not present in
the new model (they are no longer referenced). Symlink destinations are rejected.
A refresh of an existing directory is not atomic as a whole: do not run concurrent
exporters or consume a package while overwriting it.

## Direct Administration and Current Limits

Other command groups retain their current transports. API dumps currently produce
YAML; use `ontology dump --transport direct --format trig --out model.trig.gz`
for the existing graph backup. Direct YAML dumps retain the legacy `--out` and
`--include-taxonomies` layout; `--out-dir` and `--overwrite` apply to API dumps only.
For full ontology graph replacement, select it
explicitly:

```bash
oldap-tools --graphdb http://localhost:7200 --repo oldap --user "$OLDAP_USER" \
  ontology load --transport direct --mode replace --inf ontology.yaml
```

The API loader supports `--mode update` and all three connector modes.
It rejects unsupported requests before authentication. The existing API also does
not accept `node_kind` writes, removal of the class `closed` attribute, or empty
`in` constraints; these are rejected instead of silently ignored. A newly added
property needs a complete definition with exactly one of `datatype` or `to_class`.

Unit/contract tests use the existing API response shapes and failure messages;
they do not establish compatibility with an independently deployed server version.
Before first deployment use a disposable development project: create a class with
properties and a taxonomy, rerun unchanged, add a property/node, then exercise
`--remove-unused` on an unused class and on a class with an instance. Verify that
the latter is preserved and that a new dry-run shows only the outstanding work.

## Lucene configuration roundtrip

YAML dumps include the project-named Lucene connector by default, alongside the
ontology and optional taxonomy files. No separate connector file is needed:

```bash
poetry run oldap-tools --api http://localhost:8000 --user rosenth ontology dump fasnacht --out-dir export/fasnacht --include-taxonomies
poetry run oldap-tools --api http://localhost:8000 --user rosenth ontology load --inf export/fasnacht/ontology.yaml --connectors replace --dry-run
```

Remove `--dry-run` to apply the reviewed changes. Missing passwords are prompted
without echo. Loading still defaults to `--connectors skip`. `create` refuses an
existing connector during planning, before ontology writes. `replace` compares
complete configurations and does not rebuild an identical index. Changed indexes
are applied after ontology/taxonomy operations; their reviewed revision is checked
again by the server. The API ZIP backup includes the prior `lucene.json` envelope
when connector handling is requested, including explicit absence.

The existing QName shorthand remains supported. Dumps use an exclusive native form
so advanced GraphDB options, filters and analyzer settings are retained exactly:

```yaml
ontology:
  project:
    shortname: demo
  lucene_connectors:
    demo:
      configuration:
        types: [https://example.org/demo/Book]
        fields:
          - fieldName: title
            propertyChain: [https://example.org/demo/title]
            analyzed: true
```

Native `configuration` cannot be mixed with shorthand keys or additional connector
groups. Native IRIs are passed verbatim; shorthand QNames are resolved as before.
Reading and managing connector configuration require project `ADMIN_MODEL` or
system `ADMIN_OLDAP`. Only the project-named connector is managed through the API; unrelated legacy
connector names are not removed. The instructions configure an index; they do not
back up its index files or indexed instance data.

This feature requires the matching oldap-api and oldaplib source updates. With an
older API use `ontology dump --no-connectors`; unavailable endpoints are otherwise
reported explicitly, never mistaken for an absent connector. Existing loads with
`--connectors skip` do not call the new endpoint.

GraphDB connector commands are not atomic RDF transactions. Failed replacement
attempts restore the previous configuration when absence can be established;
ambiguous results require inspection, and a restored index may still be rebuilding.
Advanced options are ultimately validated by GraphDB. Existing deployment writer
coordination covers the whole library replacement operation when archive
coordination is enabled; other deployments/direct clients must serialize connector
administration. Earlier model/list operations remain applied if a final connector
operation fails, and are reported by the loader.

Native export uses GraphDB's `listOptionValues` creation-options interface; see the
[official Lucene connector documentation](https://graphdb.ontotext.com/documentation/11.3/lucene-graphdb-connector.html).

## Workbench changes and model-cache freshness

The API model JSON read and TriG download must bypass the DataModel cache. Deleting
model graphs directly in Workbench otherwise leaves cached class definitions that
can make an import incorrectly plan no model recreation and back up stale model
state. The updated API reads GraphDB freshly for both endpoints and refreshes the
model cache. A same-state dump/load roundtrip does not cover this failure mode;
API regressions also simulate graph deletion while an old model remains cached.

This does not make arbitrary Workbench edits cache-aware. Other cached entities
may still need scoped invalidation. Never use Redis FLUSHALL: the deployment's
writer-coordination database must remain intact. Ontology YAML and API snapshots
exclude instance data; preserve a complete RDF backup before destructive tests.
