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
- `--api`: OLDAP API base URL used for ontology loading/dumping and media authentication/verification. Default: `http://localhost:8000`.
- `--media`: OLDAP media-server base URL used for binary ingest. Default: `http://localhost:8088`.
- `--user`, `-u`: OLDAP user ID. Required for commands that connect to OLDAP.
- `--password`, `-p`: OLDAP password. If omitted, connected commands prompt in the terminal without echoing the input. Explicit values remain supported for automation; cancellation or EOF aborts before connection.
- `--graphdb_user`: GraphDB HTTP user. Optional; can also be set through `GRAPHDB_USER`.
- `--graphdb_password`: GraphDB HTTP password. Optional; can also be set through `GRAPHDB_PASSWORD`.
- `--verbose`, `-v`: enable debug logging.

Example:

```bash
oldap-tools \
  --api http://localhost:8000 \
  --user root \
  ontology load --inf ontology.yaml
```

The local `ontology validate`, `archive validate`, and `data validate`
commands run without OLDAP or GraphDB credentials.

## Credential Model

OLDAP credentials and GraphDB credentials are separate:

- OLDAP credentials identify the actor inside OLDAP and are used for permission checks.
- GraphDB credentials authenticate the HTTP connection to GraphDB when the repository is protected.

`ontology load` and `ontology dump` use the API by default; they need only `--api`, `--user` and
an OLDAP password (prompted without echo when `--password` is omitted).
The API server controls its repository. See [Ontology API](ontology-api.md).
Explicit `ontology load/dump --transport direct` and most other connected operations
use a trusted direct GraphDB client. It authenticates the OLDAP
user and constructs the required authorization context without issuing an
access token. JWT signing secrets such as `OLDAP_ACCESS_JWT_SECRET` are neither
required nor intended for CLI installations.

Media ingest is the deliberate exception: `data import --apply` with a local
media instruction and `data media-attach` authenticate through the public OLDAP
API to obtain the short-lived Bearer token required by oldap-mediaserver. The
same OLDAP user and password are used; signing secrets remain server-side.

If GraphDB runs without HTTP authentication, omit `--graphdb_user` and `--graphdb_password`.

## API Feature Compatibility

The deployed API needs the matching model-export fixes, fresh model JSON/TriG
reads after Workbench edits, and the Lucene connector endpoint for the complete
ontology workflow. Updating only the CLI does not activate server changes. For
older servers without connector support, `ontology dump --no-connectors` and
load's default `--connectors skip` avoid that endpoint; they do not supply missing
model-export or cache-freshness fixes. See [API contracts](ontology-api.md#api-contracts).
