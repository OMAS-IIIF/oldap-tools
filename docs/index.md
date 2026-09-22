# OLDAP Tools Documentation

OLDAP Tools is a command-line utility for managing selected parts of an OLDAP installation backed by GraphDB. It can export and import project graphs, load and dump hierarchical lists, manage ontology datamodel YAML files, and maintain selected system graphs.

## Documentation Map

- [Installation and Connection](installation.md): installation, credentials, GraphDB options, and common command syntax.
- [Command Reference](commands.md): all CLI commands and their main options.
- [Ontology YAML](ontology-yaml.md): the structure of ontology YAML files, including classes, properties, lists, external ontologies, and Lucene connectors.
- [Archive Structure YAML](archive-yaml.md): manually define, validate, and add archive trees without changing existing units.
- [Instance Data YAML/JSON](data-yaml.md): versioned project resource data with explicit value semantics, local validation, and live read-only import preflight.
- [Hierarchical Lists](lists.md): list YAML format and additive merge behavior.
- [Update Semantics](update-semantics.md): what `update` and `replace` mean, including the important difference between taxonomy and resource-property updates.
- [Ontology API](ontology-api.md): API contracts, native connector configuration, snapshots and transport limits.
- [Operations and Backups](operations.md): API dump/preview/load workflow, backup scopes, recovery tests, Workbench/cache behavior and system graph operations.

## Main Concepts

OLDAP Tools works with several named graph families:

- `<project>:shacl`: SHACL shapes for the project datamodel.
- `<project>:onto`: OWL ontology information for the project datamodel.
- `<project>:lists`: hierarchical list/taxonomy data.
- `<project>:data`: project instance data.
- `oldap:admin`: project, user, and role administration data.
- `oldap:shacl`, `oldap:onto`, `shared:shacl`, `shared:onto`: OLDAP system and shared model graphs.

Most project-level operations require an OLDAP user with sufficient OLDAP permissions. GraphDB credentials are separate and are only needed when the GraphDB repository itself is protected.

## Safety Defaults

The ontology loader defaults to API transport and `--mode update`, preserves
omitted properties, and creates an API ZIP snapshot before changes. Use
`--dry-run` to preview changes and `--remove-unused` to request guarded removal.
See [Ontology API](ontology-api.md) for the workflow and snapshot limitations.

YAML dumps include Lucene configuration by default; loads retain `--connectors skip`
unless `create` or `replace` is selected. API connector replacement skips an identical
configuration. Model planning and export require the updated API's fresh GraphDB reads.

Use `--transport direct --mode replace` only when you intentionally want to recreate the project datamodel graphs. It deletes `<project>:shacl` and `<project>:onto` and then rebuilds them from YAML.
