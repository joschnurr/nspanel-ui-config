# Änderungen

Format lose nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).
Bis 1.0 kann sich alles ändern.

## 0.32.0 – 2026-08-08

### Symbole ohne eigene Farbe waren in der Vorschau zu hell

Am Gerät ist ein Symbol ohne konfigurierte `color` **gedämpft blau**, solange nichts „an" ist —
die Vorschau zeigte es weiß. Der Grund: Sie nahm die Schriftfarbe der HMI-Komponente, die das
Backend zur Laufzeit aber immer überschreibt.

Nachgebildet ist jetzt `get_entity_color` aus `pages.py`, und die Regel ist kurz: Gelb
(253, 216, 53), wenn der Zustand als „an" gilt — dazu zählen neben `on` auch `unlocked`, `home`,
`active` und `above_horizon` —, sonst Blaugrau (68, 115, 158). Für Alarmanlage und Klima hat das
Backend eigene Tabellen, die ebenfalls übernommen sind; das Wetter hatte seine schon.

Navigationsziele bekommen immer die Aus-Farbe: Für das Backend sind sie gar keine Entity.

Eine konfigurierte Farbe schlägt die Regel weiterhin, ebenso die zustandsabhängige Form
`{on, off}` und ein Farb-Template — letzteres wird wie bisher über HAs Engine gerendert und
nicht vorher überschrieben.

**Testlage: 201 Python + 166 Node.**

## 0.31.0 – 2026-08-08

### Jedes zwölfte Symbol fehlte in der Live-Ansicht

Auf `cardGrid` und `cardGrid2` blieben Symbole leer, obwohl das Gerät sie zeigt. Die Ursache liegt
tiefer als vermutet und betrifft alle Kartentypen:

**496 der 6896 Symbole des Backends liegen zwischen U+F900 und U+FAFF** — das ist der Bereich der
CJK-Kompatibilitätsideogramme. Unicode bildet die in *jeder* Normalform auf ein anderes Zeichen ab:
Aus U+F986 (`light-flood-down`) wird 閭, das gewöhnliche Zeichen U+95AD. Irgendeine Stelle der Kette
vom Backend über MQTT bis zur Vorschau normalisiert, und danach stand das Zeichen nicht mehr in der
Symboltabelle. Die Rückübersetzung fand nichts, und schlimmer noch: Weil das Ergebnis unter U+E000
liegt, galt es als gewöhnlicher Text — die Vorschau schrieb also ein chinesisches Schriftzeichen
dorthin, wo das Gerät ein Symbol zeigt.

Statt die normalisierende Stelle zu suchen, wird jetzt zurückgerechnet: Eine Tabelle bildet die
Normalform jedes betroffenen Zeichens auf seinen Symbolnamen ab. Sie entsteht einmal beim Laden aus
derselben Liste, die auch den Hinweg trägt — es gibt also nichts, was auseinanderlaufen könnte.

Dass gewöhnlicher Text weiterhin Text bleibt, ist mitgeprüft: Ein CJK-Zeichen, das *nicht* aus der
Symbolliste stammt, gilt nach wie vor als Text. Auf dem Raster ist das wichtig, denn dort schickt
das Backend bei Sensoren den Messwert ins Symbolfeld.

**Testlage: 201 Python + 163 Node.**

## 0.30.1 – 2026-08-07

Der QR-Code aus 0.30.0 blieb unsichtbar — der graue Kasten stand weiter da.

**Ursache:** Am Anfang von `_slotElement` steht eine Tabelle für Flächen, die nur angedeutet
werden (Regler, Tastatur …). Dort war der QR-Code noch eingetragen, und die Tabelle wird
**vor** allen spezialisierten Abfragen geprüft. Sie fing den Platz also ab, und die neue
Zeichenfunktion lief nie an. Der Eintrag ist entfernt.

Damit das nicht wiederkommt, prüft `tests/test_panel_assets.py` jetzt, dass keine Art zugleich in
der Platzhalter-Tabelle steht **und** eine eigene Zeichenfunktion hat. Der Test wurde in beide
Richtungen geprüft: Mit wieder eingetragenem QR-Eintrag schlägt er fehl, ohne ihn ist er still.

**Testlage: 201 Python + 160 Node.**

## 0.30.0 – 2026-08-07

### Der QR-Code wird gezeichnet, nicht angedeutet

Auf `cardQR` stand in der Vorschau bisher ein Kasten mit der Aufschrift „QR-Code". Das beantwortet
die einzige Frage nicht, die man an dieser Karte hat: **Funktioniert der Code?** Ein WLAN-String
(`WIFI:S:…;T:WPA;P:…;;`) kann ein Semikolon zu wenig haben oder ein Template, das ins Leere
rendert — dem Text sieht man das nicht an, dem Code schon. Jetzt steht dort der echte QR-Code,
und man kann ihn mit dem Telefon scannen.

Dafür ist ein eigener Erzeuger dazugekommen (`www/panel/qr.js`, Byte-Modus, Fehlerkorrektur L,
Versionen 1–10). **Warum nicht `ha-qr-code`:** Das Element gibt es im HA-Frontend, es liegt aber in
einem nachgeladenen Bündel und ist nur definiert, wenn eine HA-Ansicht es zuvor gebraucht hat —
darauf kann sich ein Custom Panel nicht verlassen, und der Bündelname ändert sich mit jeder
HA-Fassung.

**Geprüft wurde bitgenau gegen fremde Umsetzungen:** libqrencode 4.1.1 (die C-Referenz), nayukis
`qrcodegen` und `python-qrcode` stimmen über 67 Texte und die Versionen 1–10 hinweg überein — und
mit dieser Umsetzung ebenfalls, in allen 67 Fällen. ZXing dekodiert die erzeugten Codes fehlerfrei
zum Ausgangstext.

Der Code rückt in die Mitte, sobald die Karte keine Einträge hat — auch das steht so im
Seitencode (`if(type2 leer){ if(type1 leer){ qrcode m1 } } else { qrcode m0 }`) und ist nicht
geschätzt. Templates im `qrCode`-Feld werden wie überall über HAs eigene Engine gerendert, die
Vorschau zeigt also den Code mit den echten Werten.

### cardChart ist aus der Testkonfiguration entfernt

