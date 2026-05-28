# NewsArticle {#sec:news-article}

`NewsArticle` ist die allgemeine technische Grundlage für [`NewsItem`](#sec:news-item). In der normalen Erfassung wird nicht direkt ein `NewsArticle` angelegt, sondern ein News-Eintrag des Fasnachtsprojekts.

## Warum diese Grundlage existiert {#sec:news-article-grundlage}

Das Fasnachtsprojekt nutzt Begriffe aus verbreiteten Vokabularen wie schema.org. `NewsArticle` ist dort der etablierte Begriff für eine Nachricht oder einen redaktionellen Nachrichtenartikel.

Indem [`NewsItem`](#sec:news-item) auf dieser Grundlage aufbaut, bleibt das Modell anschlussfähig: Andere Systeme können besser verstehen, dass es sich um eine Meldung oder Nachricht handelt.

## Praktische Bedeutung {#sec:news-article-praktische-bedeutung}

Für Redaktorinnen und Redaktoren ist vor allem [`NewsItem`](#sec:news-item) wichtig. Dort stehen die tatsächlich verwendeten Felder wie Titel, Inhalt, Startdatum und Enddatum.
