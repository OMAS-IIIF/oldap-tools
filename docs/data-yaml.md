# Instance Data YAML/JSON

The versioned interchange format represents ontology-driven OLDAP resources.
`oldap-tools data validate` checks it locally, while `data import --dry-run`
resolves the live project model and performs a read-only import preflight.
Version 1 supports both a conservative one-resource apply and a resumable batch
mode for documents containing several resources. A resource may additionally
declare how its media is copied into OLDAP or referenced at an external
location. Neither mode updates, overwrites, or deletes resources.

The format does not copy OLDAP API response conventions. Every property is
always a list, and each item explicitly distinguishes an IRI reference from a
literal value. This preserves intended cardinality and avoids ambiguous compact
language strings such as `text@de`.

## Document structure

```yaml
data:
  version: 1
  project: chama
  resources:
    - iri: IMG_1520
      class: chama:CataloguedPhotograph
      properties:
        schema:name:
          - value: Stationsgebäude in Chama
            language: de
        dcterms:creator:
          - iri: chama:LukasRosenthaler
        chama:publicDisplayPermission:
          - value: true
      permissions:
        oldap:Unknown: DATA_VIEW
      media:
        source:
          type: file
          path: ../../media/IMG_1520.HEIC
        handling: copy
        ingest_profile: image-iiif
```

Required document fields:

- `version`: currently the integer `1`;
- `project`: OLDAP project shortname;
- `resources`: non-empty list of resource declarations.

Required resource fields:

- `iri`: project-local name, QName, absolute IRI, or the exact source
  placeholder `auto`;
- `class`: resource-class QName or absolute IRI;
- `properties`: mapping from property QName/IRI to a non-empty value list.

`permissions` and `media` are optional. Permission keys are role QNames or IRIs, and their values are
OLDAP data-permission names from `DATA_RESTRICTED` through `DATA_PERMISSIONS`.
When `permissions` is omitted or empty, the importer does not emit an empty
`oldap:attachedToRole` relation: OLDAPLIB applies the authenticated user's
default roles. A resumable rerun verifies permissions only if the source
document explicitly declared them; omitted permissions are not an assertion
that an existing resource must have no roles.

## Resource identity and `iri: auto`

A filename, title, directory, or checksum is not a resource identity. Filenames
are allowed to repeat, titles can change, directory layouts are local, and a
checksum identifies a particular byte sequence rather than the catalogued
resource. Keep these facts as metadata such as `shared:originalName` and
`shared:checksum`.

Use an explicit `iri` whenever the institution already has a stable identifier.
Otherwise, an incoming source document may use `iri: auto` more than once:

```yaml
resources:
  - iri: auto
    class: chama:CataloguedPhotograph
    properties:
      shared:originalName:
        - value: DC_0015.HEIC
    media:
      source:
        type: file
        path: camera-a/DC_0015.HEIC
      handling: copy
      ingest_profile: image-iiif
  - iri: auto
    class: chama:CataloguedPhotograph
    properties:
      shared:originalName:
        - value: DC_0015.HEIC
    media:
      source:
        type: file
        path: camera-b/DC_0015.HEIC
      handling: copy
      ingest_profile: image-iiif
```

Prepare this source once, offline, before any live operation:

```shell
oldap-tools data prepare --inf incoming.yaml --out prepared.yaml
```

Preparation replaces each placeholder with a distinct UUID-based project-local
name such as `resource_8fd4...`, while preserving comments, block strings, and
all other source text. In project `chama`, this resolves to an RDF IRI such as
`chama:resource_8fd4...`. The two files above therefore retain the same
`shared:originalName` but obtain distinct RDF identities and distinct media
asset IDs.

The prepared document is the durable import authority: keep it, review it, and
use that same file for dry-run, apply, reruns, and recovery. Do not regenerate
it after import. Preparation never edits the input, refuses to overwrite an
existing output unless `--force` is supplied, and requires input and output in
the same directory so that relative media paths retain their meaning.

`data validate` accepts a source document containing `auto` and reports the
number of unresolved placeholders. All live operations reject such a document
until it has been prepared. Because a placeholder has no name that another
record can reference, either use an explicit stable IRI for mutually linked
new resources or prepare first and then add links using the generated names.

