# Agent {#sec:agent}

`Agent` ist ein gemeinsamer Oberbegriff für handelnde Einheiten. Im Fasnachtsprojekt sind damit vor allem [`Person`](#sec:person) und [`Organisation`](#sec:organisation) gemeint.

Diese Seite ist etwas technischer als die anderen: In der täglichen Erfassung wird meistens direkt mit Personen oder Organisationen gearbeitet. Der Oberbegriff hilft dem System aber, Felder zu bauen, in denen entweder eine Person oder eine Organisation stehen darf.

## Warum dieser Oberbegriff nützlich ist {#sec:agent-oberbegriff}

Manchmal weiss man fachlich: "Hier muss jemand verantwortlich sein." Das kann eine einzelne Person sein, aber auch eine Clique, ein Museum oder ein Archiv.

Der Oberbegriff `Agent` erlaubt solche flexiblen Angaben, ohne für jedes Feld zwei getrennte Varianten bauen zu müssen.

## Typische Verwendung {#sec:agent-typische-verwendung}

- Bei einem [`ArchiveObject`](#sec:archive-object) kann die aktuelle Verwahrerin oder der aktuelle Verwahrer eine Person oder Organisation sein.
- Bei einem [`ArchiveMediaObject`](#sec:archive-media-object) kann der Urheber der Mediendatei ebenfalls eine Person oder Organisation sein.

## Beispiel {#sec:agent-beispiel}

Ein Archivobjekt wird von einer Privatperson verwahrt. Ein anderes liegt bei einem Museum. Beide können im gleichen Feld erfasst werden, weil beide als `Agent` verstanden werden.
