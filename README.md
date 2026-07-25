<img src="custom_components/nspanel_ui_config/brand/icon.png" alt="" width="120" align="right">

# NSPanel UI Config

> **Frühe Entwicklungsphase (v0.5.x).** Dieses Repo ist zunächst **privat**. Ziel ist eine
> öffentliche Veröffentlichung, sobald ein brauchbarer Funktionsumfang steht.

Eine **Home-Assistant-Integration (HACS)**, mit der sich die
[nspanel-lovelace-ui](https://github.com/joBr99/nspanel-lovelace-ui)-Konfiguration (AppDaemon-Backend
von joBr99) **visuell in Home Assistant** zusammenklicken lässt – statt die `apps.yaml` von Hand zu
pflegen.

## Motivation

nspanel-lovelace-ui ist bewusst **rein YAML-basiert** – „no need to code, no UI". Für ein einzelnes
Panel ist das handhabbar, wird aber mit vielen Karten, Entities, Icon- und Farb-Templates schnell
unübersichtlich und fehleranfällig. Dieses Projekt schließt genau diese Lücke: eine grafische
Oberfläche in HA, die daraus **gültige nspanel-YAML** erzeugt und dem bestehenden AppDaemon-Backend
zur Verfügung stellt.

## Ansatz (bewusst *keine* Neuimplementierung des Renderings)

Diese Integration ist eine reine **Konfigurations-Schicht**. Das ausgereifte Rendering-Backend von
joBr99 (MQTT-Protokoll ans Nextion-Display, alle Kartentypen) bleibt **unverändert** und rendert
weiter. Wir erzeugen lediglich seine Eingabe-Konfiguration.

```
┌─────────────────────────┐      schreibt       ┌──────────────────────────┐   liest    ┌───────────┐
│  Home Assistant          │  ─────────────────▶ │  gemeinsame Include-Datei │ ─────────▶ │ AppDaemon │ ─MQTT─▶ NSPanel
│  (diese Integration)     │  nspanel_config.yaml │  (Bind-Mount)            │            │ luibackend │
│  · Panel / Web-Editor    │                     └──────────────────────────┘            └───────────┘
│  · Import bestehender     │                                    ▲                              │
│    apps.yaml (Vorlage)    │  ──────── Reload-Trigger ──────────┼──────────────────────────────┘
└─────────────────────────┘        (AppDaemon-App neu laden)     │
```

- **Import:** eine vorhandene `apps.yaml` wird beim Einrichten eingelesen und dient als Startpunkt.
- **Editieren:** im HA-Panel (visueller Editor) – globale Settings, Screensaver, StatusIcons, Karten,
  Entities, Icons, Farben (inkl. Templates).
- **Ausgeben:** die Integration schreibt eine `nspanel_config.yaml`, die AppDaemons `apps.yaml` per
  `!include` einbindet.
- **Übernehmen:** AppDaemon lädt die App neu (Trigger konfigurierbar), das Panel aktualisiert sich.

Warum kein natives HA-Rendering ohne AppDaemon? Das würde ein sehr großes, reifes Projekt
duplizieren (Protokoll, alle Kartentypen, Icon-Mapping mit >200 kB Daten). Der Config-Schicht-Ansatz
liefert früh Nutzen und bleibt kompatibel mit Updates des Upstream-Backends.

## Voraussetzungen

