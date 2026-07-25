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

**Problem:** HA-Container nutzt `vol-homeassistant:/config`, AppDaemon `vol-appdaemon:/conf` – zwei
getrennte, externe Docker-Volumes ohne gemeinsamen Pfad. Eine HA-Integration kann die AppDaemon-YAML
also nicht direkt schreiben.

**Gewählter Weg (MVP): gemeinsame Include-Datei per Bind-Mount.**

- Einmalig einen Host-Ordner in **beide** Container mounten, z. B.
  `- /srv/nspanel-shared:/nspanel-shared` (HA rw, AppDaemon ro).
- Die Integration schreibt `nspanel_config.yaml` in diesen Ordner.
- AppDaemons `apps.yaml` bindet ihn ein:
  ```yaml
  nspanel-1:
    module: nspanel
    class: NsPanelLovelaceUIManager
    config: !include /nspanel-shared/nspanel_config.yaml
  ```
- Der Ausgabepfad ist in der Integration konfigurierbar; der Bind-Mount ist ein einmaliger,
  dokumentierter Setup-Schritt.

**Verworfene/aufgeschobene Alternativen:**

- *`vol-appdaemon` direkt in HA mounten* – koppelt HA hart an das AppDaemon-Volume; unnötig invasiv.
- *Config-Push via MQTT/AppDaemon-REST* – das Backend liest die Config aktuell nur beim App-Start,
  bräuchte also Backend-Änderungen. Später evtl. als „live apply" interessant, vorerst zu invasiv.

## Reload-Trigger

AppDaemon lädt bei geändertem *Include* nicht automatisch neu (nur das Top-Level-App-Modul wird
hot-reloaded). Nach dem Schreiben muss die App neu geladen werden. Optionen (konfigurierbar):

- AppDaemon-Admin/REST-API zum App-Reload aufrufen (bevorzugt, feingranular).
- `nspanel.py` „anticken" (mtime), damit AppDaemon die App neu lädt.
- AppDaemon-Container neu starten – HA hat `docker.sock` gemountet, also technisch möglich, aber
  grob (volles Neuladen). Als Fallback.

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

Kartentypen (Upstream): `cardEntities`, `cardGrid`, `cardThermo`, `cardMedia`, `cardAlarm`,
`cardQR`, `cardPower`, `cardUnlock`, u. a. – MVP zuerst `cardEntities` + `cardGrid`.

## Sicherheits-/Betriebshinweise

- Keine Secrets ins Repo. Panel-HTTP-Views erfordern HA-Authentifizierung.
- Generierte YAML wird nur in den konfigurierten (gemounteten) Pfad geschrieben; Pfad validieren.
