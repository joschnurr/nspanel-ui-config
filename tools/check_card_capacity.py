#!/usr/bin/env python3
"""Zählt die Anzeigeplätze der NSPanel-Karten aus den HMI-Dumps nach und vergleicht sie mit ``schema.py``.

**Warum es dieses Werkzeug gibt:** ``CARD_CAPACITY`` in ``schema.py`` beantwortet die Frage "wie
viele Entities zeigt diese Karte eigentlich?" — und das ist die einzige Angabe im Schema, die man
nirgends im Backend nachlesen kann. Weder Backend noch Generator kürzen die Entity-Liste; die
überzähligen Einträge werden mitgesendet und vom Nextion-Display schlicht ignoriert. Die Wahrheit
steht allein in der Display-Firmware.

Ablesbar ist sie aus den Textdumps der HMI-Seiten im Upstream-Repo joBr99/nspanel-lovelace-ui:

    HMI/n2t-out-visual/<seite>.txt                      (Modell eu)
    HMI/US/landscape/n2t-out-visual/<seite>.txt         (Modell us-l)
    HMI/US/portrait/n2t-out-visual/<seite>.txt          (Modell us-p)

Dort ist jede Nextion-Komponente als ``<Typ> <Name>`` aufgeführt; die durchnummerierten
Slot-Komponenten (``tEntity1…``, ``bEntity1…``, ``t0Icon…``) ergeben die Kapazität.

Die beiden Screensaver sind der Sonderfall: sie haben keine gleichnamig durchnummerierte Reihe,
sondern verteilen den ``weatherUpdate~``-String in 6er-Blöcken auf verschiedene Bausteine. Ihre
Zahlen stammen deshalb aus ``HMI/code_gen/pages/screensaver{,2}.py`` und werden hier nur gegen die
erwarteten Bausteine plausibilisiert, nicht neu hergeleitet.

Aufruf mit einer lokalen Kopie des Upstream-Repos:

    python3 tools/check_card_capacity.py /pfad/zu/nspanel-lovelace-ui

Ausgabe ist ein Vergleich Ist/Soll; Rückgabewert 1, sobald etwas abweicht. Nach einem
Upstream-Update laufen lassen — ein neues Display-Layout ändert genau hier die Wahrheit.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

# schema.py direkt als Datei laden: ein regulärer Paketimport würde ``__init__.py`` ausführen und
# damit Home Assistant hereinziehen, das hier nirgends gebraucht wird (gleiche Überlegung wie in
# tests/conftest.py). schema.py selbst hängt an nichts außer der Standardbibliothek.
_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "custom_components/nspanel_ui_config/schema.py"
)
_spec = importlib.util.spec_from_file_location("nspanel_schema", _SCHEMA_PATH)
_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_schema)
CARD_CAPACITY = _schema.CARD_CAPACITY

# Unterverzeichnis der Dumps je Modell.
MODEL_DIRS = {
    "eu": "HMI/n2t-out-visual",
    "us-l": "HMI/US/landscape/n2t-out-visual",
    "us-p": "HMI/US/portrait/n2t-out-visual",
}

# Welche Komponentenreihe die Plätze einer Seite trägt. Mehrere Muster = Summe der Reihen.
SLOT_PATTERNS: dict[str, tuple[str, ...]] = {
    "cardEntities": (r"^Text tEntity(\d+)$",),
    "cardGrid": (r"^Text tEntity(\d+)$",),
    "cardGrid2": (r"^Text tEntity(\d+)$",),
    "cardQR": (r"^Text tEntity(\d+)$",),
    "cardMedia": (r"^Button bEntity(\d+)$",),
    # Zwei in der Mitte (tHome/tHome2), sechs außen (t0Icon…t5Icon).
    "cardPower": (r"^Text t(\d)Icon$", r"^Text tHome2?$"),
}

# Screensaver: aus code_gen/pages/screensaver{,2}.py abgeleitete Aufteilung. Der Wert ist die Summe,
# die Bausteine dienen der Plausibilisierung gegen den Dump.
SCREENSAVER_SLOTS = {
    # 1 Hauptbereich + 4 Vorhersagespalten + 1 weitere, die das alternative Layout auslöst.
    "screensaver": (6, {r"^Text tForecast(\d)$": 4, r"^Text tMainTextAlt2$": 1}),
    # 1 Hauptbereich + 3 (Icon/Wert) + 6 (Icon/Name/Wert) + 5 (nur Icon).
    "screensaver2": (15, {r"^Text d(\d)Icon$": 3, r"^Text e(\d)Icon$": 6, r"^Text f(\d)Icon$": 5}),
}


def count_slots(dump: str, patterns: tuple[str, ...]) -> int:
    total = 0
    for pattern in patterns:
        matches = re.findall(pattern, dump, re.MULTILINE)
        if not matches:
            continue
        numbered = [int(m) for m in matches if m.isdigit()]
        # Durchnummerierte Reihen über die höchste Nummer zählen (t0Icon beginnt bei 0),
        # unnummerierte (tHome/tHome2) schlicht über die Trefferzahl.
        total += max(numbered) + (1 if 0 in numbered else 0) if numbered else len(matches)
    return total


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    repo = Path(argv[1])
    if not (repo / "HMI").is_dir():
        raise SystemExit(f"{repo} sieht nicht nach nspanel-lovelace-ui aus (kein HMI/-Ordner)")

    abweichungen = 0
    for card_type, by_model in sorted(CARD_CAPACITY.items()):
        for model, erwartet in sorted(by_model.items()):
            dump_file = repo / MODEL_DIRS[model] / f"{card_type}.txt"
            if not dump_file.is_file():
                print(f"  ?  {card_type:<14} {model:<5} Dump fehlt ({dump_file})")
                continue
            dump = dump_file.read_text(encoding="utf-8", errors="replace")

            if card_type in SCREENSAVER_SLOTS:
                summe, bausteine = SCREENSAVER_SLOTS[card_type]
                fehler = [
                    f"{pattern}: {len(re.findall(pattern, dump, re.MULTILINE))} statt {anzahl}"
                    for pattern, anzahl in bausteine.items()
                    if len(re.findall(pattern, dump, re.MULTILINE)) != anzahl
                ]
                gezaehlt = summe if not fehler else -1
                hinweis = f"  ({'; '.join(fehler)})" if fehler else ""
            else:
                gezaehlt = count_slots(dump, SLOT_PATTERNS[card_type])
                hinweis = ""

            passt = gezaehlt == erwartet
            abweichungen += 0 if passt else 1
            print(
                f"  {'ok' if passt else 'XX'} {card_type:<14} {model:<5} "
                f"Schema {erwartet:>2}, HMI {gezaehlt:>2}{hinweis}"
            )

    print()
    if abweichungen:
        print(f"{abweichungen} Abweichung(en) – CARD_CAPACITY in schema.py anpassen.")
        return 1
    print("CARD_CAPACITY stimmt mit den HMI-Dumps überein.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
