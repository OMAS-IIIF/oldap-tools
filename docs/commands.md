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

- `--mode`, `-m`: `update` or `replace`. Default: `update`.
- `--connectors`: `skip`, `create`, or `replace`. Default: `skip`.
- `--backup` / `--no-backup`: create a model/list backup before loading. Default: backup enabled.
- `--backup-out`: explicit backup output file.

See [Update Semantics](update-semantics.md) before using this command on an existing project.

### `ontology dump`

Dump a project ontology datamodel as YAML or as gzipped TriG.

```bash
oldap-tools [common_options] ontology dump [options] <project_id>
```

Options:

- `--out`, `-o`: output file. Default: `ontology.yaml`.
- `--format`, `-f`: `yaml` or `trig`. Default: `yaml`.
- `--include-taxonomies`: when dumping YAML, write all project taxonomies as separate `<ListId>.yaml` files and reference them from `ontology.lists`.

The TriG format includes `<project>:shacl`, `<project>:onto`, and `<project>:lists`, but not `<project>:data`.

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
oldap-tools [common_options] system restore <oldap|shared|admin>
```

### `system purge`

Clear the `_bak` backup graph for a system graph.

```bash
oldap-tools [common_options] system purge <oldap|shared|admin>
```
