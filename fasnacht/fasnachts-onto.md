# Ontologie `fasnacht`

Diese Datei beschreibt die aktuelle Ontologie des Projekts `fasnacht`. Sie ist als lebende Dokumentation gedacht und soll bei jeder fachlichen oder technischen Änderung an den YAML-Dateien mitgeführt werden.

Quellen:

- `fasnacht-onto.yaml`: Ontologie, Klassen, Properties, externe Vokabulare und Referenzen auf Taxonomien
- `CreativeCommons.yaml`: Lizenz-Taxonomie
- `ObjectTaxonomy.yaml`: Objekt-Taxonomie
- `LocationTaxonomy.yaml`: Orts-Taxonomie
- `StoryKeywords.yaml`: Schlagwort-Taxonomie für Stories
- `OrganisationTaxonomy.yaml`: Organisations-Taxonomie

## Zweck und fachlicher Rahmen

Die Ontologie modelliert die Wissensbasis für `fasnacht.digital`, eine Plattform zur Basler Fasnacht. Sie verbindet Archivobjekte, Medien, Personen, Organisationen, Orte, Geschichten und redaktionelle Inhalte. Die Basler Fasnacht ist seit 2017 immaterielles Kulturerbe der UNESCO; die Plattform dient als Wissensportal für Vereine, Institutionen und Privatpersonen, die Material beitragen, durchsuchen und erschließen möchten.

Die Ontologie verwendet den Namespace:

```text
http://fasnacht.digital/ns/
```

Das Projekt trägt den OLDAP-Shortname:

```text
fasnacht
```

## Grundprinzipien

- Die YAML-Dateien sind die fachliche Ground Truth für das Datenmodell.
- Änderungen am Datenmodell sollen kontrolliert über `fasnacht-onto.yaml` erfolgen.
- Änderungen dürfen nicht im Widerspruch zu bereits vorhandenen Daten stehen.
- Taxonomien werden additiv erweitert: neue Knoten können ergänzt werden, bestehende Knoten werden nicht verschoben oder gelöscht.
- Bei ResourceClasses gilt die im YAML definierte `properties`-Liste als gewünschter Property-Satz der Klasse.
- Diese Dokumentation muss mit jeder Änderung an Klassen, Properties oder Taxonomien aktualisiert werden.

## Externe Vokabulare

Die Ontologie bindet externe Vokabulare ein, um etablierte Begriffe wiederzuverwenden.

### Dublin Core Terms (`dcterms`)

Namespace:

```text
http://purl.org/dc/terms/
```

Dublin Core wird vor allem für bibliografische, archivische und relationale Angaben verwendet, etwa Titel, Beschreibung, Provenienz, Rechte, Teil-Ganzes-Beziehungen und Datierungen.

### schema.org (`schema`)

Namespace:

```text
https://schema.org/
```

schema.org wird für allgemeine Begriffe wie Personen, Organisationen, Orte, Medienobjekte, Nachrichtenartikel, Beschreibungen, Namen, Autorenschaft und Ortsbezüge verwendet.

## Zentrale Klassen

### `fasnacht:FasnachtUser`

Spezialisierung von `oldap:User`.

Die Klasse erweitert OLDAP-Benutzer um einen Bezug zu einer Organisation:

- `fasnacht:memberOfOrganisation`: optionale Zuordnung zu `OrganisationTaxonomy`, maximal ein Wert.

### `fasnacht:Agent`

Abstrakter Oberbegriff für handelnde Einheiten. Die Klasse ist von `schema:Agent` und `dcterms:Agent` abgeleitet.

Sie dient als gemeinsame fachliche Basis für Personen und Organisationen.

### `fasnacht:Person`

Personen, die im Fasnachtsarchiv vorkommen, zum Beispiel Autorinnen, Urheber, Beteiligte oder Personen in Provenienz- und Kontextangaben.

Oberklassen:

- `schema:Person`
- `fasnacht:Agent`

Properties:

- `schema:familyName`: Nachname, Pflichtfeld, genau ein Wert.
- `schema:givenName`: Vorname, Pflichtfeld, genau ein Wert.

### `fasnacht:Organisation`

Organisationen, Vereine, Cliquen, Institutionen oder Gedächtnisinstitutionen mit Bezug zur Basler Fasnacht.

Oberklassen:

- `schema:Organization`
- `fasnacht:Agent`

Properties:

- `schema:name`: Name der Organisation, Pflichtfeld.
- `fasnacht:mediaStorage`: Ablagepfad für Medien dieser Organisation, Pflichtfeld, genau ein Wert.
- `fasnacht:organisationDescription`: mehrsprachige Beschreibung der Organisation.
- `fasnacht:organisationTaxonomy`: Klassifikation über `OrganisationTaxonomy`, Pflichtfeld.
- `fasnacht:organisationLocatedAtPlace`: Bezug zu einem `fasnacht:Place`.

### `schema:NewsArticle`

Externe Basisklasse für Nachrichtenartikel. Sie wird als Grundlage für `fasnacht:NewsItem` verwendet.

### `fasnacht:NewsItem`

Redaktioneller Eintrag für Neuigkeiten, Hinweise oder aktuelle Beiträge auf der Plattform.

Oberklasse:

- `schema:NewsArticle`

Properties:

- `fasnacht:newsItemTitle`: mehrsprachiger Titel, Pflichtfeld.
- `fasnacht:newsItemContent`: mehrsprachiger Inhalt, Pflichtfeld.
- `fasnacht:newsItemStartDate`: Startdatum der Sichtbarkeit oder Relevanz, Pflichtfeld, genau ein Wert.
- `fasnacht:newsItemEndDate`: optionales Enddatum, maximal ein Wert.
- `schema:author`: Autorin oder Autor des News-Eintrags.

### `fasnacht:MediaLibraryObject`

Medienobjekt der allgemeinen Medienbibliothek, unabhängig davon, ob es ein konkretes Archivobjekt repräsentiert.

Oberklasse:

- `shared:MediaObject`

Properties:

- `schema:dateCreated`: Aufnahme-, Erfassungs- oder Erstellungsdatum.
- `schema:name`: mehrsprachiger Titel oder Name, Pflichtfeld, genau ein Wert.
- `schema:description`: mehrsprachige Beschreibung, maximal ein Wert.
- `schema:creator`: Urheberin oder Urheber.
- `schema:source`: Quelle oder Provenienzangabe, maximal ein Wert.
- `dcterms:rights`: Lizenz oder Rechteangabe über `CreativeCommons`, Pflichtfeld, genau ein Wert.

### `fasnacht:Story`

Narrative oder kuratierte Geschichte zu Fasnachtspersonen, Objekten, Orten, Ereignissen, Ritualen oder Traditionen.

Properties:

- `fasnacht:storyTitle`: mehrsprachiger Titel, Pflichtfeld.
- `fasnacht:leadImage`: führendes Medienobjekt aus `fasnacht:MediaLibraryObject`, Pflichtfeld, genau ein Wert.
- `schema:abstract`: mehrsprachige Zusammenfassung, Pflichtfeld.
- `fasnacht:storyContent`: mehrsprachiger Volltext, Pflichtfeld.
- `fasnacht:storyDate`: Datum oder Bezugsdatum, Pflichtfeld, genau ein Wert.
- `schema:author`: Autorin oder Autor, Pflichtfeld.
- `fasnacht:isPublished`: Publikationsstatus, Pflichtfeld, genau ein Wert.
- `fasnacht:leadImageRegion`: optionale Crop-/Regionsangabe für das Lead Image, maximal ein Wert.
- `fasnacht:storyKeywords`: Schlagworte über `StoryKeywords`.

### `fasnacht:Place`

Orte mit Bezug zu Fasnachtsobjekten, Organisationen, Ereignissen, Stories oder Archivmaterial.

Oberklasse:

- `schema:Place`

Properties:

