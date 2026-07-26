"""Prüft die erzeugte Slot-Geometrie (``www/panel/layouts.js``) gegen das Schema.

Die Datei ist ein **Erzeugnis** von ``tools/extract_layouts.py`` und liegt trotzdem im Repo – das
Panel soll ohne Build-Schritt auskommen. Genau daraus entsteht das Risiko, das dieser Test abfängt:
Wird ``CARD_CAPACITY`` in ``schema.py`` geändert, ohne die Layouts neu zu erzeugen (oder umgekehrt),
zeigt der Editor eine andere Platzzahl an als die Vorschau zeichnet. Ohne Netz und ohne Kopie des
Upstream-Repos ist das hier die einzige Stelle, an der das auffällt.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from nspanel_ui_config import schema

LAYOUTS_JS = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "nspanel_ui_config"
    / "www"
    / "panel"
    / "layouts.js"
)


def _layouts() -> dict:
    text = LAYOUTS_JS.read_text(encoding="utf-8")
    match = re.search(r"export const LAYOUTS = (\{.*\});\s*$", text, re.DOTALL)
    assert match, "LAYOUTS nicht im erwarteten Format gefunden"
    return json.loads(match.group(1))


LAYOUTS = _layouts()


def test_datei_ist_vorhanden_und_lesbar() -> None:
    assert LAYOUTS, "layouts.js ist leer"
    assert LAYOUTS_JS.read_text(encoding="utf-8").startswith("//"), "Kopfkommentar fehlt"


def test_jede_abgemessene_karte_hat_genau_so_viele_plaetze_wie_das_schema_sagt() -> None:
    for card_type, je_modell in LAYOUTS.items():
        for model, layout in je_modell.items():
            erwartet = schema.CARD_CAPACITY.get(card_type, {}).get(model)
            assert erwartet is not None, f"{card_type}/{model} steht nicht in CARD_CAPACITY"
            assert len(layout["slots"]) == erwartet, (
                f"{card_type}/{model}: {len(layout['slots'])} Plätze in layouts.js, "
                f"{erwartet} laut Schema – tools/extract_layouts.py erneut ausführen"
            )


def test_alle_modelle_sind_abgedeckt() -> None:
    for card_type, je_modell in LAYOUTS.items():
        assert set(je_modell) == set(schema.MODELS), f"{card_type} deckt nicht alle Modelle ab"


def test_kein_rechteck_liegt_ausserhalb_des_displays() -> None:
    for card_type, je_modell in LAYOUTS.items():
        for model, layout in je_modell.items():
            breite, hoehe = layout["screen"]
            rechtecke = list(layout.get("chrome", {}).values())
            for slot in layout["slots"]:
                rechtecke.extend(slot.values())
            for x, y, w, h in rechtecke:
                assert 0 <= x and 0 <= y, f"{card_type}/{model}: negative Position"
                assert w > 0 and h > 0, f"{card_type}/{model}: leere Fläche"
                assert x + w <= breite and y + h <= hoehe, (
                    f"{card_type}/{model}: Rechteck ({x},{y},{w},{h}) ragt über {breite}×{hoehe} hinaus"
                )


def test_jede_karte_hat_titel_und_blaettertasten() -> None:
    """Der Rahmen sitzt bei allen Karten oben – Titel mittig, die Tasten links und rechts davon."""
    for card_type, je_modell in LAYOUTS.items():
        for model, layout in je_modell.items():
            chrome = layout.get("chrome", {})
            assert set(chrome) == {"title", "prev", "next"}, f"{card_type}/{model}: {sorted(chrome)}"
            titel_x = chrome["title"][0]
            assert chrome["prev"][0] < titel_x < chrome["next"][0], (
                f"{card_type}/{model}: Titel liegt nicht zwischen den Blättertasten"
            )


def test_die_plaetze_stehen_in_anzeigereihenfolge() -> None:
    """Erst von links nach rechts, dann nach unten – sonst wäre die entities-Liste vertauscht.

    Ausgenommen ist cardPower: dort stehen die ersten beiden Einträge in der Mitte, die übrigen
    außen herum (siehe CAPACITY_LAYOUT_NOTES).
    """
    for card_type, je_modell in LAYOUTS.items():
        if card_type == "cardPower":
            continue
        for model, layout in je_modell.items():
            oben_links = [
                (min(r[1] for r in slot.values()), min(r[0] for r in slot.values()))
                for slot in layout["slots"]
            ]
            # Innerhalb einer Zeile (gleiche Höhe) muss x aufsteigen, Zeilen nach unten.
            for (y1, x1), (y2, x2) in zip(oben_links, oben_links[1:]):
                assert y2 > y1 or (abs(y2 - y1) <= 2 and x2 > x1), (
                    f"{card_type}/{model}: Reihenfolge springt von ({x1},{y1}) auf ({x2},{y2})"
                )
