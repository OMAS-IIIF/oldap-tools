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
