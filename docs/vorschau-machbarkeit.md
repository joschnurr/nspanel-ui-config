# Vorschau bzw. Simulation des Panels — Machbarkeit

*Stand: 2026-07-26. Untersuchung, noch keine Umsetzung.*

Die Frage: Kann der Editor zeigen, **wie die konfigurierte Karte auf dem Panel aussehen wird** —
und lässt sich das Ganze vielleicht sogar in einem NSPanel-Emulator live simulieren?

Kurzfassung: Ein **Emulator ist für diesen Zweck eine Sackgasse**, eine **eigene Vorschau im Panel
ist gut machbar**, weil die nötigen Layout-Daten öffentlich und exakt vorliegen und die halbe
Werkzeugkette im Editor bereits existiert.

## Warum es überhaupt lohnt

Die Anzeigekapazität (siehe README) beantwortet nur, *ob* etwas passt. Offen bleibt, *wie* es
aussieht: Reihenfolge, Farbwirkung auf einem dunklen 480×320-Display mit geringem Kontrast, ob ein
Name abgeschnitten wird, ob ein Icon-Template das Richtige liefert. Heute lässt sich das nur am
echten Panel prüfen — Konfiguration schreiben, generieren, AppDaemon neu laden, hinschauen.

## Option A — Nextion-Editor-Emulation (Upstream-Wiki)

Das Upstream-Projekt beschreibt eine Emulation über den **Nextion Editor** von Itead: `nspanel.HMI`
öffnen, Debug-Modus starten, den COM-Port anbinden.

**Für uns nicht nutzbar**, und zwar nicht wegen des Aufwands, sondern grundsätzlich:

- Der Nextion Editor ist **Windows-Software**; die Gbox ist ein Linux-Docker-Host.
- Der „Emulator" braucht trotz seines Namens **echte Hardware** — eine ESP32-Platine mit Tasmota und
  angepasstem Berry-Treiber, per USB am PC. Er ersetzt nur das *Display*, nicht das Gerät.
- Er lässt sich nicht in ein HA-Panel einbetten. Ein Konfigurator, dessen Vorschau einen
  Windows-PC mit angestecktem Mikrocontroller voraussetzt, hilft niemandem.

Als **Entwicklerwerkzeug** für Layout-Fragen am HMI selbst bleibt er sinnvoll — für dieses Projekt
ist er kein Weg.

## Option B — Eigene Vorschau im Editor *(empfohlen)*

Ein 480×320-Nachbau direkt im Panel, gespeist aus dem Modell, das gerade bearbeitet wird.

**Die Layout-Daten liegen exakt vor.** Das Upstream-Repo enthält Textdumps aller HMI-Seiten
(`HMI/n2t-out-visual/*.txt`, für die US-Modelle unter `HMI/US/*/n2t-out-visual/`). Jede
Nextion-Komponente steht dort mit allem, was zum Zeichnen nötig ist:

```
Text tEntity1
    Attributes
        x coordinate        : 6
        y coordinate        : 155
        Width               : 140
        Height              : 30
        Back. Color         : 6371
        Font Color          : 65535
        Horizontal Alignment: center
```

Daraus ließe sich — analog zu `tools/extract_icon_names.py` — ein `tools/extract_layouts.py` bauen,
das ein `www/panel/layouts.json` erzeugt: je Seite und Modell die Slots mit Position, Größe, Farbe
und Ausrichtung. Damit wird die Vorschau **layout-treu statt nachempfunden**, und sie bleibt bei
Upstream-Updates durch erneutes Ausführen aktuell.

**Die halbe Werkzeugkette steht schon:**

| gebraucht | Stand |
| --- | --- |
| Icon-Namen des Backends | ✅ `www/panel/icon-names.js` (6896 Namen) |
| Icons darstellen | ✅ `<ha-icon>`, im Editor bereits als Vorschau im Einsatz |
| Farben lesen (`[r,g,b]`, `{on,off}`, Template) | ✅ `colorShape`, `parseTemplateColor` |
| Templates auswerten | ✅ über HAs `POST /api/template`, inkl. der Suffix-Eigenheit |
| Anzahl und Anordnung der Plätze | ✅ `CARD_CAPACITY` + `CAPACITY_LAYOUT_NOTES` |
| Pixelgenaue Slot-Geometrie | ⬜ aus den HMI-Dumps zu erzeugen |
| Zeichenschicht (SVG/Canvas im Panel) | ⬜ neu |

**Sinnvoll in zwei Stufen:**

1. **Schematische Vorschau** — richtige Plätze, richtige Reihenfolge, echte Icons, echte Farben,
   echte gerenderte Werte; Geometrie grob nachgebaut. Beantwortet bereits die meisten Fragen
   („passt das, wirkt die Farbe, stimmt die Reihenfolge?") und kostet am wenigsten.
2. **Layout-treue Vorschau** — Geometrie aus `layouts.json`, Seiten und Modelle vollständig.

**Was eine solche Vorschau prinzipiell nicht leisten kann:** exakte Schriftdarstellung. Das Nextion
nutzt eingebackene Bitmap-Fonts und einen eigenen Icon-Font; ob ein Name auf dem echten Gerät genau
an derselben Stelle umbricht, bleibt eine Näherung. Für die Frage „sieht das richtig aus?" spielt
das keine Rolle, für „passt dieser lange Name in die Kachel?" ist es eine Aussage mit Rest­unschärfe.

## Option C — Das echte Backend als Datenquelle

Weiter gedacht: Der Test-Stack (`stacks/homeassistant-test` mit eigenem AppDaemon und eigenem
MQTT-Broker) betreibt bereits das **echte luibackend**. Es erzeugt die realen `entityUpd~…`-Strings,
die sonst zum Display gehen. Greift man die über MQTT ab und rendert sie, entsteht eine Vorschau, in
der **keine Backend-Logik nachgebaut ist** — Icon-IDs, Farbumrechnung nach RGB565 und Sonderfälle
kämen dann vom Original.

Das ist die genaueste Variante, setzt aber Option B voraus (die Zeichenschicht wird so oder so
gebraucht) und zusätzlich eine MQTT-Anbindung. Sinnvoll als späterer Ausbau, nicht als Einstieg.

Das Protokoll ist dafür vollständig dokumentiert: `HMI/README.md` im Upstream-Repo beschreibt jeden
Parameter jeder Seite.

**Sicherheitshinweis, der hier zählt:** die generierte Konfiguration trägt die echten MQTT-Topics
(`NSPanel_1/cmnd/CustomSend`). Ein Test-AppDaemon am produktiven Broker würde damit das echte Panel
fernsteuern. Der eigene Broker im Test-Stack ist deshalb eine Sicherheitsgrenze, keine Bequemlichkeit.

## Empfehlung

Option B, Stufe 1. Sie liefert früh sichtbaren Nutzen, kommt ohne zusätzliche Infrastruktur aus und
ist die Grundlage für alles Weitere. Option C bleibt als Ausbaustufe offen, Option A scheidet aus.
