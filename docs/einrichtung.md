# Einrichtung

Diese Integration **ändert die `apps.yaml` nie**. Sie schreibt ausschließlich eine eigene Datei;
die `apps.yaml` bindet diese per `!include` ein. Diese Verbindung stellst du **einmalig von Hand**
her — danach bleibt die `apps.yaml` unverändert liegen.

Welcher Weg für dich gilt, hängt davon ab, wo du stehst:

| Ausgangslage | Weg |
| --- | --- |
| Du hast bereits eine `apps.yaml` mit deiner Panel-Konfiguration | [Bestehende Konfiguration umstellen](#bestehende-konfiguration-umstellen) |
| Du fängst neu an — AppDaemon läuft, das Panel ist noch leer | [Neu anfangen](#neu-anfangen) |

Danach gilt für beide dasselbe: [Reload einrichten](#reload-einrichten) und
[prüfen, ob es wirkt](#prüfen-ob-es-wirkt).

## Wo die Datei liegen muss

Der Pfad im `!include` ist der **aus Sicht von AppDaemon**. Der Ausgabepfad in den
Integrations-Optionen ist der **aus Sicht von Home Assistant**. Je nach Installationsart sind das
derselbe oder zwei verschiedene Pfade auf dieselbe Datei:

| Installationsart | Ausgabepfad (Home Assistant) | `!include` (AppDaemon) | einzurichten |
| --- | --- | --- | --- |
| **HA OS / Supervised** | `/share/nspanel/nspanel_config.yaml` | derselbe Pfad | nichts – das Add-on sieht `/share` bereits |
| **HA Container** | `/nspanel-shared/nspanel_config.yaml` | derselbe Pfad | einmaliger Bind-Mount in beide Container |
| **HA Core** (venv) | frei wählbar, z. B. `/config/nspanel_config.yaml` | derselbe Pfad | nichts – gleiches Dateisystem |

### Bind-Mount für die Container-Variante

Einen Host-Ordner in beide Container mounten — Home Assistant schreibend, AppDaemon lesend:

```yaml
  homeassistant:
    volumes:
      - vol-homeassistant:/config
      - /srv/nspanel-shared:/nspanel-shared        # rw: hier wird geschrieben

  appdaemon:
    volumes:
      - vol-appdaemon:/conf
      - /srv/nspanel-shared:/nspanel-shared:ro     # ro: hier wird nur gelesen
```

Beide Container danach neu erstellen (`docker compose up -d`), damit die Mounts greifen.

## Neu anfangen

Wer noch keine Konfiguration hat, braucht keine von Hand zu schreiben.

1. **Bind-Mount einrichten** (nur Container-Variante, siehe [unten](#wo-die-datei-liegen-muss)) und
   die Container neu erstellen.
2. **Integration einrichten**: *Einstellungen → Geräte & Dienste → Integration hinzufügen →
   „NSPanel UI Config"*. Ausgabepfad und Reload-Weg sind zur erkannten Installationsart bereits
   vorbelegt; das Importfeld bleibt leer.
3. **Beispiel laden** (empfohlen): Im Editor *Importieren…* öffnen und den Inhalt von
   [`beispiel-apps.yaml`](beispiel-apps.yaml) in das YAML-Feld einfügen. Damit stehen eine
   Ruheanzeige, drei Karten und eine Unterseite als Gerüst da. Alle Entities darin sind erfunden —
   der Editor markiert sie mit ⚠, und genau diese Stellen ersetzt du durch deine eigenen.
   *Ohne Beispiel* geht es auch: Der Editor startet dann mit einem leeren Gerüst, und du legst
   Karten einzeln an.
4. **Karten anpassen**, speichern, **„YAML erzeugen"**. Jetzt liegt die Datei am Ausgabepfad.
5. **`apps.yaml` anlegen** (oder um die App ergänzen) — mit der `!include`-Zeile aus dem
   [nächsten Abschnitt](#was-sich-ändert), passend zu deinem Ausgabepfad.
6. **AppDaemon neu starten.**

## Bestehende Konfiguration umstellen

### Was sich ändert

Die Struktur der `apps.yaml` bleibt, nur der Inhalt von `config:` zieht um:

**Vorher** — alles inline:

```yaml
nspanel-1:
  module: nspanel
  class: NsPanelLovelaceUIManager
  config:
    panelRecvTopic: "NSPanel_1/tele/RESULT"
    panelSendTopic: "NSPanel_1/cmnd/CustomSend"
    model: eu
    screensaver:
      type: screensaver2
      entities:
        - entity: weather.zuhause
    cards:
      - type: cardEntities
        title: Garage
        entities:
          - entity: switch.garagentor
      # … und so weiter, oft ein paar hundert Zeilen
```

**Nachher** — dieselbe App, der Block kommt aus der generierten Datei:

```yaml
nspanel-1:
  module: nspanel
  class: NsPanelLovelaceUIManager
  config: !include /nspanel-shared/nspanel_config.yaml
```

`module`, `class` und der App-Name bleiben unangetastet — sie gehören zu AppDaemon, nicht zur
Panel-Konfiguration. Nur der `config:`-Block wird ersetzt.

### Reihenfolge — und warum sie zählt

**Erst die Datei erzeugen, dann die `apps.yaml` umstellen.** Zeigt der `!include` auf eine Datei,
die es noch nicht gibt, startet AppDaemon nicht mehr sauber.

1. **`apps.yaml` sichern.** Eine Kopie danebenlegen (`apps.yaml.vor-nspanel-ui`) — die Umstellung
   ist ein Handgriff, das Zurück soll genauso einer sein.
2. **Bind-Mount einrichten** (nur Container-Variante, siehe oben) und die Container neu erstellen.
3. **Integration einrichten**, dabei den Pfad aus der Tabelle eintragen. Beim Import die bestehende
   `apps.yaml` angeben — der Editor übernimmt damit deine komplette Konfiguration.
4. **Im Editor auf „YAML erzeugen"** klicken. Jetzt liegt die Datei am Ausgabepfad.
5. **Vergleichen** (optional, aber beruhigend): der Inhalt der erzeugten Datei sollte deinem
   bisherigen `config:`-Block entsprechen — bis auf Kommentare, Einrückung und die Reihenfolge der
   Schlüssel, die maschinell vereinheitlicht werden.
6. **Jetzt erst** in der `apps.yaml` den `config:`-Block durch die `!include`-Zeile ersetzen.
7. **AppDaemon neu starten** und ins Log schauen: es muss `Started` melden, und das Panel zeigt
   weiter dieselben Karten wie vorher.

Ab hier läuft alles über den Editor: Änderungen speichern, „YAML erzeugen", fertig.

## Reload einrichten

**AppDaemon bemerkt eine geänderte `!include`-Datei nicht von selbst** (nachgemessen an 4.7.3: sein
YAML-Loader liest sie nur inline mit und überwacht sie nicht). Ohne Reload steht die neue Datei auf
der Platte, während das Panel weiter die alte Konfiguration zeigt. Der passende Weg steht in den
Integrations-Optionen:

| Installationsart | empfohlener Modus | Voraussetzung |
| --- | --- | --- |
| HA OS / Supervised | `restart_addon` | keine – der Supervisor-Token ist ohnehin da |
| HA Container | `restart_container` | `/var/run/docker.sock` in Home Assistant gemountet |
| HA Container (feiner) | `touch_module` | zusätzlich AppDaemons `apps/` in Home Assistant gemountet |
| HA Core | `touch_module` | keine – gleiches Dateisystem |

`touch_module` lädt nur die eine betroffene App neu statt AppDaemon komplett; dafür muss Home
Assistant die angetickte Datei sehen (`reload_touch_path`, z. B. `/appdaemon-apps/apps.yaml` – **die apps.yaml, nicht das App-Modul**).

> **`touch_module` braucht `production_mode: false`.** Steht in AppDaemons `appdaemon.yaml`
> `production_mode: true`, prüft es überhaupt nicht mehr auf geänderte Dateien — das Anticken bleibt
> dann folgenlos, **ohne jede Fehlermeldung**: Die YAML wird geschrieben, der Reload meldet Erfolg,
> und das Backend läuft weiter mit seinem alten Stand. Man merkt es nur daran, dass sich am Panel
> nichts ändert. Wer `production_mode` braucht, nimmt `restart_container` bzw. `restart_addon` — ein
> Neustart liest ohnehin alles neu.

**Zur Auswahl steht nur, was auf der erkannten Installationsart laufen kann.** `restart_addon`
spricht die Supervisor-API an, die es allein unter HA OS und Supervised gibt; `restart_container`
braucht den Docker-Socket im Home-Assistant-Container, den weder die Add-on-Welt noch eine
venv-Installation hat. Die Felder der übrigen Wege blendet der Dialog gleich mit aus — eine Angabe,
die niemand ausliest, ist schlimmer als keine. Ein bereits gespeicherter Modus bleibt wählbar, auch
wenn er nicht mehr passt (nach einem Umzug), sonst ließe sich der Dialog nicht einmal öffnen.

## Prüfen, ob es wirkt

Der Reload ist die Stelle, an der es lautlos schiefgehen kann: Die Datei wird geschrieben, alles
meldet Erfolg, und am Panel bleibt trotzdem der alte Stand stehen. Die Probe dauert eine Minute:

1. **Etwas Sichtbares ändern** — den Titel einer Karte, zum Beispiel auf `Test 1`.
2. **Speichern**, dann **„YAML erzeugen"**.
3. Zehn Sekunden warten (AppDaemon prüft im Sekundentakt).
4. Auf der Karte in die **Live-Ansicht** wechseln und **„Karte am Gerät aufrufen"** drücken.

Steht der neue Titel am Gerät und in der Live-Ansicht, funktioniert die ganze Kette. Sonst hilft die
Einordnung:

| Beobachtung | wo es klemmt |
| --- | --- |
| Neuer Titel erscheint | alles in Ordnung |
| Alter Titel, nach einem AppDaemon-Neustart aber der neue | der Reload greift nicht — `production_mode`, falscher `reload_touch_path`, oder auf `restart_container` wechseln |
| Alter Titel auch nach dem Neustart | die erzeugte Datei ist nicht die, die AppDaemon einbindet — Pfade im `!include` und in den Optionen vergleichen |
| Live-Ansicht bleibt leer | das Panel hat diese Karte noch nie gezeigt; der Aufruf-Knopf holt sie |

**Warum der Kartenaufruf dazugehört:** Die Live-Ansicht zeigt den *Mitschnitt* — also das, was das
Backend zuletzt wirklich ans Display geschickt hat. Eine Karte, die seit der Änderung nicht
aufgerufen wurde, steht dort zwangsläufig im alten Stand, selbst wenn alles richtig läuft. Die
Vorschau *aus der Konfiguration* zeigt dagegen sofort den neuen Titel — sie zeichnet aus dem
Editor-Modell und sagt über das Gerät nichts aus.

## Zurück zum vorherigen Stand

Falls etwas nicht passt: die `!include`-Zeile wieder durch den gesicherten `config:`-Block ersetzen
und AppDaemon neu starten. Die Integration kann dabei bleiben — sie schreibt nur ihre eigene Datei
und stört nicht, solange niemand sie einbindet.

Die erzeugte Datei selbst hat außerdem eine eigene Historie: vor jedem Überschreiben wandert der
bisherige Stand nach `backups/` daneben und lässt sich im Editor unter *Sicherungen…* zurückholen.
