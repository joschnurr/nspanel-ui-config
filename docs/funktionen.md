# Funktionen im Detail

Ergänzung zur [README](../README.md) für alles, was dort nur einen Satz bekommt.

## Erklärte Felder

Die Feldnamen des Backends sagen für sich genommen wenig – `forecastSkip`, `assumed_state`,
`sleepOverride`, `speed`. Jedes Eingabefeld trägt deshalb zwei Zeilen: **was es bewirkt** (aus Sicht
dessen, was auf dem Panel passiert) und **welche Werte zulässig sind**.

Beides steht in `schema.py` (`FIELD_DESCRIPTIONS` / `FIELD_VALUE_HINTS`) und kommt über
`GET /api/nspanel_ui_config/schema` ins Panel; im JavaScript wird nichts davon dupliziert. Ein Test
hält es vollständig: `tests/test_schema_payload.py` schlägt fehl, sobald ein gerendertes Feld ohne
Beschreibung *oder* ohne Angabe der möglichen Werte dasteht.

Wo ein Feld je Kartentyp etwas anderes bedeutet, gewinnt die spezifische Fassung
(`CARD_FIELD_DESCRIPTIONS`): `entity` heißt auf `cardThermo` „die climate-Entity dieser Karte", auf
dem Screensaver dagegen „die Wetter-Entity". Jede Karte bekommt zusätzlich einen Einzeiler darüber,
was sie überhaupt darstellt.

## Template-Editor

Felder, die das Backend als Jinja rendert, haben im Formular einen Umschalter **„als Template
bearbeiten"** – und darin eine Live-Vorschau über Home Assistants eigene Template-API
(`POST /api/template`). Das ist dieselbe Engine, die später auch das Backend benutzt
(`ha_api.render_template`); man sieht also echte Werte und echte Jinja-Fehlermeldungen statt einer
Nachbildung. Bei Farb-Feldern zeigt die Vorschau zusätzlich einen Farbfleck, sobald das Ergebnis als
RGB lesbar ist.

Template-fähig sind (nachgesehen an den `render_template`-Aufrufen des Backends, nicht geraten):
`name`, `value`, `color`, `icon`, `state_template`, `defaultCard`, `qrCode`, `speed`,
`dateAdditionalTemplate`, `timeAdditionalTemplate`.

**Eine Eigenheit, die man kennen muss:** bei `value` und `icon` rendert das Backend nur bis zum
**letzten** `}` und hängt den Rest wörtlich an – genau so entstehen Einheiten wie `{{ … }} °C`. Die
Vorschau bildet das nach, sonst zeigte sie etwas anderes als später das Panel.

Der gewählte Modus ist reine Ansichtssache und wird nie mitgespeichert. Der Umschalter allein ändert
auch keinen Wert: erst wenn im Textfeld etwas geändert wird, geht der neue Wert ins Modell.

## Icon-Picker

**Ein falscher Icon-Name fällt sonst erst am Panel auf** – und dort nur als Warndreieck: das Backend
kennt ausschließlich die Namen aus seinem eigenen Mapping und fällt bei allem anderen still auf
`alert-circle-outline` zurück (`get_icon_id` in `icon_mapping.py`). Der Editor prüft Icon-Namen
deshalb gegen genau diese Liste, zeigt eine Vorschau und warnt bei unbekannten Namen – **ohne den
Wert zu verwerfen**, denn eine neuere Backend-Version kann mehr kennen.

Die Namensliste liegt als `www/panel/icon-names.js` bei (6896 Namen, ~110 kB) und wird erzeugt aus
dem Mapping des Backends:

```bash
python3 tools/extract_icon_names.py /pfad/zu/appdaemon/apps/luibackend/icon_mapping.py
```

Mitgeliefert statt zur Laufzeit gelesen, weil HA und AppDaemon in getrennten Containern laufen. Nach
einem Upstream-Update erneut laufen lassen – der Diff zeigt die neuen Icons.

Nicht als Icon-Name bewertet werden die Sonderformen des Backends: `text:` (roher Text), `ha:`
(Template), `<I>…</I>` (Icon in einem Template) und Jinja allgemein.

## Farben

Das Backend akzeptiert drei Formen, und der Editor bedient alle drei:

| Form | Bedienung |
| --- | --- |
| `[r, g, b]` | Farbwähler plus Zahlenfeld |
| `{on: …, off: …}` | zwei Wähler, je Zustand |
| Jinja-Template | Textfeld mit Vorschau und Farbfleck |

Alles, was in keine dieser Formen passt, bleibt im JSON-Editor stehen, statt auf ein zu einfaches
Widget abgeschnitten zu werden. Eine unvollständige Eingabe im Zahlenfeld wird **nicht** übernommen –
sonst wäre der alte Wert weg.

## Sicherungen

Vor jedem Überschreiben der Ausgabedatei wandert der bisherige Stand nach `backups/` neben der
Datei, benannt nach dem Zeitpunkt (`nspanel_config.yaml.2026-07-26_11-30-00-123.bak`).

