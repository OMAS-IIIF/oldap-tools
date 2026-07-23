# Installation and Connection

## Installation

Install from PyPI:

```bash
pip install oldap-tools
```

The command-line entry point is:

```bash
oldap-tools
```

Show the installed version:

```bash
oldap-tools --version
```

## Common Options

Common options are accepted before the command group:

```bash
oldap-tools [common_options] <group> <command> [command_options]
```

Available common options:

- `--graphdb`, `-g`: GraphDB base URL. Default: `http://localhost:7200`.
- `--repo`, `-r`: GraphDB repository name. Default: `oldap`.
- `--user`, `-u`: OLDAP user ID. Required.
- `--password`, `-p`: OLDAP password. Required.
- `--graphdb_user`: GraphDB HTTP user. Optional; can also be set through `GRAPHDB_USER`.
- `--graphdb_password`: GraphDB HTTP password. Optional; can also be set through `GRAPHDB_PASSWORD`.
- `--verbose`, `-v`: enable debug logging.

Example:

```bash
oldap-tools \
  --graphdb http://localhost:7200 \
  --repo oldap \
  --user root \
  --password secret \
  ontology validate --inf ontology.yaml
```

## Credential Model

OLDAP credentials and GraphDB credentials are separate:

- OLDAP credentials identify the actor inside OLDAP and are used for permission checks.
- GraphDB credentials authenticate the HTTP connection to GraphDB when the repository is protected.

`oldap-tools` is a trusted direct GraphDB client. It authenticates the OLDAP
user and constructs the required authorization context without issuing an
access token. JWT signing secrets such as `OLDAP_ACCESS_JWT_SECRET` are neither
required nor intended for CLI installations.

If GraphDB runs without HTTP authentication, omit `--graphdb_user` and `--graphdb_password`.
