# Laienfreundliche Objekt-Dokumentation {#sec:objekte}

Diese Seiten erklären die Objekte des Fasnachtsprojekts in Alltagssprache. Sie richten sich an Fasnachtsspezialistinnen und Fasnachtsspezialisten, die fachlich genau arbeiten, aber nicht zuerst Datenmodellierung lernen möchten.

Die knappe technische Übersicht bleibt in `fasnachts-onto.md`. Die YAML-Definition bleibt die verbindliche Quelle in `fasnacht-onto.yaml`.

## Objektseiten {#sec:objekte-objektseiten}

### Administrative Objekte
- [`FasnachtUser`](#sec:fasnacht-user): Benutzerkonto mit Bezug zu einer Organisation.

### Objektseiten für die Geschichten und Aktuelles

- [`NewsItem`](#sec:news-item): aktuelle Meldungen und Hinweise auf der Plattform.
- [`NewsArticle`](#sec:news-article): technische Grundlage für News-Einträge.
- [`MediaLibraryObject`](#sec:media-library-object): allgemeines Medienmaterial für redaktionelle Zwecke, vor allem für Stories und Illustrationen.
- [`Person`](#sec:person): Personen, die im Archiv oder News/Geschichten als Urheberinnen, Autoren, Beteiligte oder Kontextpersonen vorkommen.
- [`Story`](#sec:story): redaktionelle Geschichten, die Objekte, Personen, Orte und Themen erzählerisch erschliessen.

### Objektseiten für das Archiv

- [`CarnivalThing`](#sec:carnival-thing): gemeinsamer Oberbegriff für Fasnachtsobjekte und Fasnachtsereignisse.
- [`CarnivalEvent`](#sec:carnival-event): Fasnachtsanlässe und Ereignisse, zum Beispiel Morgenstreich, Cortège oder Vorfasnachtsanlass.
- [`ArchiveObject`](#sec:archive-object): das beschriebene Archivgut selbst, zum Beispiel eine Laterne, Maske, Plakette, ein Helg oder ein Marsch.
- [`ArchiveMediaObject`](#sec:archive-media-object): eine Datei oder digitale Darstellung eines Archivobjekts, zum Beispiel Foto, Scan, Audio oder Video.
- [`Organisation`](#sec:organisation): Cliquen, Vereine, Institutionen, Archive, Museen und andere Organisationen.
- [`Place`](#sec:place): Orte, die für Objekte, Organisationen, Ereignisse oder Geschichten wichtig sind.
- [`Agent`](#sec:agent): gemeinsamer Oberbegriff für Personen und Organisationen.

## Pandoc-Zusammenführung {#sec:objekte-pandoc-zusammenfuehrung}

Alle internen Links verwenden globale Abschnitts-IDs wie `#sec:archive-object` statt Dateilinks. Dadurch funktionieren die Verweise auch dann, wenn Pandoc die einzelnen Markdown-Dateien zu einem einzigen Dokument zusammenfügt.

Empfohlene Reihenfolge:

```sh
pandoc \
  README.md \
  fasnacht-user.md \
  news-item.md \
  news-article.md \
  media-library-object.md \
  person.md \
  story.md \
  carnival-thing.md \
  archive-object.md \
  carnival-event.md \
  archive-media-object.md \
  organisation.md \
  place.md \
  agent.md \
  -o fasnacht-objekte.pdf
```

## Warum `CarnivalThing`, `ArchiveObject` und `ArchiveMediaObject` getrennt sind {#sec:objekte-trennung-carnivalthing-archiveobject-archivemediaobject}

Grundsätzlich ist das Medienobjekt, also das Foto, Video oder Audiodatei, im Zentrum des Interesses. Um aber eine
konsistente Beschreibung zu erhalten, welche auch den Anforderungen einer Archivplattform entspricht und erfolgreiche
Suchenstrategien erlaubt, ist die Datenmodellierung etwas anders aufgebaut.

_Im Grundsatz gilt, dass in Archivobjekt oder ein Ereignis und seine digitale Darstellung sind nicht dasselbe sind!_  

An oberster Stelle steht ein abstraktes "Etwas" (CarnivalThing), welches die für alle Einträge gemeinsamen Eigenschaften
beschreibt. Davon werden die zwei wichtigesten Elemente abgeleitet, nämlich das Archivobjekt (ArchiveObject) und das
Ereignsobject (EventObject). Das Medienobjekt (ArchiveMediaObject) ist dann entweder einem (oder mehreren)
Ereignsobjekt(en) und/oder einem (oder mehreren) Archivobjekt(en) zugeordnet. Ein Beispiel soll dies illustrieren:

Ein Bild zeigt den Cortège der Fasnacht 1922. Darauf sichtbar ist die Alte Garde der BMG und ihre Laterne. Das Foto
zeigt also

- den Cortège von 1922, also ein Ereignis
- die Laterne der alten Garde von 1922, ein Objekt.

Ein Archivobjekt und seine digitale Darstellung sind nicht dasselbe.

Ein `CarnivalThing` beschreibt gemeinsame Angaben zu einem Fasnachtsding: Name, Beschreibung, Datierung, Organisation, Ort und Teil-Ganzes-Beziehungen. Ein `ArchiveObject` ist eine Spezialisierung davon und beschreibt den fachlichen Gegenstand: zum Beispiel die Laterne von 1978, ein konkretes Kostüm, ein Plakettenentwurf, eine Sammlung von Helgen oder einen Marsch. Dieses Objekt hat eine Geschichte, eine Herkunft, einen Urheber, einen Aufbewahrungsort, eine Signatur und eine fachliche Einordnung.

Ein `ArchiveMediaObject` beschreibt dagegen eine Mediendatei, die dieses Fasnachtsding zeigt oder wiedergibt: ein Foto der Laterne, ein Scan des Plakettenentwurfs, eine Audiodatei des Marsches oder ein Video einer Aufführung. Diese Datei hat eigene Rechte, ein eigenes Erstellungsdatum, eine beitragende Stelle, eine Reihenfolge, eine technische Ablage und manchmal eine eigene Urheberschaft.

Die Trennung ist sinnvoll und notwendig, weil ein Archivobjekt mehrere Medien haben kann:

- eine Laterne kann von vorne, hinten und im Detail fotografiert sein;
- ein Heft kann aus vielen gescannten Seiten bestehen;
- ein Marsch kann als Notenblatt, Tonaufnahme und Video dokumentiert sein;
- ein einziges Foto kann mehrere Archivobjekte zeigen.

Ohne diese Trennung müsste man entweder dieselben Objektinformationen bei jeder Datei wiederholen oder wichtige Medieninformationen beim Archivobjekt verstecken. Beides wäre fehleranfällig. Die Trennung erlaubt saubere Suche, klare Rechteangaben, bessere Nachvollziehbarkeit und eine fachlich stabile Beschreibung des Kulturguts.
