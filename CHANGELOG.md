# Änderungen

Format lose nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).
Bis 1.0 kann sich alles ändern.

## 0.10.2 – 2026-07-26

Zwei Fehler, die erst an einer echten Anlage sichtbar wurden – beide in der Vorschau des
Screensavers.

### Die Live-Ansicht zeigte lauter leere Plätze

Für den Screensaver rendert das Backend mit `mask=["type", "entityId"]` (`pages.py`): beide Felder
kommen **leer** an, obwohl Symbol, Name und Wert gefüllt sind. Der Parser hielt einen Eintrag genau
dann für frei, wenn `type` fehlte – und damit die vollständig belegte Ruheanzeige für komplett leer.

Ob ein Platz belegt ist, entscheidet jetzt sein **Inhalt**; `delete` bleibt der explizit
freigehaltene Platz. An der Testinstanz war das nicht zu sehen: dort existieren die Entities der
Konfiguration nicht, und der Not-found-Zweig des Backends sendet sehr wohl ein `type`.

### Uhrzeit und Datum standen doppelt auf dem Schirm

Neben `tTime` und `tDate` kennt der Screensaver noch `tAMPM` (AM/PM-Zusatz, im 24-Stunden-Format
leer) und `tTimeAdd` (die frei konfigurierbare Zusatzzeile aus `timeAdditionalTemplate`). Beide
wurden mit Uhrzeit bzw. Datum gefüllt, sodass alles zweimal erschien. Sie bleiben jetzt außen vor.

## 0.10.1 – 2026-07-26

### Die Vorschau war auf der Startseite nicht zu finden

Der Editor öffnet mit den **globalen Einstellungen** – und genau dort gab es keine Vorschau. Wer das
Panel aufrief, sah sie erst, wenn er links eine Karte auswählte, und hielt sie darum leicht für
nicht vorhanden.

- Die globale Seite zeigt jetzt ebenfalls eine Vorschau, stellvertretend den Screensaver (sonst die
  erste Karte), erkennbar beschriftet. Das passt auch inhaltlich: `model` (eu/us-l/us-p) steht dort
  und ändert Größe und Aufteilung des Displays unmittelbar.
- Ist noch gar nichts konfiguriert, steht dort der Hinweis, zuerst eine Karte anzulegen oder eine
  `apps.yaml` zu importieren – statt einer leeren Fläche.
- Vorschau-Block und seine Bedienung sind jetzt an einer Stelle definiert (`_previewBlockHtml` /
  `_bindPreview`), statt in jedem Formular wiederholt zu werden.

## 0.10.0 – 2026-07-26

### Vorschau der Displayfläche

Bis hierher beantwortete der Editor, *ob* ein Eintrag noch auf die Karte passt – nicht, *wie* sie
aussieht. Über jedem Kartenformular steht jetzt eine Nachbildung des Displays in Originalgröße
(480×320, `us-p` hochkant 320×480).

- **Plätze, Reihenfolge, Symbole, Farben und Werte kommen aus dem bearbeiteten Modell**, Templates
  werden über Home Assistants `/api/template` gerendert – alle einer Karte in einem einzigen Aufruf,
  mit Einzelaufrufen als Rückfallebene.
- **Die Geometrie ist abgemessen, nicht geschätzt.** `tools/extract_layouts.py` liest die
  Slot-Positionen aus den HMI-Dumps der Display-Firmware und erzeugt `www/panel/layouts.js` – alle
  Karten mit Entity-Liste **und beide Screensaver**, in allen drei Panel-Modellen, mit Symbol-,
  Namens- und Wertfläche jedes Platzes einzeln. Das Werkzeug schreibt nur, wenn die Platzzahl zu
  `CARD_CAPACITY` passt; `tests/test_layouts.py` prüft dasselbe ohne Netz. Nebenbei bestätigt: alle
  24 Kombinationen ergeben genau die Zahlen, die schon im Schema standen.
- Beim Screensaver steht die Zuordnung nicht in den Komponentennamen, sondern im Seitencode. Sie
  wird deshalb aus den `spstr`-Aufrufen **hergeleitet**: der `weatherUpdate~`-String trägt sechs
  Felder je Eintrag, aus dem Feldindex folgen Eintrag *und* Rolle. Das Ergebnis deckt sich exakt mit
  der Aufteilung, die `CAPACITY_LAYOUT_NOTES` beschreibt.
- Dabei fiel auf, dass die Notiz zu `screensaver2` zu grob war: die fünf reinen Symbole
  (Einträge 11–15) stehen auf dem eu-Panel **über** den sechs Kacheln, nicht darunter, und die
  Einträge 2–4 stehen untereinander statt in einer Zeile. Korrigiert.
