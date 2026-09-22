# Operations and Backups

This page describes day-to-day ontology updates, exports, recovery, and the scope
of each backup. For API payloads and format details, see [Ontology API](ontology-api.md).

## Choose the Connection and Backup Scope

`ontology load` and `ontology dump` use `--transport api` by default. Supply `--api`
and an OLDAP `--user` before the command group; omitting `--password` prompts without
echo. The API server chooses the GraphDB repository. CLI `--graphdb` and `--repo`
do not redirect an API operation to another repository.

`--transport direct` selects GraphDB access for ontology commands. `project`,
`lists`, and `system` commands retain their direct transport; passing `--api`
does not convert them to API operations. See [Connection](installation.md).

| Artifact | Contents | Intended use |
| --- | --- | --- |
| API ontology YAML package | Project/model declarations, optional taxonomy files, native Lucene configuration by default | Editable definitions; incremental `ontology load` |
| API load backup `.zip` | Pre-import project/model JSON, model TriG when present, all existing taxonomy YAML, reviewed connector state when requested | Inspect/recover a failed import; no automatic ZIP restore command |
| Direct ontology backup or TriG dump | Project `shacl`, `onto`, and `lists` graphs | Graph-level model/list backup |
| Direct `project dump` | Selected project model/list/data graphs and project administration/user/role information | Project RDF transfer or recovery via `project load` |

Ontology packages and ontology-load backups contain **no instance data**. RDF
exports do not back up Lucene index files, repository settings or media binaries.
A project dump is not an entire GraphDB repository or service backup: system/shared
ontologies and other projects may also be required to reconstruct an installation.

## API Ontology Workflow

Examples below use Poetry from the source checkout. Installed CLI users can omit
`poetry run`. Common options come before `ontology`; command options follow it.

### 1. Export the Model, Taxonomies and Connector

```bash
poetry run oldap-tools --api http://localhost:8000 --user rosenth \
  ontology dump fasnacht --out-dir export/fasnacht --include-taxonomies
```

The package contains:

```text
export/fasnacht/
  ontology.yaml
  taxonomies/
    ObjectTaxonomy.yaml
    CreativeCommons.yaml
    ...
```

`ontology.yaml` contains the model and relative `ontology.lists` file references.
If the project connector exists, its complete native configuration is stored under
`ontology.lucene_connectors`; it needs no separate file. Move the whole package
together so taxonomy references remain valid.

Missing directories are created. Existing export files require `--overwrite`;
unrelated files remain. Downloads, validation and conflict checks complete before
publishing files. Each file is replaced atomically, with `ontology.yaml` last;
an overwrite is not atomic for the directory as a whole.

Use `--no-connectors` to omit Lucene instructions, including when exporting through
an older API without the connector endpoint. Without that opt-out, an unavailable
endpoint is an error, not evidence that no connector exists. For a single YAML
file, use `--out model.yaml` or `--out model.yaml.gz`; including taxonomy files
through the API requires `--out-dir`.

### 2. Validate and Preview Changes

```bash
poetry run oldap-tools ontology validate --inf export/fasnacht/ontology.yaml
poetry run oldap-tools --api http://localhost:8000 --user rosenth \
  ontology load --inf export/fasnacht/ontology.yaml --connectors replace --dry-run
```

Validation checks the ontology YAML schema offline. Load preparation also reads
referenced taxonomy files. The dry-run authenticates, reads the current API state
and lists the proposed operations; it performs no import mutations and creates no
backup. Execution-time permissions and GraphDB constraints can still reject writes.

The default model mode is `update`. Missing definitions are created; supplied
attributes are updated. Omitted classes, standalone properties and class properties
are preserved. Only `--remove-unused` requests guarded removal of omitted class
properties; an absent `properties` key never requests removal. Server in-use checks
remain authoritative. Taxonomy updates insert missing nodes, but do not rename,
move or delete existing ones. See [Update Semantics](update-semantics.md).

### 3. Apply and Verify

```bash
poetry run oldap-tools --api http://localhost:8000 --user rosenth \
  ontology load --inf export/fasnacht/ontology.yaml --connectors replace
```

A nonempty API plan is backed up before its first mutation. Successful operations
are logged individually. Run the same command with `--dry-run` again: an unchanged
representable model, taxonomy package and connector should plan **0 operations**.
Because taxonomy updates are additive, this does not certify exact equality of all
existing taxonomy labels, nodes or ordering with the YAML.

Also read representative resources in the application and test full-text search.
A zero-operation plan confirms no requested changes remain; it does not prove that
instance data exists or that a newly created search index has finished building.

## Lucene Connectors

Connector handling is independent of model `--mode` and supported by both transports:

| Load option | API behavior |
| --- | --- |
| `--connectors skip` | Default. Leave connectors unchanged; no connector endpoint reads. |
| `--connectors create` | Create the project connector. For an existing project, an existing connector is rejected during planning before model writes. |
| `--connectors replace` | Leave identical configuration unchanged; otherwise create/replace after checking the reviewed revision. |

If the YAML has no connector instructions, these modes do not remove a connector.
Reading or managing connector configuration requires project `ADMIN_MODEL` or
system `ADMIN_OLDAP`. The API manages only the connector named by the project short name. Legacy shorthand
QNames remain supported; exported native `configuration` preserves advanced options
and cannot be mixed with other connector groups or shorthand keys.

