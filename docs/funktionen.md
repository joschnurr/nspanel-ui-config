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
Zustand auswählt – und die Werte, inklusive gerenderter Templates.

Für die Templates macht das Panel **einen einzigen Aufruf** von `/api/template` je Karte, getrennt
durch ein Steuerzeichen; nur wenn die Teilezahl nicht aufgeht oder der Sammelaufruf an einem kaputten
Template scheitert, wird einzeln gerendert.

**Die Farbe liegt auf dem Symbol**, nicht auf Name und Wert. So macht es das Gerät: das HMI schreibt
die übertragene Farbe in die Schriftfarbe der Icon-Komponente (`covx tTmp.txt,tF1Icon.pco`), während
die Textfelder ihre feste Farbe behalten. Ein `color`-Template färbt also das Symbol – für farbige
Beschriftungen gibt es im Backend keine Möglichkeit.

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

**Schriftgrößen, Ausrichtung und Farben stammen ebenfalls aus dem Dump.** Jede Komponente nennt
dort ihre Font-ID, ihre horizontale und vertikale Ausrichtung und ihre Schriftfarbe – deshalb steht
die Beschriftung auf `cardGrid` mittig unter dem Symbol, ist der Kartentitel größer als sie, und die
Uhr des Screensavers ist der größte Font überhaupt. Auch der Hintergrund ist nicht rein schwarz,
sondern das dunkle Grau des Geräts (`Back. Color`).

