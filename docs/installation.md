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
- `--api`: OLDAP API base URL used for media authentication and verification. Default: `http://localhost:8000`.
- `--media`: OLDAP media-server base URL used for binary ingest. Default: `http://localhost:8088`.
- `--user`, `-u`: OLDAP user ID. Required for commands that connect to OLDAP.
- `--password`, `-p`: OLDAP password. Required for commands that connect to OLDAP.
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
  ontology load --inf ontology.yaml
```

The local `ontology validate`, `archive validate`, and `data validate`
commands run without OLDAP or GraphDB credentials.

## Credential Model

OLDAP credentials and GraphDB credentials are separate:

- OLDAP credentials identify the actor inside OLDAP and are used for permission checks.
- GraphDB credentials authenticate the HTTP connection to GraphDB when the repository is protected.

Most connected `oldap-tools` operations use a trusted direct GraphDB client. It authenticates the OLDAP
user and constructs the required authorization context without issuing an
access token. JWT signing secrets such as `OLDAP_ACCESS_JWT_SECRET` are neither
required nor intended for CLI installations.

Media ingest is the deliberate exception: `data import --apply` with a local
media instruction and `data media-attach` authenticate through the public OLDAP
API to obtain the short-lived Bearer token required by oldap-mediaserver. The
same OLDAP user and password are used; signing secrets remain server-side.

If GraphDB runs without HTTP authentication, omit `--graphdb_user` and `--graphdb_password`.
