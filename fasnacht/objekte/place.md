# Place {#sec:place}

Ein `Place` beschreibt einen Ort, der für Fasnachtsobjekte, Organisationen, Ereignisse, Stories oder Archivmaterial wichtig ist. Das kann ein Archiv, Cliquenkeller, Depot, Museum, Platz, Gebäude, Strassenzug, Quartier oder historischer Ort sein.

## Wann dieses Objekt verwendet wird {#sec:place-verwendung}

Verwenden Sie `Place`, wenn ein Ort mehr als nur beiläufig erwähnt wird und wiedergefunden oder mit mehreren Objekten verknüpft werden soll:

- heutiger Standort eines [`ArchiveObject`](#sec:archive-object);
- Standort einer [`Organisation`](#sec:organisation);
- Ort, der in einer [`Story`](#sec:story) eine Rolle spielt;
- räumlicher Bezug für Sammlungen, Ereignisse oder Überlieferung.

## Felder {#sec:place-felder}

| Feld | Bedeutung für die Erfassung |
| --- | --- |
| Name | Name des Orts. Pflichtfeld. |
| Alternativer Name | Historische, mundartliche oder gebräuchliche Zweitbezeichnung. |
| Beschreibung | Bedeutung des Orts für Fasnacht, Archiv oder Geschichte. |
| Ort der Institution/Organisation | Organisation, die für den Ort zuständig ist oder dort sitzt. |
| Ortskategorie | Kontrollierte Kategorie, zum Beispiel Archiv, Depot, Museum, Strasse oder Platz. Pflichtfeld. |
| Geometrie (WKT) | Geografische Koordinate oder Fläche in technischem Kartenformat. |
| Teil von | Übergeordneter Ort, zum Beispiel ein Gebäude als Teil eines Areals. |
| Enthält | Untergeordnete Orte. |
| Historische Bemerkung / Kommentar | Zusatzwissen, Unsicherheiten oder redaktionelle Hinweise. |

## Beispiel {#sec:place-beispiel}

Ein Cliquenkeller kann als `Place` erfasst werden. Er kann einer Organisation zugeordnet, geografisch verortet und als Standort von Archivobjekten verwendet werden.
