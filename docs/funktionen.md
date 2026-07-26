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

## Vorschau

Über jedem Kartenformular steht eine **Nachbildung der Displayfläche** – 480×320 Pixel (`us-p`
hochkant 320×480), in Originalgröße, mit den Einträgen an den Plätzen, an denen sie später
erscheinen. Sie beantwortet die Fragen, die die Kapazitätsangabe offenlässt: *wirkt* die Farbe auf
schwarzem Grund, stimmt die Reihenfolge, liefert das Template den erwarteten Wert?

Gezeichnet wird aus dem Modell, das gerade bearbeitet wird – jede Änderung schlägt nach kurzer
Verzögerung durch, ohne dass das Formular neu aufgebaut wird (der Fokus bleibt also im Feld).

**Was echt ist:** die Anzahl und Reihenfolge der Plätze (aus `CARD_CAPACITY`, nicht aus einer
zweiten Tabelle im Frontend), die Symbole, die Farben – auch `{on, off}`, das nach dem aktuellen
Zustand auswählt – und die Werte, inklusive gerenderter Templates. Für die rendert das Panel alle
Templates einer Karte **in einem einzigen Aufruf** von `/api/template`, getrennt durch ein
Steuerzeichen; nur wenn die Teilezahl nicht aufgeht oder der Sammelaufruf an einem kaputten Template
scheitert, wird einzeln gerendert.

**Die Geometrie ist abgemessen, nicht geschätzt.** Für alle Karten mit Entity-Liste und für beide
Screensaver steht in `www/panel/layouts.js` die Position jeder Slot-Komponente – Symbol, Name und
Bedienfläche einzeln, für alle drei Panel-Modelle. Erzeugt wird die Datei von
`tools/extract_layouts.py` aus den HMI-Dumps der Display-Firmware:

```bash
python3 tools/extract_layouts.py /pfad/zu/nspanel-lovelace-ui
```

Das Werkzeug prüft dabei gegen `CARD_CAPACITY` und schreibt nichts, wenn die Platzzahl abweicht –
eine Vorschau, die dem Editor widerspricht, wäre schlimmer als gar keine. `tests/test_layouts.py`
prüft dieselbe Übereinstimmung ohne Netz, damit eine vergessene Neuerzeugung auffällt.

Bei den Karten reicht dafür die Namenskonvention der Komponenten (`tEntity1…`, `bEntity1…`).
**Beim Screensaver nicht** – dort verrät kein Name, welchen Listeneintrag eine Komponente zeigt. Die
Zuordnung wird stattdessen aus den `spstr`-Aufrufen des Seitencodes hergeleitet: der
`weatherUpdate~`-String trägt sechs Felder je Eintrag, aus dem Feldindex folgen Eintrag und Rolle
(`entity = (index-1) // 6`, `rolle = (index-1) % 6`). Dass die Herleitung trägt, zeigt der Abgleich –
sie ergibt genau die Aufteilung, die schon im Schema stand.

**Was Näherung bleibt:**

- **Schriftart und Umbruch.** Das Nextion nutzt eingebackene Bitmap-Fonts; ob ein langer Name dort
  an derselben Stelle umbricht, ist eine Aussage mit Restunschärfe. Die Schriftgröße leitet die
  Vorschau aus der abgemessenen Höhe des Textfeldes ab.
- **Karten mit nur einer Entity** (`cardThermo`, `cardAlarm`, `cardChart`, `cardUnlock`) zeigen nur
  ihre Fläche – deren Innenleben gestaltet das Backend.
- **Symbole ohne eigene Angabe.** Die leitet das Backend aus Domain und Zustand ab
  (`icon_mapping.py`); nachgebaut wird das nicht. Ersatzweise steht das Symbol da, das Home
  Assistant selbst für die Entity führt – blasser dargestellt und im Tooltip als solches benannt.
- **Zustandsformate.** Ohne eigenes `value` steht der Zustand aus Home Assistant da; das Backend
  formatiert ihn teils anders.

Sonderformen sind berücksichtigt: `delete` und leere Einträge erscheinen als **freier Platz**,
`iText.` als fester Text, `navigate.`/`service.` ohne Zustandssuche. Eine `entity_id`, die es in
Home Assistant nicht gibt, wird mit ⚠ markiert – das ist fast immer ein Tippfehler.

Beim Screensaver zeigt die Vorschau zusätzlich, was sonst niemand sieht: im alternativen Layout (ab
der 6. Entity, quer) hat die 5. Entity keinen Platz mehr und wird gar nicht erst gezeichnet. Siehe
[kapazitaet.md](kapazitaet.md).

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

`custom_components/nspanel_ui_config/brand/` enthält die Bilder, die Home Assistant und HACS für die
Integration anzeigen — `icon.png` (256×256), `icon@2x.png` (512×512) und `logo.png` (512×432). Die
Icons sind oben/unten transparent aufgefüllt statt seitlich beschnitten, damit Panel-Rahmen und
Beschriftung vollständig bleiben. Quelldatei: `docs/brand-source.jpg`.

**Zwei Wege, die man nicht verwechseln darf** — beide nachgemessen:

| Wo | Woher das Bild kommt | Braucht einen brands-Eintrag? |
| --- | --- | --- |
| Home Assistant (*Geräte & Dienste*) | liest `brand/` direkt aus der Integration und serviert es unter `/api/brands/integration/<domain>/<bild>` – mit Vorrang vor dem CDN (ab HA 2026.3) | **nein** |
| HACS-Übersicht | Brands-CDN | **ja** |

Ohne Eintrag im [home-assistant/brands](https://github.com/home-assistant/brands)-Repo zeigt HACS
also den generischen Platzhalter, während Home Assistant selbst das richtige Icon anzeigt. Fehlt
eine Dark-Variante (`dark_icon.png`), fällt HA auf die helle zurück – Dark-Assets sind nicht nötig.

**Dateigröße zählt.** Das brands-Repo achtet ausdrücklich darauf, und die Bilder landen in jeder
Installation. Direkt aus einem Foto exportiert waren unsere mit 83 kB (256×256) und 285 kB (512×512)
rund fünfzehnmal so groß wie üblich. `tools/optimize-brand-png.mjs` quantisiert sie auf eine Palette
und schreibt ein indiziertes PNG:

```bash
npm install pngjs
node tools/optimize-brand-png.mjs quelle.png ziel.png 128
```

Das drückt sie um ~83 % (14,1 / 47,5 / 38,8 kB) **ohne sichtbaren Unterschied**. Bei 64 Farben
zeigt der dunkle Rahmen des Icons Banding – 128 ist die Grenze.

### Social Preview

`docs/social-preview.jpg` (1280×640, ~105 kB) ist das Bild, das GitHub in jeder Linkvorschau des
Repos zeigt. Erzeugt aus derselben Quelle:

```bash
npm install jpeg-js
node tools/make-social-preview.mjs docs/brand-source.jpg docs/social-preview.jpg
```

Das Motiv wird proportional eingepasst und auf Fast-Schwarz zentriert, **nicht beschnitten** – ein
2:1-Ausschnitt würde den Schriftzug am unteren Rand kosten.

**Hochladen lässt es sich nur von Hand:** *Settings → General → Social preview* im Web-UI von
GitHub. Es gibt dafür keinen API-Endpunkt, die Datei im Repo genügt also nicht.