## Media instructions

The `media` block is an ingest instruction, not an encoding of the binary. The
binary is never embedded as Base64 in YAML. This keeps records readable,
diffable, and suitable for version control while allowing the importer to
verify and transfer large files as streams.

The three independent decisions are:

- `source.type`: where the bytes or external service live;
- `handling`: whether OLDAP copies the bytes or stores a reference;
- `ingest_profile`: which preservation and delivery derivatives are created.

### Source types

| `source.type` | Location field | Meaning |
| --- | --- | --- |
| `file` | `path` | Local file; the path must be relative to the YAML/JSON file. |
| `url` | `url` | Direct external HTTP(S) media URL. |
| `iiif-image` | `info_url` | Complete IIIF Image API `info.json` URL. |
| `iiif-manifest` | `manifest_url` | Complete IIIF Presentation manifest URL. |

URLs must be absolute HTTP(S) URLs and must not contain embedded credentials.
An `iiif-image` URL must end in `/info.json`. Location field names are explicit
on purpose: a manifest and an Image API service have different semantics.

### Handling modes

`copy` tells OLDAP to ingest and preserve a local binary. It requires an ingest
profile. Version 1 currently enables `copy` only for `source.type: file`.

`reference` leaves the externally managed bytes in place. It is valid with
`url`, `iiif-image`, and `iiif-manifest`, and must omit `ingest_profile` because
OLDAP creates no derivative. A local file cannot be a stable external
reference.

The media block controls the workflow; RDF delivery facts remain explicit in
`properties`. This small amount of deliberate duplication makes exported YAML
self-describing. Local-copy preflight compares the instruction with canonical
OLDAP filename, MIME, checksum, access-mode, protocol, and media-type metadata.
For example, a direct external image normally declares
`shared:mediaAccessMode: external`, `shared:protocol: http`, and
`shared:mediaUrl` with the same URL.

### Ingest profiles

The profile vocabulary is media-oriented rather than file-extension-oriented:

| Profile | State | Intended result |
| --- | --- | --- |
| `image-iiif` | enabled | Preserve the original, create pyramidal `master.tif`, expose IIIF Image API 3. |
| `preserve-original` | reserved | Preserve original bytes without an access derivative. |
| `audio-access` | reserved | Preserve original audio and create a browser access copy. |
| `video-access` | reserved | Preserve original video and create a browser access copy. |
| `document-access` | reserved | Preserve a document and create an HTTP access representation/preview. |
| `document-iiif` | reserved | Preserve a document and expose it through a suitable IIIF workflow. |

Reserved names are rejected until their complete server-side workflow and
verification contract exist. This avoids YAML files that appear successful but
silently skip preservation work. Adding a profile later is backward-compatible.

### Local IIIF image example

```yaml
properties:
  dcterms:type:
    - iri: dcmitype:StillImage
  shared:mediaAccessMode:
    - value: local
  shared:originalName:
    - value: IMG_1520.HEIC
  shared:originalMimeType:
    - value: image/heic
  shared:checksum:
    - value: e58b00ea8a255a2baf0c463d91d8e05bcd9fdaaf21d6f30dc4ffd7b657a98c8b
  shared:protocol:
    - value: custom
media:
  source:
    type: file
    path: ../../../demo-data/IMG_1520.HEIC
  handling: copy
  ingest_profile: image-iiif
```

The provisional `shared:protocol: custom` is intentional. It describes the
metadata-only state before attachment. A successful ingest replaces it with
`iiif` and adds server-managed delivery properties such as `shared:assetId`,
`shared:serverUrl`, `shared:path`, and `shared:derivativeName`.

### External URL example

```yaml
properties:
  dcterms:type:
    - iri: dcmitype:StillImage
  shared:mediaAccessMode:
    - value: external
  shared:originalName:
    - value: Externally hosted photograph
  shared:originalMimeType:
    - value: image/jpeg
  shared:protocol:
    - value: http
  shared:mediaUrl:
    - value: https://images.example.org/full.jpg
media:
  source:
    type: url
    url: https://images.example.org/full.jpg
  handling: reference
```