Connector mutations run after model/taxonomy operations. A stale connector revision
stops replacement before deletion. If creation fails after deletion, the server
attempts to restore the previous configuration when absence can be established.
GraphDB connector commands are not atomic RDF transactions; an ambiguous result
requires inspection, and restoration may require rebuilding the index. An identical
`replace` is not a force-reindex command. Direct `replace` retains its explicit
rebuild behavior. See [Connector details](ontology-api.md#lucene-configuration-roundtrip).

## Ontology Load Backups

API loads with a nonempty plan create a new file by default:

```text
<project>-api-backup-YYYYMMDD-HHMMSS-microseconds.zip
```

It contains:

- `manifest.json`, `project.json` and `datamodel.json` describing pre-import state;
- `model.trig` when a model exists;
- `lists/<ListId>.yaml` for every existing project taxonomy;
- `lucene.json` when connector instructions are handled with `create` or `replace`,
  including explicit absence when no connector existed.

A backup taken after a graph was deleted cannot recover that graph's earlier
contents. Retain a known-good export **before** destructive testing. API snapshots
are assembled from sequential reads and are not one repository-wide snapshot.
They cannot be passed to `project load`; there is no automatic ZIP restore command.

Dry-runs and unchanged plans do not create backups. `--no-backup` disables them;
`--backup-out before-change.zip` selects an explicit path. An existing backup file
is never overwritten. Backup download, parsing and file-write failures stop the
import before mutations.

Direct ontology loads retain the default
`<project>-model-backup-YYYYMMDD-HHMMSS.trig.gz`, containing `shacl`, `onto` and
`lists`, without instance data or admin graphs. For an explicit direct model dump:

```bash
oldap-tools --graphdb http://localhost:7200 --repo oldap --user rosenth \
  ontology dump fasnacht --transport direct --format trig --out model.trig.gz
```

## Project Dumps and Loads

These commands use direct GraphDB access. A default project dump includes project
administration/user/role information and the project `shacl`, `onto`, `lists` and
`data` graphs:

```bash
oldap-tools --graphdb http://localhost:7200 --repo oldap --user rosenth \
  project dump fasnacht --out fasnacht.trig.gz
```

`--no-data`, `--no-model`, `--no-lists` and `--no-admin` exclude the respective
families. These dumps do not include Lucene connector creation instructions;
retain the ontology YAML package for those.

```bash
oldap-tools --graphdb http://localhost:7200 --repo oldap-test --user rosenth \
  project load --inf fasnacht.trig.gz
```

Project load posts RDF to the GraphDB statements endpoint; it does not first clear
the destination. Embedded user records are then processed: missing users are
created, and existing users whose roles/membership differ are currently replaced.
Reimport into a populated repository is not an exact rollback and can leave extra
statements or duplicate blank-node structures. Use a prepared isolated target for
recovery tests, with compatible system/shared ontologies and repository settings.

## Failure Handling and Recovery Tests

Each API mutation commits independently. A later failure leaves earlier successful
operations in place. The CLI reports the completed count and failing method/path.
Inspect the error and current state, then make a new dry-run before resuming;
ambiguous network failures are never automatically retried. Avoid concurrent schema
editors/importers during planning, backups and application.

For a real recreation test, use a disposable copy of the repository and a separate
API configured for that copy. Changing CLI `--repo` does not retarget the API.

1. Save a complete repository backup and a known-good YAML package including
   taxonomies and connector configuration before deleting anything.
2. Verify the selected test repository and the actual graph IRIs. Preserve project
   registration, OLDAP/system/shared ontologies and the project data graph.
3. Remove the intended model/list graphs only in the test copy. Deleting RDF graphs
   does not remove the connector; remove it separately there if testing recreation.
4. Run the API load dry-run. It must propose the missing model/list/connector
   operations; an unexpected zero-operation plan after deletion needs investigation.
5. Apply, verify class and resource reads, check taxonomies and full-text search,
   then repeat the dry-run. Test an ordinary data edit too, to check index updates.

### Workbench Changes and Redis

Workbench edits bypass oldaplib cache invalidation. The updated API reads model
JSON and model TriG directly from GraphDB and refreshes the DataModel cache. This
prevents a stale cached ontology from suppressing recreation after graph deletion.
Both fixes must be deployed on the API used for the test, not just in the local CLI.

Other cached entities can still require scoped invalidation after direct GraphDB
edits. Do not use Redis `FLUSHALL` or clear the writer-coordination store. A service
restart alone does not establish that persistent Redis model entries were removed.
If resources disappear from the UI, check the data graph, model definitions and
search independently before assuming instance data was lost. See
[Cache details](ontology-api.md#workbench-changes-and-model-cache-freshness).

## Full Model Replacement Through Direct Transport

```bash
oldap-tools [common_options] ontology load --transport direct \
  --mode replace --inf ontology.yaml
```

This deletes and rebuilds `<project>:shacl` and `<project>:onto`. It differs from
`--connectors replace`, which controls the search connector. Although the lists
graph is not directly deleted, list-node class definitions also reside in the
model graphs. Prefer API `--mode update` for routine changes and retain backups
before deliberately replacing model graphs.

## System Graph Operations

System graph commands affect OLDAP system/shared/admin graphs. Valid graph names are:

- `oldap`
- `shared`
- `admin`

Load system graphs:

```bash
oldap-tools [common_options] system load oldap --inf /path/to/system-files
```

The command expects:

- `oldap.trig` for `oldap`,
- `shared.trig` for `shared`,
- `admin.trig` for `admin`.

Before loading, existing target graphs are moved to `_bak` graphs.

Restore the previous backup:

```bash
oldap-tools [common_options] system restore oldap
```

Clear the backup graph:

```bash
oldap-tools [common_options] system purge oldap
```
