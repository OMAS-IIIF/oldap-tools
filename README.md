[![PyPI version](https://badge.fury.io/py/oldap-tools.svg)](https://badge.fury.io/py/oldap-tools)
[![GitHub release](https://img.shields.io/github/v/release/OMAS-IIIF/oldap-tools)](https://github.com/OMAS-IIIF/oldap-tools/releases)
# OLDAP tools

OLDAP tools is a CLI tool for managing parts of the OLDAP framework. It allows to

- dump all the data of a given project to a gzipped TriG file
- load a project from a gzipped TriG file created by oldap-tools
- load a hierarchical list from a YAML file
- dump a hierarchical list to a YAML file

# Installation

The installation is done using pip: `pip install oldap-tools`

# Usage

The CLI tool provides the following commands:

- `oldap-tools project dump`: Dump all the data of a given project to a gzipped TriG file
- `oldap-tools project load`: Load a project from a gzipped TriG file created by oldap-tools
- `oldap-tools list dump`: Dump a hierarchical list to a YAML file
- `oldap-tools list load`: Load a hierarchical list from a YAML file
- `oldap-tools ontology validate`: Validate an ontology datamodel YAML file
- `oldap-tools ontology load`: Load or update an ontology datamodel from YAML
- `oldap-tools ontology dump`: Dump an ontology datamodel to YAML or TriG

# Common options

- `--graphdb`, `-g`: URL of the GraphDB server (default: "http://localhost:7200")
- `--repo`, `-r`: Name of the repository (default: "oldap")
- `--user`, `-u`: OLDAP user (*required*) which performs the operations
- `--password` `-p`: OLDAP password (*required*)
- `--graphdb_user`: GraphDB user (default: None). Not needed if GraphDB runs without athentification.
- `--graphdb_password`: GraphDB password (default: None). Not needed if GraphDB runs without athentification.
- `--verbose`, `-v`: Print more information

# Command

## Project dump

This command dumps all the data of a given project to a gzipped TriG file. It includes user information
of all users associated with the project. The command has the following syntax (in addition to the common options):

```oldap-tools [common_options] [graphdb-options] project dump [-out <filename>] [--data | --no-data] [-verbose] <project_id>```

The graphdb options see above. The other options are defined as follows:

- `-out <filename>`: Name of the output file (default: "<project_id>.trig.gz")
- `--data | --no-data`: Include or exclude the data of the project (default: include)
- `-verbose`: Print more information
- `<project_id>`: Project identifier (project shortname)

The file is basically a dump of the project specific named graphs of the GraphDB repository.
This are the following graphs:

- `<project_id>:shacl`: Contains all the SHACL shapes of the project
- `<project_id>:onto`: Contains all the OWL ontology information of the project
- `<project_id>:lists`: Contains all the hierarchical lists of the project
- `<project_id>:data`: Contains all the resources (instances) of the project

The user information is stored as special comment in the TriG file and is interpreted by oldap-tools project load.

## Project load

This command loads a project from a gzipped TriG file created by oldap-tools. It has the following syntax
(in addition to the common options):

```oldap-tools [common_options] [graphdb-options] project load --i <filename>```

The options are as follows:

- `--inf`, `-i`: Name of the input file (required)
- `-verbose`: Print more information

If a user does not exist, then the user is created. If the User is already existing, then the user is replaced.

*NOTE: This will change in the future in order to only update project specific permissions to the existing user.*

## List dump

This command dumps a hierarchical list to a YAML file. This file can be edited to add/remove or change list items.
The command has the following syntax (in addition to the common options):

```oldap-tools [common_options] list dump [-out <filename>] <project_id> <list_id>```

This command generates a YAML file which can be edited and contains the list and all it nodes

The options are as follows:

- `-out `, `-o`: Output file
- `<project_id>`: Project identifier (project shortname)
- `<list_id>`: List identifier

## List load

This command loads a hierarchical list from a YAML file into the given project. The command has the following syntax
(in addition to the common options):

```oldap-tools [common_options] list load --inf <filename> <project_id>```

The options are as follows:

- `--inf`, `-i`: Name of the input file (required)
- `<project_id>`: Project identifier (project shortname)

## Ontology validate

This command validates an ontology YAML file against the bundled schema:

```oldap-tools [common_options] ontology validate --inf <filename>```

## Ontology load

This command loads or updates a project datamodel from a YAML file:

```oldap-tools [common_options] ontology load --inf <filename> [--mode update|replace] [--connectors create|replace] [--backup|--no-backup] [--backup-out <filename>]```

By default, the command makes a TriG gzip backup of the model and list graphs before loading. The
`replace` mode deletes the existing datamodel graphs (`<project>:shacl` and `<project>:onto`) and
recreates them from YAML. The `update` mode compares the YAML classes and properties with the current
datamodel and lets `oldaplib` perform the corresponding updates.
Set an attribute to `null` in update mode to delete it, for example `label`, `comment`, `name`,
`description`, `min_count`, or `max_count`.

Hierarchical lists can be referenced as external YAML files or defined inline. A property can point to
a list node class with `to_class: list:<ListId>`.

Lucene connectors can be declared in the same YAML file. They are skipped by default and only applied
when `--connectors create` or `--connectors replace` is passed. Single-property fields can use a QName
directly and get their Lucene field name from the property fragment. Multi-step chains must be given an
explicit Lucene field name.

Example:

```yaml
ontology:
  project:
    shortname: fasnacht
    iri: https://fasnacht.digital
    namespace: http://fasnacht.digital/ns/
    start: 2025-06-01

  lists:
    CreativeCommons: CreativeCommons.yaml

  external_ontologies:
    schema:
      namespace: https://schema.org/
      label: schema.org
      proposedResourceClass:
        - Person
        - Organization

  classes:
    fasnacht:Person:
      label:
        en: Person
        de: Person
      superclass:
        - schema:Person
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

  lucene_connectors:
    fasnacht:
      types:
        - fasnacht:Story
        - fasnacht:ArchiveObject
        - fasnacht:ArchiveMediaObject
      fields:
        - fasnacht:storyContent
        - schema:abstract
        - fasnacht:archiveObjectTitle
        - schema:description
        - fieldName: representedArchiveObjectTitle
          chain:
            - fasnacht:archiveMediaObjectOf
            - fasnacht:archiveObjectTitle
```

`oldap-tools` creates one GraphDB Lucene connector per project. The connector
name is always the project short name. Multiple entries below
`lucene_connectors` are treated as YAML grouping/specification blocks and are
merged into that project connector.

## Ontology dump

This command dumps an ontology datamodel either as YAML or as a TriG gzip file containing the
`<project>:shacl`, `<project>:onto`, and `<project>:lists` graphs:

```oldap-tools [common_options] ontology dump [-out <filename>] [--format yaml|trig] <project_id>```
