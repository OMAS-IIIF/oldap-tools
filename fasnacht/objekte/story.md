# Story {#sec:story}

Eine `Story` ist ein redaktioneller Beitrag. Sie erklärt, erzählt und kontextualisiert Fasnachtsthemen für ein Publikum. Stories können Personen, Objekte, Orte, Ereignisse, Rituale, Handwerk oder Sammlungen sichtbar machen.

Eine Story ist kein Archivobjekt. Sie ist eine kuratierte Erzählung über Archivmaterial und Fasnachtswissen.

## Wann dieses Objekt verwendet wird {#sec:story-verwendung}

Verwenden Sie `Story`, wenn ein Thema nicht nur als Datensatz, sondern als lesbarer Beitrag präsentiert werden soll:

- Hintergrundartikel zu einem Sujet, Brauch oder Objekt;
- Sammlungsporträt;
- Beitrag zu einer Person, Organisation oder Werkstatt;
- redaktioneller Einstieg in einen Themenbereich.

## Felder {#sec:story-felder}

| Feld | Bedeutung für die Erfassung |
| --- | --- |
| Titel | Titel der Geschichte. Pflichtfeld. |
| Lead Image | Hauptbild aus der Medienbibliothek. Pflichtfeld. |
| Zusammenfassung | Kurze Einführung oder Teaser. Pflichtfeld. |
| Inhalt | Vollständiger Story-Text. Pflichtfeld. |
| Datum | Bezugsdatum oder Veröffentlichungsdatum der Story. Pflichtfeld. |
| Autor | Person, die die Story verfasst oder kuratiert hat. Pflichtfeld. |
| Veröffentlicht | Gibt an, ob die Story sichtbar ist. Pflichtfeld. |
| Lead image region | Bildausschnitt für die Darstellung des Leadbilds. |
| Rubrik | Schlagwort oder Kategorie, zum Beispiel Wissenschaft & Hintergrund oder Objekte & Sammlungen. |
| Verknüpftes Fasnachtsobjekt | Bezug zu einem Archivobjekt oder Ereignis, das in der Story behandelt wird. |

## Beispiel {#sec:story-beispiel}

Eine Story kann erklären, wie ein bestimmter Laternenbestand entstanden ist, wer daran beteiligt war und welche Objekte im Archiv dazu gehören. Die Objekte bleiben eigene [`ArchiveObject`](#sec:archive-object)-Datensätze; die Story verbindet sie erzählerisch.

Eine Story kann auch ein Ereignis wie den Morgenstreich oder einen Vorfasnachtsanlass behandeln und über das Feld "Verknüpftes Fasnachtsobjekt" mit einem [`CarnivalEvent`](#sec:carnival-event) verbunden werden.
