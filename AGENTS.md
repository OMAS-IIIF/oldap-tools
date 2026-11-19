# Repository instructions

- Keep ontology YAML validation synchronized with both direct-library and HTTP import/export paths; preserve omitted fields and unordered-set semantics on replay.
- Use offline tests or isolated disposable RDF fixtures for verification. Do not run service-backed imports against a live project.
- Follow `docs/ontology-yaml.md` for the public YAML contract and `docs/reification-stage2.md` for reifier import/export boundaries.
