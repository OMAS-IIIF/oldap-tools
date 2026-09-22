# Command Reference

This page lists the CLI command groups and their main behavior. Common connection options are documented in [Installation and Connection](installation.md).

## Project Commands

### `project dump`

Export project graphs to a gzipped TriG file.

```bash
oldap-tools [common_options] project dump [options] <project_id>
```

Options:

- `--out`, `-o`: output file. Default: `<project_id>.trig.gz`.
- `--data` / `--no-data`: include or exclude `<project>:data`. Default: include.
- `--model` / `--no-model`: include or exclude `<project>:shacl` and `<project>:onto`. Default: include.
- `--admin` / `--no-admin`: include or exclude admin/project/user/role information. Default: include.
- `--lists` / `--no-lists`: include or exclude `<project>:lists`. Default: include.

The dump includes selected named graphs and, when admin data is included, serializes project users into special comment records that `project load` can read.

### `project load`

Import a gzipped TriG project dump.

```bash
oldap-tools [common_options] project load --inf dump.trig.gz
```

Options:

- `--inf`, `-i`: input dump file.

User records embedded in the dump are created if missing. If a user exists but project roles or project membership differ, the current implementation replaces the user.

## List Commands

### `lists dump`

Dump a hierarchical list to YAML.

```bash
oldap-tools [common_options] lists dump [options] <project_id> <list_id>
```

Options:

- `--out`, `-o`: output YAML file.

### `lists load`

Load or extend hierarchical lists from YAML.

```bash
oldap-tools [common_options] lists load <project_id> --inf lists.yaml
```

Options:

- `--inf`, `-i`: input YAML file.

Existing lists are extended additively. Missing nodes are inserted; existing nodes are not moved or deleted.

## Ontology Commands

### `ontology validate`

Validate an ontology YAML file against the bundled Yamale schema.

```bash
oldap-tools [common_options] ontology validate --inf ontology.yaml
```

Options:

- `--inf`, `-i`: input ontology YAML.
- `--schema`, `-s`: optional alternative Yamale schema.

### `ontology load`

Load or update a project datamodel from ontology YAML.

```bash
oldap-tools [common_options] ontology load --inf ontology.yaml [options]
```

Options:

- `--transport`: `api` (default) or `direct`.
- `--mode`, `-m`: `update` (default); `replace` requires direct transport.
- `--remove-unused`: opt in to guarded removal of omitted class properties.
- `--dry-run`: preview planned API operations without applying them (API only).
- `--connectors`: `skip` (default), `create`, or `replace`; supported with both transports.
- `--backup` / `--no-backup`: back up pre-import model/list state before applying a nonempty plan; API snapshots also retain reviewed connector state when requested. Default: enabled.
- `--backup-out`: API snapshot `.zip` or direct graph backup `.trig.gz`.

