[![PyPI version](https://badge.fury.io/py/oldap-tools.svg)](https://badge.fury.io/py/oldap-tools)
[![GitHub release](https://img.shields.io/github/v/release/OMAS-IIIF/oldap-tools)](https://github.com/OMAS-IIIF/oldap-tools/releases)
# OLADP tools

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


