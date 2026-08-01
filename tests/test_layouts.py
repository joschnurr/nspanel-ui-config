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


SCREENSAVER = ("screensaver", "screensaver2")


def test_jede_karte_hat_titel_und_blaettertasten() -> None:
    """Der Rahmen sitzt bei allen Karten oben – Titel mittig, die Tasten links und rechts davon.

    Die Screensaver haben ihn nicht: sie füllen das Display vollständig aus.
    """
    for card_type, je_modell in LAYOUTS.items():
        for model, layout in je_modell.items():
            chrome = layout.get("chrome", {})
            if card_type in SCREENSAVER:
                assert not chrome, f"{card_type}/{model} sollte keinen Rahmen haben"
                continue
            assert set(chrome) == {"title", "prev", "next"}, f"{card_type}/{model}: {sorted(chrome)}"
            titel_x = chrome["title"][0]
            assert chrome["prev"][0] < titel_x < chrome["next"][0], (
                f"{card_type}/{model}: Titel liegt nicht zwischen den Blättertasten"
            )


def test_die_plaetze_stehen_in_anzeigereihenfolge() -> None:
    """Erst von links nach rechts, dann nach unten – sonst wäre die entities-Liste vertauscht.

    Ausgenommen sind die Karten, deren Plätze bewusst nicht in Leserichtung liegen: ``cardPower``
    hält die ersten beiden Einträge in der Mitte, und beim Screensaver gehört der letzte Platz dem
    alternativen Layout (er sitzt im Hauptbereich, also weiter oben als die Vorhersagespalten).
    """
    for card_type, je_modell in LAYOUTS.items():
        if card_type in ("cardPower",) + SCREENSAVER:
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


def test_screensaver_vorhersagespalten_stehen_nebeneinander() -> None:
    """Die Einträge 2–5 sind die Vorhersagespalten und laufen nach rechts.

    Das ist der Teil der Screensaver-Zuordnung, der beim Herleiten aus dem Seitencode schiefgehen
    könnte: ein vertauschter Feldindex würde die Spalten in falscher Reihenfolge belegen.
    """
    for model, layout in LAYOUTS["screensaver"].items():
        spalten = [min(r[0] for r in slot.values()) for slot in layout["slots"][1:5]]
        assert spalten == sorted(spalten), f"{model}: Vorhersagespalten nicht von links nach rechts"


def test_screensaver_kennt_uhrzeit_datum_und_das_alternative_layout() -> None:
    for model, layout in LAYOUTS["screensaver"].items():
        assert "tTime" in layout["special"], f"{model}: Uhrzeit fehlt"
        assert "tDate" in layout["special"], f"{model}: Datum fehlt"
        # Der Hauptbereich hat eine zweite Position für das alternative Layout (Eintrag 1 rückt
        # dorthin, sobald eine 6. Entity gesetzt ist).
        assert "0" in layout.get("alt", {}), f"{model}: Alt-Position von Eintrag 1 fehlt"

    for model, layout in LAYOUTS["screensaver2"].items():
        assert "tTime" in layout["special"], f"{model}: Uhrzeit fehlt"
        assert not layout.get("alt"), f"{model}: screensaver2 hat kein alternatives Layout"


def test_cardpower_symbole_tragen_die_abgemessene_umrandung() -> None:
    """Auf dem Gerät sitzt jedes äußere Symbol von ``cardPower`` in einem eingefassten Feld.

    Im Dump steht das als ``Style: border`` mit ``Border Color: 17299`` und ``Border Width: 2``.
    Ohne diese Angaben schweben die Symbole in der Vorschau frei, während das Gerät sie umrandet
    zeigt — nach den Laufbalken der auffälligste Unterschied, und er ist gemeldet worden.

    Die beiden mittleren Plätze haben keinen Rahmen; stünde dort einer, wäre die Zuordnung der
    Attribute zu den Komponenten verrutscht.
    """
    layouts = _layouts()
    for model, layout in layouts["cardPower"].items():
        attrs = layout["slotAttrs"]
        for index in range(2, 8):
            icon = attrs[index].get("icon") or {}
            assert icon.get("bw") == 2, f"cardPower/{model}: Platz {index} ohne Rahmenbreite"
            assert icon.get("bc") == 17299, f"cardPower/{model}: Platz {index} mit fremder Farbe"
        for index in (0, 1):
            assert "bc" not in (attrs[index].get("icon") or {}), (
                f"cardPower/{model}: der mittlere Platz {index} hat auf dem Gerät keinen Rahmen"
            )


def test_nur_cardpower_hat_umrandete_felder() -> None:
    """Gegenprobe: Der Rahmen darf nicht überall auftauchen, sonst ist das Muster zu grob.

    Name- und Wertfelder stehen im Dump als ``Style: flat`` — sie tragen zwar eine ``Border Color``,
    benutzen sie aber nicht. Würde die nur nach der Farbe gelesen, bekäme die halbe Karte Kästchen.
    """
    layouts = _layouts()
    for seite, modelle in layouts.items():
        if seite == "cardPower":
            continue
        for model, layout in modelle.items():
            for index, attrs in enumerate(layout.get("slotAttrs") or []):
                for rolle, attr in (attrs or {}).items():
                    assert "bc" not in (attr or {}), (
                        f"{seite}/{model}: Platz {index}/{rolle} hat unerwartet einen Rahmen"
                    )
