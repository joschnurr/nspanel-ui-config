# Einrichtung: bestehende `apps.yaml` umstellen

Diese Integration **ändert die `apps.yaml` nie**. Sie schreibt ausschließlich eine eigene Datei;
die `apps.yaml` bindet diese per `!include` ein. Diese Verbindung stellst du **einmalig von Hand**
her — danach bleibt die `apps.yaml` unverändert liegen.

## Was sich ändert

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

## Reihenfolge — und warum sie zählt

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

## Zurück zum vorherigen Stand

Falls etwas nicht passt: die `!include`-Zeile wieder durch den gesicherten `config:`-Block ersetzen
und AppDaemon neu starten. Die Integration kann dabei bleiben — sie schreibt nur ihre eigene Datei
und stört nicht, solange niemand sie einbindet.

Die erzeugte Datei selbst hat außerdem eine eigene Historie: vor jedem Überschreiben wandert der
bisherige Stand nach `backups/` daneben und lässt sich im Editor unter *Sicherungen…* zurückholen.
