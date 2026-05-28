# CarnivalThing {#sec:carnival-thing}

Ein `CarnivalThing` ist der gemeinsame Oberbegriff für Dinge, die zur Fasnacht gehören und fachlich beschrieben werden sollen. Das kann ein Archivobjekt sein, aber auch ein Anlass oder Ereignis.

Die Klasse sammelt Felder, die für mehrere Arten von Fasnachtsdingen gleich sind: Name, Beschreibung, Datierung, beteiligte Organisation, Ort und Teil-Ganzes-Beziehungen.

## Wann dieses Objekt verwendet wird {#sec:carnival-thing-verwendung}

`CarnivalThing` wird normalerweise nicht direkt als einzelner Erfassungstyp verwendet. Es ist die gemeinsame Grundlage für speziellere Objekte wie:

- [`ArchiveObject`](#sec:archive-object): Archivgut, Werk, Objekt oder Dokument.
- [`CarnivalEvent`](#sec:carnival-event): Anlass oder Ereignis.

## Felder {#sec:carnival-thing-felder}

| Feld | Bedeutung für die Erfassung |
| --- | --- |
| Name | Name oder Titel des Fasnachtsdings. Pflichtfeld. |
| Beschreibung | Freitext zu Inhalt, Bedeutung, Kontext oder Besonderheiten. |
| Datierung | Datum, Jahr, Zeitraum oder unsichere Datierung. |
| Mit Organisation/Einrichtung verbunden | Person, Organisation, Clique, Institution oder Archiv, die mit dem Ding verbunden ist. |
| Verknüpft mit Organisationseinheit | Bezug auf eine Kategorie aus der Organisationstaxonomie. |
| Teil von | Grössere Einheit, zu der dieses Ding gehört. |
| Hat Teil | Untergeordnete Dinge, die dazu gehören. |
| Ort | Ort, an dem das Ding verortet ist oder stattfindet. |

## Warum diese Oberklasse existiert {#sec:carnival-thing-oberklasse}

Archivobjekte und Ereignisse haben viele gemeinsame Angaben. Eine Laterne und ein Cortège sind fachlich verschieden, können aber beide einen Namen, eine Beschreibung, ein Datum, einen Ort und organisatorische Bezüge haben.

Durch `CarnivalThing` müssen diese gemeinsamen Felder nicht mehrfach modelliert werden. Gleichzeitig können spezielle Objektarten eigene zusätzliche Felder erhalten.