Die *Pixelgrößen* der Font-IDs stehen allerdings nicht im Dump – sie stecken im Nextion-Projekt.
`FONT_PX` im Panel ist deshalb **kalibriert**: anhand der Feldhöhen, in denen ein Font vorkommt, und
im Abgleich mit den Beispielbildern der [Upstream-Doku](https://docs.nspanel.pky.eu/). Das ist die
einzige geschätzte Größe, die übrig bleibt.

**Ein `font` am Eintrag schlägt den Font der Komponente.** Auf dem Raster lässt sich die
Schriftgröße je Eintrag setzen (`small`, `medium-icon`, `medium`, `large` oder direkt eine Nummer);
das Backend hängt sie als `¬<nummer>` an das Symbol, und das Display wählt danach die Schrift. Die
Vorschau macht dasselbe – auch in der Live-Ansicht, wo diese Angabe mitgeliefert wird und vom Symbol
abgetrennt werden muss (sonst stünde dort wörtlich `19¬2`).

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

**Auf dem Raster steht bei Sensoren der Messwert, kein Symbol.** `cardGrid`/`cardGrid2` haben kein
eigenes Wertfeld – deshalb setzt das Backend bei `sensor`-Entities ohne eigenes `icon` den Zustand an
die Stelle des Symbols, gekürzt auf vier Zeichen (endet das auf einen Punkt, auf drei): `21.53` wird
zu `21.5`, `100.0` zu `100`. Die Vorschau macht es genauso; ein selbst gesetztes `icon` gewinnt.

Sonderformen sind berücksichtigt: `delete` und leere Einträge erscheinen als **freier Platz**,
`iText.` als fester Text, `navigate.`/`service.` ohne Zustandssuche. Eine `entity_id`, die es in
Home Assistant nicht gibt, wird mit ⚠ markiert – das ist fast immer ein Tippfehler.

Beim Screensaver zeigt die Vorschau zusätzlich, was sonst niemand sieht: im alternativen Layout (ab
der 6. Entity, quer) hat die 5. Entity keinen Platz mehr und wird gar nicht erst gezeichnet. Siehe
[kapazitaet.md](kapazitaet.md).

Auch die beiden **Status-Symbole** (`statusIcon1`/`statusIcon2`, links und rechts oben) sind dabei.
Sie stehen nicht in der Entity-Liste, sondern als eigene Felder am Screensaver, und sie dürfen mehr
als ein Symbol tragen: schreibt man `<I>mdi:fireplace</I> ha:{{ … }} °C`, ersetzt das Backend nur
den `<I>…</I>`-Teil durch das Zeichen und rendert den Rest — auf dem Display steht dann Symbol *und*
Messwert nebeneinander. Genau so zeichnet es die Vorschau, samt der übertragenen Farbe für beides.

### Live-Ansicht: was das Gerät wirklich anzeigt

Über der Displayfläche steht ein Umschalter: **aus der Konfiguration** (das oben Beschriebene) oder
**vom Gerät (live)**. Im Live-Modus zeigt dieselbe Fläche das, was das Backend zuletzt ans Display
geschickt hat — und da ist **nichts mehr geschätzt**: Symbole, die das Backend selbst aus Domain und
Zustand ableitet, Werte in seiner Formatierung, Farben so, wie das Display sie darstellt.

**Wie das geht:** das Backend schickt seine Zeilen als MQTT-Nachricht ans Panel
(`entityUpd~…`/`weatherUpdate~…` auf dem `panelSendTopic`). Die Integration abonniert dieses Topic
und zerlegt die Nachrichten (`protocol.py`). Vorher schickt das Backend `pageType~<karte>` — erst
damit ist der Aufbau der folgenden Nachricht bekannt, denn sie selbst sagt nicht, zu welcher Karte
sie gehört.

> **Lesend, mit einer Ausnahme auf Knopfdruck.** Von sich aus veröffentlicht die Integration
> nichts; auf das **Sende**-Topic schreibt sie nie – dort würde eine Nachricht das Display
> unmittelbar überschreiben. Nur der Knopf *Karte am Gerät aufrufen* sendet, und zwar auf dem
> *Empfangs*-Topic (siehe unten).

Voraussetzungen: die MQTT-Integration ist in Home Assistant eingerichtet, und im Modell steht ein
`panelSendTopic`. Fehlt eines von beidem, sagt die Live-Ansicht genau das — statt leer zu bleiben.

**Der Mitschnitt merkt sich jede Karte einzeln.** Das ist entscheidend, denn ein Panel steht die
meiste Zeit im Ruhezustand und sendet dann nur den Screensaver — eine Ansicht, die immer nur das
Letzte zeigt, wäre beim Bearbeiten einer Karte nutzlos. Wer am Gerät einmal durch die Karten
blättert, hat danach für jede den echten Stand; der Editor legt beim Bearbeiten automatisch die
passende Fassung daneben, mitsamt Zeitpunkt. War eine Karte noch nie dran, sagt die Ansicht das und
zeigt solange, was gerade läuft.

Die **Status-Symbole gehören keiner Karte**: sie kommen in einer eigenen Nachricht
(`statusUpdate~…`) und gelten für die Ruheanzeige, egal welche Karte gerade dran ist. Der Mitschnitt
hält sie deshalb neben den Karten — ein Kartenwechsel macht sie nicht ungültig, und umgekehrt
überschreibt eine Statusnachricht keinen Karten-Mitschnitt. Sendet ein Panel gar keine (weil keine
Status-Symbole konfiguriert sind), bleiben die beiden Stellen leer — wie am Gerät.

**Karte gezielt aufrufen.** Neben der Fläche steht *Karte am Gerät aufrufen*: ein Klick, und das
Panel springt auf diese Karte – damit muss man nicht am Gerät stehen, um die Ansicht zu füllen.
Gesendet wird dabei auf dem `panelRecvTopic` genau die Nachricht, die auch das Panel bei einem
Tastendruck schickt (`event,buttonPress2,navigate.<key>,button`); das Backend rendert daraufhin die
Karte. **Das Gerät wechselt sichtbar die Anzeige** – geschaltet wird nichts. Voraussetzung: die Karte
hat ein Feld `key`, denn darüber findet das Backend sie (`search_card` in `config.py`). Ohne `key`
sagt der Editor das an dieser Stelle.

**Farben** kommen als 16-Bit-Wert des Displays zurück (5/6/5 Bit). Zurückgerechnet ergibt das
leichte Abweichungen zum konfigurierten RGB — kein Fehler, sondern genau die Farbe, die das Display
darstellt.

Symbole überträgt das Protokoll als Zeichen des Nextion-Fonts. `www/panel/icon-chars.js` (erzeugt
von `tools/extract_icon_names.py`, in derselben Reihenfolge wie `icon-names.js`) führt sie zurück
auf ihren MDI-Namen. Ein Zeichen aus einer neueren Backend-Version bleibt namenlos und wird als
solches gekennzeichnet.

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

## Felder, die eine ganze Entity tragen

Vier Karten-Keys sind kein einzelner Wert, sondern ein Dict im Aufbau einer Entity-Zeile: die beiden
Navigationsschaltflächen jeder Karte (`navItem1`/`navItem2`) und die beiden **Status-Symbole** der
Ruheanzeige (`statusIcon1`/`statusIcon2`). Der Editor klappt sie an Ort und Stelle auf und zeigt
darin dieselben Felder wie eine Entity-Zeile – mit Icon-Picker, Farbwähler und Template-Umschalter.
Ist der Key nicht gesetzt, steht dort *nicht gesetzt* und ein **anlegen**; das ✕ am Kopf entfernt ihn
wieder ganz, statt ein leeres Dict zurückzulassen.

Die Status-Symbole haben ein Feld, das es sonst nirgends gibt: **`altFont`** schaltet für dieses eine
Symbol auf die größere Schrift. Nur der Screensaver-Renderer liest den Key – auf einer gewöhnlichen
Entity-Zeile bliebe er wirkungslos und gilt dort weiterhin als unbekannt. Welches Feld welche
Zusatzkeys hat, steht in `schema.py` (`ENTITY_LIKE_EXTRA_FIELDS`) und kommt über dieselbe
Schema-Antwort ins Panel.

### Sprungziele werden vorgeschlagen

Wohin ein Navigationsplatz springt, steht als `navigate.<key>` – und den `key` müsste man sonst aus
einer anderen Karte im Kopf haben. Der Editor schlägt deshalb alle vor: ein Klick ins Feld listet
jede Karte, die einen `key` hat, mit ihrem Titel; versteckte sind als solche gekennzeichnet, denn sie
sind der eigentliche Grund für ein navItem – ohne Sprungziel erreicht man sie gar nicht
([Doku: Subpages](https://docs.nspanel.pky.eu/subpages/)). Ein doppelt vergebener `key` erscheint nur
einmal: das Backend findet dazu ohnehin nur die erste Karte.

Dieselbe Liste bekommen `defaultCard` (Karte nach dem Aufwachen) und `destination` (Ziel nach der
PIN-Eingabe) – dieselbe Wertform, dieselbe Frage. Welche Felder das sind, steht in `schema.py` unter
`NAVIGATION_FIELDS`.

Beim `entity` eines navItems bleiben die **Entities zusätzlich wählbar**: laut Doku darf dort statt
eines Sprungziels auch eine gewöhnliche `entity_id` stehen, der Platz schaltet dann etwa ein Licht.
Sie erscheinen ab dem zweiten getippten Zeichen und auf 50 Treffer begrenzt, damit nicht die halbe
Installation im DOM steht. `delete` wird ebenfalls angeboten – damit lässt das Backend den Platz
bewusst frei.

## YAML ansehen und bearbeiten

**YAML ansehen…** in der Kopfzeile zeigt die Datei, die beim nächsten Speichern entstehen würde –
aus dem Stand *im Editor*, auch dem ungespeicherten. Die Frage lautet „was landet gleich in der
Datei?", nicht „was steht dort jetzt". Erzeugt wird der Text über `POST …/yaml`, der bewusst nichts
schreibt und keinen Reload auslöst.

Der Text ist bearbeitbar. **Übernehmen** liest ihn über denselben Weg zurück wie der Import: aus dem
YAML wird ein Modell, das den Editor füllt; geschrieben wird erst mit *Speichern*. Damit bleibt es
bei einer Quelle der Wahrheit – die Ausgabedatei erzeugt weiterhin nur der Generator, von Hand
gepflegt wird sie nie (beim nächsten Speichern wäre das wieder überschrieben).

Ein YAML-Fehler lässt den Dialog offen stehen und meldet die Stelle, statt den bearbeiteten Text zu
verwerfen. Dass der Rundlauf nichts verliert – auch die ausgelagerte Form ohne App-Wrapper, mit der
Kopfzeilen-Warnung davor –, hält `tests/test_roundtrip.py` fest.

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
| `touch_module` | setzt die mtime von AppDaemons `apps.yaml` neu; AppDaemon lädt daraufhin genau diese App **mitsamt Konfiguration** neu. **Nicht das App-Modul antippen** – das startet die App neu, liest die per `!include` eingebundene YAML aber nicht neu ein, die Änderung bliebe unsichtbar | HA muss die Datei sehen. Bei Core ohne Weiteres gegeben; bei getrennten Containern AppDaemons `apps/` zusätzlich in den HA-Container mounten. Pfad unter `reload_touch_path` |
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
| `POST` | `/api/nspanel_ui_config/yaml` | YAML zum übergebenen Stand (`{"model": …}`, ohne Body der gespeicherte) — **nur zum Ansehen**, schreibt nichts |
| `POST` | `/api/nspanel_ui_config/generate` | YAML erzeugen, schreiben und AppDaemon neu laden (`{"reload": false}` überspringt den Reload) |
| `GET` | `/api/nspanel_ui_config/backups` | vorhandene Sicherungen der Ausgabedatei |
| `POST` | `/api/nspanel_ui_config/backups/restore` | eine Sicherung zurückspielen (`{"name": …}`) |

Beim Import über `path` muss das Verzeichnis in Home Assistants `allowlist_external_dirs` stehen
(der Pfad kommt aus dem Request). Der *Ausgabe*pfad stammt dagegen aus den Integrations-Optionen und
wird von einem Administrator gesetzt. Beim Zurückspielen werden Pfadanteile im `name` abgewiesen.

## Brand-Assets

`custom_components/nspanel_ui_config/brand/` enthält die Bilder, die Home Assistant und HACS für die
Integration anzeigen: `icon.png` (256×256), `icon@2x.png` (512×512), `logo.png` (304×256) und
`logo@2x.png` (607×512). Erzeugt werden sie aus `docs/brand-source.jpg`:

```bash
npm install jpeg-js pngjs
node tools/make-brand-images.mjs docs/brand-source.jpg custom_components/nspanel_ui_config/brand
```

**Die Icons sind mittig quadratisch beschnitten, nicht aufgefüllt.** Das brands-Repo verlangt
ausdrücklich getrimmte Bilder („minimum amount of empty space on the edges"); eine frühere Fassung
mit transparenten Rändern oben und unten wäre dort abgelehnt worden. Beschnitten wird nur der
seitliche Geräterahmen — Display, Stift und Schriftzug bleiben vollständig. Das Logo behält das
ganze Bild, es darf rechteckig sein. `tests/test_manifests.py` prüft die Maße mit, weil sie sonst
erst im PR auffallen.

**Zwei Wege, die man nicht verwechseln darf** — beide nachgemessen:

| Wo | Woher das Bild kommt | Zeigt es unser Icon? |
| --- | --- | --- |
| Home Assistant (*Geräte & Dienste*) | liest `brand/` direkt aus der Integration und serviert es unter `/api/brands/integration/<domain>/<bild>` – mit Vorrang vor dem CDN (ab HA 2026.3) | **ja** |
| HACS-Übersicht | Brands-CDN, feste URL auf `brands.home-assistant.io` (Stand HACS 2.0.5) | **nein**, generischer Platzhalter |

**Ein Eintrag im [brands-Repo](https://github.com/home-assistant/brands) hilft dagegen nicht mehr –
er ist gar nicht mehr möglich.** Seit Home Assistant 2026.3 liefern Custom-Integrationen ihre Bilder
selbst, und das Repo nimmt dafür keine Beiträge mehr an; ein PR wird vom Bot automatisch geschlossen
([Ankündigung](https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api), hier am
2026-07-26 mit PR #10853 ausprobiert und genau so beschieden).

Dass die HACS-Übersicht trotzdem den Platzhalter zeigt, liegt allein daran, dass HACS seine
Bild-URLs noch fest gegen das CDN baut, statt den lokalen Proxy zu nutzen. Das ist dort bekannt
(u. a. hacs/frontend#937, hacs/integration#5179) und kommt mit einer künftigen HACS-Version – von
dieser Integration aus lässt sich daran nichts ändern.

Fehlt eine Dark-Variante (`dark_icon.png`), fällt HA auf die helle zurück – Dark-Assets sind nicht
nötig.

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