- **Die Zahl der Plätze bleibt allein Sache des Schemas** (`CARD_CAPACITY`); die Vorschau bekommt sie
  übergeben und kann ihr deshalb nicht widersprechen.
- Freie Plätze (`entity: delete`, leer) sind als solche zu sehen, `iText.`/`navigate.`/`service.`
  werden nicht nach einem Zustand durchsucht, und eine `entity_id`, die es in Home Assistant nicht
  gibt, bekommt ein ⚠.
- Ehrlich gekennzeichnet ist, was Näherung bleibt: Größen und Schriftart sind nachempfunden, und ein
  Symbol, das nicht selbst gesetzt ist, leitet das Backend eigenständig ab – hier steht ersatzweise
  das aus Home Assistant, blasser dargestellt.

### Live-Ansicht: was das Gerät wirklich anzeigt

Ein Umschalter über der Displayfläche zeigt statt der Nachbildung das, was das Backend zuletzt ans
Panel geschickt hat. Damit fallen die letzten Näherungen weg: Symbole, die das Backend selbst
ableitet, und Werte in seiner Formatierung stehen dort im Original.

- Die Integration abonniert das `panelSendTopic` über die MQTT-Integration von Home Assistant und
  zerlegt `entityUpd~`/`weatherUpdate~` (`protocol.py`). **Sie veröffentlicht nie** – eine einzige
  Nachricht auf diesem Topic würde das echte Panel umschalten.
- Ohne MQTT in Home Assistant oder ohne `panelSendTopic` im Modell sagt die Ansicht genau das,
  statt leer zu bleiben.
- Symbole kommen als Zeichen des Nextion-Fonts; `icon-chars.js` (neu, aus demselben Werkzeug wie
  `icon-names.js`) führt sie auf ihren MDI-Namen zurück. Farben werden aus dem 16-Bit-Format des
  Displays zurückgerechnet – mit dem Verlust, den das Display selbst hat.
- Gefunden beim ersten Mitschnitt an einer echten Instanz: welcher der beiden Screensaver läuft,
  steht **nicht** in der Nachricht (beide füllen dieselben 6er-Blöcke). Maßgeblich ist der
  vorherige `pageType` – ohne ihn hätte die Ansicht bei `screensaver2` zwei Drittel der Einträge
  weggeworfen.

### Ein Befund aus dem HMI: das alternative Screensaver-Layout verdrängt einen Eintrag

Beim Abmessen der echten Screensaver-Geometrie kam heraus, dass die 6. Entity mehr tut als
umzusortieren: quer (`eu`, `us-l`) blendet das Display die erste Vorhersagespalte aus und rückt die
übrigen nach rechts – **die 5. Entity ist danach konfiguriert, wird gesendet und nirgends
angezeigt**. Hochkant (`us-p`) passiert das nicht. Die Validierung meldet es jetzt, die Layout-Notiz
im Schema beschreibt es genau, und die Vorschau zeichnet den verdrängten Eintrag erst gar nicht.

### Kleinigkeiten

- `package.json` mit `"type": "module"`: die Node-Tests liefen sonst nur auf Node ≥ 22.7.
- Brand-Icons um 83 % verkleinert (`tools/optimize-brand-png.mjs`) – Vorarbeit für einen PR ins
  brands-Repo, das ausdrücklich auf Dateigröße achtet.

## 0.9.0 – 2026-07-26

### Alle Installationsarten statt nur Docker

Die Einrichtung setzte bisher unausgesprochen eine Container-Installation voraus: getrennte Volumes,
selbst gelegter Bind-Mount, Docker-Socket für den Reload. Für Home Assistant OS ist davon nichts
richtig – dort läuft AppDaemon als Add-on, es gibt keinen Docker-Socket, und einen Mount braucht es
auch nicht. Bei einer Core-Installation liegen beide sogar im selben Dateisystem.

- **Der Einrichtungsdialog erkennt die Installationsart** (über Home Assistants `installation_type`)
  und belegt Ausgabepfad und Reload-Weg passend vor. Über dem Formular steht, was erkannt wurde und
  was in diesem Fall zu tun ist. Alle Felder bleiben überschreibbar.
- **Neuer Reload-Modus `restart_addon`**: startet das AppDaemon-Add-on über den Supervisor neu
  (`POST http://supervisor/addons/<slug>/restart`). Einzurichten ist dafür nichts – der
  `SUPERVISOR_TOKEN` steht bei HA OS/Supervised ohnehin in der Umgebung. Slug einstellbar
  (Community-Add-on: `a0d7b954_appdaemon`).
- **Kein Bind-Mount unter HA OS.** Das AppDaemon-Add-on hat `share:rw`, sieht `/share` also unter
  demselben Pfad wie Home Assistant. Vorgabe dort: `/share/nspanel/nspanel_config.yaml`.
