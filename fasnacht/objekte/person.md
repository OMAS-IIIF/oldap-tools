# Person {#sec:person}

Eine `Person` beschreibt eine einzelne natürliche Person, die im Fasnachtsarchiv vorkommt. Personen können Urheberinnen, Autoren, Fotografen, Beteiligte, Sammlerinnen, Zeitzeugen oder andere relevante Personen sein.

## Wann dieses Objekt verwendet wird {#sec:person-verwendung}

Verwenden Sie `Person`, wenn eine konkrete Person eindeutig genannt und wiederverwendet werden soll:

- als Urheber eines [`ArchiveObject`](#sec:archive-object);
- als Autorin einer [`Story`](#sec:story) oder eines [`NewsItem`](#sec:news-item);
- als Fotografin oder Produzent eines Medienobjekts;
- als fachlich relevante Person in Beschreibungen und Provenienzen.

## Felder {#sec:person-felder}

| Feld | Bedeutung für die Erfassung |
| --- | --- |
| Nachname | Familienname der Person. Pflichtfeld. |
| Vorname | Vorname der Person. Pflichtfeld. |

## Hinweise {#sec:person-hinweise}

Die Personendaten sind bewusst knapp. Weitere Rollen ergeben sich aus den Verknüpfungen: Eine Person kann bei einem Archivobjekt Urheber sein, bei einer Story Autorin und bei einem Medienobjekt Fotografin.

## Beispiel {#sec:person-beispiel}

Wenn Max Muster eine Laterne entworfen hat, wird Max Muster einmal als `Person` erfasst. Beim Archivobjekt der Laterne wird er dann als Urheber verknüpft.
