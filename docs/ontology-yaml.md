# Ontology YAML

Ontology YAML describes an OLDAP project datamodel and optional supporting configuration.

The top-level object must contain an `ontology` mapping:

```yaml
ontology:
  project:
    shortname: fasnacht
    iri: https://fasnacht.digital
    namespace: http://fasnacht.digital/ns/
    start: 2025-06-01
```

## Project

The `project` block identifies the target project:

```yaml
project:
  shortname: fasnacht
  iri: https://fasnacht.digital
  namespace: http://fasnacht.digital/ns/
  start: 2025-06-01
  label:
    en: Fasnacht
  comment:
    en: Fasnacht project
```

If the project already exists, `shortname` is sufficient for lookup. If it does not exist, `iri`, `namespace`, and `start` are required so the loader can create it.

## Lists

Lists can be external files or inline mappings:

```yaml
lists:
  CreativeCommons: CreativeCommons.yaml
  ObjectTaxonomy:
    label:
      - Object taxonomy@en
    nodes:
      Costume:
        label:
          - Costume@en
```

See [Hierarchical Lists](lists.md) for the list format and merge behavior.

`ontology dump --include-taxonomies` writes all project lists as separate `<ListId>.yaml`
files next to the ontology YAML file and adds a `lists` block that references those files.

## External Ontologies

External ontologies declare prefixes and proposed classes/properties:

```yaml
external_ontologies:
  schema:
    namespace: https://schema.org/
    label: schema.org
    proposedResourceClass:
      - Person
      - Organization
    proposedDatatypePropertyClass:
      - name
```

The schema also accepts snake-case aliases:

- `resource_classes`
- `datatype_properties`
- `object_properties`

## Resource Classes

Resource classes are listed under `classes` using QNames:

```yaml
classes:
  fasnacht:Person:
    label:
      en: Person
      de: Person
    comment:
      en: A person represented in the archive
    superclass:
      - schema:Person
    closed: true
    properties:
      - iri: schema:familyName
        datatype: xsd:string
        name:
          en: Family name
          de: Nachname
        min_count: 1
        max_count: 1
        order: 1
        editor: TEXT_FIELD
```

## Properties

Properties can be defined inline on a resource class or as reusable standalone properties.

Inline property:

```yaml
classes:
  fasnacht:Story:
    properties:
      - iri: fasnacht:storyContent
        datatype: rdf:langString
        name:
          en: Story content
        language_in:
          - en
          - de
        min_count: 1
```

Standalone property:

```yaml
standalone_properties:
  fasnacht:archiveObjectTitle:
    datatype: rdf:langString
    name:
      en: Archive object title
```

`subproperty_of` accepts one IRI string or a complete list of parent IRIs, including
multiple imported parents. Direct exports use lists; API exports may retain a
singleton string. Parent order does not cause an API update on reimport. Omission
preserves existing parents during incremental import; null or an empty list clears
them explicitly. The same syntax applies to reifier fields, and library ownership
checks still protect foreign predicate hierarchies.

Common property keys:

- `iri`
- `subproperty_of`
- `datatype`
- `to_class`
- `node_kind`
- `name`
- `description`
- `language_in`
- `unique_lang`
- `in`
- `min_length`, `max_length`, `pattern`
- `min_exclusive`, `min_inclusive`, `max_exclusive`, `max_inclusive`
- `less_than`, `less_than_or_equals`
- `inverse_of`, `equivalent_property`
- `min_count`, `max_count`
- `order`
- `group`
- `editor`

Use `to_class: list:<ListId>` to point to the node class generated for a hierarchical list.

## Lucene Connectors

Lucene connectors are optional and are skipped unless `ontology load` is called with `--connectors create` or `--connectors replace`. Both transports support these modes.

```yaml
lucene_connectors:
  fasnacht:
    types:
      - fasnacht:Story
      - fasnacht:ArchiveObject
    fields:
      - fasnacht:storyContent
      - schema:description
      - fieldName: representedArchiveObjectTitle
        chain:
          - fasnacht:archiveMediaObjectOf
          - fasnacht:archiveObjectTitle
```

OLDAP Tools creates one GraphDB Lucene connector per project. The connector name is always the project short name. Multiple shorthand entries under `lucene_connectors` are treated as grouping blocks and merged into that one project connector. Native `configuration` must be the sole connector entry.

Single-property fields may be written as a QName. Multi-step chains must provide an explicit `fieldName`.

Supported shorthand connector settings:

