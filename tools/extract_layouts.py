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
    """
    komponenten: dict[str, tuple[int, int, int, int]] = {}
    for block in re.split(r"\n(?=[A-Za-z]+ \S+\n)", text):
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


def slots_card_power(komponenten: dict) -> list[dict]:
    """``cardPower`` nummeriert anders: die ersten beiden Einträge sitzen in der Mitte.

    ``tHome`` und ``tHome2`` tragen Eintrag 1 und 2, die sechs Außenplätze liegen in ``t0…t5`` mit
    Symbol (``t<N>Icon``), oberer Zeile (``t<N>o``) und unterer Zeile (``t<N>u``).
    """
    slots: list[dict] = []
    for name in ("^Text tHome$", "^Text tHome2$"):
        treffer = [rect for k, rect in komponenten.items() if re.match(name, k)]
        slots.append({"value": list(treffer[0])} if treffer else {})
    slots.extend(
        _rollen(
            komponenten,
            {"icon": r"^Text t(\d)Icon$", "name": r"^Text t(\d)o$", "value": r"^Text t(\d)u$"},
            basis=0,
        )
    )
    return slots


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


def layout_fuer(dump: str, model: str, seite: str) -> dict:
    komponenten = parse_components(dump)
    chrome = {}
    for rolle, muster in CHROME_PATTERNS.items():
        for name, rect in komponenten.items():
            if re.match(muster, name):
                chrome[rolle] = list(rect)
                break
    return {
        "screen": list(SCREENS[model]),
        "chrome": chrome,
        "slots": SEITEN[seite](komponenten),
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    repo = Path(argv[1])
    if not (repo / "HMI").is_dir():
        raise SystemExit(f"{repo} sieht nicht nach nspanel-lovelace-ui aus (kein HMI/-Ordner)")

    layouts: dict[str, dict] = {}
    abweichungen = 0
    for seite in SEITEN:
        layouts[seite] = {}
        for model, unterordner in MODEL_DIRS.items():
            datei = repo / unterordner / f"{seite}.txt"
            if not datei.is_file():
                print(f"  ?  {seite:<14} {model:<5} Dump fehlt ({datei})")
                abweichungen += 1
                continue
            layout = layout_fuer(datei.read_text(encoding="utf-8", errors="replace"), model, seite)
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
        "// Aufbau: LAYOUTS[<kartentyp>][<modell>] = { screen: [w, h], chrome: {...}, slots: [...] }.\n"
        "// Jeder Slot trägt die Rechtecke [x, y, w, h] seiner Bestandteile (icon/name/value); welche\n"
        "// es gibt, hängt von der Karte ab. Die Reihenfolge der Slots ist die der entities-Liste.\n"
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
