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
- [Operations and Backups](operations.md): backup behavior, project dumps, system graph restore/purge, and operational cautions.

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

The ontology loader defaults to `--mode update` and creates a model/list backup before loading. This is the recommended default for normal schema evolution.

Use `--mode replace` only when you intentionally want to recreate the project datamodel graphs. It deletes `<project>:shacl` and `<project>:onto` and then rebuilds them from YAML.