- Wird der falsche Modus gewählt, sagt die Fehlermeldung das und nennt die passende Alternative.
- Neue Anleitung [docs/einrichtung.md](docs/einrichtung.md): wie die bestehende `apps.yaml` auf den
  `!include` umgestellt wird – inklusive der Reihenfolge (erst erzeugen, dann umstellen), des
  Bind-Mounts für die Container-Variante und des Rückwegs.

## 0.8.0 – 2026-07-26

### Sicherungen der erzeugten YAML

- Vor jedem Überschreiben wandert der bisherige Stand nach `backups/` neben der Ausgabedatei.
  **Lässt sich der alte Stand nicht sichern, wird nicht geschrieben.**
- Ist der Inhalt unverändert, passiert nichts – weder Schreiben noch Sichern. Sonst häufte jeder
  Klick auf „YAML erzeugen" eine identische Kopie an und drängte die echten Vorversionen aus der
  Rotation.
- Neuer Dialog *Sicherungen…* zum Ansehen und Zurückspielen. Beim Zurückspielen wird der aktuelle
  Stand seinerseits gesichert.
- Neue Option **Anzahl aufbewahrter Sicherungen** (Standard 10, `0` schaltet ab).
- Neue Endpunkte `GET /backups` und `POST /backups/restore`; `/generate` liefert zusätzlich
  `changed` und `backup`.

### Aufgeräumt

- README auf das Wesentliche gekürzt; Details nach `docs/funktionen.md` und `docs/kapazitaet.md`,
  Versionsverlauf in diese Datei.
- `strings.json` ist jetzt englisch (HA-Konvention: es ist die Quelldatei für Übersetzungen, die
  deutschen Texte stehen in `translations/de.json`).

## 0.7.0 – 2026-07-26

### Erklärte Felder

- Jedes Eingabefeld nennt jetzt **was es bewirkt** und **welche Werte zulässig sind**. Beides steht
  in `schema.py`; ein Test erzwingt, dass kein gerendertes Feld ohne beides dasteht.
- Beschreibungen, die je Kartentyp abweichen, haben eine eigene Fassung – `entity` bedeutet auf
  `cardThermo` etwas anderes als auf dem Screensaver.
- Jede Karte hat einen Einzeiler darüber, was sie darstellt.

### Anzeigekapazität

- Der Editor zeigt „*n* von *m* Plätzen" und markiert Entities, die das Display nicht mehr anzeigt.
  Die Validierung meldet es zusätzlich.
- Die Zahlen hängen am Panel-Modell (`cardEntities`: 4 auf eu, 6 auf us-p) und stammen aus den
  HMI-Dumps der Display-Firmware. `tools/check_card_capacity.py` zählt sie nach.
- `cardGrid` wechselt ab 7 Entities selbst auf `cardGrid2` – das ist abgebildet, damit keine falsche
  Warnung erscheint.

### Ergänzt und korrigiert

- Fehlende globale Keys: `timezone`, `displayURL-EU/US-L/US-P`, `berryURL`.
- Auswahllisten für `locale`, `font`, `temperatureUnit`, `dateFormatBabel` und weitere; freie
  Eingabe bleibt möglich.
- `sleepOverride` ist ein Dict aus `entity` und `brightness`, kein entity_id – Widget korrigiert.
- Keys, die das Backend nirgends liest (`unit`), werden benannt, aber nicht gelöscht.

## 0.6.0 – 2026-07-25

- Template-Editor mit Live-Vorschau über Home Assistants Template-API, inklusive der Eigenheit, dass
  das Backend bei `value`/`icon` nur bis zum letzten `}` rendert.

## 0.5.0 – 2026-07-25

- Icon-Picker mit Vorschau, geprüft gegen die 6896 Namen des Backend-Mappings.
- Farbwähler für `[r, g, b]` und getrennte `on`/`off`-Zustände.

## 0.4.0 – 2026-07-25

- AppDaemon-Reload nach dem Generieren (`touch_module`, `restart_container`). Grundlage: eine
  geänderte `!include`-Datei löst bei AppDaemon von sich aus **keinen** Reload aus.
- Brand-Assets für HACS und die Integrationskarte.

## 0.3.0 – 2026-07-25

- Visueller Editor als Custom-Panel: Karten- und Entity-Listen, Umsortieren, Entity-Picker.
  Die Formulare entstehen aus dem Schema, nicht aus doppelt gepflegten Feldlisten im JavaScript.

## 0.2.0 – 2026-07-25

- Import bestehender `apps.yaml` und YAML-Generator, verlustfrei in beide Richtungen: was die
  Integration nicht kennt, bleibt unverändert liegen und wird wieder herausgeschrieben.

## 0.1.0 – 2026-07-25

- Grundgerüst: HACS-Metadaten, Panel-Registrierung, Config-Flow, authentifizierte HTTP-API.