- Home Assistant (2024.4+), Zugriff über HACS oder manuelle Installation.
- Ein laufendes **nspanel-lovelace-ui**-Setup auf AppDaemon.
- Eine **gemeinsame Datei** zwischen HA- und AppDaemon-Container (einmaliger Bind-Mount, siehe
  [docs/architecture.md](docs/architecture.md#transport)). HA und AppDaemon laufen in getrennten
  Docker-Volumes und teilen sich sonst keinen Pfad.

## Installation (früh, manuell)

1. `custom_components/nspanel_ui_config/` nach `<config>/custom_components/` kopieren
   (oder das Repo später als benutzerdefiniertes HACS-Repository hinzufügen).
2. Home Assistant neu starten.
3. *Einstellungen → Geräte & Dienste → Integration hinzufügen → „NSPanel UI Config"*.
4. Im Setup-Dialog Pfad der Include-Datei und den AppDaemon-Reload-Weg angeben; optional bestehende
   `apps.yaml` importieren.

## Status / Roadmap

| Bereich | Status |
| --- | --- |
| Repo-/HACS-Skelett, Panel-Registrierung, Config-Flow | ✅ v0.1 |
| Import bestehender `apps.yaml` → internes Modell | ✅ v0.2 |
| YAML-Generator inkl. aller Kartentypen des Backends | ✅ v0.2 |
| Verlustfreier Round-Trip (Import → Modell → YAML) | ✅ v0.2, testabgedeckt |
| Visueller Editor als Custom-Panel (Karten-/Entity-Listen, Formulare aus dem Schema) | ✅ v0.3 |
| AppDaemon-Reload-Automatik (`touch_module` / `restart_container`) | ✅ v0.4 |
| Icon/Brand-Assets (HACS + HA-Integrationskarte) | ✅ v0.4 |
| Icon-Picker (geprüft gegen das Backend-Mapping) und Farbwähler | ✅ v0.5 |
| Template-Editor (Jinja für color/value) | ⬜ geplant |

Details und Designentscheidungen: **[docs/architecture.md](docs/architecture.md)**.

## Verlustfreier Round-Trip

Der Import zerlegt die Konfiguration in benannte Felder; alles, was die Integration (noch) nicht
kennt, bleibt unverändert in einem `extra`-Bereich liegen und wird beim Generieren wieder
herausgeschrieben. **Keine Einstellung geht verloren, nur weil dieser Konfigurator sie nicht
versteht** – auch nicht bei Keys aus einer neueren Backend-Version.

Belegt durch [`tests/test_roundtrip.py`](tests/test_roundtrip.py) gegen eine Fixture, die alle
Kartentypen und die üblichen YAML-Fallen abdeckt (`"on"`/`"off"` als Mapping-Keys, Jinja-Templates,
RGB-Listen, `sleepBrightness` als Zeitplan). Gegen die eigene Konfiguration testen:

```bash
pip install pyyaml pytest
NSPANEL_REAL_APPS_YAML=/pfad/zu/appdaemon/apps/apps.yaml pytest
```

Einzige bewusste Abweichung: ein config-Block ganz ohne `cards` bekommt beim Generieren ein leeres
`cards: []`, weil das Backend sonst auf seine eingebaute Demo-Karte zurückfällt.

## AppDaemon-Reload

**AppDaemon bemerkt eine geänderte `!include`-Datei nicht von selbst** – nachgemessen an AppDaemon
4.7.3: nach dem Neuschreiben erscheint keine Zeile im AppDaemon-Log. Sein YAML-Loader liest die
Datei nur inline mit und überwacht ausschließlich die Dateien im `apps/`-Verzeichnis. Ohne Reload
steht die neue YAML also auf der Platte, während das Panel weiter die alte Konfiguration zeigt.

Nach dem Generieren löst die Integration deshalb den in den Optionen gewählten Reload aus:

| `reload_mode` | Wirkung | Voraussetzung |
| --- | --- | --- |
| `none` (Standard) | nichts – man lädt AppDaemon selbst neu | – |
| `touch_module` | setzt die mtime einer von AppDaemon überwachten Datei neu (`apps/nspanel.py` oder `apps.yaml`); AppDaemon lädt daraufhin genau diese App neu | HA muss die Datei sehen: AppDaemons `apps/` zusätzlich in den HA-Container mounten, Pfad unter `reload_touch_path` angeben |
| `restart_container` | startet den AppDaemon-Container über die Docker-Engine-API neu | `/var/run/docker.sock` im HA-Container; Containername unter `reload_container` |

Angetickt wird nur die mtime, der Inhalt bleibt unberührt; nicht existierende Dateien werden nicht
angelegt. Scheitert der Reload, bleibt die geschriebene YAML gültig – die API antwortet mit `200`
und `reload: {"ok": false, "detail": …}`, das Panel zeigt es als Fehler an.

## HTTP-API

Alle Endpunkte sind authentifiziert und **nur für Administratoren**.

| Methode | Pfad | Zweck |
| --- | --- | --- |
| `GET` | `/api/nspanel_ui_config/schema` | Feld-/Kartentyp-Schema, aus dem das Panel seine Formulare baut |
| `GET` | `/api/nspanel_ui_config/config` | aktuelles Modell + Validierungsbefunde |
| `POST` | `/api/nspanel_ui_config/config` | Modell speichern |
| `POST` | `/api/nspanel_ui_config/import` | `apps.yaml` einlesen (`{"text": …}` oder `{"path": …}`, optional `app_name`, `save`) |
| `POST` | `/api/nspanel_ui_config/generate` | YAML erzeugen, in den Ausgabepfad schreiben und AppDaemon neu laden (`{"reload": false}` überspringt den Reload) |

Beim Import über `path` muss das Verzeichnis in HAs `allowlist_external_dirs` stehen (der Pfad kommt
aus dem Request). Der *Ausgabe*pfad stammt dagegen aus den Integrations-Optionen und wird von einem
Administrator gesetzt.

## Icon-Picker und Farbwähler

**Ein falscher Icon-Name fällt sonst erst am Panel auf** – und dort nur als Warndreieck: das Backend
kennt ausschließlich die Namen aus seinem eigenen Mapping und fällt bei allem anderen still auf
`alert-circle-outline` zurück (`get_icon_id` in `icon_mapping.py`). Der Editor prüft Icon-Namen
deshalb gegen genau diese Liste, zeigt eine Vorschau (`<ha-icon>`) und warnt bei unbekannten Namen –
**ohne den Wert zu verwerfen**, denn das Backend kann in einer neueren Version mehr kennen.

Die Namensliste liegt als `www/panel/icon-names.js` bei (6896 Namen, ~110 kB) und wird erzeugt aus
dem Mapping des Backends:

```bash
python3 tools/extract_icon_names.py /pfad/zu/appdaemon/apps/luibackend/icon_mapping.py
```

Mitgeliefert statt zur Laufzeit gelesen, weil HA und AppDaemon in getrennten Containern laufen. Nach
einem Upstream-Update das Skript erneut laufen lassen – der Diff zeigt die neuen Icons.

Nicht als Icon-Name bewertet werden die Sonderformen des Backends: `text:` (roher Text), `ha:`
(Template), `<I>…</I>` (Icon in einem Template) und Jinja allgemein.

**Farben** akzeptiert das Backend in drei Formen, und der Editor bedient alle drei: `[r, g, b]`
(Farbwähler plus Zahlenfeld), je Zustand `{on, off}` (zwei Wähler) und Jinja-Templates (Textfeld).
Alles, was in keine dieser Formen passt, bleibt im JSON-Editor stehen, statt auf ein zu einfaches
Widget abgeschnitten zu werden. Eine unvollständige Eingabe im Zahlenfeld wird **nicht** übernommen –
sonst wäre der alte Wert weg.

## Icon / Brand-Assets

`custom_components/nspanel_ui_config/brand/` enthält die Bilder, die HACS und Home Assistant für die
Integration anzeigen — `icon.png` (256×256), `icon@2x.png` (512×512) und `logo.png` (512×432). Die
Icons sind oben/unten transparent aufgefüllt statt seitlich beschnitten, damit Panel-Rahmen und
Beschriftung vollständig bleiben. Quelldatei: `docs/brand-source.jpg` (945×797).

**Ab Home Assistant 2026.3 liest HA diese Bilder direkt aus der Integration** und serviert sie unter
`/api/brands/integration/nspanel_ui_config/<bild>` — mit **Vorrang vor dem Brands-CDN**. Fehlt eine
Dark-Variante (`dark_icon.png`), fällt HA auf die helle zurück; ein Eintrag im
[home-assistant/brands](https://github.com/home-assistant/brands)-Repo ist damit nur noch für ältere
HA-Versionen nötig (dort inzwischen als *legacy folder* geführt). Ohne lokale Assets *oder*
Brands-Eintrag zeigt HA den generischen Platzhalter des CDN.

Das GitHub-**Social-Preview**-Bild lässt sich nicht per API setzen; das geht nur über *Settings →
General → Social preview* im Web-UI (dafür eignet sich `docs/brand-source.jpg`).

## Referenzen

- Backend: <https://github.com/joBr99/nspanel-lovelace-ui>
- Doku/Config-Schema: <https://docs.nspanel.pky.eu/>

## Lizenz

[MIT](LICENSE)