- **Lässt sich der alte Stand nicht sichern, wird nicht geschrieben.** Eine nicht sicherbare Datei
  ist genau die, die man am wenigsten überschreiben will.
- **Ist der Inhalt unverändert, passiert nichts** – weder Schreiben noch Sichern. Sonst häufte jeder
  Klick auf „YAML erzeugen" eine weitere identische Kopie an und drängte die echten Vorversionen aus
  der Rotation.
- **Beim Zurückspielen wird der aktuelle Stand seinerseits gesichert.** Ein versehentliches
  Wiederherstellen ist damit selbst wieder rückgängig zu machen.
- Wie viele Sicherungen aufgehoben werden, steht in den Optionen (Standard 10; `0` schaltet ab).

Über *Sicherungen…* in der Kopfzeile des Editors lassen sie sich ansehen und zurückspielen. Das
Zurückspielen betrifft nur die **Datei** – das Modell im Editor bleibt, wie es ist. Wer beides
angleichen will, importiert die Datei anschließend.

## AppDaemon-Reload

**AppDaemon bemerkt eine geänderte `!include`-Datei nicht von selbst** – nachgemessen an AppDaemon
4.7.3: nach dem Neuschreiben erscheint keine Zeile im AppDaemon-Log. Sein YAML-Loader liest die
Datei nur inline mit und überwacht ausschließlich die Dateien im `apps/`-Verzeichnis. Ohne Reload
steht die neue YAML also auf der Platte, während das Panel weiter die alte Konfiguration zeigt.

Nach dem Generieren löst die Integration deshalb den in den Optionen gewählten Reload aus. Welcher
Weg möglich ist, hängt an der Installationsart — der Einrichtungsdialog wählt den passenden vor:

| `reload_mode` | Wirkung | Voraussetzung |
| --- | --- | --- |
| `none` (Standard) | nichts – man lädt AppDaemon selbst neu | – |
| `restart_addon` | startet das AppDaemon-**Add-on** über den Supervisor neu | Home Assistant OS/Supervised; Slug unter `reload_addon` (Community-Add-on: `a0d7b954_appdaemon`) |
| `touch_module` | setzt die mtime einer von AppDaemon überwachten Datei neu (`apps/nspanel.py` oder `apps.yaml`); AppDaemon lädt daraufhin genau diese App neu | HA muss die Datei sehen. Bei Core ohne Weiteres gegeben; bei getrennten Containern AppDaemons `apps/` zusätzlich in den HA-Container mounten. Pfad unter `reload_touch_path` |
| `restart_container` | startet den AppDaemon-**Container** über die Docker-Engine-API neu | `/var/run/docker.sock` im HA-Container; Containername unter `reload_container` |

`touch_module` ist der feingranularste Weg – nur die betroffene App startet neu. `restart_addon` und
`restart_container` sind grob (alle AppDaemon-Apps starten neu), dafür brauchen sie keinen
zusätzlichen Dateizugriff. Beim Add-on-Weg ist gar nichts einzurichten: der `SUPERVISOR_TOKEN` steht
dort ohnehin in der Umgebung des HA-Containers.

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
| `POST` | `/api/nspanel_ui_config/generate` | YAML erzeugen, schreiben und AppDaemon neu laden (`{"reload": false}` überspringt den Reload) |
| `GET` | `/api/nspanel_ui_config/backups` | vorhandene Sicherungen der Ausgabedatei |
| `POST` | `/api/nspanel_ui_config/backups/restore` | eine Sicherung zurückspielen (`{"name": …}`) |

Beim Import über `path` muss das Verzeichnis in Home Assistants `allowlist_external_dirs` stehen
(der Pfad kommt aus dem Request). Der *Ausgabe*pfad stammt dagegen aus den Integrations-Optionen und
wird von einem Administrator gesetzt. Beim Zurückspielen werden Pfadanteile im `name` abgewiesen.

## Brand-Assets

`custom_components/nspanel_ui_config/brand/` enthält die Bilder, die HACS und Home Assistant für die
Integration anzeigen — `icon.png` (256×256), `icon@2x.png` (512×512) und `logo.png` (512×432). Die
Icons sind oben/unten transparent aufgefüllt statt seitlich beschnitten, damit Panel-Rahmen und
Beschriftung vollständig bleiben. Quelldatei: `docs/brand-source.jpg`.

**Ab Home Assistant 2026.3 liest HA diese Bilder direkt aus der Integration** und serviert sie unter
`/api/brands/integration/nspanel_ui_config/<bild>` — mit Vorrang vor dem Brands-CDN. Fehlt eine
Dark-Variante (`dark_icon.png`), fällt HA auf die helle zurück; ein Eintrag im
[home-assistant/brands](https://github.com/home-assistant/brands)-Repo ist damit nur noch für ältere
HA-Versionen nötig (dort inzwischen als *legacy folder* geführt).