For an external IIIF Image service, use `source.type: iiif-image` with the full
`info_url`; use `iiif-manifest` only when the referenced object is a IIIF
Presentation manifest. The corresponding OLDAP IIIF delivery properties remain
explicit in `properties`.

## Property values

An IRI reference contains only `iri`:

```yaml
dcterms:creator:
  - iri: chama:LukasRosenthaler
```

A literal contains `value` and may optionally declare either `language` or
`datatype`, but never both:

```yaml
schema:name:
  - value: Stationsgebäude in Chama
    language: de
schema:identifier:
  - value: "1520"
    datatype: xsd:string
chama:publicDisplayPermission:
  - value: true
```

Without an explicit datatype, the live preflight uses the ontology property
definition. This also permits OLDAP-supported structured-value shorthand, such
as a quoted date string for a property targeting `oldap:Dating`, without
hard-coding class-specific structures into version 1.

Unknown keys, duplicate YAML mapping keys, duplicate resource identities,
empty property lists, invalid identifiers, ambiguous value items, and invalid
permissions are rejected. JSON is accepted because it is a subset of YAML.

## Validation

```bash
oldap-tools data validate --inf resource.yaml
```

Validation is offline and therefore does not require `--user` or `--password`.
It checks the interchange document itself, not whether the named project,
classes, properties, roles, or linked resources exist in a live OLDAP instance.
It validates media source shapes and profile combinations but does not read a
local file or contact an external URL.

## Live dry-run preflight

```bash
oldap-tools -u rosenth -p '...' data import --dry-run --inf resource.yaml
```

The dry-run connects as the supplied OLDAP user and verifies:

- the project and each resource class;
- direct and inherited properties;
- literal, language, datatype, allowed-value, and cardinality constraints;
- required properties through the dynamic OLDAP resource class;
- linked-resource existence, visibility, and target-class compatibility;
- referenced roles and their data-permission values;
- `ADMIN_CREATE` for the authenticated user;
- visible create-only target IRI collisions;
- local media-file existence, filename, MIME category, and streaming SHA-256;
- compatibility of local image metadata with the `image-iiif` profile.

Links to other resources declared in the same document are supported, including
forward references. Controlled-vocabulary IRIs fixed by a property's `sh:in`
constraint—such as `dcmitype:StillImage` or `shared:ArchiveGroup`—are checked
against the property's allowed values but are not mistaken for project-data
resources. This also applies when the object property additionally declares a
target class, as `shared:archiveLevel` does with `shared:ArchiveLevel`.
Object properties targeting `oldap:Role`, such as
`shared:stagingDefaultRole`, are resolved through OLDAP's administrative role
registry rather than incorrectly searched in the project's data graph. The
role must exist and be visible to the authenticated user.

The dry-run constructs candidate objects only in memory and never calls a write
method. A target that is not visible to the authenticated user cannot be
distinguished from a missing target; the command reports this explicitly.

## Strict create-only apply

```bash
oldap-tools -u rosenth -p '...' data import --apply --inf resource.yaml
```

Apply is intentionally restricted to a document containing exactly one
resource. The command first performs the complete preflight, repeats it
immediately before writing, and then calls OLDAP's transactional `create()`.
Both preflight and `create()` reject an existing target IRI. There is no update,
merge, upsert, overwrite, or delete path.

The one-resource restriction is a safety boundary, not a format limitation.
OLDAP currently commits each resource separately, while generic compensating
deletion cannot yet guarantee removal of every helper node belonging to
structured values such as `oldap:Dating`. A genuinely atomic multi-resource
apply would therefore require a different transaction design; batch mode is
explicitly sequential and resumable instead.

This restriction applies only without `--batch`. Larger imports use the
resumable workflow below instead of pretending to be one atomic transaction.

When a local `image-iiif` media block is present, apply first creates the RDF
resource and then authenticates to the OLDAP API, streams the file to
oldap-mediaserver attach mode, and verifies the resulting OLDAP delivery facts
and authenticated IIIF `info.json`. The default service origins are
`http://localhost:8000` and `http://localhost:8088`; common options `--api` and
`--media` override them.

