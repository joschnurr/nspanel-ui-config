# Änderungen

Format lose nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).
Bis 1.0 kann sich alles ändern.

## 0.18.3 – 2026-07-28

### Auf dem Handy war vom Editor nichts zu sehen

Der Editor war fürs Tablet gebaut: die Seitenleiste liegt mit **festen 290 px** neben dem Inhalt.
Auf einem Telefon (meist 360–400 CSS-Pixel breit) blieb für das Formular ein Streifen von wenigen
Pixeln – der Bildschirm sah leer aus. Eine Media-Query gab es bis jetzt nicht.

- Unterhalb von 700 px liegen Kartenliste und Formular **untereinander** statt nebeneinander; die
  Liste bekommt höchstens 42 % der Höhe (unter 480 px: 34 %), der Rest gehört dem Formular.
- Kopfzeile, Ränder und Dialoge sind dort kompakter.
- Die Displayfläche bleibt bei ihren 480 px – sie soll maßstäblich sein – und wird stattdessen
  waagerecht gescrollt.
- Die Seitenleiste zeigt jetzt „Wird geladen…", solange Modell und Schema fehlen. Vorher war sie
  in dieser Zeit leer, was auf einem schmalen Schirm wie ein Defekt aussah.

## 0.18.2 – 2026-07-28

### Der YAML-Dialog lag quer – und prüft jetzt beim Tippen

Die Dialoge legten Überschrift, Hinweis, Textfeld und Schaltflächen **nebeneinander** statt
untereinander; die drei Knöpfe standen als hohe Balken rechts, das Textfeld blieb ein schmaler
Streifen. In 0.18.1 fiel es auf, weil die Dialoge breiter wurden – falsch war es schon vorher.

Der Grund: Die Dialoge tragen die Klasse `body`, aber nur, damit ihre Knöpfe die hellen Farben
bekommen (`.body button`). Dieselbe Klasse ist zugleich das **Hauptlayout der App** – `display:
flex` für Navigation neben Inhalt. Der Dialog wurde damit zur Flex-Zeile, und `align-items:
stretch` zog die Knöpfe auf volle Höhe. Jetzt steht dort ausdrücklich eine Spalte.

Damit sitzt der Hinweis *„So sähe die Datei beim nächsten Speichern aus…"* oben über dem Feld, die
Schaltflächen haben wieder ihre normale Höhe, und **das Textfeld bekommt den ganzen Rest** – der
Dialog ist 90 % der Fensterhöhe hoch, alles andere behält seine eigene Höhe.

### YAML-Syntaxprüfung beim Tippen

Kurz nach der letzten Eingabe geht der Text an dieselbe Stelle, die ihn später wirklich liest. Die
Statuszeile meldet *YAML in Ordnung – n Karte(n)* oder die Fehlerstelle mit Zeile und Spalte;
solange etwas nicht stimmt, bleibt **Übernehmen** gesperrt.

Geprüft wird auf dem Server, nicht im Browser: ein nachgebautes „sieht gültig aus", das beim
Übernehmen dann doch scheitert, wäre schlimmer als keine Prüfung.

## 0.18.1 – 2026-07-28

### Mehr Platz für YAML, kleinere Schaltflächen

Die beiden Dialoge, in denen YAML steht — *YAML ansehen…* und *Importieren…* —, sind jetzt **breit**
(bis 1180 px statt 680) und ihre Textfelder richten sich nach der **Fensterhöhe** statt nach einer
festen Zeilenzahl: 62 % der Höhe für die YAML-Ansicht, 28 % fürs Einfügen beim Import. Auf einem
großen Schirm ist damit auch viel zu sehen, auf einem kleinen wächst der Dialog trotzdem nicht über
den Rand. Ziehen an der unteren Kante geht weiterhin.

Zeilen **brechen dort nicht mehr um** (`wrap="off"`). Bei YAML trägt die Einrückung die Bedeutung —
eine umgebrochene lange Template-Zeile sieht aus wie eine neue Ebene. Statt umzubrechen, lässt sich
jetzt waagerecht scrollen.