- `types`
- `languages`
- `fields`
- `readonly`
- `detectFields`
- `importGraph`
- `skipInitialIndexing`
- `boostProperties`
- `stripMarkup`

Dumps use the native form to retain all GraphDB creation options, including
advanced field filters and analyzers:

```yaml
lucene_connectors:
  fasnacht:
    configuration:
      types:
        - http://fasnacht.digital/ns/ArchiveObject
      fields:
        - fieldName: title
          propertyChain:
            - http://schema.org/name
          analyzed: true
```

Native values are passed verbatim, so use full IRIs rather than shorthand QNames.
`configuration` cannot be combined with shorthand keys or other connector groups.
Existing shorthand remains accepted. For modes, API requirements and roundtrip
behavior, see [API workflow](ontology-api.md#lucene-configuration-roundtrip).

## Reifier shapes (stage 2)

Named annotation definitions are available through both ontology transports.
They require the matching local stage 1B library/API sources; released 1.1.0
packages do not yet provide these endpoints. No deployment is implied.

```yaml
ontology:
  project:
    shortname: travel
  reifier_shapes:
    travel:VisitAnnotationShape:
      properties:
        - iri: travel:dateTime
          datatype: xsd:dateTime
          min_count: 1
          max_count: 1
  classes:
    travel:Travel:
      properties:
        - iri: travel:isAt
          to_class: travel:GeographicLocation
          reifier_shapes: [travel:VisitAnnotationShape]
          reification_required: true
    travel:GeographicLocation: {}
```

The complete [Travel fixture](../examples/ontology/travel-reification.yaml)
also includes new-project metadata. `ontology validate --inf FILE` checks local
syntax and supported field keys; connected planning resolves existing/shared
shape references and merged constraints before mutations. Shape declarations
may follow their references in the YAML file.

`reifier_shapes` on a property is a list of named local or `shared:` shapes.
All listed shapes apply together. The attachment belongs to that class's
property use, not to every occurrence of the predicate. Shared definitions
remain in their own project; exports preserve references without copying them.
`reification_required` accepts true, false, or null (explicit removal).
A flag, including false, requires local or inherited shape references.

A definition's fields reuse supported property constraints: datatype or
`to_class`, cardinalities, string/numeric restrictions, enumeration, language
restrictions and display metadata. `node_kind` may supplement a type; node kind
alone, inverse paths, nested annotation policies and cross-property constraints
are not supported. Unsupported keys and duplicate field identities fail early.
The API transport accepts `node_kind` for annotation fields; its existing
restriction for ordinary property imports is unchanged.

### Incremental changes and removal

| Input | Update behavior |
| --- | --- |
| Omitted definition, property field or attribute | Preserve existing state |
| `reification_required: false` | Store explicit false |
| `reification_required: null` | Remove the optional flag |
| `reifier_shapes: []` on a property | Clear its own references; also clear the flag if no inherited reference remains |
| Definition with omitted `properties` | Preserve fields (create an empty shape if new) |
| Definition with supplied `properties` | Merge fields by IRI and explicitly supplied attributes |
| Field attribute set to null | Remove that attribute, subject to model validity |
| `--remove-unused` with supplied shape `properties` | Also remove omitted fields; `properties: []` empties the shape |
| `reifier_shapes: {travel:VisitAnnotationShape: null}` | Delete this definition, only with `--remove-unused` |

Omitted shape definitions are never garbage-collected. Delete a shape by
explicitly removing its references and flag in the same input and requesting
its null definition. Planning rejects references that would remain dangling.
The store still refuses deletion when other models reference the shape, and
refuses unsafe structural/policy changes on predicates with existing data.
Those checks are transactional and cannot be guaranteed by an earlier dry run.

API plans create definitions before property references and delete definitions
after reference removals. Shape updates send complete merged field lists, as
required by the API replacement contract. `--dry-run` prints the concrete
requests and affected class/property paths. Each request commits independently;
an error identifies completed steps. Inspect failures and produce a fresh plan
before resuming; already completed changes are omitted on replay. Never retry
an ambiguous failed HTTP mutation blindly. Direct updates also retain their
existing per-object transaction boundaries.

Both YAML dumps include managed definitions and property references. API ZIP
snapshots retain shapes in `datamodel.json` and `model.trig`; direct model-graph
backups already include their RDF. These are model operations only: instance
annotation writes remain gated until stage 3. OLDAP keeps its own validation.

See [stage 2 acceptance](reification-stage2.md) for local tests and commands.
