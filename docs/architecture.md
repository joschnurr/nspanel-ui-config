# Architektur & Designentscheidungen

Dieses Dokument hält die grundlegenden Entscheidungen fest, damit sie nicht in späteren Sessions neu
hergeleitet werden müssen.

## Zielbild

Grafischer Konfigurator **innerhalb von Home Assistant** für das AppDaemon-basierte
nspanel-lovelace-ui-Backend (joBr99). Die Integration erzeugt die nspanel-YAML; das bestehende
Backend rendert unverändert weiter.

## Kern-Entscheidungen

1. **Config-Schicht statt Neuimplementierung.** Wir bauen das MQTT-/Nextion-Rendering *nicht* neu.
   Begründung: Upstream ist reif und groß (u. a. `icon_mapping.py` >200 kB, `pages.py`, `controller.py`).
   Wir liefern nur die Eingabe-Config und bleiben so kompatibel mit Upstream-Updates.
2. **UI als eigenes HA-Panel (Web-Editor).** Für Listen von Karten/Entities inkl. Icon-/Farb-Picker
   ist ein `config_flow`/Options-Dialog zu unhandlich. MVP registriert ein Sidebar-Panel (zunächst als
   iFrame auf statisch ausgelieferte Assets), das über eine authentifizierte HA-HTTP-View das
   Config-Modell lädt/speichert.
3. **Persistenz über HA-Store.** Das interne Config-Modell (JSON) wird via
   `homeassistant.helpers.storage.Store` unter der Domain gespeichert. Aus diesem Modell wird die
   nspanel-YAML generiert – das Modell ist die Quelle der Wahrheit, die YAML ein Artefakt.

## Transport (HA ➜ AppDaemon) <a id="transport"></a>

**Grundproblem:** Die Integration läuft in Home Assistant, die Zieldatei gehört AppDaemon. Ob beide
überhaupt denselben Pfad sehen, hängt an der Installationsart — und die unterscheidet sich stärker,
als es zunächst aussieht. **Allen Varianten gemeinsam ist nur das Prinzip: HA schreibt eine Datei,
AppDaemon bindet sie per `!include` ein.** Wo sie liegt und wie AppDaemon zum Neuladen bewegt wird,
ist von Fall zu Fall verschieden.

Der Einrichtungsdialog erkennt die Installationsart über Home Assistants `installation_type` und
belegt die Felder passend vor ([`install_profile.py`](../custom_components/nspanel_ui_config/install_profile.py)) —
überschreibbar, damit ungewöhnliche Aufbauten nicht ausgesperrt sind.

### Home Assistant OS / Supervised — AppDaemon als Add-on

**Kein Mount nötig.** Das AppDaemon-Add-on hat laut seiner `config.yaml` unter anderem `share:rw`
und `homeassistant_config:rw` — es sieht `/share` also unter demselben Pfad wie Home Assistant.
Genau deshalb ist `/share` hier der Ort der Wahl: HAs eigenes Konfigurationsverzeichnis sieht das
Add-on zwar auch, aber unter `/homeassistant` statt `/config`, was beim Einrichten zuverlässig in
die Irre führt.

- Ausgabepfad: `/share/nspanel/nspanel_config.yaml`
- In der `apps.yaml` des Add-ons: `config: !include /share/nspanel/nspanel_config.yaml`
- Reload: `restart_addon` (siehe unten)

### Home Assistant Container — zwei Docker-Container

Hier greift das ursprüngliche Problem: `vol-homeassistant:/config` und `vol-appdaemon:/conf` sind
getrennte, externe Volumes ohne gemeinsamen Pfad.

- Einmalig einen Host-Ordner in **beide** Container mounten, z. B.
  `- /srv/nspanel-shared:/nspanel-shared` (HA rw, AppDaemon ro).
- Ausgabepfad: `/nspanel-shared/nspanel_config.yaml`
- AppDaemons `apps.yaml` bindet ihn ein:
  ```yaml
  nspanel-1:
    module: nspanel
    class: NsPanelLovelaceUIManager
    config: !include /nspanel-shared/nspanel_config.yaml
  ```
- Reload: `touch_module` oder `restart_container`

### Home Assistant Core — venv/pip auf demselben Host

**Ebenfalls kein Mount nötig**, hier aus dem umgekehrten Grund: beide laufen im selben Dateisystem.
Der Ausgabepfad ist frei wählbar, HAs Konfigurationsordner liegt nahe. Reload: `touch_module` auf
AppDaemons App-Modul — hier ohne jede Zusatzeinrichtung möglich.

**Verworfene/aufgeschobene Alternativen:**

