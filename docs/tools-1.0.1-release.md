# oldap-tools 1.0.1 release

The 1.0.1 patch makes ontology API exports use Jena managed fulltext by default
and includes the production Fasnacht ontology/taxonomy snapshot. Explicit
GraphDB API/direct exports remain available. The Git source is commit
`3b944299db222c5e88c7b99bd2e50ad76f959fba`, tag `v1.0.1`.

## Python distribution

Version 1.0.0 was already published on PyPI on 2026-11-09. Version 1.0.1 publishes
both a wheel and source distribution. Their PyPI SHA-256 values match the locally
built artifacts. The isolated installed wheel passes 173 offline tests and seven
subtests with socket connections blocked, and `pip check` passes.

Install with `pip install oldap-tools==1.0.1`. The package is an API client and CLI,
not an HTTP server. Its declared oldaplib constraint remains >=1.0.0,<2.0.0.

## Container build

The image contains the exact released tools wheel and the published oldaplib
1.0.1 wheel. It uses the existing Jena tools recipe and pinned Python base;
third-party versions are constrained to the accepted tools 1.0.0 ARM64 image.
The build context contains only wheels, constraints and release metadata.
No checkout, virtual environment or deployment credentials enter the context.

Both ARM64 and AMD64 containers pass offline checks for package/library versions,
`pip check`, CLI startup and the full Fasnacht snapshot (16 classes, ten
taxonomies, nine fulltext fields). AMD64 was tested under local emulation,
not as a new production integration run.

```sh
docker run --rm lrosenth/oldap-tools:v1.0.1 --version
docker run --rm lrosenth/oldap-tools:v1.0.1 ontology dump --help
```

For connected operator commands, supply the target API and use an interactive
password prompt; do not embed passwords in shell commands or image layers.

The release directory on the development machine is:
`/Users/rosenth/Library/Application Support/OLDAP-Jena/releases/20261110-tools-1.0.1`.
It contains both distribution files, an isolated wheel test environment,
the sanitized Docker context, build logs and publication evidence.
Archive that directory with the migration artifacts before removing OLDAP-Jena.

## Operation

Production inspection found no running tools service or current Compose/cron
reference requiring replacement. Tools is invoked for individual operator tasks;
publishing it does not require restarting the API, identity service or database.
No production data or service configuration was changed by this release.

The repository Makefile still contains migration-era disabled publication targets.
Restoring the general Make deployment/release workflow remains the separately
planned consolidation task; this release used the verified explicit workflow.

Published multi-platform digest:
`lrosenth/oldap-tools@sha256:339056aba1906c834a8a365e490b2a88e432fedf4f883eb7a0bf2a680a921d16`.
See [release receipt](tools-1.0.1-release-results.json) for hashes and platform manifests.
