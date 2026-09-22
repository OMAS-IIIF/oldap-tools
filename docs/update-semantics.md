# Update Semantics

This page documents what OLDAP Tools changes when loading YAML into an existing project.

## Ontology Load Modes

`ontology load` defaults to API transport and incremental updates. Direct
administration also supports graph replacement:

```bash
oldap-tools [common_options] ontology load --inf ontology.yaml --mode update
oldap-tools [common_options] ontology load --transport direct --inf ontology.yaml --mode replace
```

### `update`

`update` is the default and recommended mode. It reads the current datamodel and
applies explicit YAML changes through existing `oldap-api` endpoints. The server
uses `oldaplib`; `--transport direct` invokes that library locally.

It can:

- create missing external ontology declarations,
- update existing external ontology declarations,
- create new standalone properties,
- update existing standalone properties,
- create new resource classes,
- update existing resource classes,
- add properties to existing resource classes,
- update properties on existing resource classes.

### `replace`

`replace` deletes the existing datamodel graphs:

- `<project>:shacl`
- `<project>:onto`

Then it recreates them from YAML.

It does not delete `<project>:lists` directly. However, because list node classes have SHACL/OWL definitions in the model graphs, replacing the datamodel should still be treated as a high-impact operation. Keep backups.

## Automatic Backup

By default, API loading writes a ZIP snapshot before applying a nonempty plan.
It includes the API model TriG export, project/model JSON and all project list
YAML, plus reviewed connector state when requested, but no instance data or complete administrative graphs. It is not accepted
by `project load`. Direct transport retains the gzipped model/list graph backup.
See [Ontology API](ontology-api.md) for snapshot scope and recovery limitations.

Disable only when you already have another reliable backup:

```bash
oldap-tools [common_options] ontology load --inf ontology.yaml --no-backup
```

## Hierarchical Lists / Taxonomies

List updates are additive and conservative.

For an existing list:

- YAML nodes that do not exist are inserted.
- Subtrees below new nodes are inserted recursively.
- Existing nodes are not deleted.
- Existing nodes are not moved.
- Existing node labels and definitions are not updated.
- A parent mismatch for an existing node aborts the load before inserts are performed.

This behavior is designed to support safe taxonomy extension.

## Resource Classes

Resource classes under `ontology.classes` are handled as datamodel update items.

If a class does not exist, it is created.

If a class exists:

- `label`, `comment`, `closed`, and `superclass` are updated only when the corresponding key is present in YAML.
- If `properties` is absent, the class property set is left unchanged.
- If `properties` is present, supplied properties are added or updated; omitted properties remain unchanged by default.

Only `--remove-unused` makes omitted class properties removal candidates. An
absent `properties` key never requests deletion, even with this option. Classes
and standalone definitions absent from YAML are never automatically deleted.

## Properties On Existing Resource Classes

When `properties` is present for an existing resource class:

- New properties listed in YAML are added.
- Existing properties listed in YAML are updated.
- Relationship targets declared with `to_class` replace the existing `sh:class`
  value when they differ.
- Existing properties missing from YAML are preserved unless `--remove-unused` is supplied.

The API loader excludes standalone and foreign-project definitions from removal.
`oldaplib` performs permission and in-use checks during updates. Its current guard
may refuse removal for any class with instances, even if the particular property
has no values. API loading prints `KEEP` for that specific refusal and continues;
other failures stop the import. Direct transport propagates the library refusal.
Review `--remove-unused --dry-run` before requesting synchronization.

## Standalone Properties

Standalone properties under `ontology.standalone_properties` are handled independently:

- Missing standalone properties are created.
- Existing standalone properties are updated.
- Standalone properties not mentioned in YAML are not deleted by the current loader.

## Attribute Deletion With `null`

Some property/class attributes can be deleted by setting them to `null` in update mode, for example:

```yaml
classes:
  fasnacht:Person:
    properties:
      - iri: schema:familyName
        max_count: null
```

Use this intentionally. A missing YAML key usually means "do not change this attribute"; a key set to `null` means "remove this attribute" where supported by the datamodel update logic.

## Connector Updates

Connector mode is independent of model mode. Loading defaults to
`--connectors skip`, even when the YAML includes connector instructions. In API
mode, `create` refuses an existing connector and `replace` leaves an identical
configuration unchanged. A changed configuration is applied after model/list
operations with a revision check. Native configuration replaces the complete
connector configuration; it is not an additive field merge with the remote index.
Direct `replace` explicitly rebuilds the connector. See
[Operations](operations.md#lucene-connectors) for failures and backup scope.

## Recommended Workflow

For existing production-like projects:

1. Run with the default backup behavior.
2. Validate YAML first with `ontology validate`.
3. Prefer `--mode update`.
4. Use `--dry-run` to inspect API changes; opt into removals with `--remove-unused` only when the supplied class property lists describe the intended retained set.
5. Use taxonomy YAML for additive list growth, but do not expect it to rename, move, or delete existing nodes.
6. Select connector mode explicitly and verify resource reads and search after application.

For a complete command sequence and tests after Workbench changes, see
[Operations and Backups](operations.md).
