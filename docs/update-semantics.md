# Update Semantics

This page documents what OLDAP Tools changes when loading YAML into an existing project.

## Ontology Load Modes

`ontology load` supports two modes:

```bash
oldap-tools [common_options] ontology load --inf ontology.yaml --mode update
oldap-tools [common_options] ontology load --inf ontology.yaml --mode replace
```

### `update`

`update` is the default and recommended mode. It reads the current datamodel and applies changes from YAML through `oldaplib`.

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

By default, `ontology load` writes a gzipped TriG backup before applying changes. The backup includes model and list graphs, but not project data.

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
- If `properties` is present, the YAML property list is treated as the desired property set for that class.

The last point is important: existing class properties that are not listed in YAML are removed from the resource class. This is intentional current behavior and differs from taxonomy merging.

## Properties On Existing Resource Classes

When `properties` is present for an existing resource class:

- New properties listed in YAML are added.
- Existing properties listed in YAML are updated.
- Relationship targets declared with `to_class` replace the existing `sh:class`
  value when they differ.
- Existing properties missing from YAML are removed from the resource class.

`oldaplib` performs permission and in-use checks during the update. If a removal or restrictive change would affect data that is already in use, the update can fail. Do not rely on that as the primary safety mechanism; treat the YAML property list as a complete class definition whenever `properties` is present.

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

## Recommended Workflow

For existing production-like projects:

1. Run with the default backup behavior.
2. Validate YAML first with `ontology validate`.
3. Prefer `--mode update`.
4. Include full `properties` lists for resource classes when you intend class-property synchronization.
5. Use taxonomy YAML freely for additive list growth, but do not expect it to rename, move, or delete existing nodes.
