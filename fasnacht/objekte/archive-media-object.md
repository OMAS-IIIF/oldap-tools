# ArchiveMediaObject {#sec:archive-media-object}

Ein `ArchiveMediaObject` ist eine digitale Darstellung eines Fasnachtsdings. Es beschreibt also eine Datei oder Medienaufnahme, die ein [`CarnivalThing`](#sec:carnival-thing) zeigt, wiedergibt oder dokumentiert. Das kann ein [`ArchiveObject`](#sec:archive-object) sein, aber auch ein [`CarnivalEvent`](#sec:carnival-event).

Typische Beispiele sind Fotografien, Scans, Videos, Tonaufnahmen, Digitalisate von Seiten oder Detailaufnahmen eines Objekts.

## Wann dieses Objekt verwendet wird {#sec:archive-media-object-verwendung}

Verwenden Sie `ArchiveMediaObject`, wenn Sie eine Datei erfassen, die direkt zu einem Archivobjekt oder Ereignis gehört:

- Foto einer Maske, Laterne oder Plakette;
- Scan eines Programms, Helgs, Entwurfs oder Notenblatts;
- Tonaufnahme eines Marsches;
- Video einer Aufführung oder eines Umzugs;
- mehrere Seiten-Scans eines einzigen Dokuments.

## Felder {#sec:archive-media-object-felder}

| Feld | Bedeutung für die Erfassung |
| --- | --- |
| Titel | Anzeigename der Datei oder Mediendarstellung. Pflichtfeld. |
| Beschreibung | Was ist auf der Datei zu sehen oder zu hören? Welche Ansicht, Seite oder Besonderheit wird dokumentiert? |
| Medium, das ein Fasnachtsding darstellt | Verknüpfung zum Archivobjekt oder Ereignis, das diese Datei zeigt oder wiedergibt. Pflichtfeld. |
| Zur Verfügung gestellt von | Person oder Organisation, die das Medium bereitstellt. Pflichtfeld. |
| Urheber | Person oder Organisation, die Foto, Scan, Video, Aufnahme oder Digitalisat erstellt hat. |
| Erstellungsdatum | Datum der Aufnahme, Digitalisierung oder Erstellung der Mediendatei. |
| Lizenz | Rechteangabe für die Nutzung der Mediendatei. Pflichtfeld. |
| Position/Sequenznummer/Seite | Reihenfolge innerhalb einer Serie, zum Beispiel Seite 3, Bild 2 oder Track 1. |

## Warum es nicht einfach Teil des Archivobjekts ist {#sec:archive-media-object-nicht-teil-des-archivobjekts}

Medien haben eigene Eigenschaften, die nicht zum Archivobjekt selbst gehören. Ein Foto hat eine Fotografin, ein Aufnahmedatum und eine Lizenz. Ein Scan kann Seite 5 eines Hefts sein. Eine Tonaufnahme kann Jahrzehnte nach der Komposition eines Marsches entstanden sein.

Würden diese Angaben direkt beim [`ArchiveObject`](#sec:archive-object) stehen, wäre unklar, ob sie das historische Objekt oder nur die Datei betreffen. Die Trennung macht sichtbar:

- Das Archivobjekt ist das fachliche Kulturgut.
- Das Archivmedienobjekt ist die konkrete digitale Darstellung dieses Kulturguts.

## Beispiel {#sec:archive-media-object-beispiel}

Ein Plakettenentwurf von 1962 ist ein `ArchiveObject`. Ein hochauflösender Scan davon ist ein `ArchiveMediaObject`. Wenn später noch ein Detailfoto und ein zweiter Scan hinzukommen, bleiben alle drei Medien mit demselben Archivobjekt verbunden.

Ebenso kann ein Video des Morgenstreichs als `ArchiveMediaObject` mit einem `CarnivalEvent` verbunden werden.