- *`vol-appdaemon` direkt in HA mounten* – koppelt HA hart an das AppDaemon-Volume; unnötig invasiv.
- *Config-Push via MQTT/AppDaemon-REST* – das Backend liest die Config aktuell nur beim App-Start,
  bräuchte also Backend-Änderungen. Später evtl. als „live apply" interessant, vorerst zu invasiv.

## Reload-Trigger

**Nachgemessen (AppDaemon 4.7.3):** Eine neu geschriebene Include-Datei löst **keinen** Reload aus —
nach dem Generieren erscheint keine einzige Zeile im AppDaemon-Log. Der Grund steht im Loader:
`_include_yaml` in `appdaemon/utils.py` liest die Datei beim Einlesen der `apps.yaml` nur inline mit
und nimmt ihren Pfad nicht in die Datei-Überwachung auf. Überwacht werden ausschließlich die
App-Config- und Python-Dateien im `apps/`-Verzeichnis.

Ohne Reload steht die neue YAML also auf der Platte, während das NSPanel weiter die alte
Konfiguration zeigt — ein Zustand, den der Editor nicht als Erfolg melden darf. Umgesetzt in
[`reload.py`](../custom_components/nspanel_ui_config/reload.py), Modus über die Integrations-Optionen:

| Modus | Wirkung | Voraussetzung | typisch für |
| --- | --- | --- | --- |
| `none` (Standard) | nichts; man lädt AppDaemon selbst neu | – | alle |
| `touch_module` | setzt die mtime einer von AppDaemon überwachten Datei neu (`apps/nspanel.py` oder `apps.yaml`) → AppDaemon lädt genau diese App neu | HA muss die Datei sehen | Core (dort ohne Weiteres), Container (mit zusätzlichem Mount von `apps/`) |
| `restart_container` | startet den AppDaemon-Container über die Docker-Engine-API neu | `/var/run/docker.sock` im HA-Container; grob, alle Apps starten neu | Container |
| `restart_addon` | startet das AppDaemon-Add-on über den Supervisor neu (`POST http://supervisor/addons/<slug>/restart`) | Supervisor vorhanden; grob, alle Apps starten neu | HA OS / Supervised |

Zu `restart_addon`: der Token steht bei diesen Installationsarten als `SUPERVISOR_TOKEN` ohnehin in
der Umgebung des HA-Containers, es ist also nichts einzurichten. Fehlt er, ist schlicht der falsche
Modus gewählt — die Fehlermeldung sagt das und verweist auf die Alternativen. Der Slug des
Community-Add-ons ist `a0d7b954_appdaemon`; nachzusehen ist er in der URL der Add-on-Seite
(`…/hassio/addon/<slug>/info`), da andere Add-on-Repositories eigene Präfixe vergeben.

Details, die leicht schiefgehen:

- Angetickt wird nur die **mtime** (`os.utime`), der Inhalt bleibt unberührt. Nicht existierende
  Dateien werden **nicht** angelegt — eine leere `nspanel.py` in `apps/` würde AppDaemon als kaputte
  App lesen.
- Ein fehlgeschlagener Reload macht das Generieren nicht rückgängig: die Datei ist schon geschrieben.
  Die API antwortet deshalb mit `200` und `reload: {ok: false, detail: …}`, und das Panel zeigt das
  als Fehler an — sichtbar, aber ohne den Eindruck, die Ausgabe sei misslungen.
- *Verworfen:* AppDaemons REST-API. Sie führt nur von Apps registrierte Endpunkte
  (`register_endpoint`), einen eingebauten „App neu laden"-Aufruf gibt es nicht.

## Template-Vorschau

Die Vorschau im Template-Editor ruft **HAs eigene Template-API** (`POST /api/template`) auf — nicht
eine eigene Jinja-Implementierung. Grund: das Backend rendert später mit derselben Engine
(`ha_api.render_template`, das über HA geht), also stimmt die Vorschau mit dem Ergebnis überein und
Fehlermeldungen sind die echten (`TemplateSyntaxError: …`, HTTP 400).

Nachgebildet werden muss dabei eine Eigenheit: bei `value` und `icon` rendert das Backend nur bis zum
**letzten** `}` und hängt den Rest wörtlich an (`rpartition('}')` in `pages.py`) — so entstehen
Einheiten wie `{{ … }} °C`. Ohne diese Nachbildung zeigte die Vorschau etwas anderes als das Panel.

Welche Felder überhaupt Templates sind, steht in `schema.py` (`TEMPLATE_FIELDS`) und ist an den
`render_template`-Aufrufen des Backends abgelesen, nicht geraten.

## Datenmodell (aus dem Upstream-Schema abgeleitet)

