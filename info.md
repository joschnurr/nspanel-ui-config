# NSPanel UI Config

**Das NSPanel in Home Assistant zusammenklicken – statt `apps.yaml` von Hand zu pflegen.**

Ein visueller Editor für [nspanel-lovelace-ui](https://github.com/joBr99/nspanel-lovelace-ui) (das
AppDaemon-Backend von joBr99): Karten anlegen, Entities sortieren, Icons und Farben wählen,
Templates mit Live-Vorschau schreiben. Heraus kommt gültige nspanel-YAML für das bestehende
Backend – das Rendering selbst bleibt unverändert.

Der Editor zeigt dabei, was der YAML nicht anzusehen ist:

- **Anzeigekapazität** – auf eine `cardEntities` passen vier Einträge; ein fünfter steht in der
  Datei und erscheint nie auf dem Display. Der Editor markiert ihn.
- **Icon-Namen** – geprüft gegen die 6896 Namen, die das Backend wirklich kennt.
- **Jedes Feld erklärt** – was es bewirkt und welche Werte es annehmen darf.

**Sicher gegen Datenverlust:** Was der Editor noch nicht kennt, bleibt beim Bearbeiten unverändert
erhalten. Und vor jedem Überschreiben wird der bisherige Stand gesichert und lässt sich aus dem
Editor zurückholen.

> Frühe Entwicklungsphase. Voraussetzung ist ein laufendes nspanel-lovelace-ui-Setup auf AppDaemon
> sowie eine gemeinsame Datei zwischen HA- und AppDaemon-Container (einmaliger Bind-Mount) –
> Einrichtung siehe README.
