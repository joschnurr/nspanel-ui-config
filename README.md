# NSPanel UI Config

> **Frühe Entwicklungsphase (v0.1.x).** Dieses Repo ist zunächst **privat**. Ziel ist eine
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
| Repo-/HACS-Skelett, Panel-Registrierung, Config-Flow-Gerüst | 🟡 in Arbeit (v0.1) |
| Import bestehender `apps.yaml` → internes Modell | ⬜ geplant |
| YAML-Generator (Screensaver, cardEntities, cardGrid) | ⬜ geplant |
| Visueller Editor (Karten-/Entity-Listen, Icon-/Farb-Picker) | ⬜ geplant |
| Weitere Kartentypen (Thermo, Media, Alarm, QR, Power …) | ⬜ geplant |
| Template-Editor (Jinja für color/value) | ⬜ geplant |
| AppDaemon-Reload-Automatik | ⬜ geplant |

Details und Designentscheidungen: **[docs/architecture.md](docs/architecture.md)**.

## Referenzen

- Backend: <https://github.com/joBr99/nspanel-lovelace-ui>
- Doku/Config-Schema: <https://docs.nspanel.pky.eu/>

## Lizenz

[MIT](LICENSE)
