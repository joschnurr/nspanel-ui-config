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
