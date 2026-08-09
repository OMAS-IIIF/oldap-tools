# Archive Structure YAML

Archive YAML describes a manually curated hierarchy of `shared:ArchiveUnit`
resources. The format is project-neutral: a project may contain one root, several
independent fonds, or new branches attached to an archive unit that already
exists in OLDAP.

The input file defines structure and descriptive archive metadata. It does not
import media files, update existing archive units, move nodes, or delete data.

## Minimal document

```yaml
archive:
  version: 1
  language: de
  units:
    - id: bmg
      level: Fonds
      title: Archiv der BMG
      children:
        - id: bmg-stamm
          level: Subfonds
          title: Stamm
```

`units` is a list, so a project can contain several independent roots. This is
how a project that represents several associations can give every association
its own fonds; neither the YAML format nor `shared:ArchiveUnit` needs to know
what an association is.

## Stable identifiers and IRIs

Every unit needs a document-wide unique `id`. It must be a valid XML NCName: it
may contain letters, digits, `_`, `-`, and `.`, but no spaces or `/`, and it must
not start with a digit.

The ID becomes the persistent resource IRI in the target project. Loading the
example into project `fasnacht` creates:

```text
fasnacht:bmg
fasnacht:bmg-stamm
```

This deterministic mapping makes references and later imports predictable. An
import aborts if any target IRI already exists. Existing data is never silently
merged or overwritten.

## Supported archive levels

`level` must be one of the seven controlled levels from the Shared ontology:

- `ArchiveGroup` — archive group / Bestandsgruppe
- `Fonds` — fonds / Bestand
- `Subfonds` — subfonds / Teilbestand
- `Series` — series / Serie
- `Subseries` — subseries / Teilserie
- `File` — file or dossier / Dossier or Akte
- `Item` — item / Dokument or Einzelstück

The loader does not enforce a fixed sequence. Real archive structures may skip
levels or use different combinations.

## Multilingual text

`language` is the language applied to every scalar text value. Use a language
map when a field is available in more than one language:

```yaml
archive:
  version: 1
  language: de
  units:
    - id: bmg
      level: Fonds
      title:
        de: Archiv der BMG
        en: BMG Archive
```

The same scalar-or-language-map syntax is available for `title`, `description`,
`extent`, `provenance`, and `access_conditions`.

## Complete unit syntax

Only `id`, `level`, and `title` are required:

```yaml
archive:
  version: 1
  language: de
  units:
    - id: bmg
      level: Fonds
      title:
        de: Archiv der BMG
        en: BMG Archive
      identifier: BMG
      description: Unterlagen des Vereins seit seiner Gründung.
      date:
        start: "1911"
        end: "2026"
        verbatim: seit 1911
        calendar: GREGORIAN
      extent: 18 Laufmeter und digitale Unterlagen
      creators:
        - fasnacht:BMG
      provenance: Durch den Verein geführt und dem Archiv übergeben.
      access_conditions: Benutzung nach Voranmeldung.
      about:
        - fasnacht:BMG
      position: 1
      children:
        - id: bmg-protokolle
          level: Series
          title: Protokolle
          identifier: BMG-P
          position: 1
```

Fields map to the Shared ontology as follows:

| YAML field | OLDAP property | Meaning |
|---|---|---|
| `title` | `schema:name` | Title |
| `level` | `shared:archiveLevel` | Controlled archive level |
| hierarchy | `shared:parentArchiveUnit` | Direct parent |
| `identifier` | `schema:identifier` | Reference code |
| `description` | `schema:description` | Scope and content |
| `date` | `dcterms:temporal` | Date or date range |
| `extent` | `schema:materialExtent` | Extent and medium |
| `creators` | `dcterms:creator` | Existing record-creator IRIs |
| `provenance` | `dcterms:provenance` | Custodial history |
| `access_conditions` | `schema:conditionsOfAccess` | Informational access conditions |
| `about` | `schema:about` | Existing subject-resource IRIs |
| `position` | `schema:position` | Optional sibling order |

Date values use `YYYY`, `YYYY-MM`, or `YYYY-MM-DD`. `end`, `verbatim`, and
`calendar` are optional. Supported calendars are `GREGORIAN`, `JULIAN`,
`HEBREW`, `ISLAMIC`, and `PERSIAN`. Quote dates so YAML keeps them as strings.

`creators` and `about` contain existing absolute IRIs or QNames. Their target
classes remain subject to the Shared ontology's SHACL rules.

## Extending an existing archive tree

An otherwise top-level YAML unit can be attached below one archive unit that
already exists in OLDAP:

```yaml
archive:
  version: 1
  language: de
  units:
    - id: bmg-protokolle-1949-1960
      level: File
      title: Protokolle 1949–1960
      parent: fasnacht:bmg-protokolle
```

`parent` is permitted only on entries directly below `units`. Nested entries
derive their parent from `children` and must not specify it again. The referenced
external parent must exist in the target project and must be a visible
`shared:ArchiveUnit`.

This is deliberately create-only behavior:

- new units and subtrees can be added;
- existing units are not updated or re-declared;
- existing units are not moved;
- nothing is deleted;
- matching by title or identifier never occurs.

## Validation and loading

Validate the file without connecting to OLDAP:

```shell
oldap-tools -u rosenth -p '...' archive validate --inf archive.yaml
```

The global user and password options are currently required by the CLI even
though local schema validation does not connect to GraphDB.

Preflight against an existing project without writing data:

```shell
oldap-tools -u rosenth -p '...' archive load fasnacht --inf archive.yaml
```

The load command defaults to dry-run. It validates the YAML, resolves the target
project, rejects existing target IRIs, and verifies external parents. Apply the
same plan explicitly after reviewing the output:

```shell
oldap-tools -u rosenth -p '...' archive load fasnacht --inf archive.yaml --apply
```

Parents are created before children. If an error occurs during creation, the
loader attempts to delete all units created by that invocation in reverse
order. The command reports any rollback failure explicitly.

New resources receive the authenticated OLDAP user's default role assignments,
using the same behavior as normal `ResourceInstance` creation. Explicit archive
permission profiles are intentionally outside version 1 of this format.

The authoritative machine-readable schema is bundled as
`oldap_tools/schemas/archive_schema.yaml`. A complete small input file with two
independent fonds is available as [`examples/archive-structure.yaml`](../examples/archive-structure.yaml).
