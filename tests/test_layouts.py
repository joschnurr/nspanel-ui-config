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


# Karten mit festem Aufbau statt Entity-Liste: Sie zeigen genau eine Entity, aber auf fest
# aufgeteilter Fläche (Ist-Temperatur, Sollwert, Zustand, Betriebsarten). `CARD_CAPACITY` zählt
# Listenplätze und kennt sie deshalb bewusst nicht — ihre Prüfungen stehen weiter unten.
FESTE = ("cardThermo", "cardAlarm")


def test_jede_abgemessene_karte_hat_genau_so_viele_plaetze_wie_das_schema_sagt() -> None:
    for card_type, je_modell in LAYOUTS.items():
        if card_type in FESTE:
            continue
        for model, layout in je_modell.items():
            erwartet = schema.CARD_CAPACITY.get(card_type, {}).get(model)
            assert erwartet is not None, f"{card_type}/{model} steht nicht in CARD_CAPACITY"
            assert len(layout["slots"]) == erwartet, (
                f"{card_type}/{model}: {len(layout['slots'])} Plätze in layouts.js, "
                f"{erwartet} laut Schema – tools/extract_layouts.py erneut ausführen"
            )


def test_feste_karten_haben_rollen_statt_plaetze() -> None:
    """`cardThermo` bringt benannte Flächen mit – und keine Listenplätze, die es nicht hat."""
    for card_type in FESTE:
        assert card_type in LAYOUTS, f"{card_type} fehlt in layouts.js"
        for model, layout in LAYOUTS[card_type].items():
            assert layout["slots"] == [], f"{card_type}/{model} sollte keine Listenplätze haben"
            assert layout["fixed"], f"{card_type}/{model}: keine benannten Flächen"
            assert card_type not in schema.CARD_CAPACITY, (
                f"{card_type} steht in CARD_CAPACITY – dann gehört es nicht zu den festen Karten"
            )


def test_cardalarm_hat_tastatur_zustand_und_vier_aktionstasten() -> None:
    """Zwoelf Tastaturplaetze, das Zustandssymbol, das PIN-Feld und vier Aktionstasten.

    `b9` ist dabei KEINE Ziffer, sondern die Zusatztaste unten links — deshalb traegt sie eine
    eigene Rolle (`extra`) und steht trotzdem im Tastenraster.
    """
    for model, layout in LAYOUTS["cardAlarm"].items():
        fest = layout["fixed"]
        for rolle in ("code", "state", "extra"):
            assert rolle in fest, f"cardAlarm/{model}: Rolle {rolle} fehlt"
        tasten = [r for r in fest if r.startswith("key")]
        assert len(tasten) == 12, f"cardAlarm/{model}: {len(tasten)} Tastaturplaetze statt 12"
        assert fest["extra"] == fest["key9"], "die Zusatztaste ist der Platz b9"
        assert len(layout["modes"]) == 4, f"cardAlarm/{model}: {len(layout['modes'])} Aktionstasten statt 4"


def test_cardthermo_hat_beide_bedienbilder_und_acht_betriebsarten() -> None:
    """Ein und zwei Sollwerte, dazu die acht Tasten – auf jedem Modell vollständig.

    Die acht Tasten sind der Grund, warum der Dump-Parser an jeder nicht eingerückten Zeile
    trennen muss: Sie heißen ``Dual-state Button btN``, und ein Muster wie ``[A-Za-z]+ \\S+``
    übersieht diesen Typ samt Bindestrich. Vor dieser Korrektur fehlten sie hier spurlos.
    """
    ein_sollwert = ("dest", "destUnit", "up", "down")
    zwei_sollwerte = ("destHigh", "destLow", "upHigh", "downHigh", "upLow", "downLow")
    for model, layout in LAYOUTS["cardThermo"].items():
        fest = layout["fixed"]
        for rolle in ein_sollwert + zwei_sollwerte + ("curTemp", "state", "detail"):
            assert rolle in fest, f"cardThermo/{model}: Rolle {rolle} fehlt"
        assert len(layout["modes"]) == 8, (
            f"cardThermo/{model}: {len(layout['modes'])} Betriebsartentasten statt 8"
        )
        # Jede Taste braucht ihre Darstellungsattribute, sonst steht das Symbol falsch im Feld.
        assert len(layout["modeAttrs"]) == 8, f"cardThermo/{model}: Attribute fehlen"


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
            # Feste Karten: die benannten Flächen und die Betriebsartentasten zählen genauso.
            rechtecke.extend(layout.get("fixed", {}).values())
            rechtecke.extend(layout.get("modes", []))
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
        # Platz 0 ist die Mittelsäule – dasselbe umrandete Symbolfeld, nur hoch statt quadratisch.
        assert (attrs[0].get("icon") or {}).get("bw") == 2, f"cardPower/{model}: Säule ohne Rahmen"
        # Platz 1 hat am Gerät gar kein Symbolfeld, also auch keinen Rahmen.
        assert "icon" not in attrs[1], f"cardPower/{model}: Eintrag 1 hat kein Symbol"


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


def test_cardpower_mitte_ist_ein_eintrag_mit_zahl_und_einheit() -> None:
    """Die Mitte trägt **zwei** Einträge, nicht vier Felder — jeder mit Zahl und Einheit getrennt.

    Vorher galten ``tHome`` und ``tHome2`` als Eintrag 1 und 2. Der Seitencode sagt etwas anderes:
    Feld 19 geht nach ``tHome`` und wird am ersten Leerzeichen geteilt (Zahl nach ``tHome``,
    Einheit nach ``tHome2``); Feld 26 ebenso nach ``tHomeO``/``tHomeO2``. Aus der Feldarithmetik
    folgt: 19 ist der Wert von Eintrag 0, 26 der von Eintrag 1.

    ``t1`` ist Rahmen und Symbol in einem — die umrandete Mittelsäule mit dem Haussymbol. Eintrag 1
    hat kein eigenes Symbol; auf dem Gerät steht dort nur eine Zahl.
    """
    for model, layout in _layouts()["cardPower"].items():
        mitte, oben = layout["slots"][0], layout["slots"][1]
        assert set(mitte) == {"icon", "value", "unit"}, f"cardPower/{model}: Platz 0 {sorted(mitte)}"
        assert set(oben) == {"value", "unit"}, f"cardPower/{model}: Platz 1 {sorted(oben)}"

        # Das Symbolfeld von Platz 0 ist die Säule: es umschließt beide Wertefelder.
        ix, iy, iw, ih = mitte["icon"]
        for rolle in ("value", "unit"):
            x, y, w, h = mitte[rolle]
            assert ix <= x and iy <= y, f"cardPower/{model}: {rolle} liegt außerhalb der Säule"
            assert x + w <= ix + iw and y + h <= iy + ih, f"cardPower/{model}: {rolle} ragt heraus"

        rand = layout["slotAttrs"][0]["icon"]
        assert rand.get("bw") == 2 and rand.get("bc") == 17299, "die Säule ist umrandet"
        assert "icon" not in layout["slotAttrs"][1], "Eintrag 1 hat kein Symbolfeld"


def test_nur_cardpower_kennt_die_einheit_als_eigenes_feld() -> None:
    """Sonst würde anderswo ein Wert an einem Leerzeichen zerschnitten, wo das Gerät ihn ganz zeigt."""
    for seite, modelle in _layouts().items():
        if seite == "cardPower":
            continue
        for model, layout in modelle.items():
            for index, slot in enumerate(layout.get("slots") or []):
                assert "unit" not in slot, f"{seite}/{model}: Platz {index} hat unerwartet ein unit-Feld"
