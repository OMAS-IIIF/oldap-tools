# Fasnacht taxonomy simplification — Phase 1

Status: completed locally and superseded by `TaxonomyPhase2.md`  
Date: 31 August 2026

## Scope

Phase 1 prepared the expert-approved simplification without changing an active
OLDAP list, ontology, or project-data graph. The active files referenced by
`fasnacht-onto.yaml` remain unchanged.

The inactive target drafts are:

- `ObjectTaxonomy-Flat-Draft.yaml`: twelve root nodes;
- `CarnivalEventTaxonomy-Flat-Draft.yaml`: fifteen root nodes, with
  `Vereinsaktivität` and `Morgenstreich` kept separate;
- `CarnivalPracticeTaxonomy-Draft.yaml`: four multi-valued practice categories.

`OrganisationTaxonomy` remains active and unchanged until the experts clarify
whether the proposed grouping vocabulary classifies only organisations or also
persons and private actors. `Ehrung` is present as the provisional new object
type `Honour`; no existing value is automatically mapped to it.

## Stable identifiers

Existing node IDs are retained where their meaning remains suitable. This
includes `Musikinstrument` for the displayed label “Instrument”,
`PublicationsAndPress` for “Drucksachen”, `Kunst` for “Bild”, and the existing
event IDs where possible. The parent path is not part of an OLDAP list-node
IRI, so retained IDs can preserve references during a controlled list
replacement.

The drafts are deliberately flat and contain no hidden parent node. Their
source order is the editorial display order.

## Mapping authority

`TaxonomyPhase1Mapping.yaml` covers every node in the four current source
lists and explicitly records discovered data references to legacy nodes that
are no longer present in the repository list YAML. Rules have one of three modes:

- `exact`: eligible for automatic migration after inventory review;
- `broader`: intentional information loss through consolidation; requires an
  approved migration policy before apply;
- `review`: no automatic successor; inspect referenced records individually.

Topic-to-practice rules may have more than one target because practice is
multi-valued. The mapping is still a proposal until the experts approve the
automatic-assignment policy.

The first local inventory found two such legacy values: `HistorischAnderes` in
`CarnivalEventTaxonomy` and `Stamm` in `OrganisationTaxonomy`. Both are marked
`source_state: legacy` and require review; their absence from the active YAML
must not make their data references invisible during migration.

## First local baseline

The read-only run on 31 August 2026 completed against the local `fasnacht`
project:

| Source list | References | References requiring review |
|---|---:|---:|
| ObjectTaxonomy | 119 | 104 |
| CarnivalEventTaxonomy | 87 | 6 |
| CarnivalTopicsTaxonomy | 21 | 9 |
| OrganisationTaxonomy | 30 | 30 |

The high ObjectTaxonomy review count is dominated by 102 assignments to
`Undetermined`. Other directly used review nodes are `Marsch` and
`Memorabilia`. The event legacy node `HistorischAnderes` has six references;
the organisation legacy node `Stamm` has 26 references.

The project contains 87 CarnivalEvents. Of 74 titles matching `Fasnacht YYYY`,
67 have no incoming project-data references and are therefore empty-year
review candidates. None is a strict candidate because each still carries at
least one substantive property, currently a description. The report preserves
those values so the editorial review can decide whether they are boilerplate or
meaningful content.

The complete generated local report is intentionally not committed because it
contains resource-level data and can be reproduced at any time with the
documented command. The reviewed production report remains an explicit Phase-1
follow-up.

## Media form

No additional media-format HList is introduced. Existing DCMI values remain
the semantic representation:

| Editorial label | Existing value |
|---|---|
| Dokument | `dcmitype:Text` |
| Foto | `dcmitype:StillImage` |
| Ton | `dcmitype:Sound` |
| Video | `dcmitype:MovingImage` |

“Objekt” starts or selects an `ArchiveObject`; it is not stored as the digital
media form of an `ArchiveMediaObject`.

## Read-only inventory

Run the same command locally and in production, changing only the connection
options and report path:

```console
oldap-tools --user <user> --password <password> \
  fasnacht taxonomy-inventory \
  --mapping fasnacht/TaxonomyPhase1Mapping.yaml \
  --out taxonomy-inventory.local.yaml
```

The command has no apply mode. It performs SELECT queries only and reports:

- every list node and direct project-data reference;
- referenced node IRIs missing from their current list;
- source resource IRI, class, label, and property;
- migration mode and proposed target values;
- counts requiring record-level review;
- all CarnivalEvents and strict empty-year deletion candidates.

An event is an empty-year review candidate when its preferred name matches
`Fasnacht YYYY` and it has no incoming project-data reference. It becomes a
strict candidate only when it additionally has no outgoing property beyond the
known identity, audit, classification, dating, permission, and
publication-status fields. Substantive property values remain visible for
human review. The report never deletes anything.

## Cutover prerequisites

The original Phase-2 gates were:

1. local and production reports have been reviewed;
2. every referenced `review` value has a record-level decision;
3. broader mappings and topic-to-practice suggestions are approved;
4. the future organisation/grouping model is decided;
5. complete GraphDB backups and a rollback procedure are rehearsed;
6. the explicit OLDAP list-replacement procedure is implemented and tested.