- `schema:name`: mehrsprachiger Ortsname, Pflichtfeld.
- `schema:alternateName`: alternative, historische oder mundartliche Bezeichnung.
- `schema:description`: mehrsprachige Beschreibung, maximal ein Wert.
- `fasnacht:ofOrganisation`: Bezug zu einer Organisation oder Institution.
- `dcterms:type`: Ortskategorie über `LocationTaxonomy`, Pflichtfeld, genau ein Wert.
- `geo:asWKT`: Geometrie im WKT-Format, maximal ein Wert.
- `dcterms:isPartOf`: übergeordneter Ort, maximal ein Wert.
- `dcterms:hasPart`: untergeordnete Orte.
- `rdfs:comment`: historische Bemerkung oder redaktioneller Kommentar, maximal ein Wert.

### `fasnacht:ArchiveObject`

Archivisches Objekt aus Fasnachtsbeständen. Dazu gehören physische und konzeptuelle Objekte wie Laternen, Masken, Kostüme, Plaketten, Märsche oder Helgen.

Properties:

- `fasnacht:archiveObjectTitle`: mehrsprachiger Titel, Pflichtfeld.
- `dcterms:type`: Objekttyp über `ObjectTaxonomy`, Pflichtfeld, genau ein Wert.
- `schema:description`: mehrsprachige archivische Beschreibung.
- `dcterms:creator`: Urheberin oder Urheber als `fasnacht:Person`.
- `fasnacht:hasCreationDating`: Erstellungsdatum oder Datierung als `oldap:Dating`.
- `schema:provider`: bereitstellende Person oder Organisation als `fasnacht:Agent`, Pflichtfeld, genau ein Wert.
- `dcterms:provenance`: mehrsprachige Provenienzangabe.
- `dcterms:hasPart`: enthaltene Archivobjekte.
- `dcterms:isPartOf`: übergeordnetes Archivobjekt oder Sammlung.
- `fasnacht:usedAt`: Datierung der Verwendung als `oldap:Dating`.
- `fasnacht:currentLocation`: aktueller Ort als `fasnacht:Place`, maximal ein Wert.
- `schema:identifier`: Signatur oder Identifikator, maximal ein Wert.

### `fasnacht:ArchiveMediaObject`

Medienobjekt, das ein oder mehrere Archivobjekte repräsentiert, zum Beispiel Foto, Scan, Video, Audiodatei oder Digitalisat.

Oberklasse:

- `shared:MediaObject`

Properties:

- `schema:name`: mehrsprachiger Titel, Pflichtfeld.
- `schema:description`: mehrsprachige Beschreibung, maximal ein Wert.
- `fasnacht:archiveMediaObjectOf`: repräsentiertes `fasnacht:ArchiveObject`, Pflichtfeld.
- `dcterms:creator`: Urheberin oder Urheber als `fasnacht:Agent`.
- `schema:dateCreated`: Erstellungsdatum.
- `dcterms:rights`: Lizenz oder Rechteangabe über `CreativeCommons`, Pflichtfeld, genau ein Wert.
- `schema:position`: Position, Sequenznummer oder Seitenangabe.

## Wichtige Beziehungen

Die Ontologie modelliert mehrere zentrale Beziehungstypen:

- Personen und Organisationen sind beide `fasnacht:Agent`.
- Organisationen können über eine Taxonomie klassifiziert und mit Orten verbunden werden.
- Medienobjekte können allgemein in der Medienbibliothek liegen oder konkret Archivobjekte repräsentieren.
- Archivobjekte können Teil-Ganzes-Beziehungen bilden.
- Orte können hierarchisch miteinander verbunden werden.
- Stories verknüpfen Text, Lead Image, Autorenschaft, Datum, Publikationsstatus und Schlagworte.
- Lizenzen und kontrollierte Kategorien werden über Taxonomien modelliert.

## Taxonomien

### `CreativeCommons`

Lizenz-Taxonomie für Rechteangaben an Medienobjekten.

Knoten:

- `CC_BY`
- `CC_BY-NC`
- `CC_BY-NC-ND`
- `CC_BY-NC-SA`
- `CC_BY-ND`
- `CC_BY-SA`
- `CC0`

Verwendet in:

- `fasnacht:MediaLibraryObject` über `dcterms:rights`
- `fasnacht:ArchiveMediaObject` über `dcterms:rights`

### `ObjectTaxonomy`

Kontrollierte Objektkategorien für Archivobjekte.

Knoten:

- `Laterne`
- `Maske`
- `Kostuem`
- `Plakette`
- `Marsch`
- `Helge`

Verwendet in:

- `fasnacht:ArchiveObject` über `dcterms:type`

### `LocationTaxonomy`

Kontrollierte Ortskategorien.

Knoten:

- `Archiv`
- `Cliquenkeller`
- `Depot`
- `Veranstaltungsort`
- `Privat`
- `Museum`
- `Werkstatt`
- `Strasse`
- `Platz`
- `Gebaeude`
- `Quartier`
- `Bruecke`
- `Route`
- `Restaurant`
- `Treffpunkt`
- `Areal`
- `HistorischerOrt`

Verwendet in:

- `fasnacht:Place` über `dcterms:type`

### `StoryKeywords`

Schlagworte für Stories.

Knoten:

- `ScienceBackground`: Wissenschaft & Hintergrund
- `ObjectsCollections`: Objekte & Sammlungen
- `RitualsCrafts`: Rituale & Handwerk
- `Miscellanious`: Mümpfeli & Allergattigs

Verwendet in:

- `fasnacht:Story` über `fasnacht:storyKeywords`

### `OrganisationTaxonomy`

Kontrollierte Organisationskategorien.

Struktur:

- `Fasnachtsvereine`
  - `Clique`
    - `Stamm`
    - `AlteGarde`
    - `JungeGarde`
      - `Binggis`
      - `Nachwuchs`
  - `Wagenclique`
  - `Guggenmusik`
  - `Chaise`
  - `Schyssdraeggzuegli`
  - `Fasnachtscomite`
- `Gedaechtnisinstitutionen`
  - `Archiv`
    - `Bundesarchiv`
    - `Staatsarchiv`
    - `Cliqenarchiv`
    - `Institutionsarchiv`
    - `Privatarchiv`
  - `Museum`
    - `Staatsmuseum`
    - `Privatmuseum`

Verwendet in:

- `fasnacht:FasnachtUser` über `fasnacht:memberOfOrganisation`
- `fasnacht:Organisation` über `fasnacht:organisationTaxonomy`

## Lucene-Indexierung

Die Ontologie definiert Lucene-Connector-Konfigurationen für die Suche.

### Story-Suche

Indexiert `fasnacht:Story` über:

- `fasnacht:storyContent`
- `schema:abstract`

### Archiv-Suche

Indexiert `fasnacht:ArchiveObject` und `fasnacht:ArchiveMediaObject` über:

- `fasnacht:archiveObjectTitle`
- `schema:description`
- `schema:name`
- zusammengesetzte Property Chains von `fasnacht:ArchiveMediaObject` zum repräsentierten `fasnacht:ArchiveObject`

## Pflegehinweise

Bei Änderungen an der Ontologie sollte diese Datei angepasst werden.

Typische Änderungen, die dokumentiert werden müssen:

- neue Klassen,
- entfernte oder umbenannte Klassen,
- neue Properties,
- geänderte Pflichtfelder oder Kardinalitäten,
- neue Taxonomien,
- neue Taxonomieknoten,
- Änderungen an Lucene-Indexfeldern,
- neue externe Vokabulare.

Vor produktiven Änderungen sollte geprüft werden:

- Ist die YAML-Datei syntaktisch gültig?
- Widerspricht die Änderung bestehenden Daten?
- Werden Pflichtfelder verschärft?
- Werden Properties aus einer bestehenden Klasse entfernt?
- Werden Taxonomieknoten nur additiv ergänzt?