Basierend auf `luibackend/config.py` und docs.nspanel.pky.eu:

- **global:** `panelRecvTopic`, `panelSendTopic`, `model` (eu/us-l/us-p), `updateMode`,
  `sleepTimeout`, `sleepBrightness` (Zahl oder Zeit-Liste), `locale`, `timeFormat`, `dateFormat`, …
- **screensaver:** `type`, `doubleTapToUnlock`, `entities[]`, `statusIcon1/2`.
- **cards[]:** je Karte `type`, `title`, `key`, `entities[]` bzw. `entity`, plus typ-spezifische Felder.
- **hiddenCards[]**, **subpages**, **notifications**, **physicalButtons** (später).
- **entity:** `entity`, `name`, `icon`, `color`, `value`, `type`, `state`/`state_not`/`state_template`,
  `status`, `font`, `data{}`. `icon`/`color` können pro `on`/`off` gesetzt sein; `color`/`value` dürfen
  Jinja-Templates sein.

Kartentypen (Upstream): `cardEntities`, `cardGrid`, `cardGrid2`, `cardThermo`, `cardMedia`,
`cardAlarm`, `cardQR`, `cardPower`, `cardUnlock`, `cardChart`. Import und Generator behandeln
inzwischen **alle** davon; der visuelle Editor beginnt bei `cardEntities` + `cardGrid`.

Die maßgebliche, maschinenlesbare Fassung dieses Schemas steht in `schema.py` (Feldlisten je
Kartentyp, Backend-Defaults, Validierung) und ist direkt aus `luibackend/config.py` und den
Renderer-Zugriffen in `pages.py`/`controller.py` abgeleitet.

## Verlustfreier Round-Trip <a id="roundtrip"></a>

**Anforderung:** Ein Konfigurator, der beim ersten Speichern stillschweigend Einstellungen
wegwirft, ist unbrauchbar – besonders, weil das Backend mehr Keys kennt als diese Integration und
mit jeder Upstream-Version neue dazukommen.

**Lösung:** Jede Ebene des Modells (global / Karte / Entity) trennt in *benannte Felder* und ein
`extra`-Dict. Beim Import landet alles Unbekannte unverändert in `extra`, beim Generieren wird es
wieder eingemischt. `generator.build_config_dict` ist damit die exakte Umkehrung von
`importer.config_block_to_model`.

Konsequenzen, die dazugehören:

- **Backend-Defaults werden beim Import *nicht* eingemischt.** Sonst stünden nach dem ersten
  Speichern Dutzende Keys in der Datei, die nie jemand gesetzt hat. `GLOBAL_DEFAULTS` dient nur der
  Anzeige im Editor.
- **Kommentare und Formatierung der Quelldatei gehen verloren** – der Round-Trip ist auf
  Datenebene definiert, nicht auf Textebene. Die Zieldatei wird ohnehin maschinell erzeugt und
  trägt einen Warnhinweis im Kopf.
- **Einzige bewusste Abweichung:** ein config-Block ohne `cards` bekommt beim Generieren
  `cards: []`, weil das Backend sonst auf seine Demo-Karte zurückfällt.
- Die erzeugte YAML wird bewusst so formatiert, wie man sie von Hand schriebe (eingerückte Listen,
  einzeilige RGB-Werte, Jinja-Templates in doppelten Quotes statt mit verdoppelten Apostrophen) –
  sie landet in der Konfiguration des Nutzers und wird dort beim Debuggen gelesen.

Abgesichert durch `tests/test_roundtrip.py` gegen eine Fixture mit allen Kartentypen und den
typischen YAML-Fallen (`"on"`/`"off"` als Mapping-Keys, Jinja, RGB-Listen, `sleepBrightness` als
Zeitplan). Optional zusätzlich gegen die echte eigene Datei via `NSPANEL_REAL_APPS_YAML=<pfad>`.
Die Tests hängen nur an PyYAML, nicht an einer HA-Testumgebung – `conftest.py` registriert das
Integrationsverzeichnis als Paket, ohne `__init__.py` (und damit Home Assistant) zu laden.

## Sicherheits-/Betriebshinweise

- Keine Secrets ins Repo. Die HTTP-Views erfordern HA-Authentifizierung **und** Admin-Rechte – sie
  lesen und schreiben Konfigurationsdateien.
- Der *Import*pfad kommt aus dem Request und wird deshalb gegen HAs `allowlist_external_dirs`
  geprüft. Der *Ausgabe*pfad stammt aus den Entry-Optionen, ist also bereits Admin-gesetzt.
- Generierte YAML wird atomar geschrieben (Temp-Datei + `os.replace`), damit AppDaemon nie eine
  halb geschriebene Datei einliest.
