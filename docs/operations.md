# Operations and Backups

This page covers operational behavior that matters when running OLDAP Tools against a real GraphDB repository.

## Project Dumps

Create a full project dump:

```bash
oldap-tools [common_options] project dump <project_id>
```

By default, the dump includes:

- admin/project/user/role information,
- `<project>:shacl`,
- `<project>:onto`,
- `<project>:lists`,
- `<project>:data`.

You can exclude graph families:

```bash
oldap-tools [common_options] project dump <project_id> --no-data --out model-only.trig.gz
```

## Project Loads

Load a project dump:

```bash
oldap-tools [common_options] project load --inf project.trig.gz
```

The TriG content is posted to the GraphDB statements endpoint. Embedded user records are then processed:

- missing users are created,
- existing users whose project role/membership differs are currently replaced.

## Ontology Load Backups

`ontology load` creates a backup by default:

```bash
oldap-tools [common_options] ontology load --inf ontology.yaml
```

The default backup name is:

```text
<project>-model-backup-YYYYMMDD-HHMMSS.trig.gz
```

The backup includes:

- `<project>:shacl`,
- `<project>:onto`,
- `<project>:lists`.

It does not include `<project>:data` or admin graphs.

Use an explicit backup path:

```bash
oldap-tools [common_options] ontology load --inf ontology.yaml --backup-out before-schema-change.trig.gz
```

## Ontology Dumps With Taxonomy Files

For YAML roundtrip checks, dump the ontology and all project taxonomies together:

```bash
oldap-tools [common_options] ontology dump <project_id> --out ontology.yaml --include-taxonomies
```

This creates:

- the ontology YAML file passed through `--out`,
- one `<ListId>.yaml` file per project list in the same directory,
- an `ontology.lists` mapping in the ontology YAML that references those files.

For `--format trig`, taxonomies are already included in `<project>:lists`; `--include-taxonomies` is intended for YAML dumps.

## Replace Mode Caution

`ontology load --mode replace` deletes and rebuilds:

- `<project>:shacl`
- `<project>:onto`

It is useful when deliberately recreating a datamodel from YAML, but it is not a small patch operation. Use only with a backup and a clear reason.

## Lucene Connectors

Lucene connector handling is controlled separately from datamodel loading:

```bash
oldap-tools [common_options] ontology load --inf ontology.yaml --connectors skip
oldap-tools [common_options] ontology load --inf ontology.yaml --connectors create
oldap-tools [common_options] ontology load --inf ontology.yaml --connectors replace
```

Modes:

- `skip`: do not touch connectors. Default.
- `create`: create the project connector; fail if it already exists.
- `replace`: drop the existing project connector if present and create it again.

The project connector name is always the project short name.

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

## Operational Checklist

Before changing a shared or production-like repository:

1. Validate YAML.
2. Keep the default ontology backup, or create an explicit project dump.
3. Prefer `ontology load --mode update`.
4. Review any resource class that contains `properties`, because that list is treated as the desired class-property set.
5. Use `--connectors replace` only when rebuilding the GraphDB Lucene connector is intended.
