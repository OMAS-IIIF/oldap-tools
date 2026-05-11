# Hierarchical Lists

Hierarchical lists are used for taxonomies and controlled vocabularies. They are stored in the project list graph:

```text
<project>:lists
```

The list loader supports both initial creation and safe additive extension.

## YAML Format

A list YAML file is a mapping from list IDs to list definitions:

```yaml
ObjectTaxonomy:
  label:
    - Object taxonomy@en
    - Objekttaxonomie@de
  definition:
    - Terms for classifying archival objects@en
  nodes:
    Costume:
      label:
        - Costume@en
        - Kostuem@de
      nodes:
        Mask:
          label:
            - Mask@en
            - Maske@de
```

Labels and definitions are lists of language-tagged strings in the form `Text@ll`.

## Loading Lists Directly

```bash
oldap-tools [common_options] lists load <project_id> --inf ObjectTaxonomy.yaml
```

If the list does not exist, it is created. If it already exists, the YAML is merged additively.

## Referencing Lists From Ontology YAML

Ontology YAML can reference list files:

```yaml
ontology:
  lists:
    ObjectTaxonomy: ObjectTaxonomy.yaml
```

It can also define a list inline:

```yaml
ontology:
  lists:
    ObjectTaxonomy:
      label:
        - Object taxonomy@en
      nodes:
        Costume:
          label:
            - Costume@en
```

A property can target a list node class:

```yaml
to_class: list:ObjectTaxonomy
```

## Dumping Lists With Ontology YAML

Use `ontology dump --include-taxonomies` to dump the ontology YAML and all project lists together:

```bash
oldap-tools [common_options] ontology dump <project_id> --out ontology.yaml --include-taxonomies
```

This writes the ontology YAML to `ontology.yaml`, writes each project list to `<ListId>.yaml` in the same directory, and adds references like this:

```yaml
ontology:
  lists:
    ObjectTaxonomy: ObjectTaxonomy.yaml
    CreativeCommons: CreativeCommons.yaml
```

## Additive Merge Behavior

For an existing list, loading is intentionally conservative:

- Missing YAML nodes are inserted.
- Missing subtrees are inserted recursively.
- Existing nodes are not deleted.
- Existing nodes are not moved.
- Existing labels and definitions are not changed by the merge.
- If the YAML would place an existing node under a different parent, the load aborts before inserting new nodes.

This means a YAML file can be used to grow a taxonomy safely, but not to reorder or prune it.

## Insertion Order

When possible, new nodes are inserted according to their position in the YAML relative to existing siblings. If the YAML only contains new nodes and omits existing siblings, new nodes are appended to the existing sibling list.

## Not Supported By The Safe Merge

The additive list merge does not currently support:

- deleting nodes,
- moving nodes,
- updating labels or definitions of existing nodes,
- interpreting YAML as a complete replacement of an existing taxonomy.
