# ObjectTaxonomy migration mapping

Status: Replacement taxonomy activated in the repository; retained IDs and migration constraints validated  
Date: 26 July 2026

This document compares every node in the archived `ObjectTaxonomy-OLD.yaml` with its proposed or retained place in the replacement `ObjectTaxonomy.yaml`.

## Result

The migration remains **case 2b** because four old nodes have no single semantic successor. Following editorial approval, however, the old node IDs are used in the replacement `ObjectTaxonomy.yaml` for:

- all 19 clear mappings;
- the 2 approved broad mappings `Kunst` and `Vereinsdokument`.

This preserves the corresponding existing node IRIs. Static verification against `oldaplib` confirms that a node IRI is constructed from the list ID and node ID as `L-<ListId>:<NodeId>`; the parent is not part of the IRI.

The repository now references the replacement `ObjectTaxonomy.yaml`; the former hierarchy is retained as `ObjectTaxonomy-OLD.yaml`. Database assignments were not changed as part of preparing the YAML files.

## Loader and migration constraint

The current `oldap-tools` list merge deliberately rejects moving an existing node to a different parent. Therefore the replacement hierarchy cannot be installed over the old hierarchy with an ordinary ontology update while the old list still exists.

A controlled migration must:

1. back up the project model, lists, and relevant data;
2. confirm or temporarily remove every reference to ObjectTaxonomy nodes that will not exist in the replacement;
3. replace or recreate the `ObjectTaxonomy` list rather than merge it;
4. reload the ontology model against the recreated list;
5. verify that all retained references still resolve to the same `L-ObjectTaxonomy:<NodeId>` IRIs;
6. assign a new type to the two Rädäbäng records only after the separate editorial decision.

The ontology command's `--mode replace` replaces the data model but currently loads or merges lists before doing so; it does not by itself replace an existing list. List replacement must therefore be handled explicitly.

## Assessment levels

- **Applied clear**: The old and new concepts are semantically equivalent enough, and the old node ID is now used in the NEW taxonomy.
- **Applied broad**: The old ID is now used for the closest new broad category following editorial approval; existing assignments should still be reviewed when practical.
- **Unresolved**: The old node combines concepts represented by several new branches or resource models and cannot be migrated automatically.

## Complete node mapping