RDF create and binary ingest are separate service transactions. If media ingest
fails after RDF creation, the command keeps the valid metadata resource and
prints the recovery command instead of attempting a potentially incomplete
generic rollback.

## Attaching or recovering media

```bash
oldap-tools -u rosenth -p '...' data media-attach --dry-run --inf resource.yaml
oldap-tools -u rosenth -p '...' data media-attach --apply --inf resource.yaml
```

`media-attach` requires exactly one existing resource and one local copy
instruction. Dry-run verifies the relative file, checksum, identity metadata,
credentials, target visibility, and MediaObject compatibility without writing.
Apply uploads when no asset is attached and otherwise verifies the matching
existing asset. It therefore provides both explicit recovery and a safe,
idempotent verification command.

The repository example at
`examples/data/chama-img-1520.yaml` represents the next SALSAH Chama demo
photograph without importing it. It can be used directly for both validation
and media preflight. Because its RDF resource was already created during the
incremental Chama demo, use `data media-attach --apply` to finish it. For a new
resource, the normal `data import --apply` performs both phases.

## Resumable batch import

```bash
oldap-tools -u rosenth -p '...' data import --dry-run --batch \
  --inf resources.yaml --report preflight.json

oldap-tools -u rosenth -p '...' data import --apply --batch \
  --inf resources.yaml --report import-report.yaml
```

Batch mode is intended for many metadata-and-media records in one document. It
preserves YAML order and follows two phases:

1. Before the first write, validate the complete YAML, every ontology-driven
   resource, link, role, local media path, MIME category, and checksum.
2. Process resources sequentially. For each resource, create or verify its RDF
   metadata and then attach or verify its media.

Order new dependencies before resources that reference them. Batch preflight
rejects a forward link to another new resource in the same document, including
new circular dependencies. References to already existing OLDAP resources may
appear anywhere. This guarantees that a failed create cannot leave an earlier
new resource pointing to a missing later target.

Processing stops at the first operational failure. Earlier resources remain
valid, the failed resource records its precise phase, and later resources are
reported as `not_started`. This produces a simple recoverable prefix and avoids
creating later links after a prerequisite failed.

Rerunning the identical command resumes from actual OLDAP state:

- a missing resource is created;
- an existing resource is accepted only if its class, every YAML-declared
  property, and role permissions match;
- server-managed properties not declared in YAML are allowed;
- for copied images, the completed transition from provisional
  `shared:protocol: custom` to `shared:protocol: iiif` is accepted;
- any other metadata discrepancy aborts preflight before new writes;
- an existing matching media asset is verified rather than uploaded again.

This is intentionally not an upsert. Editing YAML after a partial import does
not modify existing OLDAP data; it exposes a mismatch requiring an explicit
curatorial decision.

### Batch result states

Each row reports independent metadata and media states:

| Phase | Values |
| --- | --- |
| Metadata dry-run | `would_create`, `existing_verified` |
| Metadata apply | `created`, `existing_verified`, `failed`, `not_started` |
| Media dry-run | `would_attach`, `reference`, `not_declared` |
| Media apply | `attached`, `existing_verified`, `reference`, `not_declared`, `failed`, `not_started` |

The command exits with status 1 if preflight fails or processing stops on a
resource failure. A completed successful batch exits with status 0.

### Audit report

`--report` is available only with `--batch`. The `.json`, `.yaml`, or `.yml`
suffix selects the serialization. Reports contain the project, mode, overall
success flag, resource IRI, both phase states, and any error message. They are
useful for human review and automation but are not the authority for resuming;
every run verifies the current OLDAP and media state again.

`examples/data/batch-external-images.example.yaml` shows two complete resources
in one document. Its `example.org` URLs and resource IRIs are placeholders and
must be replaced before live apply.

`examples/data/chama-photographs-batch-01.yaml` is the first real Chama batch.
It contains three owner-cleared HEIC photographs (`IMG_1508`, `IMG_1521`, and
the corrected Foster's filename `IMG_0171`), their three complete
KnowledgeContributions, two shared places, and locomotive 489. Dependencies
precede their users, and every local file checksum is verified by dry-run.
