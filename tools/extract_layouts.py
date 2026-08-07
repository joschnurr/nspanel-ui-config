#!/usr/bin/env python3
"""Erzeugt aus den HMI-Dumps die Slot-Geometrie für die Vorschau (``www/panel/layouts.js``).

**Warum das geht:** die Display-Firmware liegt im Upstream-Repo joBr99/nspanel-lovelace-ui nicht nur
als Binärdatei, sondern auch als Textdump je Seite (``HMI/n2t-out-visual/<seite>.txt``, für die
US-Modelle unter ``HMI/US/{landscape,portrait}/n2t-out-visual/``). Dort steht jede Nextion-Komponente
mit Position und Größe:

    Text tEntity1
        Attributes
            x coordinate        : 6
            y coordinate        : 155
            Width               : 140
            Height              : 30

Damit ist die Vorschau **abgemessen statt nachempfunden** — und nach einem Upstream-Update durch
erneutes Ausführen wieder aktuell.

**Warum es trotzdem eine Tabelle je Seite braucht:** aus dem Dump geht nicht hervor, welche
Komponente welchen Listeneintrag zeigt. Die Zuordnung steckt im Seitencode (``spstr``-Aufrufe) und
folgt je Seite einer eigenen Namenskonvention: ``tEntity1…`` beginnt bei 1, ``t0Icon…`` bei 0, und
``cardPower`` hält die ersten beiden Einträge in ``tHome``/``tHome2``. Diese Konventionen stehen
unten explizit — geraten wird nichts.

Aufruf mit einer lokalen Kopie des Upstream-Repos (es genügen die Dumps in derselben
Verzeichnisstruktur):

    python3 tools/extract_layouts.py /pfad/zu/nspanel-lovelace-ui

Geschrieben wird ``custom_components/nspanel_ui_config/www/panel/layouts.js``. Die Zahl der Plätze
wird dabei gegen ``CARD_CAPACITY`` aus ``schema.py`` geprüft: weicht sie ab, bricht das Werkzeug ab,
statt eine Vorschau zu erzeugen, die dem Editor widerspricht.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SCHEMA_PATH = _REPO / "custom_components/nspanel_ui_config/schema.py"
_spec = importlib.util.spec_from_file_location("nspanel_schema", _SCHEMA_PATH)
_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_schema)
CARD_CAPACITY = _schema.CARD_CAPACITY

ZIEL = _REPO / "custom_components/nspanel_ui_config/www/panel/layouts.js"

# Unterverzeichnis der Dumps je Modell (wie in check_card_capacity.py).
MODEL_DIRS = {
    "eu": "HMI/n2t-out-visual",
    "us-l": "HMI/US/landscape/n2t-out-visual",
    "us-p": "HMI/US/portrait/n2t-out-visual",
}

# Displaygröße je Modell. Der Dump nennt zwar p0 (das Hintergrundbild), aber mal mit 479×319 statt
# 480×320 – die reale Auflösung ist die verlässlichere Bezugsgröße.
SCREENS = {"eu": (480, 320), "us-l": (480, 320), "us-p": (320, 480)}

# Komponenten, die auf jeder Karte den Rahmen bilden.
CHROME_PATTERNS = {
    "title": r"^Text tHeading$",
    "prev": r"^Button bPrev$",
    "next": r"^Button bNext$",
}


def parse_components(text: str) -> dict[str, tuple[int, int, int, int]]:
    """Name → (x, y, w, h) für jede Komponente mit Koordinaten.

    Der Dump listet jede Komponente als ``<Typ> <Name>`` mit eingerücktem Attributblock. Der Name
    allein wäre mehrdeutig (es gibt ``Text t1`` und ``Button t1`` auf verschiedenen Seiten), deshalb
    ist der Schlüssel ``"<Typ> <Name>"`` – genau die Form, die auch die Muster unten verwenden.

    **Getrennt wird an jeder nicht eingerückten Zeile**, nicht an einem Typmuster. Ein Muster wie
    ``[A-Za-z]+ \\S+`` übersieht den Typ ``Dual-state Button`` – der Bindestrich passt nicht, das
    zweite Leerzeichen erst recht nicht. Dessen Attributblock landete dadurch beim *vorherigen*
    Bauteil, wo die zweite Koordinatenangabe schlicht ignoriert wurde: Auf ``cardThermo`` fehlten so
    sämtliche Tasten (die acht Betriebsarten, Plus/Minus, Detail) spurlos. Die Einrückung ist das
    einzige verlässliche Merkmal, weil sie unabhängig vom Namen des Typs gilt.
    """
    komponenten: dict[str, tuple[int, int, int, int]] = {}
    for block in re.split(r"\n(?=\S)", text):
        kopf = block.split("\n", 1)[0].strip()
        if " " not in kopf:
            continue
        werte = {}
        for schluessel, muster in (
            ("x", r"x coordinate\s*:\s*(-?\d+)"),
            ("y", r"y coordinate\s*:\s*(-?\d+)"),
            ("w", r"Width\s*:\s*(\d+)"),
            ("h", r"Height\s*:\s*(\d+)"),
        ):
            treffer = re.search(muster, block)
            if treffer:
                werte[schluessel] = int(treffer.group(1))
        if len(werte) == 4:
            komponenten[kopf] = (werte["x"], werte["y"], werte["w"], werte["h"])
    return komponenten


# Kurze Schlüssel, weil die Tabelle für jede Komponente jeder Seite mitgeliefert wird:
# f = Font-ID, h = horizontale Ausrichtung, v = vertikale, c = Schriftfarbe (RGB565).
def parse_attributes(text: str) -> dict[str, dict[str, object]]:
    """Name → Darstellungsattribute jeder Komponente.

    Ohne sie bleibt die Vorschau eine grobe Nachbildung: die Ausrichtung entscheidet, ob eine
    Beschriftung mittig unter dem Symbol steht oder links klebt, und die Font-ID, wie groß sie ist.
    Beides steht im Dump und war bisher ungenutzt.

    Buttons benennen dieselben Dinge anders (``Font Color (Unpressed)``) – die Muster decken beide
    Schreibweisen ab.

    Getrennt wird an nicht eingerückten Zeilen, aus demselben Grund wie in ``parse_components``:
    sonst fehlen alle ``Dual-state Button`` – auf ``cardThermo`` also Schriftgröße und Farbe jeder
    Taste.
    """
    ausrichtung = {"left": "l", "center": "c", "right": "r", "top": "t", "bottom": "b"}
    attribute: dict[str, dict[str, object]] = {}
    for block in re.split(r"\n(?=\S)", text):
        kopf = block.split("\n", 1)[0].strip()
        if " " not in kopf:
            continue
        eintrag: dict[str, object] = {}
        font = re.search(r"Font ID\s*:\s*(\d+)", block)
        if font:
            eintrag["f"] = int(font.group(1))
        for schluessel, muster in (
            ("h", r"Horizontal Alignment\s*:\s*(\w+)"),
            ("v", r"Vertical Alignment\s*:\s*(\w+)"),
        ):
            treffer = re.search(muster, block)
            if treffer:
                eintrag[schluessel] = ausrichtung.get(treffer.group(1).lower(), treffer.group(1)[:1])
        farbe = re.search(r"Font Color(?:\s*\(Unpressed\))?\s*:\s*(\d+)", block)
        if farbe:
            eintrag["c"] = int(farbe.group(1))
        # Umrandung: auf ``cardPower`` sitzt jedes Symbol in einem 60×60-Feld mit 2 px Rahmen
        # (``Style: border``), ebenso die Mittelsäule. Ohne ihn schweben die Symbole frei, während
        # das Gerät sie eingefasst zeigt — der auffälligste Unterschied nach den Laufbalken.
        # ``Style`` muss mitgeprüft werden: ``Border Color`` steht auch an Komponenten, die als
        # ``flat`` gezeichnet werden und den Wert schlicht nicht benutzen.
        stil = re.search(r"Style\s*:\s*(\w+)", block)
        if stil and stil.group(1).lower() == "border":
            rand = re.search(r"Border Color\s*:\s*(\d+)", block)
            breite = re.search(r"Border Width\s*:\s*(\d+)", block)
            if rand and breite and int(breite.group(1)) > 0:
                eintrag["bc"] = int(rand.group(1))
                eintrag["bw"] = int(breite.group(1))
        if eintrag:
            attribute[kopf] = eintrag
    return attribute


def hintergrundfarbe(text: str) -> int | None:
    """Die Hintergrundfarbe der Seite – im Dump die des Hintergrundbilds bzw. der Komponenten.

    Das Display ist nicht rein schwarz, sondern sehr dunkelgrau; ohne diesen Wert wirkt die Vorschau
    kontrastreicher als das Gerät.
    """
    treffer = re.findall(r"Back\. Color\s*:\s*(\d+)", text)
    if not treffer:
        return None
    # Der häufigste Wert ist der Seitenhintergrund; einzelne Komponenten weichen bewusst ab.
    from collections import Counter

    return Counter(int(wert) for wert in treffer).most_common(1)[0][0]


def _treffer(komponenten: dict, muster: str) -> dict[int, tuple[int, int, int, int]]:
    """Alle Komponenten, deren Name auf das Muster passt, nach der Nummer darin sortiert."""
    gefunden: dict[int, tuple[int, int, int, int]] = {}
    for name, rect in komponenten.items():
        match = re.match(muster, name)
        if match:
            gefunden[int(match.group(1))] = rect
    return gefunden


def _rollen(komponenten: dict, muster: dict[str, str], basis: int) -> list[dict]:
    """Baut die Slot-Liste aus je einem Muster pro Rolle.

    ``basis`` ist die Nummer des ersten Eintrags im Namen (1 bei ``tEntity1``, 0 bei ``t0Icon``).
    Maßgeblich für die Anzahl ist die Rolle mit den meisten Treffern – auf ``cardMedia`` etwa gibt es
    Symbolflächen ohne zugehöriges Textfeld.
    """
    je_rolle = {rolle: _treffer(komponenten, m) for rolle, m in muster.items()}
    anzahl = max((len(t) for t in je_rolle.values()), default=0)
    slots = []
    for i in range(anzahl):
        slot = {}
        for rolle, treffer in je_rolle.items():
            rect = treffer.get(i + basis)
            if rect:
                slot[rolle] = list(rect)
        if slot:
            slots.append(slot)
    return slots


def fluss_card_power(dump: str) -> list[dict]:
    """Die sechs Laufbalken von ``cardPower`` – je einer zwischen Mitte und Außenplatz.

    Es sind Nextion-**Slider** (``h0``…``h5``), keine Textfelder, deshalb fehlen sie in der
    Slot-Tabelle. Gezeichnet werden sie trotzdem: auf dem Gerät läuft dort der Punkt, der den
    Energiefluss anzeigt, und ohne ihn zeigt die Vorschau eine leere Fläche, wo das Auffälligste
    der Karte passiert.

    ``h<N>`` gehört zum Außenplatz ``t<N>``, also zu Slot ``N + 2`` (die ersten beiden Plätze sitzen
    in der Mitte). Mitgenommen werden auch Bereich und Startwert des Sliders: der Seitencode addiert
    im 100-ms-Takt ``speed`` auf ``h<N>.val`` und springt am Ende auf die andere Seite – daraus
    ergibt sich die Umlaufzeit, die die Vorschau nachbildet.
    """
    balken = []
    for block in re.split(r"\n(?=[A-Za-z]+ \S+\n)", dump):
        kopf = block.split("\n", 1)[0].strip()
        treffer = re.match(r"^Slider h(\d)$", kopf)
        if not treffer:
            continue
        werte = {}
        for schluessel, muster in (
            ("x", r"x coordinate\s*:\s*(-?\d+)"),
            ("y", r"y coordinate\s*:\s*(-?\d+)"),
            ("w", r"Width\s*:\s*(\d+)"),
            ("h", r"Height\s*:\s*(\d+)"),
            ("start", r"Position\s*:\s*(\d+)"),
            ("min", r"Lower range limit\s*:\s*(\d+)"),
            ("max", r"Upper range limit\s*:\s*(\d+)"),
        ):
            gefunden = re.search(muster, block)
            if gefunden:
                werte[schluessel] = int(gefunden.group(1))
        richtung = re.search(r"Direction\s*:\s*(\w+)", block)
        if len(werte) != 7 or not richtung:
            continue
        balken.append(
            {
                "index": int(treffer.group(1)) + 2,
                "rect": [werte["x"], werte["y"], werte["w"], werte["h"]],
                "dir": "v" if richtung.group(1).startswith("vertical") else "h",
                "start": werte["start"],
                "min": werte["min"],
                "max": werte["max"],
            }
        )
    return sorted(balken, key=lambda b: b["index"])


def slots_card_power(komponenten: dict) -> list[dict]:
    """``cardPower`` nummeriert anders: die ersten beiden Einträge sitzen in der Mitte.

    **Die Mitte war falsch zugeordnet.** ``tHome`` und ``tHome2`` sahen wie zwei Einträge aus, sind
    aber Zahl und Einheit *desselben* Werts. Der Seitencode sagt es genau::

        spstr strCommand.txt, t1.txt,     "~", 16   # Symbol von Eintrag 0
        spstr strCommand.txt, tHome.txt,  "~", 19   # Wert  von Eintrag 0
        spstr tHome.txt, tHome2.txt, " ", 1         #   … am ersten Leerzeichen getrennt:
        spstr tHome.txt, tHome.txt,  " ", 0         #   Zahl nach tHome, Einheit nach tHome2
        spstr strCommand.txt, tHomeO.txt, "~", 26   # Wert  von Eintrag 1 (ebenso getrennt)

    Die Feldnummern gehen auf: 12 Navigationsfelder (zwei Tasten à 6) und 7 Felder je Eintrag
    (``generate_entities_item`` liefert 6, ``cardPower`` hängt ``speed`` an). Eintrag 0 liegt damit
    auf 14…20 — Symbol 16, Wert 19 —, Eintrag 1 auf 21…27 mit Wert 26.

    ``t1`` ist dabei **Rahmen und Symbol in einem**: ein 60×230 hohes Feld mit ``Style: border``,
    dessen Text die Symbolglyphe ist (``Font ID 3``). Auf dem Gerät steht das Haussymbol deshalb
    mittig in der umrandeten Mittelsäule, mit dem Wert von Eintrag 1 darüber und dem von Eintrag 0
    darunter. Eintrag 1 hat kein eigenes Symbol.

    Die sechs Außenplätze liegen in ``t0…t5`` mit Symbol (``t<N>Icon``), oberer Zeile (``t<N>o``)
    und unterer Zeile (``t<N>u``).
    """

    def rect(name: str) -> list | None:
        treffer = komponenten.get(f"Text {name}")
        return list(treffer) if treffer else None

    slots: list[dict] = []
    for rollen in (
        {"icon": "t1", "value": "tHome", "unit": "tHome2"},
        {"value": "tHomeO", "unit": "tHomeO2"},
    ):
        slot = {rolle: rect(name) for rolle, name in rollen.items()}
        slots.append({rolle: r for rolle, r in slot.items() if r})
    slots.extend(
        _rollen(
            komponenten,
            {"icon": r"^Text t(\d)Icon$", "name": r"^Text t(\d)o$", "value": r"^Text t(\d)u$"},
            basis=0,
        )
    )
    return slots


# --- Screensaver ------------------------------------------------------------------------------
#
# Hier tragen die Komponentennamen die Zuordnung *nicht*: ``tMainText`` und ``tForecast3`` verraten
# nicht, welchen Listeneintrag sie zeigen. Das steht im Seitencode, und zwar präzise: der
# ``weatherUpdate~``-String besteht aus 6 Feldern je Entity, und jede Komponente holt sich ihr Feld
# mit ``spstr strCommand.txt,<komponente>.txt,"~",<feldindex>``. Aus dem Index folgt beides —
# Eintrag und Rolle:
#
#     entity = (feldindex - 1) // 6
#     rolle  = (feldindex - 1) %  6   →  0 type, 1 entityId, 2 icon, 3 color, 4 name, 5 value
#
# Damit ist die Zuordnung *hergeleitet* statt abgeschrieben. Probe aufs Exempel: sie ergibt für
# ``screensaver`` genau 6 Einträge (1 Hauptbereich, 4 Vorhersagen, 1 für das alternative Layout) und
# für ``screensaver2`` genau 15 in den Gruppen 1 / 3 / 6 / 5 — dieselbe Aufteilung, die
# ``CAPACITY_LAYOUT_NOTES`` beschreibt.
SPSTR = re.compile(r'spstr\s+strCommand\.txt\s*,\s*(\w+)\.txt\s*,\s*"~"\s*,\s*(\d+)')
BLOCK = re.compile(r'if\(tInstruction\.txt=="(\w+)"')
ALIAS = re.compile(r"(\w+)\.txt\s*=\s*(\w+)\.txt")
FELD_ROLLEN = {2: "icon", 4: "name", 5: "value"}

# Komponenten anderer Befehle (Uhrzeit, Datum, Statussymbole). Sie gehören nicht zur Entity-Liste,
# die Vorschau braucht ihre Lage aber, sonst fehlte die halbe Anzeige.
SPECIAL_BLOCKS = {"time": "time", "date": "date", "statusUpdate": "status"}


def _blocks(text: str) -> dict[str, str]:
    """Der Seitencode, zerlegt nach ``if(tInstruction.txt=="…")``.

    Ohne diese Trennung liest man Feldindizes anderer Befehle mit — ``tIcon1`` etwa holt sich Feld 1
    des *statusUpdate*-Strings und wäre sonst fälschlich Eintrag 0 der Entity-Liste.
    """
    marken = [(m.start(), m.group(1)) for m in BLOCK.finditer(text)]
    ergebnis: dict[str, str] = {}
    for i, (pos, name) in enumerate(marken):
        ende = marken[i + 1][0] if i + 1 < len(marken) else len(text)
        ergebnis.setdefault(name, text[pos:ende])
    return ergebnis


def slots_screensaver(text: str, komponenten: dict) -> tuple[list[dict], dict, dict]:
    """(slots, alt, special) für eine Screensaver-Seite."""
    nach_name = {kopf.split(" ", 1)[1]: rect for kopf, rect in komponenten.items()}
    bloecke = _blocks(text)
    zuordnung: dict[str, tuple[int, str]] = {}
    for name, index in SPSTR.findall(bloecke.get("weatherUpdate", "")):
        if name == "tTmp":  # Hilfsfeld für die Farbumrechnung, keine Anzeige
            continue
        entity, offset = divmod(int(index) - 1, 6)
        if offset in FELD_ROLLEN:
            zuordnung.setdefault(name, (entity, FELD_ROLLEN[offset]))

    anzahl = max((e for e, _ in zuordnung.values()), default=-1) + 1
    slots: list[dict] = [{} for _ in range(anzahl)]
    for name, (entity, rolle) in zuordnung.items():
        if name in nach_name:
            slots[entity][rolle] = list(nach_name[name])

    # Das alternative Layout zeigt denselben Eintrag an anderer Stelle. Diese Komponenten holen
    # sich kein eigenes Feld, sondern werden zugewiesen (`tMainTextAlt.txt=tMainText.txt`) — und
    # heißen wie das Original mit angehängtem Alt/Alt2.
    alt: dict[str, dict] = {}
    for ziel, quelle in ALIAS.findall(bloecke.get("weatherUpdate", "")):
        if not re.fullmatch(rf"{re.escape(quelle)}Alt\d*", ziel) or quelle not in zuordnung:
            continue
        entity, rolle = zuordnung[quelle]
        if ziel in nach_name:
            alt.setdefault(str(entity), {})[rolle] = list(nach_name[ziel])

    special = {}
    for block, schluessel in SPECIAL_BLOCKS.items():
        for name, _ in SPSTR.findall(bloecke.get(block, "")):
            if name != "tTmp" and name in nach_name:
                special[name] = list(nach_name[name])
    # tTime wird nicht per spstr gefüllt (die Uhr kommt aus der RTC), gehört aber dazu.
    for name in ("tTime", "tTimeAdd", "tDate", "tAMPM"):
        if name in nach_name:
            special.setdefault(name, list(nach_name[name]))
    return slots, alt, special


# Wie die Plätze je Seite heißen. Gruppe 1 des Musters ist die Nummer im Namen.
SEITEN = {
    "cardEntities": lambda k: _rollen(
        k,
        {
            "icon": r"^Text tIcon(\d+)$",
            "name": r"^Text tEntity(\d+)$",
            # Rechte Spalte: je nach Entity ein Regler, ein Zahlenfeld oder ein Schaltsymbol.
            # Für die Vorschau zählt nur die Fläche, die das Bedienelement einnimmt.
            "value": r"^Slider hSlider(\d+)$",
        },
        basis=1,
    ),
    "cardGrid": lambda k: _rollen(
        k, {"icon": r"^Button bEntity(\d+)$", "name": r"^Text tEntity(\d+)$"}, basis=1
    ),
    "cardGrid2": lambda k: _rollen(
        k, {"icon": r"^Button bEntity(\d+)$", "name": r"^Text tEntity(\d+)$"}, basis=1
    ),
    "cardQR": lambda k: _rollen(
        k,
        {"icon": r"^Text tIcon(\d+)$", "name": r"^Text tEntity(\d+)$", "value": r"^Button bText(\d+)$"},
        basis=1,
    ),
    "cardMedia": lambda k: _rollen(k, {"icon": r"^Button bEntity(\d+)$"}, basis=1),
    "cardPower": slots_card_power,
}

# Diese beiden gehen den Weg über den Seitencode (siehe slots_screensaver).
SCREENSAVER_SEITEN = ("screensaver", "screensaver2")


# --- Karten mit festem Aufbau statt Entity-Liste -----------------------------------------------
#
# `cardThermo` zeigt **eine** Entity, aber nicht als Listeneintrag: Die Fläche ist fest aufgeteilt
# in Ist-Temperatur, Soll-Temperatur, Zustand und die Betriebsartentasten. Deshalb gibt es hier
# keine nummerierten Plätze, sondern benannte Rollen — `CARD_CAPACITY` kennt die Seite folgerichtig
# gar nicht.
#
# **Zwei Bedienbilder in einer Seite**, umgeschaltet über `vis` (Zeile 53–60 des Seitencodes
# blendet den zweiten Satz zunächst aus):
#   * ein Sollwert  → `xTempDest` mittig, dazu die großen Tasten `btUp`/`btDown`
#   * zwei Sollwerte (`target_temp_high`/`_low`, z. B. Heizen/Kühlen) → `xTempDest1` + `xTempDest2`
#     nebeneinander, dazu die kleinen Tastenpaare `btUp1`/`btDown1` und `bUp2`/`bDown2`
# Welches gilt, entscheidet das Backend daran, ob die Entity `temperature` liefert oder nicht
# (`generate_thermo_page` in pages.py). Die Vorschau zeichnet deshalb immer nur eines von beiden.
THERMO_ROLLEN = {
    "curTempLbl": r"^Text tCurTempLbl$",
    "curTemp": r"^Text tCurTemp$",
    "stateLbl": r"^Text tStateLbl$",
    "state": r"^Text tStatus$",
    "dest": r"^XFloat xTempDest$",
    "destUnit": r"^Text tCF$",
    "destHigh": r"^XFloat xTempDest1$",
    "destHighUnit": r"^Text tCF1$",
    "destLow": r"^XFloat xTempDest2$",
    "destLowUnit": r"^Text tCF2$",
    "up": r"^Dual-state Button btUp$",
    "down": r"^Dual-state Button btDown$",
    "upHigh": r"^Dual-state Button btUp1$",
    "downHigh": r"^Dual-state Button btDown1$",
    "upLow": r"^Dual-state Button bUp2$",
    "downLow": r"^Dual-state Button bDown2$",
    "detail": r"^Dual-state Button btDetail$",
}


def fixed_card_thermo(komponenten: dict) -> tuple[dict, list]:
    """Benannte Flächen und die acht Betriebsartentasten von ``cardThermo``.

    Die Tasten kommen als eigene Liste zurück, weil sie – anders als die übrigen Rollen – eine
    *Reihenfolge* haben: Das Backend füllt sie ab Feld 21 in Viererschritten
    (``spstr … bt0.txt,"~",21``, dann 25, 29 …), also genau in der Reihenfolge der `hvac_modes`.
    """
    fest = {}
    for rolle, muster in THERMO_ROLLEN.items():
        for name, rect in komponenten.items():
            if re.match(muster, name):
                fest[rolle] = list(rect)
                break

    tasten = []
    for nummer in range(8):
        name = f"Dual-state Button bt{nummer}"
        if name in komponenten:
            tasten.append(list(komponenten[name]))
    return fest, tasten


FESTE_SEITEN = {"cardThermo": fixed_card_thermo}


def _attrs_zu(rechtecke: dict, komponenten: dict, attribute: dict) -> dict:
    """Ordnet jedem Rechteck die Attribute seiner Komponente zu – über die Position.

    Der Umweg über die Koordinaten spart es, die Namensmuster ein zweites Mal zu pflegen: ein
    Rechteck stammt genau von der Komponente, die dort sitzt.
    """
    nach_rect = {tuple(rect): name for name, rect in komponenten.items()}
    ergebnis = {}
    for rolle, rect in rechtecke.items():
        name = nach_rect.get(tuple(rect))
        eintrag = attribute.get(name) if name else None
        if eintrag:
            ergebnis[rolle] = eintrag
    return ergebnis


def layout_fuer(dump: str, model: str, seite: str) -> dict:
    komponenten = parse_components(dump)
    attribute = parse_attributes(dump)
    hintergrund = hintergrundfarbe(dump)

    if seite in SCREENSAVER_SEITEN:
        slots, alt, special = slots_screensaver(dump, komponenten)
        layout = {"screen": list(SCREENS[model]), "chrome": {}, "slots": slots, "special": special}
        layout["slotAttrs"] = [_attrs_zu(slot, komponenten, attribute) for slot in slots]
        layout["specialAttrs"] = _attrs_zu(special, komponenten, attribute)
        if alt:
            layout["alt"] = alt
            layout["altAttrs"] = {k: _attrs_zu(v, komponenten, attribute) for k, v in alt.items()}
        if hintergrund is not None:
            layout["back"] = hintergrund
        return layout

    chrome = {}
    for rolle, muster in CHROME_PATTERNS.items():
        for name, rect in komponenten.items():
            if re.match(muster, name):
                chrome[rolle] = list(rect)
                break
    if seite in FESTE_SEITEN:
        fest, tasten = FESTE_SEITEN[seite](komponenten)
        layout = {
            "screen": list(SCREENS[model]),
            "chrome": chrome,
            "chromeAttrs": _attrs_zu(chrome, komponenten, attribute),
            # Leer, damit jede Auswertung, die Plätze erwartet, nichts findet statt zu stolpern.
            "slots": [],
            "fixed": fest,
            "fixedAttrs": _attrs_zu(fest, komponenten, attribute),
            "modes": tasten,
            "modeAttrs": _attrs_zu({str(i): r for i, r in enumerate(tasten)}, komponenten, attribute),
        }
        if hintergrund is not None:
            layout["back"] = hintergrund
        return layout

    slots = SEITEN[seite](komponenten)
    layout = {
        "screen": list(SCREENS[model]),
        "chrome": chrome,
        "chromeAttrs": _attrs_zu(chrome, komponenten, attribute),
        "slots": slots,
        "slotAttrs": [_attrs_zu(slot, komponenten, attribute) for slot in slots],
    }
    if seite == "cardPower":
        fluss = fluss_card_power(dump)
        if fluss:
            layout["flow"] = fluss
    if hintergrund is not None:
        layout["back"] = hintergrund
    return layout


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    repo = Path(argv[1])
    if not (repo / "HMI").is_dir():
        raise SystemExit(f"{repo} sieht nicht nach nspanel-lovelace-ui aus (kein HMI/-Ordner)")

    layouts: dict[str, dict] = {}
    abweichungen = 0
    for seite in list(SEITEN) + list(SCREENSAVER_SEITEN) + list(FESTE_SEITEN):
        layouts[seite] = {}
        for model, unterordner in MODEL_DIRS.items():
            datei = repo / unterordner / f"{seite}.txt"
            if not datei.is_file():
                print(f"  ?  {seite:<14} {model:<5} Dump fehlt ({datei})")
                abweichungen += 1
                continue
            layout = layout_fuer(datei.read_text(encoding="utf-8", errors="replace"), model, seite)
            if seite in FESTE_SEITEN:
                # Keine Plätze, sondern feste Rollen — CARD_CAPACITY kennt diese Seiten nicht.
                print(
                    f"  ok  {seite:<14} {model:<5} {len(layout['fixed'])} Rollen,"
                    f" {len(layout['modes'])} Betriebsartentasten"
                )
                layouts[seite][model] = layout
                continue
            erwartet = CARD_CAPACITY.get(seite, {}).get(model)
            gefunden = len(layout["slots"])
            status = "ok "
            if erwartet is not None and gefunden != erwartet:
                status = "!! "
                abweichungen += 1
            print(f"  {status} {seite:<14} {model:<5} {gefunden} Plätze (Schema: {erwartet})")
            layouts[seite][model] = layout

    if abweichungen:
        print(
            f"\n{abweichungen} Abweichung(en) – nichts geschrieben. Entweder hat sich das HMI "
            f"geändert (dann gehört CARD_CAPACITY in schema.py angepasst) oder die Namensmuster "
            f"oben stimmen nicht mehr.",
            file=sys.stderr,
        )
        return 1

    kopf = (
        "// Slot-Geometrie der HMI-Seiten – **erzeugt von tools/extract_layouts.py, nicht von Hand "
        "pflegen.**\n"
        "//\n"
        "// Quelle sind die Textdumps der Display-Firmware im Upstream-Repo joBr99/"
        "nspanel-lovelace-ui\n"
        "// (`HMI/n2t-out-visual/*.txt`, US-Modelle unter `HMI/US/{landscape,portrait}/`). Die Werte\n"
        "// sind **Pixel des jeweiligen Displays** – so lassen sie sich direkt gegen den Dump "
        "prüfen;\n"
        "// die Umrechnung in Prozent macht preview-layouts.js.\n"
        "//\n"
        "// Aufbau: LAYOUTS[<kartentyp>][<modell>] = { screen: [w, h], chrome: {...}, slots: [...],\n"
        "//         slotAttrs: [...], back: <RGB565> }.\n"
        "// Zu jedem Rechteck stehen in *Attrs die Darstellungsangaben der Komponente:\n"
        "//   f = Font-ID · h/v = Ausrichtung (l/c/r bzw. t/c/b) · c = Schriftfarbe (RGB565).\n"
        "// Jeder Slot trägt die Rechtecke [x, y, w, h] seiner Bestandteile (icon/name/value); welche\n"
        "// es gibt, hängt von der Karte ab. Die Reihenfolge der Slots ist die der entities-Liste.\n"
        "//\n"
        "// `flow` (nur cardPower) sind die sechs Laufbalken – Nextion-Slider statt Textfelder, mit\n"
        "// `index` auf ihren Slot sowie Bereich und Startwert des Sliders.\n"
        "//\n"
        "// Nach einem Upstream-Update neu erzeugen. Das Werkzeug prüft dabei gegen CARD_CAPACITY.\n"
    )
    ZIEL.write_text(
        f"{kopf}\nexport const LAYOUTS = {json.dumps(layouts, indent=1, sort_keys=True)};\n",
        encoding="utf-8",
    )
    groesse = ZIEL.stat().st_size / 1024
    print(f"\n{ZIEL.relative_to(_REPO)} geschrieben ({groesse:.1f} kB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