| Old path and node ID | Successor in `ObjectTaxonomy.yaml` | Assessment | Migration note |
|---|---|---|---|
| `Laterne` | `CarnivalEquipmentAndMaterialObjects/Laterne` | Applied clear | Old node ID retained. |
| `Larve` | `CarnivalEquipmentAndMaterialObjects/Larve` | Applied clear | Old node ID retained. |
| `Kostuem` | `CarnivalEquipmentAndMaterialObjects/Kostuem` | Applied clear | Old node ID retained; umlaut remains in labels only. |
| `Plakette` | `CarnivalEquipmentAndMaterialObjects/Plakette` | Applied clear | Old node ID retained. |
| `Requisite` | `CarnivalEquipmentAndMaterialObjects/Requisite` | Applied clear | Old node ID retained. |
| `Memorabilia` | `Memorabilia` | Applied clear | Old node ID retained for the expanded “Memorabilia and collectibles” category. |
| `Musik` | No unique successor. Candidates include `CarnivalEquipmentAndMaterialObjects/Musikinstrument`, `CarnivalTextsAndMusicNotation`, `MusicalWorks`, and `AnalogMediaAndCarriers`. | Unresolved | GraphDB contains no direct archive-data assignment to this node. It is used only as the old parent of three taxonomy nodes, so no instance migration is currently required. |
| `Musik/Musikinstrument` | `CarnivalEquipmentAndMaterialObjects/Musikinstrument` | Applied clear | Old node ID retained under the new parent. |
| `Musik/Musikinstrument/Trommel` | `CarnivalEquipmentAndMaterialObjects/Musikinstrument/Trommel` | Applied clear | Old node ID retained. |
| `Musik/Musikinstrument/Piccolo` | `CarnivalEquipmentAndMaterialObjects/Musikinstrument/Piccolo` | Applied clear | Node ID already matched. |
| `Musik/Musikinstrument/AnderesInstrument` | `CarnivalEquipmentAndMaterialObjects/Musikinstrument/AnderesInstrument` | Applied clear | Old node ID retained. |
| `Musik/Musiktext` | No unique successor. Main candidates are `CarnivalTextsAndMusicNotation/SongLyrics`, `CarnivalTextsAndMusicNotation/MusicalNotation`, and possibly `CarnivalTextsAndMusicNotation/Manuscript`. | Unresolved | GraphDB contains no direct archive-data assignment to this node, so no current instance migration is required. |
| `Musik/Aufnahme` | No unique successor. Physical carriers belong below `AnalogMediaAndCarriers`; digital files are ArchiveMediaObjects; an intellectual recording may require additional modelling. | Unresolved | GraphDB contains no direct archive-data assignment to this node, so no current instance migration is required. |
| `Marsch` | `MusicalWorks/Marsch` | Applied clear | Old node ID retained; the new label may remain “Marsch oder Komposition”. |
| `Helge` | `Kunst/Helge` | Applied clear | Node ID already matched; the approved old broad parent ID `Kunst` is retained. |
| `Zeedel` | `CarnivalTextsAndMusicNotation/Zeedel` | Applied clear | Node ID already matched. |
| `Kunst` | `Kunst` | Applied broad | Old broad node ID retained for “Visual and design works” following editorial approval. Existing direct assignments can be reviewed later. |
| `Dokument` | No unique successor. Candidates include `Vereinsdokument`, `PublicationsAndPress`, `CarnivalTextsAndMusicNotation`, and parts of `Kunst`. | Unresolved | GraphDB contains exactly two direct assignments, the ArchiveObjects “Rädäbäng 1911” and “Rädäbäng 1912”. They require a separate editorial migration decision. |
| `Dokument/Vereinsdokument` | `Vereinsdokument` | Applied broad | Old broad node ID retained for “Written and administrative records”. More specific records may later be refined to child nodes. |
| `Dokument/Protokoll` | `Vereinsdokument/Protokoll` | Applied clear | Old node ID retained. |
| `Dokument/Buch` | `PublicationsAndPress/Buch` | Applied clear | Old node ID retained. |
| `Dokument/Magazin` | `PublicationsAndPress/Magazin` | Applied clear | Old node ID retained for “Periodical or magazine”. |
| `Dokument/Chronik` | `PublicationsAndPress/Chronik` | Applied clear | Old node ID retained. |
| `Other` | `Other` | Applied clear | Node ID already matched. |
| `Undetermined` | `Undetermined` | Applied clear | Node ID already matched. |

## Applied old IDs

The replacement taxonomy contains these 21 approved old node IDs:

- `Laterne`
- `Larve`
- `Kostuem`
- `Plakette`
- `Requisite`
- `Memorabilia`
- `Musikinstrument`
- `Trommel`
- `Piccolo`
- `AnderesInstrument`
- `Marsch`
- `Helge`
- `Zeedel`
- `Kunst`
- `Vereinsdokument`
- `Protokoll`
- `Buch`
- `Magazin`
- `Chronik`
- `Other`
- `Undetermined`

## Programme and event guide

The former proposed node `ProgrammeBooklet` has been broadened to:

- node ID `ProgrammeAndEventGuide`;
- German label “Programm- und Veranstaltungsführer”;
- English label “Programme and event guide”.

It describes official or editorially responsible publications containing programme information, participants, themes, routes, schedules, and organisational guidance for an event.

The two existing Rädäbäng ArchiveObjects have **not** been assigned to this node. Their current `Dokument` references remain unchanged until a separate solution is approved.

## Current GraphDB findings for unresolved nodes

| Old node | Direct archive-data assignments |
|---|---:|
| `Musik` | 0 |
| `Musiktext` | 0 |
| `Aufnahme` | 0 |
| `Dokument` | 2 |

The two `Dokument` assignments are:

- `urn:uuid:1c38fa55-cb24-4fc9-8bb3-e7055a746372` — Rädäbäng 1911;
- `urn:uuid:997bddb1-bf0c-4e66-aa7e-aa6abc4ce0de` — Rädäbäng 1912.

## Remaining migration steps

1. Decide the separate treatment of the two Rädäbäng ArchiveObjects.
2. Recheck GraphDB immediately before a production migration in case new assignments have been created.
3. Confirm in GraphDB that the repository's replacement list was recreated rather than partially merged with obsolete nodes.
4. Validate all existing `fasnacht:objectType` values against the replacement list after migration.

The former `Aufnahme` node currently has no direct data assignments. The replacement deliberately distinguishes physical analogue carriers in `AnalogMediaAndCarriers` from digital ArchiveMediaObjects; no additional intellectual-recording type is introduced until a concrete archival use case requires it.
