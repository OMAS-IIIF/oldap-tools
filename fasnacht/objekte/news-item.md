# NewsItem {#sec:news-item}

Ein `NewsItem` ist eine aktuelle Meldung auf der Plattform. Es eignet sich für Hinweise, Neuigkeiten, Veranstaltungen, neue Beiträge oder organisatorische Informationen.

Im Unterschied zur [`Story`](#sec:story) ist ein News-Eintrag meist kürzer, aktueller und zeitlich begrenzter.

## Wann dieses Objekt verwendet wird {#sec:news-item-verwendung}

Verwenden Sie `NewsItem` für:

- Hinweise auf neue Inhalte;
- Ankündigungen;
- Plattformmeldungen;
- zeitlich relevante Informationen;
- kurze redaktionelle Mitteilungen.

## Felder {#sec:news-item-felder}

| Feld | Bedeutung für die Erfassung |
| --- | --- |
| Autor | Person, die die Meldung verfasst oder vorbereitet hat. |
| Titel | Überschrift der Meldung. Pflichtfeld. |
| Inhalt | Vollständiger Text der Meldung. Pflichtfeld. |
| Startdatum | Datum, ab dem die Meldung sichtbar oder relevant ist. Pflichtfeld. |
| Enddatum | Datum, nach dem die Meldung nicht mehr aktuell ist. |

## Beispiel {#sec:news-item-beispiel}

Eine Meldung "Neue Sammlung von Plakettenentwürfen online" wird als `NewsItem` erfasst. Sie kann ein Startdatum und optional ein Enddatum erhalten.
