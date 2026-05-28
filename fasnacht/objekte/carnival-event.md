# CarnivalEvent {#sec:carnival-event}

Ein `CarnivalEvent` beschreibt einen Fasnachtsanlass oder ein Ereignis. Beispiele sind Morgenstreich, Cortège, Guggenkonzert, Kinderfasnacht, Vorfasnachtsveranstaltung, interner Clique-Anlass oder historischer Anlass.

Ein `CarnivalEvent` ist zugleich ein [`CarnivalThing`](#sec:carnival-thing). Es besitzt daher die gemeinsamen Felder wie Name, Beschreibung, Datierung, Organisation, Ort und Teil-Ganzes-Beziehungen.

## Wann dieses Objekt verwendet wird {#sec:carnival-event-verwendung}

Verwenden Sie `CarnivalEvent`, wenn ein Anlass selbst beschrieben werden soll:

- offizieller Fasnachtsanlass;
- Vorfasnachtsveranstaltung;
- interner Anlass einer Clique oder Organisation;
- historischer Anlass;
- Wettbewerb oder musikalischer Anlass.

## Felder {#sec:carnival-event-felder}

| Feld | Bedeutung für die Erfassung |
| --- | --- |
| Typ | Ereignistyp aus der CarnivalEventTaxonomy, zum Beispiel Morgenstreich, Cortège oder Drummeli. |
| Ort | Ort des Ereignisses. |

Weitere allgemeine Angaben wie Name, Beschreibung, Datierung und Organisationsbezug kommen über [`CarnivalThing`](#sec:carnival-thing).

## Beispiel {#sec:carnival-event-beispiel}

Der Morgenstreich 2024 kann als `CarnivalEvent` erfasst werden. Er erhält einen Namen, eine Datierung, einen Ort und den Typ `Morgenstreich`. Medien oder Stories können später mit diesem Ereignis verbunden werden.
