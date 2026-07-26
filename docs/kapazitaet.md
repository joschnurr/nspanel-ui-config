# Anzeigekapazität: wie viele Entities passen auf eine Karte?

**Der stille Fehler schlechthin.** Weder das Backend noch dieser Generator kürzen die
`entities`-Liste. Zu viele Einträge werden mitgesendet und vom Display einfach ignoriert: die YAML
ist gültig, das Log schweigt, und auf dem Panel fehlt der letzte Eintrag. Eine `cardEntities` mit
fünf Entities zeigt auf einem EU-Panel nur vier.

Der Editor zeigt deshalb an jeder Entity-Liste „*n* von *m* Plätzen", markiert überzählige Einträge
als **nicht sichtbar** und erklärt, wie sich die Plätze auf der Karte verteilen. Die Validierung
meldet es zusätzlich als Befund.

## Die Zahlen

| Karte | eu | us-l | us-p |
| --- | --- | --- | --- |
| `cardEntities` | 4 | 4 | 6 |
| `cardGrid` | 6 | 6 | 6 |
| `cardGrid2` | 8 | 8 | 9 |
| `cardQR` | 2 | 2 | 2 |
| `cardMedia` (untere Symbolreihe) | 6 | 6 | 6 |
| `cardPower` (2 Mitte + 6 außen) | 8 | 8 | 8 |
| `screensaver` | 6 | 6 | 6 |
| `screensaver2` | 15 | 15 | 15 |

`cardThermo`, `cardAlarm`, `cardChart` und `cardUnlock` werten keine Entity-Liste aus – sie zeigen
die eine Entity, die direkt auf der Karte steht.

## Zwei Feinheiten

**`cardGrid` wechselt von selbst.** Ab dem 7. Eintrag stellt das Backend die Karte intern auf
`cardGrid2` um (`pages.py`). Eine Warnung ab 7 wäre also falsch – erst ab 9 (eu) fehlt wirklich
etwas. Das Layout ändert sich dabei allerdings sichtbar: kleinere Kacheln, andere Anordnung.

**Beim `screensaver` schaltet die 6. Entity das Layout um.** Die Aufteilung dort:

| Karte | Aufteilung der Plätze |
| --- | --- |
| `screensaver` | 1. = großes Hauptsymbol · 2.–5. = die vier Vorhersagespalten · eine 6. aktiviert das alternative Layout (siehe unten) |
| `screensaver2` | 1. = Hauptbereich · 2.–4. = Zeile mit Symbol und Wert · 5.–10. = Kacheln mit Symbol, Name und Wert · 11.–15. = reine Symbole |

**Das alternative Layout des `screensaver` verdrängt quer einen Eintrag.** Sobald eine 6. Entity
gesetzt ist, trägt der Hauptbereich zwei Textblöcke (1. und 6. Entity). Was mit den
Vorhersagespalten passiert, hängt an der Ausrichtung – im HMI steht die Verschiebung hinter
`if(p0.w!=320)`:

| Ausrichtung | Vorhersagespalten | Folge |
| --- | --- | --- |
| quer (`eu`, `us-l`) | die erste wird ausgeblendet, die übrigen rücken nach rechts (`tForecast4 = tForecast3` …) | die **5. Entity verliert ihren Platz** – konfiguriert, gesendet, nirgends sichtbar |
| hochkant (`us-p`) | bleiben alle vier stehen (die Textblöcke stehen nebeneinander) | alle sechs sichtbar |

Der Editor meldet das als Befund und zeigt es in der Vorschau: der verdrängte Eintrag wird dort gar
nicht erst gezeichnet.

Bei `cardPower` stehen die **ersten beiden** Entities in der Mitte, die restlichen sechs außen
herum; `entity: delete` hält einen Außenplatz frei. Bei `cardMedia` hängt das Backend die
Lautsprecherauswahl automatisch an die Symbolreihe an – mit sechs eigenen Einträgen verdrängt man
sie.

## Woher die Zahlen stammen

Nicht aus der Dokumentation des Backends – die schweigt dazu –, sondern aus der Display-Firmware
selbst. Im Upstream-Repo liegen Textdumps aller HMI-Seiten, in denen jede Nextion-Komponente mit
Position und Größe aufgeführt ist:

```
HMI/n2t-out-visual/<seite>.txt                 # Modell eu
HMI/US/landscape/n2t-out-visual/<seite>.txt    # Modell us-l
HMI/US/portrait/n2t-out-visual/<seite>.txt     # Modell us-p
```

Die durchnummerierten Slot-Komponenten (`tEntity1…`, `bEntity1…`, `t0Icon…`) ergeben die Kapazität.

Die beiden Screensaver sind der Sonderfall: sie haben keine gleichnamig durchnummerierte Reihe,
sondern verteilen den `weatherUpdate~`-String in 6er-Blöcken auf verschiedene Bausteine. Ihre Zahlen
stammen aus dem Nextion-Codegenerator `HMI/code_gen/pages/screensaver{,2}.py`.

**Nachprüfbar** mit einer lokalen Kopie des Upstream-Repos:

```bash
python3 tools/check_card_capacity.py /pfad/zu/nspanel-lovelace-ui
```

Das Skript zählt die Slot-Komponenten je Seite und Modell nach und vergleicht sie mit `schema.py`.
Nach einem Upstream-Update erneut laufen lassen – ein neues Display-Layout ändert genau hier die
Wahrheit.

## Wirkungslose Keys

Manche Keys sehen plausibel aus, werden vom Backend aber nirgends gelesen. `unit:` etwa: die Einheit
kommt aus dem Home-Assistant-Attribut `unit_of_measurement`, für eigenen Text ist `value` zuständig:

```yaml
- entity: sensor.pv_ertrag
  value: "{{ states('sensor.pv_ertrag') }} kWh"
```

Die Validierung weist darauf hin und nennt die betroffenen Zeilen, **löscht aber nichts** – der
verlustfreie Round-Trip gilt auch für Wirkungsloses.
