# Fasnacht taxonomy simplification — Phase 2

Status: local and production cutovers complete; matching frontend rollout pending  
Date: 31 August 2026

## Implemented scope

Phase 2 activates the expert-approved flat `ObjectTaxonomy` (12 nodes), flat
`CarnivalEventTaxonomy` (15 nodes), and multi-valued
`CarnivalPracticeTaxonomy` (4 nodes). `fasnacht:carnivalPractice` replaces
`dcterms:subject` on `CarnivalThing` and `ArchiveMediaObject`.

`OrganisationTaxonomy`, all organisation references, and all CarnivalEvent
resources are explicitly outside this cutover. The old
`CarnivalTopicsTaxonomy` is deleted only after its data references and SHACL
property shapes have been replaced. DCMI continues to represent the medium
forms Dokument, Foto, Ton, and Video.

The data-reference migration is restricted to resources typed exclusively as
`fasnacht:ArchiveObject`, `fasnacht:CarnivalEvent`, or
`fasnacht:ArchiveMediaObject`. Any matching taxonomy reference on another or
additionally typed resource blocks the complete plan. In particular,
`fasnacht:NewsItem`, `fasnacht:EventAnnouncement`, `fasnacht:Story`, and
`fasnacht:MediaLibraryObject` are outside the migration and remain unchanged.

## Safety contract

The migration has two commands:

```console
oldap-tools --user <user> --password <password> \
  fasnacht taxonomy-migration-plan \
  --decisions fasnacht/TaxonomyPhase2LocalDecisions.yaml \
  --out taxonomy-migration-plan.yaml

oldap-tools --user <user> --password <password> \
  fasnacht taxonomy-migration-apply \
  --expected-digest <digest-from-plan> \
  --backup-out <new-full-project-backup.trig.gz> \
  --allow-local-rehearsal
```

The dry-run expands every source reference into a resource-level manifest. It
fails closed on overlapping review rules, unexpected title matches, changed
expected counts, unresolved records, or any out-of-scope taxonomy reference. Apply reruns the inventory and requires
the exact digest, validates the final ontology YAML, refuses an existing backup
path, and writes a complete admin/model/list/data backup before the first OLDAP
mutation.

The list replacement retains compatible node IRIs but recreates node audit
timestamps because it replaces the old tree as one controlled operation. The
practice model cutover is intentionally narrow: only the two old topic property
shapes and their OWL property declaration are replaced. A full DataModel update
cannot remove a property from an in-use resource class, so rebuilding or
incrementally updating the complete model is not used for this migration.

## Local result

The local manifest digest was
`e7a95dc85bda2109e819be191c994415ff3f3e073e227f1ea51c16bb95099f05`:

- 227 taxonomy references in scope;
- 134 changed references;
- 93 references already using retained target nodes;
- zero unresolved references and zero rule-count errors;
- 12 Object nodes, 15 Event nodes, and 4 Practice nodes, all at root level;
- zero remaining references to removed Object/Event/Topics nodes;
- 10 resulting `fasnacht:carnivalPractice` values;
- all 30 organisation-taxonomy references unchanged;
- all 87 CarnivalEvent resources unchanged.

The complete pre-cutover backup is local operator evidence and is not committed
to the repository. Its SHA-256 is
`f1d430c51e01ffd2c53d18af3ffa141edfb2d013a9a286b19c6026aa1c8048a7`.

During rehearsal, an attempted generic full-model replace exposed an unrelated
OLDAPLIB SPARQL-generation failure after it had cleared the two model graphs.
Only those two graphs were restored from the full backup, then the narrow model
cutover was applied and verified. The production procedure must use the final
narrow migration command and must not invoke `ontology load --mode replace`.

## Production gate

Do not reuse the local rehearsal file unchanged on production. Before a
production write:

1. generate and review a fresh production inventory;
2. create a production decisions file with production-specific expected counts
   and change its status to `approved`;
3. review every expanded resource action and approve the new digest;
4. schedule a maintenance window and confirm a new full backup destination;
5. rehearse restoring the four Fasnacht graphs in the target environment;
6. run apply without `--allow-local-rehearsal`;
7. verify list node/parent counts, zero legacy references, two practice SHACL
   shapes, unchanged organisation references, and unchanged event count;
8. deploy the matching FasnachtsPage build.

The production run is an operator handoff. It is not started automatically and
must stop immediately on a digest or verification mismatch.

The reviewed production decision source is
`fasnacht/TaxonomyPhase2ProductionDecisions.yaml`. It additionally resolves
the production-only `Plagge` record to `Requisite` and binds `ClubHistory` to
four production references. It must be passed explicitly to both the plan and
apply commands; neither command may fall back to the local rehearsal file.

## Production result

The approved production cutover completed on 31 August 2026 with manifest
digest
`a2ea33a59866a8b73695e07a8ab901ea8d9dc65c1e8c3edcc6969f4659e0b295`:

- 231 archive taxonomy references resolved;
- 138 references changed and 93 retained unchanged;
- zero unresolved, out-of-scope, or rule-count errors;
- `Plagge` migrated from `Memorabilia` to `Requisite`;
- 88 CarnivalEvent resources and 30 OrganisationTaxonomy references retained;
- exact 12/15/4 flat-list contents, no parents, two practice SHACL shapes,
  zero legacy references, and Topics removal verified by apply.

The immediate pre-cutover full backup is
`RepoBackups/production-phase2/fasnacht-before-phase2-20260831-220438.trig.gz`
with SHA-256
`7dc8525f928acb5d7e9306ae40e02209d0e6f60d8dd58841107a152fdff522bb`.
Its gzip and TriG integrity and all four required project graphs were verified
locally. The first production attempt performed no mutation: it stopped during
the mandatory backup because raw RDF4J export had not forwarded GraphDB HTTP
credentials. That defect was fixed and a standalone authenticated backup was
validated before the successful retry.

## Deferred decisions

- The expert clarification for the grouping vocabulary and its use on persons,
  organisations, and private actors remains open.
- The 67 unreferenced `Fasnacht YYYY` resources still have descriptions. None
  was deleted; their editorial review is a separate migration.
- The Wizard sequence and its complete editorial copy remain a later phase.