Die Schaltflächen sind durchgehend etwas kleiner (13 px statt 14, schmalere Ränder). Das betrifft
die ganze Oberfläche, nicht nur die Dialoge — in der Kopfzeile stehen inzwischen fünf davon.

## 0.18.0 – 2026-07-28

### Die YAML ansehen – und darin arbeiten

Bisher sah man das Ergebnis erst in der Datei, also nach dem Schreiben. **YAML ansehen…** in der
Kopfzeile zeigt sie jetzt vorher: den Stand *im Editor*, auch den ungespeicherten. Die Frage, die
man vor dem Speichern stellt, lautet ja „was landet gleich in der Datei?" und nicht „was steht dort
noch von letztem Mal".

Dahinter steht ein eigener Endpunkt (`POST …/yaml`), der **nichts schreibt und keinen Reload
auslöst** — im Unterschied zu *YAML erzeugen*, das beides tut. Wer nur nachsehen will, muss die
Anlage dafür nicht anfassen.

Der Text ist **bearbeitbar**. *Übernehmen* liest ihn über denselben Weg zurück wie der Import: aus
dem YAML wird ein Modell, das den Editor füllt; geschrieben wird es erst mit *Speichern*. Damit
bleibt es bei einer Quelle der Wahrheit — die Ausgabedatei erzeugt weiterhin nur der Generator. Von
Hand gepflegt wird sie nach wie vor nicht: der nächste Speichervorgang überschriebe das ohnehin.

Ein YAML-Fehler verwirft den bearbeiteten Text nicht, sondern lässt den Dialog stehen und nennt die
Stelle. Dass der Rundlauf nichts verliert — auch in der ausgelagerten Form ohne App-Wrapper und mit
der Kopfzeilen-Warnung davor —, hält ein neuer Test fest.

## 0.17.3 – 2026-07-28

### Die Live-Ansicht hielt `screensaver2` manchmal für den klassischen Screensaver

Dann quetschten sich die Kacheln in ein Layout mit **6 statt 15 Plätzen**, und die Beschriftungen
brachen mitten im Wort ab. Das trat nicht immer auf, und der Grund dafür ist der eigentliche Fund:

Im Ruhezustand schickt das Backend die Wetteraktualisierung (`weatherUpdate~…`) immer wieder — den
`pageType`, der die Bauart nennt, aber **nur beim Wechsel** in die Ruheanzeige. In der Nachricht
selbst steht sie nicht; beide Bauarten füllen dieselben 6er-Blöcke. Nach einem Neustart von Home
Assistant ist der letzte `pageType` deshalb unbekannt — der Mitschnitt liegt im Speicher —, und es
galt der klassische Screensaver. Bis zum nächsten Wechsel blieb es dabei.

Zwei Stellen ziehen das jetzt gerade:

- **Die Zahl der Blöcke entscheidet mit.** Mehr als sechs kann der klassische Screensaver nicht
  zeigen; kommen mehr, ist es zwingend `screensaver2`. Das ist hart entscheidbar und schlägt sogar
  einen anderslautenden `pageType`.
- **Bei der Ruheanzeige gilt die Konfiguration.** Steht im Editor `screensaver2`, zeichnet die
  Live-Ansicht auch so — welche Bauart läuft, ergibt sich aus der Konfiguration, nicht aus einer
  Nachricht, die es nicht verrät. Für alle übrigen Karten bleibt es beim Mitschnitt: dort leitet die
  Live-Ansicht weiterhin nichts ab.

## 0.17.2 – 2026-07-28

### Mehrzeilige Templates standen als eine Zeile voller `\n` in der Datei

Wer ein Template über mehrere Zeilen schreibt – das Eingabefeld ist ein mehrzeiliger Kasten und lädt
dazu ein –, fand es in der erzeugten YAML als **eine einzige lange Zeile** wieder, mit `\n` an jeder
Umbruchstelle:

```yaml
value: "{% if is_state('input_boolean.party','on') %}\n  [255, 0, 200]\n{% else %}\n  [0, 0, 0]\n{% endif %}"
```

