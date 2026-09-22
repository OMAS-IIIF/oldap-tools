[![PyPI version](https://badge.fury.io/py/oldap-tools.svg)](https://badge.fury.io/py/oldap-tools)
[![GitHub release](https://img.shields.io/github/v/release/OMAS-IIIF/oldap-tools)](https://github.com/OMAS-IIIF/oldap-tools/releases)
# OLDAP tools

OLDAP tools is a CLI tool for managing parts of the OLDAP framework. It allows to

- dump all the data of a given project to a gzipped TriG file
- load a project from a gzipped TriG file created by oldap-tools
- load a hierarchical list from a YAML file
- dump a hierarchical list to a YAML file
- validate and add manually defined archive trees from YAML
- validate versioned instance-data YAML/JSON locally and preflight it against a live OLDAP model

# Installation

The installation is done using pip: `pip install oldap-tools`

# Documentation

Structured documentation is available in [`docs/`](docs/index.md):

- [Installation and Connection](docs/installation.md)
- [Command Reference](docs/commands.md)
- [Ontology YAML](docs/ontology-yaml.md)
- [Ontology Loading Through the API](docs/ontology-api.md)
- [Archive Structure YAML](docs/archive-yaml.md)
- [Instance Data YAML/JSON](docs/data-yaml.md)

The first real resumable media batch is
`examples/data/chama-photographs-batch-01.yaml`: three Chama HEIC photographs,
their owner annotations, and the reusable resources they reference.
- [Hierarchical Lists](docs/lists.md)
- [Update Semantics](docs/update-semantics.md)
- [Operations and Backups](docs/operations.md)

# Usage

The CLI tool provides the following commands:

- `oldap-tools project dump`: Dump all the data of a given project to a gzipped TriG file
- `oldap-tools project load`: Load a project from a gzipped TriG file created by oldap-tools
- `oldap-tools lists dump`: Dump a hierarchical list to a YAML file
- `oldap-tools lists load`: Load a hierarchical list from a YAML file
- `oldap-tools ontology validate`: Validate an ontology datamodel YAML file
- `oldap-tools ontology load`: Load or update an ontology datamodel from YAML
- `oldap-tools ontology dump`: Dump an ontology datamodel to YAML or TriG
- `oldap-tools archive validate`: Validate a manually defined archive structure YAML file
- `oldap-tools archive load`: Add a YAML-defined archive structure to an existing project
- `oldap-tools data validate`: Validate a versioned instance-data YAML/JSON document offline
- `oldap-tools data prepare`: Replace `iri: auto` placeholders once with stable UUID-based project-local identities
- `oldap-tools data import --dry-run`: Check instance data against a live project without writing
- `oldap-tools data import --apply`: Create one resource and process a declared local IIIF image without updates or overwrites
- `oldap-tools data import --apply --batch`: Resume a sequential multi-resource metadata-and-media import
- `oldap-tools data media-attach`: Attach or idempotently verify media for one existing resource
- `oldap-tools staging ensure-mobile-folder`: Add the application-managed Mobile folder to existing StagingAreas
- `oldap-tools fasnacht taxonomy-inventory`: Produce a read-only Fasnacht taxonomy and empty-event migration report
- `oldap-tools fasnacht taxonomy-migration-plan`: Expand the current Fasnacht data references into a digest-bound read-only migration manifest
- `oldap-tools fasnacht taxonomy-migration-apply`: Apply the reviewed Object/Event/Practice cutover after a full project backup; organisations and event resources remain untouched

# Common options

- `--graphdb`, `-g`: URL of the GraphDB server (default: "http://localhost:7200")
- `--repo`, `-r`: Name of the repository (default: "oldap")
- `--api`: OLDAP API URL for ontology loading and media operations (default: "http://localhost:8000")
- `--user`, `-u`: OLDAP user which performs connected operations
- `--password` `-p`: OLDAP password; connected commands prompt without echo when omitted
- `--graphdb_user`: GraphDB user (default: None). Not needed if GraphDB runs without athentification.
- `--graphdb_password`: GraphDB password (default: None). Not needed if GraphDB runs without athentification.
- `--verbose`, `-v`: Print more information

The local `ontology validate`, `archive validate`, and `data validate`
commands do not require OLDAP credentials.

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

```oldap-tools [common_options] lists dump [-out <filename>] <project_id> <list_id>```

This command generates a YAML file which can be edited and contains the list and all it nodes

The options are as follows:

- `-out `, `-o`: Output file
- `<project_id>`: Project identifier (project shortname)
- `<list_id>`: List identifier

## List load

This command loads a hierarchical list from a YAML file into the given project. The command has the following syntax
(in addition to the common options):

```oldap-tools [common_options] lists load --inf <filename> <project_id>```

If a list already exists, loading is additive: nodes that are present in YAML but missing in the
store are inserted, including their subtrees. Existing nodes are never deleted or moved; if the YAML
would place an existing node below a different parent, the load aborts with an error.

The options are as follows:

- `--inf`, `-i`: Name of the input file (required)
- `<project_id>`: Project identifier (project shortname)

## Ontology validate

This command validates an ontology YAML file against the bundled schema:

```oldap-tools [common_options] ontology validate --inf <filename>```

## Ontology load

This command loads or updates a project datamodel from a YAML file:

```oldap-tools --api <api-url> --user <user> ontology load --inf <filename> [--dry-run] [--remove-unused]```

The omitted password is prompted without echo. The command uses `oldap-api` by default, with an API ZIP snapshot before
changes. Omitted properties are preserved unless `--remove-unused` is supplied; server in-use
checks still apply. Use `--dry-run` for a live change preview. Each API mutation is a separate
transaction, so earlier successful changes remain committed if a later request fails.
See [Operations and Backups](docs/operations.md) for the complete workflow and
[Ontology API](docs/ontology-api.md) for contracts and limitations.

`--transport direct` retains the GraphDB administrative path and its TriG gzip backup.
`--mode replace` requires direct transport and deletes/recreates the datamodel graphs
(`<project>:shacl` and `<project>:onto`). The separate `--connectors create|replace`
option also works through the updated API; API `replace` skips an identical connector configuration.
Set an attribute to `null` in update mode to delete it, for example `label`, `comment`, `name`,
`description`, `min_count`, or `max_count`.

Hierarchical lists can be referenced as external YAML files or defined inline. A property can point to
a list node class with `to_class: list:<ListId>`. Existing lists are extended additively from YAML:
missing nodes are inserted, while existing nodes are not deleted or moved.

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
name is always the project short name. Multiple shorthand entries below
`lucene_connectors` are merged into that project connector. Dumps use one native
`configuration` entry to preserve all GraphDB options; this form cannot be mixed
with other groups.

## Ontology dump

This command exports the current ontology through the API. For a portable package
including all taxonomies, supply an output directory (created if missing):

```bash
oldap-tools --api http://localhost:8000 --user rosenth ontology dump fasnacht \
  --out-dir ./export/fasnacht --include-taxonomies
```

The directory contains `ontology.yaml` and `taxonomies/<ListId>.yaml`, linked by relative
`ontology.lists` paths. Project metadata, external ontology declarations, standalone properties
and classes are included, along with native Lucene configuration when a connector
exists. Use `--no-connectors` to omit it. Existing export files require `--overwrite`;
unrelated files remain.
The password is prompted without echo. Use `--out model.yaml` for a single file without taxonomies.

For the legacy TriG graph backup, select `--transport direct --format trig --out model.trig.gz`.
See [Ontology API](docs/ontology-api.md) for roundtrip, overwrite and export-scope details.

## Ensure the Staging Mobile folder

This command validates an existing StagingArea and ensures that it contains one `Mobile` folder
directly below its unique root folder named `top`. It is idempotent and defaults to a dry-run:

```shell
oldap-tools [common_options] staging ensure-mobile-folder --staging-area <staging-area-iri>
```

After checking the report, repeat the command with `--apply` to create the missing folder. Use
`--staging-area` more than once for an explicit set or use `--all` to process every StagingArea in
the project. The command aborts on ambiguous or misplaced system folders instead of guessing.