Die Karte lässt sich nicht sinnvoll darstellen (das Display malt die Balken mit Zeichenbefehlen,
es gibt keine Bauteile) — und sie ist mit aktuellem Home Assistant ohnehin defekt:
`generate_chart_page` im Backend reicht `last_updated` an `datetime.fromisoformat`, bekommt dort
inzwischen aber bereits ein `datetime` und bricht mit `TypeError` ab. Das ist ein Fehler des
Backends, nicht dieser Integration; der Kartentyp bleibt wählbar, taugt derzeit aber nicht.

**Testlage: 200 Python + 160 Node.**

## 0.29.0 – 2026-08-07

Von zehn Kartentypen zeigten drei in der Vorschau nur einen grauen Kasten, und vier lieferten in
der Live-Ansicht nichts. Diese Fassung schließt den größten Teil davon — und korrigiert dabei eine
Annahme, die seit der ersten Live-Ansicht falsch war.

### cardMedia war nie „unstrukturiert"

Die Karte stand in `UNSTRUCTURED_PAGES`, also unter denen, die das Backend *nicht* aus
Eintragsblöcken baut. Das stimmt nicht: Nach der Navigation stehen neun eigene Felder (Titel,
Interpret, Lautstärke, Play/Pause, Ein/Aus, Zufallswiedergabe), und **danach folgen die ganz
normalen 6er-Blöcke** ab Feld 23. Belegt ist das doppelt — über die `spstr`-Nummern des
Seitencodes und über den f-String in `generate_media_page`.

Zwei Dinge sieht man der Nachricht dabei nicht an, und sie stehen deshalb im Code:

- **Der erste Block ist der Medienplayer selbst, der letzte die Lautsprecherauswahl.** Die Rolle
  folgt der *Position*, nicht dem `type`-Feld: Ist an der Karte `status:` gesetzt, trägt der
  letzte Block eine ganz andere Domäne.