Gelesen hat das Backend immer den richtigen Text – der Wert war nie beschädigt, ein Roundtrip kam
unverändert zurück. Nur ansehen konnte man sich die Datei nicht mehr, und sie landet nun einmal in
der Konfiguration des Nutzers. Jetzt steht dort ein Literalblock, Zeile für Zeile:

```yaml
value: |-
  {% if is_state('input_boolean.party','on') %}
    [255, 0, 200]
  {% else %}
    [0, 0, 0]
  {% endif %}
```

Denselben Ursprung hatte ein zweiter Fall: enthielt ein Template Apostroph **und**
Anführungszeichen, verdoppelte PyYAML jeden Apostroph (`is_state(''x'',''on'')`). Der Umweg auf
doppelte Quotes, der genau das verhindern soll, griff nur bei Templates ganz ohne `"`, `\` und
Zeilenumbruch. Gewählt wird jetzt die Form, die weniger zu escapen hat; ein Backslash bleibt bei den
einfachen Quotes, weil doppelte ihn verdoppeln müssten.

Beim nächsten Speichern werden betroffene Stellen einmalig umformatiert – inhaltlich ändert sich
nichts, die Sicherung davor entsteht wie immer.

## 0.17.1 – 2026-07-27

### Der Aufruf-Knopf fehlte ausgerechnet im leeren Zustand

Hatte die Integration noch gar nichts mitgeschnitten, zeigte die Live-Ansicht nur den Grund – ohne
den Knopf *Karte am Gerät aufrufen*. Das trifft nach **jedem Neustart von Home Assistant** zu, denn
der Mitschnitt liegt im Speicher. Man hätte ans Gerät gehen müssen, um die Ansicht wieder zu füllen.
Der Knopf steht jetzt auch dort.

## 0.17.0 – 2026-07-27

### Die Live-Ansicht zeigt nur noch die Karte, um die es geht

Wechselte man auf eine Karte, die das Gerät noch nicht angezeigt hatte, stand dort die zuletzt
empfangene – meist der Screensaver. Das sah aus wie ein Ergebnis, war aber eine fremde Karte.
Jetzt bleibt die Fläche leer, bis der passende Mitschnitt da ist; der Hinweis erklärt es, und der
Knopf *Karte am Gerät aufrufen* holt sie.

### Auswahlfelder zeigen wieder alle Möglichkeiten

Felder mit fester Auswahl (Screensaver-Typ, `locale`, `font`, …) waren Textfelder mit
Vorschlagsliste. Der Browser filtert eine solche Liste nach dem, was schon im Feld steht: bei
`screensaver2` erschien beim Aufklappen nur dieser eine Wert, und die zweite Bauart blieb
unsichtbar. Jetzt ist es ein echtes Auswahlfeld.

Ein Wert, den die Liste nicht kennt (etwa aus einer neueren Backend-Version), wird als zusätzlicher
Eintrag aufgenommen und dabei als „aus der Konfiguration" gekennzeichnet – verlorengehen kann so
nichts.

## 0.16.3 – 2026-07-27

### Die Blättertasten zeigen das konfigurierte Ziel

`navItem1`/`navItem2` ersetzen auf der Karte die Standardpfeile durch ein eigenes Ziel samt Symbol.
Am Gerät steht dort dann dieses Symbol – die Vorschau zeichnete stur ◀ und ▶ und zeigte damit eine
Navigation, die es so nicht gibt. Jetzt erscheint das eingestellte Symbol, im Live-Modus das, was das
Backend tatsächlich geschickt hat.

## 0.16.2 – 2026-07-27

### Die Kopfzeile zeigt, welche Fassung der Browser geladen hat

Ein Update kann installiert und trotzdem unsichtbar sein: ES-Module lädt der Browser **pro
Seitenaufruf einmal**. Bleibt die Home-Assistant-Oberfläche offen, läuft weiter die alte Fassung –
der Server liefert längst die neue aus, die Anzeige ändert sich aber nicht. Genau das führte gerade
dazu, dass die neuen Schriftgrößen nicht ankamen, obwohl Server und Dateien stimmten.

Neben dem Titel steht deshalb jetzt die Version, die dieser Browser ausführt (aus der eigenen
Modul-URL). Weicht sie von der installierten ab: Seite neu laden (Strg+Shift+R).

## 0.16.1 – 2026-07-27

### Die Schriftgröße je Eintrag (`font`) wirkt jetzt auch in der Vorschau

Auf dem Raster lässt sich die Größe pro Eintrag einstellen – daher stehen auf einer `cardGrid2` große
und kleine Werte nebeneinander. Das Backend hängt die gewählte Nummer als `¬<font>` an das Symbol
(`pages.py`), das Display wählt danach die Schrift.

- Die Vorschau wertet das Feld aus (`small`/`medium-icon`/`medium`/`large` oder eine Nummer) und
  bemisst das Symbolfeld danach.
- **Der Live-Parser trennt die Angabe ab.** Ohne das stand im Symbolfeld wörtlich `19¬2` statt der
  Zahl – ein Fehler, den erst ein Blick auf ein echtes `cardGrid2` zeigte.
- Text im Symbolfeld (der Messwert eines Sensors) bekommt keinen Symbolfaktor mehr: Glyphen füllen
  die Zeile stärker aus als Ziffern, die Zahlen waren dadurch zu groß.

## 0.16.0 – 2026-07-27

### Die Vorschau folgt jetzt auch den Schriften und Ausrichtungen des Geräts

Bisher nutzte die Vorschau aus den HMI-Dumps nur Position und Größe der Komponenten. Dort steht aber
mehr: **Font-ID, horizontale und vertikale Ausrichtung, Schriftfarbe und Hintergrundfarbe.** Das
erklärt die Abweichungen, die im Vergleich mit der [Upstream-Doku](https://docs.nspanel.pky.eu/)
auffielen – auf `cardGrid` etwa klebte die Beschriftung links, statt mittig unter dem Symbol zu
stehen, und Symbol, Titel und Beschriftung hatten fast dieselbe Größe.

- `tools/extract_layouts.py` liest die Attribute mit und legt sie neben die Rechtecke
  (`slotAttrs`, `chromeAttrs`, `specialAttrs`; kurze Schlüssel `f`/`h`/`v`/`c`).
- Die Zeichenschicht richtet Text danach aus, färbt ihn in der Schriftfarbe der Komponente und
  bemisst ihn nach der Font-ID: auf `cardGrid` also Symbol 55 px, Titel 24 px, Beschriftung 15 px –
  alles zentriert. Die Uhr des Screensavers nutzt den größten Font (92 px).
- Der Bildschirm bekommt den echten Hintergrund des Geräts (`#191c19`) statt reinem Schwarz.
- **Kalibriert, nicht gemessen:** die Pixelgrößen der Font-IDs stehen nicht im Dump. `FONT_PX` ist
  aus den Feldhöhen und den Doku-Bildern abgeleitet – die einzige geschätzte Größe, die bleibt.
