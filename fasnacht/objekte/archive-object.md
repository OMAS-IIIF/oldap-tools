# ArchiveObject {#sec:archive-object}

Ein `ArchiveObject` ist das eigentliche Archivgut: ein Gegenstand, Werk, Dokument, Bestandsteil oder kulturelles Zeugnis der Fasnacht. Beispiele sind Laternen, Masken, Kostüme, Plaketten, Helgen, Märsche, Entwürfe, Dokumente oder Sammlungen.

Ein `ArchiveObject` ist zugleich ein [`CarnivalThing`](#sec:carnival-thing). Allgemeine Angaben wie Name, Beschreibung, Datierung, Ort, Organisationsbezug und Teil-Ganzes-Beziehungen kommen daher aus dieser gemeinsamen Oberklasse.

Wichtig: Ein `ArchiveObject` ist nicht die Datei auf dem Computer. Es beschreibt den Gegenstand oder Inhalt, über den das Archiv fachlich Auskunft geben soll. Die digitalen Fotos, Scans, Tonaufnahmen oder Videos dazu werden als [`ArchiveMediaObject`](#sec:archive-media-object) erfasst.

## Wann dieses Objekt verwendet wird {#sec:archive-object-verwendung}

Verwenden Sie `ArchiveObject`, wenn Sie ein Stück Fasnachtsgeschichte beschreiben möchten:

- ein physisches Objekt wie Maske, Larve, Kostüm, Laterne oder Requisit;
- ein Dokument wie Programm, Notenblatt, Korrespondenz oder Entwurf;
- ein Werk wie Marsch, Vers, Zeichnung oder Plakettenentwurf;
- einen Bestandteil einer Sammlung oder eines grösseren Objekts.

## Felder {#sec:archive-object-felder}

| Feld | Bedeutung für die Erfassung |
| --- | --- |
| Name | Der Name, unter dem das Objekt gefunden und angezeigt wird. Pflichtfeld. |
| Beschreibung | Freitext zu Aussehen, Inhalt, Verwendung, Motiv, Sujet, Geschichte oder Besonderheiten. |
| Datierung | Wann das Objekt entstanden ist oder fachlich datiert wird. Das kann ein genaues Datum, ein Jahr oder eine unsichere Datierung sein. |
| Art | Die fachliche Objektkategorie aus der Objekttaxonomie, zum Beispiel Laterne, Maske, Kostüm, Plakette, Marsch oder Helg. Pflichtfeld. |
| Urheber | Person, die das Objekt entworfen, hergestellt, geschrieben, komponiert oder anderweitig geschaffen hat. |
| Aktuelle Verwahrerin / aktueller Verwahrer | Person, Organisation oder Institution, die das Objekt aktuell verwahrt. |
| Provenienz | Herkunft, Besitzgeschichte, Erwerbungszusammenhang oder Überlieferungsgeschichte. |
| Enthält | Andere Archivobjekte, die zu diesem Objekt gehören. Beispiel: ein Konvolut enthält mehrere Helgen. |
| Teil von | Grössere Einheit, zu der dieses Objekt gehört. Beispiel: ein einzelner Helg ist Teil einer Sammlung. |
| Verwendet am | Datum oder Zeitraum, in dem das Objekt in der Fasnacht verwendet wurde. |
| Ort | Aktueller Standort oder Aufbewahrungsort. |
| Signatur | Archivkennung, Inventarnummer oder andere Nummer, mit der das Objekt wiedergefunden wird. |

## Warum die Trennung vom Medienobjekt wichtig ist {#sec:archive-object-trennung-medienobjekt}

Das `ArchiveObject` beantwortet die Frage: "Was ist das für ein Archivgut?"

Das [`ArchiveMediaObject`](#sec:archive-media-object) beantwortet die Frage: "Welche Datei zeigt, scannt, dokumentiert oder spielt dieses Archivgut ab?"

Diese Trennung ist notwendig, weil ein Objekt viele Dateien haben kann. Eine Laterne kann mehrere Fotos haben, ein Heft viele Seiten-Scans, ein Marsch eine Notenausgabe und mehrere Tonaufnahmen. Die Beschreibung der Laterne, des Hefts oder des Marsches soll aber nur einmal gepflegt werden.

## Beispiel {#sec:archive-object-beispiel}

Eine Laterne von 1985 wird als `ArchiveObject` beschrieben: Name, Sujet, Objektart "Laterne", Urheber, Datierung, heutiger Standort und Signatur. Die drei Fotografien der Laterne werden separat als `ArchiveMediaObject` erfasst und mit dieser Laterne verbunden.