- **`disable` heißt „am Gerät unsichtbar", ein leeres Feld heißt „vorhanden, ohne Wert".** Der
  Fehlerfall („Not found") schickt leer — wer beides gleich behandelt, blendet dort fälschlich aus.

### cardAlarm ist abgemessen — und cardUnlock gleich mit

`cardUnlock` hat **keine eigene Display-Seite**: Das Backend schreibt sie in `page_type()` auf
`cardAlarm` um, bevor der Kartentyp ans Panel geht. Beide teilen sich damit Geometrie und Parser.

Die Namen der zwölf Tastaturtasten führen in die Irre: `b0`…`b8` sind die Ziffern 1–9, `b10` die
Null, `b11` löscht — und **`b9` ist keine Ziffer**, sondern die Zusatztaste unten links. Sie ist
die einzige der zwölf, die das Backend überhaupt füllt.

Wie viele Aktionstasten erscheinen, entscheidet die Anlage: unscharf so viele, wie
`supported_features` meldet, in jedem anderen Zustand genau eine („Deaktivieren"). Die
Zifferntastatur entfällt nur, wenn die Anlage unscharf ist *und* zum Scharfschalten keinen Code
verlangt. Beides bildet die Vorschau nach, statt vier Tasten zu zeigen, die es nicht gibt.

### Die Formatprüfung, die vorher gefehlt hat

`entity` ist auf einer Ein-Entity-Karte ein reiner Text, in `entities:` dagegen ein Objekt.
Verwechselt man das, bricht das Backend beim Registrieren der Callbacks ab — **bevor irgendetwas
gezeichnet wird**, das Panel bleibt also komplett dunkel. Die Validierung meldet das jetzt als
Fehler, statt es bis zum nächsten Erzeugen unbemerkt zu lassen.

### Was bewusst offen bleibt: cardChart

Die Seite hat **gar keine Diagramm-Bauteile**. Das Display malt die Balken beim Eintreffen der
Nachricht mit Zeichenbefehlen (`fill`, `line`, `xstr`) direkt auf die Fläche — es gibt nichts, was
sich vermessen oder einem Bauteil zuordnen ließe. Die Karte bleibt deshalb bei der
Flächen-Darstellung.

**Testlage: 199 Python + 152 Node.**

## 0.28.0 – 2026-08-07

Die Vorschau aus der Konfiguration zeigte den Thermostat seit v0.27 – die **Live-Ansicht** blieb
leer. Sie kannte das Format der Karte nicht und lieferte nur den Titel.

### cardThermo hat ein eigenes Nachrichtenformat, und das wird jetzt gelesen

Alle anderen Karten bestehen aus 6er-Blöcken je Eintrag. Der Thermostat nicht: Er schickt
Ist-Temperatur, Sollwert, Zustand, Grenzen, acht Betriebsarten zu je vier Feldern, drei
übersetzte Beschriftungen, das Einheitensymbol, den zweiten Sollwert und ein Kennzeichen für die
Detailseite – alles am Stück.

**Die Feldnummern sind abgelesen, nicht gezählt.** Der Seitencode des HMI-Dumps holt sich seine
Werte mit `spstr strCommand.txt,<ziel>,"~",<nummer>`: `tCurTemp` steht auf 15, `tStatus` auf 17,
`bt0.txt` auf 21 und jede weitere Taste vier Felder später. Das bestätigt zugleich, dass die
Navigation genau zwölf Felder belegt.

Was dadurch in der Live-Ansicht steht, ist **gemessen statt hergeleitet**: die Beschriftungen in
der Sprache des Geräts, der Zustandstext so, wie das Backend ihn übersetzt und um die Aktion
ergänzt hat, und die Betriebsarten mit dem Symbolzeichen des Nextion-Fonts und der Farbe, die das
Display wirklich bekommen hat.

Zwei Kleinigkeiten, die dabei nicht geraten wurden:

- **Ungenutzte Betriebsartentasten bleiben weg.** Das Backend füllt die Nachricht immer auf acht
  Tasten auf; die überzähligen sind vier leere Felder und am Gerät ausgeblendet. Als leere
  Kästchen zu erscheinen wäre eine Behauptung.
- **Die Detailtaste folgt dem Seitencode.** `if(tTmp.txt!="1") vis btDetail,1` – sie erscheint
  genau dann, wenn das letzte Feld *nicht* "1" ist, also wenn die Entity Preset-, Schwenk- oder
  Lüftermodi kennt.

**Testlage: 189 Python + 148 Node.**

## 0.27.0 – 2026-08-07

Der Thermostat war die letzte häufig genutzte Karte, die in der Vorschau nur als grauer Kasten mit
der Aufschrift „Thermostat-Bedienung" dastand. Jetzt ist auch sie abgemessen — und dabei kam ein
Fehler im Extraktor ans Licht, der ihn seit jeher blind für einen ganzen Bauteiltyp machte.

### Der Dump-Parser übersah jeden „Dual-state Button"

Getrennt wurden die Bauteile des HMI-Dumps bisher am Muster `[A-Za-z]+ \S+` — also „ein Wort, ein
Name". Der Nextion-Typ heißt aber **`Dual-state Button`**: mit Bindestrich und zwei Leerzeichen.
Sein Attributblock landete deshalb beim jeweils vorherigen Bauteil, wo die zweite Koordinatenangabe
schlicht ignoriert wurde.

Auf `cardThermo` sind das **15 von 35 Bauteilen**: die acht Betriebsartentasten, beide
Plus/Minus-Paare und die Detailtaste — alle spurlos verschwunden. Getrennt wird jetzt an jeder
nicht eingerückten Zeile; das ist unabhängig davon, wie der Typ heißt. Für die bereits
abgemessenen Karten ändert sich dadurch nichts (nachgewiesen: `layouts.js` blieb bis auf den neuen
Abschnitt zeichengleich).

### cardThermo zeigt jetzt, was das Gerät zeigt

Statt eines Platzhalters stehen die echten Flächen da: links Ist-Temperatur und Zustand, mittig der
Sollwert, unten die Betriebsarten — auf allen drei Modellen.

Gefüllt werden sie **aus der Entity**, denn genau das tut das Backend auch: Konfiguriert wird auf
dieser Karte nur, welche Entity gilt. Drei Dinge entscheidet sie, und die Vorschau liest sie
genauso ab wie `generate_thermo_page`:

| Was | Woran es hängt |
| --- | --- |
| ein oder zwei Sollwerte | `temperature` gesetzt → einer, sonst `target_temp_high`/`_low` → zwei |
| welche Tasten dazu | ein Sollwert: die großen Plus/Minus; zwei: zwei kleine Paare |
| wie viele Betriebsarten | `hvac_modes`, überschreibbar per `hvacModes` auf der Karte |

Beide Bedienbilder gleichzeitig gibt es am Gerät nie — der Seitencode blendet das jeweils andere
aus (`vis btUp1,0` …). Ohne gewählte Entity bleiben die Betriebsartentasten leer, statt acht zu
zeigen, die es vielleicht nie gibt: Eine Taste, die es nicht gibt, sieht aus wie eine Möglichkeit,
die es nicht gibt.

Farben und Symbole der Betriebsarten sind die des Backends (`heat` orange, `cool` blau, `auto`
grün, `off` grau); hervorgehoben wird die, in der die Entity gerade steht.

**Testlage: 186 Python + 148 Node.**

## 0.26.0 – 2026-08-01

Aus einem Vergleich von Gerätefoto und Vorschau nebeneinander — drei Befunde, einer davon betrifft
**alle** Karten.

### Die Vorschau zeigte Blättertasten, die es am Gerät nicht gibt

Auf einer Unterseite steht am Panel oben links ↑ und oben rechts **nichts**. Die Vorschau malte
dort ein ▶. `render_card` in `pages.py` ist eindeutig: Beide Tasten beginnen mit `delete~~~~~`, also
leer, und werden nur unter Bedingungen gefüllt.

| Lage | links | rechts |
| --- | --- | --- |
| versteckte Karte (Unterseite) | ↑ `navUp` | leer |
| sichtbare Karte, mehrere davon | ◀ | ▶ |
| sichtbare Karte, die einzige | leer | leer |
| `navItem1`/`navItem2` gesetzt | das konfigurierte Symbol | dito |

Der letzte Fall galt schon, die anderen drei nicht. Dass bei **einer** sichtbaren Karte gar nichts
steht, liegt an `config.py`: `uuid_prev`/`uuid_next` werden nur bei `len(card_uuids) > 1` vergeben.
Im Mitschnitt wird nichts abgeleitet — dort steht, was das Gerät bekommen hat.

Eine Taste, die es nicht gibt, ist kein Schönheitsfehler: Sie sieht aus wie ein Weg, den es gibt.

### Die Mitte von cardPower war falsch zugeordnet

`tHome` und `tHome2` sahen wie zwei Einträge aus. Der Seitencode sagt etwas anderes:

```
spstr strCommand.txt, t1.txt,     "~", 16   # Symbol von Eintrag 0
spstr strCommand.txt, tHome.txt,  "~", 19   # Wert  von Eintrag 0
spstr tHome.txt, tHome2.txt, " ", 1         #   am ersten Leerzeichen geteilt:
spstr tHome.txt, tHome.txt,  " ", 0         #   Zahl nach tHome, Einheit nach tHome2
spstr strCommand.txt, tHomeO.txt, "~", 26   # Wert  von Eintrag 1 (ebenso)
```

Die Feldnummern gehen auf: 12 Navigationsfelder (zwei Tasten à 6) und 7 Felder je Eintrag
(`generate_entities_item` liefert 6, `cardPower` hängt `speed` an). Eintrag 0 liegt damit auf
14…20 — Symbol 16, Wert 19 —, Eintrag 1 auf 21…27 mit Wert 26.

Es sind also **zwei Einträge mit je Zahl und Einheit**, nicht vier Felder. Die Vorschau teilt den
Wert jetzt am ersten Leerzeichen und setzt die Zahl groß, die Einheit klein darunter. Außerhalb von
`cardPower` bleibt ein Wert ganz — „21.5 °C" gehört auf `cardGrid` in ein Feld.

### Der Rahmen des Home-Feldes und sein Symbol

`t1` ist **Rahmen und Symbol in einem**: ein 60×230 hohes Feld mit `Style: border`, dessen Text die
Symbolglyphe trägt (`Font ID 3`). Genau deshalb steht das Haussymbol am Gerät mittig in der
umrandeten Mittelsäule — mit dem Wert von Eintrag 1 darüber und dem von Eintrag 0 darunter. In der
Vorschau fehlte beides, weil `t1` keinem Platz zugeordnet war. Eintrag 1 hat kein eigenes Symbol;
dort steht auch am Gerät nur eine Zahl.

`layouts.js` ist neu erzeugt. Kontrolllauf: Von den 24 Kombinationen haben sich **genau die drei
cardPower-Layouts** geändert, alle anderen sind unverändert.

## 0.25.0 – 2026-07-31

### Die Symbole von cardPower stehen jetzt in ihrem Feld, wie auf dem Gerät

Gemeldet nach den Laufbalken: „die Umrandung wie im Original fehlt auch noch". Sie fehlte
tatsächlich — und sie war die ganze Zeit im Dump abgemessen vorhanden, nur nicht ausgelesen:

```
Text t0Icon
    Width : 60    Height : 60
    Style        : border
    Border Color : 17299
    Border Width : 2
```

`tools/extract_layouts.py` liest `Style: border` samt Farbe und Breite jetzt mit, dort wo auch
Font, Ausrichtung und Schriftfarbe herkommen. Die Vorschau zeichnet daraus `2px solid #42719c`
(RGB565 17299) um jedes der sechs äußeren Symbolfelder. **Abgemessen, nicht nachempfunden.**

Zwei Feinheiten, die sonst falsch geworden wären:

- **`Style` muss mitgeprüft werden.** Auch Name- und Wertfelder tragen eine `Border Color`, stehen
  aber auf `flat` und benutzen sie nie. Wer nur die Farbe liest, malt der halben Karte Kästchen an.
- **Der Rahmen gehört zum Feld, die Farbe zum Inhalt.** Eine konfigurierte Farbe färbt weiterhin
  das Symbol; der Rahmen bleibt der des Geräts. Sonst zeichnete ein rot eingefärbter Eintrag ein
  rotes Kästchen, das auf dem Display nie erscheint.

Die beiden mittleren Plätze bekommen keinen Rahmen — das Gerät hat dort auch keinen. Ein Test
prüft beides, und ein zweiter hält fest, dass **außer cardPower keine Karte** umrandete Felder hat.

`layouts.js` ist dafür neu erzeugt worden. Kontrolllauf wie beim letzten Mal: Bis auf die neuen
`bc`/`bw` ist die Datei zeichengleich mit der vorigen, alle 24 Kombinationen stimmen weiter mit
`CARD_CAPACITY`.

## 0.24.3 – 2026-07-30

### Die Laufbalken fehlten wirklich – ein statischer Import hat die Kennung fallen lassen

Der Editor lief nachweislich auf der neuen Fassung (die Kopfzeile zeigte sie), die Balken blieben
trotzdem weg. Die Ursache liegt eine Ebene tiefer, als bisher gesucht wurde:

`preview-layouts.js` wurde **mit** Kennung geladen, holte sich die Geometrie daneben aber per
`import { LAYOUTS } from "./layouts.js"`. Ein statischer Import löst den Pfad relativ zur
importierenden Datei auf und **lässt die Query dabei fallen**. Der Browser fragte also
`layouts.js` ohne Kennung an und bekam seine zwischengespeicherte Fassung — eine aus der Zeit vor
0.24.0, die `flow` noch nicht kannte. `LAYOUTS.cardPower.eu.flow` war damit `undefined`, die Liste
der Balken leer. Alles andere sah richtig aus, weil die übrige Geometrie seit Wochen unverändert
ist.

`layouts.js` wird jetzt dynamisch geladen, mit der Query aus `import.meta.url`. Die Kennung reicht
damit durch die **ganze** Kette, nicht nur bis zur ersten Ebene.

### Der Test sah nur die Hauptdatei an

Es gab bereits eine Prüfung gegen statische Importe — sie las aber ausschließlich
`nspanel-ui-config-panel.js`. Genau daran ist das hier vorbeigelaufen. Geprüft werden jetzt **alle**
Panel-Module, auf statische Nachbarimporte ebenso wie auf dynamische ohne Query. Gegenprobe
gemacht: Mit dem alten Import schlägt der Test fehl.

## 0.24.2 – 2026-07-30

### Die Laufbalken waren da – nur kaum zu sehen

Nachgemessen mit der echten Karte und dem echten Schema einer laufenden Anlage: Das Layout liefert
sechs Balken, `_slotElement` zeichnet alle siebzehn Plätze ohne Ausnahme, und die vier
`speed`-Templates werden zum Rendern angemeldet. Fehlte also nichts — die Spur war nur mit 8 % Weiß
gezeichnet und auf dem fast schwarzen Displaygrund praktisch unsichtbar.

Der Dump gibt keine Farbe her: Der Slider ist mit einem Bild gefüllt (`Fill: image`,
Back. Picture ID 20). Er nennt aber `Opacity: 127` — auf dem Gerät ist die Spur halbtransparent
hell. 20 % Weiß mit einer feinen Kante ist damit **näher am Original** als der bisherige Wert und
zugleich das, wozu eine Vorschau da ist.

## 0.24.1 – 2026-07-30

### Ein Update konnte auf der Platte liegen und trotzdem nicht ankommen

Gemeldet als „auf cardPower fehlen die Laufbalken". Sie fehlten nicht: Dateien, Layout-Daten, CSS
und Zeichencode waren vollständig ausgeliefert, und der Weg vom Layout bis zum fertigen Element ist
nachgemessen worden — sechs Balken, richtige Maße, laufender Punkt. Ausgeliefert wurde trotzdem die
alte Fassung.

Der Grund liegt daran, wie Home Assistant ein Custom-Panel anmeldet: Die Adresse steht fest, sobald
der Config-Entry eingerichtet ist, und HA hängt von sich aus nichts daran. Die Version dafür kam aus
`async_get_integration` — und die liest HA **einmal beim Start**. Wer die Dateien einer laufenden
Instanz austauscht (hier der übliche Weg, weil HACS neue Fassungen stundenlang nicht anbietet),
bekommt deshalb weiter die alte Adresse. Dazu kommt, dass die Assets **ohne `Cache-Control`**
ausgeliefert werden; was der Browser damit macht, ist Auslegungssache. Das Ergebnis ist in beiden
Fällen dasselbe Bild: Der Editor zeigt eine alte Versionsnummer in der Kopfzeile, und die neue
Funktion ist nicht da.

Version **und** Dateistand kommen jetzt von der Platte: die Nummer direkt aus `manifest.json`, dazu
ein kurzer Fingerabdruck über Größe und Zeitstempel der Panel-Dateien (`v=0.24.1&b=1a2b3c4d`).
Ändert sich eines von beidem, ändert sich die Adresse.

**Praktische Folge: Ein Neuladen der Integration genügt jetzt für neue Editor-Dateien** — unter
*Einstellungen → Geräte & Dienste → NSPanel UI Config → Neu laden*. Ein voller Neustart ist dafür
nicht mehr nötig. Er bleibt nötig, wenn sich Python geändert hat.

### Zwei Tests, die genau diese Lücke schließen

Die Laufbalken waren getestet — aber nur, indem der Test `_flowSlot` direkt aufrief. Gezeichnet wird
über `_slotElement`, wo eine Kette von `kind`-Abfragen entscheidet, wer welchen Zweig bekommt. Fiele
„flow" dort durch, wäre auf dem Gerätebild nichts zu sehen und kein Test würde es merken. Der Weg
ist jetzt abgedeckt, ebenso die Zuordnung jedes Balkens zu genau einem Außenplatz.

## 0.24.0 – 2026-07-30

### Auf cardPower fehlte das, was die Karte ausmacht

Die Vorschau zeichnete acht Textfelder an abgemessenen Stellen — und dazwischen nichts. Auf dem
Gerät liegt dort das Auffälligste der Karte: sechs Balken zwischen der Mitte und den Außenplätzen,
auf denen je ein Punkt den Energiefluss anzeigt.

Der Grund, warum sie fehlten, steckt im Dump: es sind Nextion-**Slider**, keine Textfelder, und die
Slot-Tabelle sammelt Textfelder. `tools/extract_layouts.py` liest sie jetzt mit, samt Bereich,
Startwert und Ausrichtung — die Balken sind damit **abgemessen wie alles andere**, nicht
nachempfunden. Ein Kontrolllauf gegen die unveränderten Dumps hat vorher bestätigt, dass das
Werkzeug den bisherigen Stand zeichengenau reproduziert; die neue Fassung unterscheidet sich also
nur um die Balken.

Der Laufpunkt bildet den Seitencode nach statt einer Vorstellung davon: alle 100 ms addiert das
Display `speed` auf den Sliderwert, Bereich 0–1200, am Ende springt er auf die andere Seite. Ein
Umlauf dauert deshalb `1200 / |speed| · 0,1 s` — bei `speed: 20` sechs Sekunden, und genau so lange
läuft er auch in der Vorschau. Zwei Eigenheiten sind übernommen, nicht geglättet: gedeckelt wird auf
**±120**, obwohl die Upstream-Doku ±100 nennt, und im Querformat dreht der Seitencode das Vorzeichen
für alle sechs Balken (`if(p0.h==320)`), wodurch die Punkte einheitlich über die Karte laufen.
Hochkant stehen die Balken senkrecht, dort entfällt der Dreher.

`speed` ist in der Praxis fast immer ein Template — es rechnet den Anteil an der Gesamtleistung aus.
Es geht deshalb durch dieselbe Sammelanfrage wie Name, Wert, Symbol und Farbe; bis die Antwort da
ist, steht der Punkt still. Auch die Live-Ansicht kann ihn: `speed` ist das siebte Feld der
Nachricht, `protocol.py` hebt es ohnehin auf.

## 0.23.1 – 2026-07-30

### Das Icon hatte Balken, wo es keine haben sollte

Aufgefallen bei der Frage, warum HACS das Icon nicht zeigt (dazu unten). Beim Nachmessen der
mitgelieferten Brand-Bilder: `icon.png` war das ganze, querformatige Motiv in ein Quadrat gelegt —
mit 9 px einfarbigem Rand oben und 12 px unten, `icon@2x.png` entsprechend 19 px. Auch `logo.png`
trug ringsum einen schwarzen Saum. Die Spezifikation von `home-assistant/brands` verlangt
beschnittene Bilder ohne solche Leerflächen, und als Avatar wirkt ein randloses Motiv ohnehin
kompakter.

Alle vier Dateien sind deshalb neu aus `docs/brand-source.jpg` gerechnet: schwarzer Rand
abgeschnitten, das Icon **mittig auf ein Quadrat beschnitten** statt mit Balken gefüllt, das Logo im
ursprünglichen Seitenverhältnis. Maße wie gefordert — Icon 256×256 und 512×512, Logo mit kurzer
Seite 256 bzw. 512 (314×256, 628×512).

### Warum HACS das Icon trotzdem nicht anzeigt

Nicht unsere Baustelle, aber die Erklärung gehört hierher, damit sie nicht immer wieder gesucht
wird. Seit Home Assistant 2026.3 dürfen Custom Integrations ihre Brand-Bilder selbst mitbringen —
genau das tut der `brand/`-Ordner hier, und Home Assistant liefert sie über
`/api/brands/integration/nspanel_ui_config/icon.png` auch aus; unter *Geräte & Dienste* erscheint
das Icon.

HACS 2.0.5 nutzt diesen Weg nicht: Es baut die Adresse selbst gegen den CDN
(`https://brands.home-assistant.io/_/<domain>/icon.png`, in `update.py` und noch einmal als eigene
`brandsUrl`-Kopie im Frontend). Dort ist die Integration nicht hinterlegt, also kommt der
Platzhalter „icon not available" zurück. Nachreichen lässt sich das nicht mehr: die PR-Vorlage von
`home-assistant/brands` sagt ausdrücklich, dass Pull Requests für neue Custom Components nicht mehr
angenommen werden, und kennt unter „Type of change" nur noch Core-Integrationen. Es bleibt also
beim Warten auf HACS (offene Issues #5223, #5179; offene PRs #5228, #5339).

## 0.23.0 – 2026-07-30

### Im Screensaver stand „sunny“, wo das Gerät die Temperatur zeigt

Das Symbol stimmte seit 0.22.0, der Text daneben nicht: die Vorschau setzte dort den **Zustand**
der Wetter-Entity ein, weil sie das bei jeder Entity so macht — Zustand, notfalls mit Einheit.
Beim Wetter ist das falsch. `pages.py` hat für `weather` einen eigenen Zweig und schreibt fest
`f'{temperature}{unit}'`; „sunny“ landet nie im Textfeld, das steckt schon im Symbol. Die Einheit
kommt dabei aus dem Attribut `temperature_unit` der Entity, **nicht** aus `weatherUnit` des
Screensavers — das gilt nur für cardThermo und die Klima-Zeilen. Auch das Leerzeichen fehlt
bewusst: das Backend setzt keines, und die schmale Vorhersagespalte hat dafür keinen Platz.

### Und die vier Vorhersagespalten waren gar keine

Dieselbe Entity steht auf dem Screensaver fünfmal; die vier Spalten unterscheiden sich allein
durch `type: 0` … `3`, ihr Wert ist die Temperatur **dieses Vorhersagetages**, ihre Überschrift der
Wochentag, ihr Symbol das Wetter von morgen oder übermorgen. Die Vorschau zeigte fünfmal dasselbe
aktuelle Wetter.

Das ließ sich bisher nicht besser machen: seit Home Assistant 2024 trägt eine `weather.*`-Entity
ihre Vorhersage in **keinem** Attribut mehr — `hass.states` allein kann diese Plätze also gar nicht
füllen. Sie kommt nur noch über `weather.get_forecasts`, einen Dienst mit Antwort, den die REST-API
mit `?return_response` herausgibt. Genau den ruft die Vorschau jetzt auf, einmal je Entity und
Reihe, und zeichnet sich danach selbst neu. Welche Reihe, entscheidet dieselbe Regel wie im Backend
(`daily`/`hourly`/`twice_daily` nach `supported_features`, ausdrücklich wählbar als `daily:1`).

Zwei Feinheiten sind nachgebildet, nicht geglättet. `pages.py` verzweigt nach dem **Python-Typ**:
nur eine echte Ganzzahl ist ein Vorhersage-Index, `type: "0"` als Text zeigt die aktuelle
Temperatur — die Vorschau unterscheidet das genauso. Und reicht die Vorhersage nicht so weit wie
der Index, fällt auch das Backend auf das aktuelle Wetter zurück. Ein Fehlschlag beim Abruf wird
als leere Vorhersage vermerkt, damit die Vorschau ihn nicht bei jeder Zeichnung wiederholt.

Der Wochentag ist die eine Näherung, die bleibt: das Backend formatiert ihn mit babel, hier macht
es der Browser mit seiner Locale. Trägt der Eintrag ein eigenes `name`, ist das im Backend kein
Name, sondern ein Formatmuster — die Vorschau zeigt es dann unverändert an, statt zu raten.

### Ein Weg aus dem Editor heraus

Der Kopf hatte fünf Knöpfe und keinen zum Verlassen. Ein Custom-Panel füllt die ganze Fläche und
bringt keine Kopfleiste von Home Assistant mit; auf einem schmalen Bildschirm ist die Seitenleiste
eingeklappt und es gibt kein Menü — dann führt nur noch die Zurück-Taste des Browsers hinaus.
„✕ Schließen“ geht dorthin zurück, wo man hergekommen ist, ohne Verlauf auf das Standard-Dashboard.
Ungespeicherte Änderungen fragt er vorher ab: direkt neben „Speichern“ wäre er sonst eine Falle.

## 0.22.1 – 2026-07-29

### Manchmal blieb der Editor leer, und jeder Knopf meldete „callApi"

Gemeldet aus dem Betrieb: der Editor lädt, aber im Inhalt steht nichts — nur die Kopfzeile mit
„Importieren…", „YAML ansehen…", „Speichern" und „YAML erzeugen". Wer dann einen Knopf drückt,
bekommt `Cannot read properties of undefined (reading 'callApi')`. Ein Neuladen der Seite half
meistens, weshalb es als Zufall erschien.

Es ist kein Zufall, sondern eine Reihenfolge. `customElements.define` steht am Dateiende, also
hinter den `await import(...)` der Nebenmodule am Dateianfang. Home Assistant lädt das Panel-Modul
und erzeugt sein Element danach mit `document.createElement(…)` — trifft dieser Moment das Fenster,
in dem die Definition noch nicht steht, ist das Element **noch nicht aufgewertet**. Dann greift in
`setCustomPanelProperties` der Ausweichpfad `el[key] = wert` (auf ein `setProperties` prüft es
zuerst, das gibt es hier nicht), und `hass` landet als **eigene** Eigenschaft auf dem Element. Eine
eigene Dateneigenschaft verdeckt den Setter aus der Prototypkette dauerhaft: beim späteren Upgrade
feuert `set hass` nie, `this._hass` bleibt `undefined`.

Damit erklärt sich das Bild vollständig — die Kopfzeile erscheint, weil sie kein `hass` braucht,
der Inhalt fehlt, weil er erst nach dem Laden von Schema und Modell entsteht, und der Knopfdruck
läuft in genau jenes `undefined`. Es heilt auch nicht von selbst: Home Assistant schreibt bei jedem
State-Update weiter auf dieselbe eigene Eigenschaft. Warum „manchmal": ob das Fenster getroffen
wird, hängt daran, wie lange die fünf Nebenmodule brauchen — im warmen Browser-Cache sind sie da,
bevor das Element entsteht, nach einem Update oder auf einer langsamen Verbindung nicht.

Der Konstruktor räumt solche vor dem Upgrade eingetroffenen Eigenschaften jetzt ab und setzt sie neu,
womit die Accessoren greifen. Lit macht in `_saveInstanceProperties` genau das; ohne Framework muss
es von Hand dastehen. Zwei Tests halten es fest: einer stellt das Upgrade nach (eigene Eigenschaft
setzen, Prototyp untertauschen, retten, prüfen), einer sichert ab, dass der Aufruf im Konstruktor
nicht wieder verschwindet.

## 0.22.0 – 2026-07-29

### Das Wettersymbol fehlte in der Vorschau – ausgerechnet auf dem Screensaver

Aus der Konfiguration gezeichnet stand dort ein Platzhalter, vom Gerät abgerufen ein richtiges
Symbol. Der Grund: `weather.*`-Entities tragen in Home Assistant **kein `icon`-Attribut**. Die
Vorschau borgt sich sonst das Symbol, das HA für eine Entity führt — beim Wetter gibt es nichts zu
borgen, das Frontend leitet es selbst aus `sunny`, `rainy`, `cloudy` ab. Und das Backend tut
dasselbe, mit einer eigenen Tabelle.

Genau die ist jetzt nachgebildet, Symbol **und** Farbe, aus derselben Quelle wie beim Gerät
(`luibackend/icons.py: weather_mapping`, Farbwerte aus `pages.py`): `sunny` wird zur gelben Sonne,
`rainy` zum blauen Regen, `exceptional` zum Warnzeichen — das ist im Backend bewusst kein
Wettersymbol. Ein selbst gesetztes `icon` gewinnt weiterhin, wie am Gerät.

Eine Kleinigkeit wurde dabei mitgenommen, statt sie zu glätten: Bei `windy-variant` steht im
Backend `icon_color: 64495` — mit Doppelpunkt statt Zuweisung. Die Zeile setzt also nichts, und das
Gerät zeigt die Standardfarbe. Die Vorschau macht es genauso. **Nachgebildet wird, was das Gerät
tut, nicht was dort gemeint war** — sonst zeigte die Vorschau ein Rot, das auf dem Display nie
erscheint.

### Screenshots im README

Zwei Bilder zeigen jetzt, worum es geht, statt es nur zu beschreiben: der Editor mit
Navigationsbaum, erklärten Feldern und Kapazitätsanzeige — und die Vorschau der Ruheanzeige in
Originalgröße. Sie liegen unter `docs/bilder/`.

## 0.21.1 – 2026-07-29

### Die Dokumentation trennt jetzt Anwender von Mitbauern

Wer die Integration einrichten will, musste sich bisher durch Abschnitte arbeiten, die ihn nichts
angehen: die HTTP-API, die Maße der Brand-Bilder, das Werkzeug zum Optimieren von PNGs. Das steht
jetzt in [`docs/entwicklung.md`](docs/entwicklung.md); `funktionen.md` beschreibt nur noch, was man
im Editor tatsächlich benutzt. Die Verweisliste im README ist entsprechend zweigeteilt — *zum
Einrichten und Bedienen* und *für alle, die mitbauen wollen*.

**Entfernt: die Machbarkeitsuntersuchung zur Panel-Vorschau.** Sie hat ihren Zweck erfüllt — die
Vorschau steht seit Wochen. Als Eintrag in einer Doku-Liste, die jemandem beim Einrichten helfen
soll, war sie nur noch Ballast. Was daraus bleibenden Wert hat, ist in `architecture.md` gewandert:
**woher die Vorschau-Geometrie kommt** und warum den Koordinaten zu trauen ist (Abgleich mit
`CARD_CAPACITY`, Herleitung der Screensaver-Zuordnung aus den `spstr`-Aufrufen).

Im README ist außerdem ein Platz für Screenshots vorbereitet.

## 0.21.0 – 2026-07-29

### Eine Beispielkonfiguration zum Anfangen

Die Einrichtungsdoku kannte bisher nur einen Weg: eine bestehende `apps.yaml` umstellen. Wer neu
anfängt, stand vor einem leeren Editor. `docs/beispiel-apps.yaml` ist jetzt der Startpunkt — im
Editor unter *Importieren…* einlesen, und es stehen eine Ruheanzeige, drei Karten und eine
Unterseite da, kommentiert und mit den Stellen, auf die es ankommt (`key`, `navigate.<key>`,
`statusIcon`, versteckte Karten).

**Alle Entities darin sind erfunden.** Das ist Absicht: Der Editor markiert unbekannte Entities
mit ⚠ — und genau diese Markierungen sind die Liste dessen, was noch zu ersetzen ist. Ein Test hält
die Datei an denselben Maßstäben wie eine echte Konfiguration: einlesbar, ohne Validierungsbefund,
verlustfrei im Rundlauf. Eine Beispieldatei, die beim ersten Import stolpert, wäre der schlechteste
denkbare erste Eindruck.

### Die Einrichtung führt jetzt durch beide Wege — und bis zur Abnahme

[`docs/einrichtung.md`](docs/einrichtung.md) beginnt mit einem Wegweiser (neu anfangen oder
umstellen), zieht die Pfadfrage nach vorn, weil sie für beide gilt, und endet nicht mehr beim
Reload, sondern bei der Frage, ob er auch wirkt:

**Neu: „Prüfen, ob es wirkt".** Vier Schritte — Titel ändern, erzeugen, warten, Karte am Gerät
aufrufen — und eine Tabelle, die jede Beobachtung einordnet: neuer Titel, alter Titel, alter Titel
auch nach dem Neustart, leere Live-Ansicht. Genau diese Kette hat einen halben Vormittag gekostet,
weil der Reload lautlos ins Leere lief; sie steht jetzt aufgeschrieben da.

Dazu die Erklärung, die dabei am meisten gefehlt hat: Die Live-Ansicht zeigt den **Mitschnitt**. Eine
Karte, die seit der Änderung nicht aufgerufen wurde, steht dort zwangsläufig im alten Stand — auch
wenn alles richtig läuft.

### Kein Ortsname mehr im Repo

In den Protokoll-Tests stand „Wetter Seebach" aus einem Mitschnitt der echten Anlage. Jetzt „Wetter
Zuhause". Sonst war nichts Persönliches zu finden: Die Testfixture nutzt erfundene Entity-IDs, die
Beispiele in der Doku sind generisch, und die Bilder zeigen ein Panel ohne Bezug zu einer bestimmten
Installation.

### HACS zeigt weiterhin den Platzhalter – und daran ändert sich so bald nichts

Nachgeprüft: Die neueste HACS-Fassung ist **2.0.5 vom 28.01.2025**, seit anderthalb Jahren kein
Release. Solange HACS seine Bild-URLs fest gegen das Brands-CDN baut, bleibt der Platzhalter stehen —
unabhängig davon, dass die HACS-Doku inzwischen das `brand/`-Verzeichnis im Repository als
bevorzugten Weg nennt. Am Repo liegt es nicht: Die Bilder sind vorhanden, haben die geforderten
Maße, und Home Assistant selbst zeigt sie korrekt an. Steht so in `docs/funktionen.md`.

## 0.20.1 – 2026-07-29

### `touch_module` braucht `production_mode: false` – sonst passiert nichts, und niemand sagt es

An einer laufenden Anlage nachgemessen: Kartentitel im Editor geändert, YAML korrekt geschrieben,
`apps.yaml` angetickt — und das Panel bekam beim Kartenaufruf trotzdem den **alten** Titel. Alle
Glieder der Kette meldeten Erfolg.

Der Grund lag eine Ebene tiefer, in AppDaemons eigener Konfiguration: Mit `production_mode: true`
prüft es überhaupt nicht mehr auf geänderte Dateien (`app_management.py`). Die mtime kann sich
beliebig oft ändern, es sieht gar nicht hin. **Damit ist `touch_module` wirkungslos — und zwar
lautlos:** Das Schreiben gelingt, das Anticken gelingt, das Generieren meldet Erfolg. Sichtbar wird
es allein daran, dass sich am Panel nichts tut.

Das steht jetzt dort, wo man es sucht: in der Beschreibung des Feldes *Datei zum Anticken* (beide
Sprachen), in `einrichtung.md` und im Modulkopf von `reload.py` — jeweils mit dem Ausweg:
`restart_container` bzw. `restart_addon`, denn ein Neustart liest ohnehin alles neu.

Nichts am Verhalten der Integration geändert; sie hatte sich korrekt verhalten. Was fehlte, war die
Voraussetzung, die niemand nennt.

## 0.20.0 – 2026-07-29

### Zur Auswahl steht nur, was auf dieser Installation laufen kann

Der Einrichtungs- und der Optionen-Dialog boten alle vier Reload-Wege an, gleich welche
Installationsart erkannt wurde — samt der drei Textfelder dazu. Wer unter Home Assistant OS
`restart_container` einstellte, bekam keine Fehlermeldung: Die YAML wurde geschrieben, das Generieren
meldete nichts Auffälliges, und am Panel änderte sich trotzdem nichts. Ein Weg, den es auf dem
System gar nicht gibt, ist keine Wahlmöglichkeit, sondern eine Falle.

Angeboten wird jetzt nur noch, was funktionieren kann:

| Installationsart | zur Auswahl |
| --- | --- |
| HA OS / Supervised | `none`, `touch_module`, `restart_addon` |
| HA Container | `none`, `touch_module`, `restart_container` |
| HA Core (venv) | `none`, `touch_module` |
| nicht erkannt | alle — hier wird nichts ausgeschlossen |

Die Begründung steckt in der Sache: `restart_addon` spricht die Supervisor-API an, die es nur mit
Supervisor gibt; `restart_container` braucht `/var/run/docker.sock` im Home-Assistant-Container, den
weder die Add-on-Welt noch eine venv-Installation hat. Die **Textfelder der übrigen Wege sind
mit ausgeblendet** — eine Angabe, die niemand ausliest, ist schlimmer als keine.

Ein bereits gespeicherter Modus bleibt wählbar, auch wenn er nicht mehr zum System passt. Nach einem
Umzug (etwa von Home Assistant OS auf Docker) ließe sich der Optionen-Dialog sonst nicht einmal mehr
öffnen: Der vorbelegte Wert stünde nicht in der Liste, und man käme gar nicht erst dazu, ihn
umzustellen.

## 0.19.1 – 2026-07-28

### `hidden` an der Karte: gesetzt, aber von niemandem gelesen

Beim Ziehen einer Karte zu den Unterseiten setzte der Editor ihr ein `hidden: true`. Der Kommentar
daneben behauptete, das Backend lese diese Eigenschaft und sie müsse zur Liste passen. Beides
stimmte nicht:

- **Das Backend liest keinen `hidden`-Key.** Es baut seine Karten als `Card(card, hidden=True)`
  (`config.py`) — die Eigenschaft ergibt sich allein daraus, dass die Karte unter `hiddenCards:`
  steht.
- **In der Datei kam der Key ohnehin nie an.** `hidden` ist kein bekanntes Kartenfeld, also ließ
  `denormalize_card` es weg. Es stand nur im gespeicherten Modell und verschwand beim nächsten
  Rundlauf über den YAML-Dialog wieder.

Gefunden bei der Frage, ob Änderungen aus dem YAML-Dialog vollständig in den Masken ankommen. Die
Antwort ist ja — `hidden` war der einzige Key im Modell einer laufenden Anlage, der beim Erzeugen
still wegfiel, und er war wirkungslos.

Der Editor setzt ihn jetzt nicht mehr und **entfernt einen Altbestand**, sobald eine Karte verschoben
wird. Am Verhalten des Panels ändert das nichts: Die Zugehörigkeit zur Liste war schon immer die
ganze Information, auch für den Kartenbaum.

## 0.19.0 – 2026-07-28

### Die Kartenliste ist jetzt ein Baum – und zeigt, was am Panel nicht erreichbar ist

Die flache Liste verriet nur, *dass* es eine Karte gibt, nicht ob man am Gerät je hinkommt. Das ist
kein Schönheitsfehler: In einer echten Konfiguration hatten zwei Karten beide Blättertasten mit
festen Zielen überschrieben, die Kette endete dort, und drei Karten dahinter waren unerreichbar.
Die YAML war dabei vollkommen gültig – niemand meldete etwas.

- **Baumansicht.** Unterseiten stehen eingerückt unter der Karte, die sie verlinkt, wie im
  Dateimanager. Ein `↳` markiert den Weg über einen Eintrag, ein `⤷` den über eine Blättertaste.
  Verlinken sich Karten gegenseitig, erscheint die zweite Erwähnung blass als „schon oben"
  statt den Baum unendlich tief zu machen.
- **Abschnitt „Nicht verlinkt".** Versteckte Karten, auf die kein `navigate.…` zeigt, stehen dort
  mit Zähler – am Panel sind sie nicht aufrufbar.
- **Ziehen und Fallenlassen.** Karten lassen sich mit der Maus umsortieren und zwischen „Aufbau"
  und Unterseite verschieben; `hidden` wird dabei passend gesetzt oder entfernt. Zieht man zwei
  Zeilen **innerhalb desselben Menüs**, ändert sich die Reihenfolge der Menüpunkte auf dieser
  Karte – das ist die Reihenfolge, die man am Gerät sieht. Die ▲▼-Knöpfe folgen derselben Regel.

### Vier Navigationsfehler, die vorher niemand gemeldet hat

Die Prüfung kannte Kartentypen und Kapazitäten, aber nicht die Navigation:

- **Totes Sprungziel** – `navigate.heizung`, obwohl keine Karte den Key `heizung` trägt (Fehler).
  Der häufigste Fall: der Titel wurde für den Key gehalten. Beide Schreibweisen, die das Backend
  akzeptiert (`<key>` und die Altform `<typ>_<key>`), gelten als gültig, `uuid.`-Ziele werden
  übersprungen – die vergibt das Backend zur Laufzeit.
- **Doppelter Key** – `search_card` liefert immer den ersten Treffer, die zweite Karte ist über
  ihren Namen nicht mehr ansprechbar (Fehler).
- **Unerreichbare Unterseite** – eine versteckte Karte, die niemand verlinkt, oder eine ohne
  `key`, die gar nicht Ziel sein *kann* (Warnung).
- **Gekappte Blätterkette** – beide Tasten überschrieben (Warnung). Eine einzelne Überschreibung
  ist üblich (ein „zurück"-Knopf) und bleibt still.

Auch `screensaver.defaultCard` wird geprüft: zeigt sie auf eine gelöschte Karte, landet das Panel
nach dem Aufwachen nirgends.

### Fixture

Die Beispiel-`apps.yaml` enthielt selbst zwei dieser Fehler – `navigate.heizung` ohne passenden
Key und eine versteckte Karte, die nichts verlinkte. Beides ist korrigiert; sie ist damit wieder
das, was sie sein soll: eine gültige Konfiguration.

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