- Ein Test deckte dabei einen echten Fehler auf: `attr && FONT_PX[attr.f]` ergibt bei fehlendem
  Attribut `null`, und `null !== undefined` – die Ersatzgröße hätte nie gegriffen, jede Schrift wäre
  auf den Mindestwert gefallen.

## 0.15.0 – 2026-07-27

### Der Editor schlägt die Sprungziele vor

Ein Navigationsplatz zeigt mit `navigate.<key>` auf eine andere Karte – und dieser `key` steht an
einer ganz anderen Stelle der Konfiguration. Bisher musste man ihn im Kopf haben und fehlerfrei
abtippen; ein Vertipper fiel erst am Gerät auf, wo die Schaltfläche dann ins Leere ging.

Ein Klick ins Feld listet jetzt **jede Karte mit einem `key`**, mit ihrem Titel als Beschriftung.
Versteckte Karten sind als solche markiert – sie sind der eigentliche Grund für ein navItem, denn
ohne Sprungziel erreicht man sie überhaupt nicht. Ein doppelt vergebener `key` erscheint nur einmal,
weil das Backend dazu ohnehin nur die erste Karte findet.

Dieselbe Liste bekommen `defaultCard` und `destination`: gleiche Wertform, gleiche Frage.

Beim `entity` eines navItems bleiben die Entities daneben wählbar. Die
[Doku](https://docs.nspanel.pky.eu/subpages/) zeigt beides – `entity: navigate.home` mit
`icon: mdi:home` als Rückweg auf eine Unterseite, aber ebenso `entity: light.bad_lights`, wo der
Navigationsplatz schlicht ein Licht schaltet. Entities kommen ab dem zweiten Zeichen und auf 50
Treffer begrenzt dazu, damit nicht die halbe Installation im DOM steht; `delete` für den bewusst
freien Platz steht ebenfalls in der Liste.

## 0.14.0 – 2026-07-27

### Die Status-Symbole sind jetzt wirklich einstellbar

Im letzten Eintrag stand, die beiden Status-Symbole seien „bearbeitbar, nur nicht sichtbar". Das
stimmte nicht: im Formular stand an ihrer Stelle ein Textfeld mit dem Inhalt `[object Object]`. Der
Editor kannte für diese Felder zwar einen eigenen Widget-Namen (`entity_object`), hatte ihn aber
nirgends gebaut – also fiel das Dict bis zum allgemeinen Textfeld durch, und dort wird aus einem
Objekt eben jene Zeichenkette. Wer sie angeklickt und etwas hineingeschrieben hätte, hätte das Feld
überschrieben.

`statusIcon1`/`statusIcon2` klappen sich jetzt an Ort und Stelle auf und zeigen darin die Felder
einer Entity-Zeile, mit Icon-Picker, Farbwähler und Template-Umschalter. Dasselbe gilt für
`navItem1`/`navItem2` – dieselben zwei Zeilen Code, und die stehen auf **jeder** Karte, nicht nur auf
der Ruheanzeige. Ist nichts gesetzt, steht dort *nicht gesetzt* und ein **anlegen**; das ✕ entfernt
den Key wieder ganz, statt ein leeres Dict zurückzulassen.

**`altFont` ist dabei ein eigenes Ja/Nein-Feld geworden.** Bisher galt der Key als unbekannt und
landete beim Import im `extra`-Dict des Symbols – erhalten blieb er, einstellbar war er nur als JSON.
Da ihn ausschließlich der Screensaver-Renderer liest, ist er auch nur *dort* benannt
(`ENTITY_LIKE_EXTRA_FIELDS`): auf einer gewöhnlichen Entity-Zeile bleibt `altFont` weiterhin ein
unbekannter Key, weil er dort nichts bewirkt. Bereits gespeicherte Konfigurationen, in denen er noch
im `extra`-Dict steht, erzeugen unverändert dieselbe YAML.

## 0.13.0 – 2026-07-27

### Die Ruheanzeige zeigt ihre beiden Status-Symbole

Oben links und rechts trägt der Screensaver zwei kleine Felder (`statusIcon1`/`statusIcon2`) – bei
vielen Panels der Heizungs- oder Wetterwert, den man den ganzen Tag sieht. In der Vorschau fehlten
sie bisher ganz: bearbeitbar waren sie, sichtbar nicht.

Sie sind kein gewöhnlicher Listeneintrag, und daran lag es. Ein Feld darf **Symbol und Text zugleich**
tragen: aus `<I>mdi:fireplace</I> ha:{{ … }} °C` ersetzt das Backend nur den `<I>…</I>`-Teil durch das
Zeichen und rendert den Rest weiter – auf dem Display steht dann das Flammensymbol *und* der Messwert.
Die Vorschau setzt beides jetzt genauso zusammen und färbt, wie das HMI es tut, Symbol und Text
gemeinsam.

In der Live-Ansicht kommen sie aus einer **eigenen Nachricht** (`statusUpdate~…`, aus
`update_status_icons`) und gehören keiner Karte: der Mitschnitt hält sie deshalb neben den Karten,
sodass ein Kartenwechsel sie nicht ungültig macht und eine Statusnachricht umgekehrt keinen
Karten-Mitschnitt überschreibt. Sendet ein Panel keine – weil nichts konfiguriert ist –, bleiben die
beiden Stellen leer statt gefüllt zu wirken.

## 0.12.1 – 2026-07-27

### Auf dem Raster steht bei Sensoren der Messwert, kein Symbol

Auf `cardGrid` fehlten in der Vorschau die Werte, und an ihrer Stelle stand der Platzhalter-Kreis.
Der Grund ist eine Eigenheit des Backends, die man sonst erst am Gerät sieht (`pages.py`): auf einem
Raster ist kein Platz für Symbol *und* Wert, also tritt bei `sensor`-Entities **ohne eigenes `icon`**
der Zustand an die Stelle des Symbols – gekürzt auf vier Zeichen, und endet der Ausschnitt auf einen
Punkt, auf drei (`21.53` → `21.5`, `100.0` → `100`).

Die Vorschau bildet das jetzt nach, in beiden Modi: aus der Konfiguration über dieselbe Regel, in der
Live-Ansicht daran, dass im Icon-Feld Text statt eines Symbolzeichens ankommt. Ein selbst gesetztes
`icon` gewinnt weiterhin, und auf Karten mit eigenem Wertfeld (`cardEntities` …) ändert sich nichts.

Nebenbei behoben: die Erkennung „Symbol oder Text?" hatte am klassischen PUA-Ende (U+F8FF) eine zu
enge Grenze – das Mapping des Backends reicht bis U+FAEF. Icons daraus wären als Text durchgerutscht.

## 0.12.0 – 2026-07-26

### Karte gezielt am Gerät aufrufen

Die Live-Ansicht hing davon ab, was das Panel zufällig zeigte – im Ruhezustand also immer der
Screensaver. Neben der Displayfläche steht jetzt **„Karte am Gerät aufrufen"**: ein Klick, und das
Panel springt auf die gerade bearbeitete Karte.

Gesendet wird dabei auf dem `panelRecvTopic` genau die Nachricht, die auch das Panel bei einem
Tastendruck schickt (`event,buttonPress2,navigate.<key>,button`). **Das Gerät wechselt sichtbar die
Anzeige** – geschaltet wird nichts, und es passiert nur auf Klick. Auf das *Sende*-Topic schreibt die
Integration weiterhin nie. Voraussetzung ist ein `key` an der Karte; fehlt er, sagt der Editor das an
dieser Stelle.

### Wichtig für `reload_mode: touch_module` – es muss die `apps.yaml` sein

Beim Prüfen des Kartenaufrufs kam heraus: Tickt man **das App-Modul** (`apps/nspanel.py`) an, startet
AppDaemon die App zwar sichtbar neu (*Modified Python files* → *Started*), **liest die per `!include`
eingebundene Konfiguration dabei aber nicht neu ein**. Die frisch erzeugte YAML bleibt wirkungslos –
und das merkt man nur daran, dass sich am Panel nichts ändert.

Nachgemessen: nach dem Anticken der `.py` fand das Backend einen neu vergebenen `key` nicht, nach dem
Anticken der `apps.yaml` sofort. Hinweistexte, Voreinstellungen und Doku nennen jetzt durchgängig die
`apps.yaml`. Wer `restart_container` oder `restart_addon` nutzt, war davon nie betroffen.

### Farbe des Symbols abgesichert

`ha-icon` füllt sein SVG mit `var(--icon-primary-color, currentcolor)`. Ist die Variable von einem
Theme gesetzt, gewinnt sie gegen die geerbte Farbe – die Vorschau setzt jetzt beides.

Neu ist außerdem `tests/draw.test.mjs`: fünf Tests der Zeichenschicht gegen eine minimale
DOM-Attrappe. Die bisherigen Tests prüften Geometrie und Inhalt, aber nicht das Zusammensetzen –
genau dort saß der Fehler mit der Farbe am falschen Element.

## 0.11.0 – 2026-07-26

Drei Rückmeldungen von der echten Anlage.

### Die Live-Ansicht merkt sich jetzt jede Karte einzeln

**„Macht keinen Sinn, weil im Standby immer der Screensaver aktiv ist"** – zu Recht: eine Ansicht,
die nur die *letzte* Nachricht zeigt, ist beim Bearbeiten einer Karte nutzlos, weil das Panel die
meiste Zeit ruht.

Der Mitschnitt legt den Stand deshalb **je Karte** ab (Schlüssel ist der Titel, beim Screensaver die
Bauart). Wer am Gerät einmal durchblättert, hat danach für jede Karte den echten Stand; der Editor
fragt beim Bearbeiten gezielt danach (`GET /live?card=…&type=…`) und zeigt sie mit Zeitpunkt an –
auch Stunden später, wenn das Panel längst wieder im Ruhezustand ist. War eine Karte noch nie dran,
sagt die Ansicht das und zeigt solange, was gerade läuft.

### Die Farbe gehört auf das Symbol

Die Vorschau färbte den ganzen Platz – dadurch wurden Name und Wert bunt, während das Symbol weiß
blieb. Auf dem Gerät ist es genau umgekehrt: das HMI schreibt die übertragene Farbe in die
Schriftfarbe der Icon-Komponente (`covx tTmp.txt,tF1Icon.pco`), die Textfelder behalten ihre feste
Farbe. Jetzt trägt das Symbol die Farbe – auch die aus einem `color`-Template.

### Nebenmodule bekommen die Versions-Query mit

Home Assistant hängt an die Panel-URL `?v=<Version>`; die davon importierten Module
(`preview-layouts.js`, `layouts.js`, die Icon-Listen) bekamen keinen Parameter und blieben nach
einem Update im Browser-Cache liegen. Dann lief das neue Panel mit alter Geometrie – ein Fehler, der
wie ein nicht installiertes Update aussieht (und die doppelte Uhrzeit aus 0.10.1 überdauern ließ).
Die Module werden jetzt dynamisch mit derselben Query geladen, die `import.meta.url` trägt.

## 0.10.3 – 2026-07-26

### Brand-Bilder aufgeräumt – und die Sache mit dem HACS-Symbol geklärt

Die Icons waren oben und unten transparent aufgefüllt, damit vom nicht-quadratischen Foto nichts
verlorengeht. Sauberer ist ein **quadratischer Ausschnitt**: er füllt die Fläche, wie es sich für
ein Icon gehört – und Home Assistant zeigt genau diese Datei an der Integration an.

**Zum Symbol in der HACS-Übersicht, das dort weiterhin fehlt:** Ein Eintrag im
[brands-Repo](https://github.com/home-assistant/brands) hilft nicht – er ist seit Home Assistant
2026.3 gar nicht mehr möglich, das Repo nimmt für Custom-Integrationen keine Beiträge mehr an
([Ankündigung](https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api)). Dass HACS
trotzdem den Platzhalter zeigt, liegt daran, dass es seine Bild-URLs noch fest gegen das CDN baut
statt über den lokalen Proxy. Dort ist es bekannt (hacs/frontend#937, hacs/integration#5179) und
kommt mit einer künftigen HACS-Version; von hier aus lässt sich daran nichts ändern.

- `tools/make-brand-images.mjs` erzeugt alle vier Dateien reproduzierbar aus derselben Quelle: Icons als mittiger
  **quadratischer Ausschnitt** (256×256, 512×512) – beschnitten wird nur der seitliche
  Geräterahmen –, Logos aus dem vollen Bild (304×256 und 607×512, die vom Repo erlaubten Bereiche
  für die kürzeste Seite).
- `logo@2x.png` ist neu; Home Assistant nutzt sie auf hochauflösenden Anzeigen.
- `tests/test_manifests.py` prüft die Maße mit – sie fielen sonst erst im PR auf.

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