See [Update Semantics](update-semantics.md) before using this command on an existing project.
See [Operations and Backups](operations.md#api-ontology-workflow) for the full workflow, and
[Ontology API](ontology-api.md) for authentication, endpoint contracts and partial-failure handling.

### `ontology dump`

Dump a project ontology datamodel and its Lucene configuration through the API as YAML, optionally with taxonomy files.

```bash
oldap-tools [common_options] ontology dump [options] <project_id>
```

Options:

- `--out`, `-o`: output file. Default: `ontology.yaml`.
- `--out-dir`: API package directory, created if missing; writes `ontology.yaml`. Mutually exclusive with `--out`.
- `--include-taxonomies`: include all project taxonomy YAML files and relative `ontology.lists` references. API transport requires `--out-dir` and writes files under `taxonomies/`.
- `--include-connectors/--no-connectors`: include native Lucene instructions in YAML (default: included; API requires matching server update).
- `--overwrite`: replace conflicting API export files; unrelated files are retained. Default: refuse conflicts.
- `--transport`: `api` (default) or the legacy `direct` transport.
- `--format`, `-f`: `yaml` (default); `trig` requires direct transport.

```bash
oldap-tools --api http://localhost:8000 --user rosenth ontology dump fasnacht \
  --out-dir ./export/fasnacht --include-taxonomies
```

Direct TriG includes `<project>:shacl`, `<project>:onto`, and `<project>:lists`, but not `<project>:data`.
Direct YAML retains the existing file layout and overwrite behavior; the new directory and overwrite options apply to API exports.

## Archive Commands

### `archive validate`

Validate a recursive archive structure YAML file against the bundled Yamale schema without connecting
to OLDAP.

```shell
oldap-tools [common_options] archive validate --inf archive.yaml
```

Options:

- `--inf`, `-i`: input archive YAML.
- `--schema`, `-s`: optional alternative Yamale schema.

### `archive load`

Preflight or add a YAML-defined archive structure to an existing project. Dry-run is the default;
existing resources are never updated, moved, merged, or deleted.

```shell
oldap-tools [common_options] archive load <project_id> --inf archive.yaml
oldap-tools [common_options] archive load <project_id> --inf archive.yaml --apply
```

Options:

- `--inf`, `-i`: input archive YAML.
- `--dry-run`, `--apply`: preflight only or create the new archive units. Default: `--dry-run`.

Each YAML `id` deterministically becomes `<project_id>:<id>`. The loader refuses collisions. A
top-level YAML entry may use `parent` to attach its new subtree below an existing ArchiveUnit.
See [Archive Structure YAML](archive-yaml.md) for the complete format and safety semantics.

## Data Commands

### `data validate`

Validate a versioned OLDAP instance-data YAML or JSON document locally. This
command does not connect to OLDAP and does not require credentials.

```shell
oldap-tools data validate --inf resources.yaml
```

Options:

- `--inf`, `-i`: input YAML or JSON file.

Version 1 distinguishes literal values, language-tagged or explicitly typed
literals, IRI references, resource role permissions, and explicit media source,
handling, and ingest-profile instructions. It rejects unknown or duplicate keys
and ambiguous or unsupported media combinations. It accepts `iri: auto` in a
source document and reports how many identities still require preparation.
Validation is not yet
ontology-aware and performs no writes. See [Instance Data YAML/JSON](data-yaml.md)
for the complete format.

### `data prepare`

Mint stable, UUID-based project-local resource names for every `iri: auto`
placeholder. This is an offline step and requires no OLDAP credentials.

```shell
oldap-tools data prepare --inf incoming.yaml --out prepared.yaml
```

Options:

- `--inf`, `-i`: source YAML or JSON document;
- `--out`, `-o`: new prepared document in the same directory as the source;
- `--force`: replace an existing output file; the input is never overwritten.

The command changes only the placeholder scalars and preserves the source
formatting and comments. The prepared output becomes the durable authority for
dry-run, apply, reruns, and recovery. Live import and media-attach commands
reject unresolved `auto` identities. Resource names are never inferred from a
title, filename, path, or checksum. See
[Resource identity and `iri: auto`](data-yaml.md#resource-identity-and-iri-auto).

### `data import`

Preflight a versioned instance-data document against its live OLDAP project.
`--dry-run` is the default. `--apply` creates exactly one new RDF metadata
resource and rejects documents containing zero or multiple resources. A local
`image-iiif` instruction also imports the binary and verifies IIIF delivery.

```shell
oldap-tools [common_options] data import --dry-run --inf resources.yaml
```

Options:

- `--inf`, `-i`: input YAML or JSON file;
- `--dry-run`, `--apply`: read-only preflight or strict one-resource create.
- `--batch`: enable resumable sequential multi-resource processing;
- `--report`: with `--batch`, write a `.json`, `.yaml`, or `.yml` audit report.

The command checks the live classes, inherited properties, OLDAP value and
cardinality constraints, linked-resource visibility and target classes, roles,
administrative role-valued object properties such as
`shared:stagingDefaultRole`, `ADMIN_CREATE`, and existing target IRIs. Apply
repeats those checks immediately before OLDAP's atomic create. It never updates,
overwrites, or deletes data.
Local-media preflight additionally verifies the relative source path and
SHA-256 before any write. Use common `--api` and `--media` options to override
the OLDAP API and media-server origins. The input must contain no unresolved
`iri: auto` placeholders; prepare them offline first.

With `--batch`, the complete document is preflighted before the first write.
Apply then processes resources in document order and stops at the first
failure. A repeated run verifies already-created metadata and already-attached
media, then resumes. Existing metadata must match the YAML apart from documented
server-managed delivery properties; batch mode never becomes an update or
upsert operation.

### `data media-attach`

Attach or idempotently verify the media declared for one existing resource.
This is the recovery path when RDF creation succeeded but media ingest did not,
and it also supports records created by an earlier metadata-only workflow.

```shell
oldap-tools [common_options] data media-attach --dry-run --inf resource.yaml
oldap-tools [common_options] data media-attach --apply --inf resource.yaml
```

Dry-run verifies source integrity, authentication, target visibility, and
MediaObject compatibility without writing. Apply streams the binary to
oldap-mediaserver or verifies an already attached matching asset, then checks
the OLDAP delivery fields and authenticated IIIF `info.json`.

## Staging Commands

### `staging ensure-mobile-folder`

Validate existing StagingArea folder hierarchies and create the application-managed `Mobile`
folder directly below `top` when it is missing. The operation is idempotent and uses dry-run by
default.

```shell
oldap-tools [common_options] staging ensure-mobile-folder --staging-area <staging-area-iri>
oldap-tools [common_options] staging ensure-mobile-folder --staging-area <staging-area-iri> --apply
```

Options:

- `--project`: project containing the StagingAreas. Default: `fasnacht`.
- `--staging-area`: StagingArea IRI; repeat the option to process several explicit areas.
- `--all`: process every StagingArea instead of explicit IRIs.
- `--dry-run`, `--apply`: report only or create missing folders. Default: `--dry-run`.

Exactly one of `--all` and one or more `--staging-area` options is required. The command refuses
ambiguous `top` folders, duplicate `Mobile` folders, and a folder named `Mobile` outside `top`.

## Fasnacht Migration Commands

### `fasnacht taxonomy-inventory`

Run the SELECT-only source-list and empty-year-event inventory described in
`fasnacht/TaxonomyPhase1.md`.

### `fasnacht taxonomy-migration-plan`

Build a fresh resource-level migration manifest from the live inventory,
Phase-1 mapping, and reviewed Phase-2 decisions. The command never writes to
OLDAP. The manifest reports actionable, unchanged, unresolved, and unexpected
rule-count totals and carries a deterministic digest.

```shell
oldap-tools [common_options] fasnacht taxonomy-migration-plan \
  --decisions fasnacht/TaxonomyPhase2LocalDecisions.yaml \
  --out migration-plan.yaml
```

### `fasnacht taxonomy-migration-apply`

Apply the Object/Event/Practice migration only after a matching dry-run. The
command requires the exact plan digest and a new full-project backup path. A
`local-rehearsal` decision document additionally requires the explicit
`--allow-local-rehearsal` flag and must never be treated as production
approval.

```shell
oldap-tools [common_options] fasnacht taxonomy-migration-apply \
  --expected-digest <digest> \
  --backup-out <new-backup.trig.gz> \
  --allow-local-rehearsal
```

The command does not modify `OrganisationTaxonomy` and never deletes
CarnivalEvent resources. See `fasnacht/TaxonomyPhase2.md` for the complete
production gate and rollback requirements.

## System Commands

System graph commands operate on OLDAP system/shared/admin graphs. Valid graph arguments are `oldap`, `shared`, and `admin`.

### `system load`

Load system graph files from a directory.

```bash
oldap-tools [common_options] system load <oldap|shared|admin> --inf <directory>
```

The loader expects the file name to match the graph argument:

- `oldap`: `<directory>/oldap.trig`
- `shared`: `<directory>/shared.trig`
- `admin`: `<directory>/admin.trig`

Existing system graphs are first moved to backup graphs with a `_bak` suffix.

### `system restore`

Restore the last `_bak` system graph backup.

```bash
oldap-tools [common_options] system restore oldap
```

### `system purge`

Clear the `_bak` backup graph for a system graph.

```bash
oldap-tools [common_options] system purge oldap
```
