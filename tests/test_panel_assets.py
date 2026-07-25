"""Prüft die statischen Dateien des Panels — vor allem die mitgelieferte Icon-Namensliste.

Diese Liste (erzeugt von ``tools/extract_icon_names.py``) entscheidet, ob der Editor einen Icon-Namen
als gültig anzeigt. Ist sie kaputt oder leer, fällt das im Browser nur als „alles unbekannt" auf —
hier fällt es sofort auf. Der Node-Test (``tests/panel.test.mjs``) prüft die Logik darauf, dieser Test
die Datei selbst.
"""

from __future__ import annotations

import re
from pathlib import Path

PANEL_DIR = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "nspanel_ui_config"
    / "www"
    / "panel"
)
PANEL_MODULE = PANEL_DIR / "nspanel-ui-config-panel.js"
ICON_LIST = PANEL_DIR / "icon-names.js"

# Der Fallback des Backends: fehlt er, ist es nicht dessen Mapping (siehe tools/extract_icon_names.py).
FALLBACK_ICON = "alert-circle-outline"


def _icon_names() -> list[str]:
    text = ICON_LIST.read_text(encoding="utf-8")
    match = re.search(r'export const ICON_NAMES = "(.*?)"\.split\(","\);', text, re.DOTALL)
    assert match, "ICON_NAMES nicht im erwarteten Format gefunden"
    return match.group(1).split(",")


def _declared_count() -> int:
    match = re.search(r"export const ICON_COUNT = (\d+);", ICON_LIST.read_text(encoding="utf-8"))
    assert match, "ICON_COUNT fehlt"
    return int(match.group(1))


def test_panel_dateien_sind_vorhanden() -> None:
    assert PANEL_MODULE.is_file(), "Panel-Modul fehlt"
    assert ICON_LIST.is_file(), "Icon-Namensliste fehlt"


def test_panel_importiert_die_icon_liste_unter_dem_ausgelieferten_namen() -> None:
    """Der Importpfad ist relativ zum statischen Verzeichnis — ein Tippfehler bricht das Panel."""
    quelle = PANEL_MODULE.read_text(encoding="utf-8")
    treffer = re.findall(r'^import .*? from "(\./[^"]+)";', quelle, re.MULTILINE)
    assert treffer, "Das Panel importiert nichts – Icon-Liste nicht eingebunden?"
    for pfad in treffer:
        assert (PANEL_DIR / pfad[2:]).is_file(), f"Importierte Datei fehlt: {pfad}"


def test_icon_liste_ist_plausibel_gross() -> None:
    """Das Mapping des Backends hat ~6900 Einträge; ein Bruchteil davon wäre ein Extraktionsfehler."""
    namen = _icon_names()
    assert len(namen) > 5000, f"nur {len(namen)} Icon-Namen – Extraktion vermutlich kaputt"
    assert _declared_count() == len(namen), "ICON_COUNT passt nicht zur Liste"


def test_icon_liste_ist_sortiert_und_eindeutig() -> None:
    namen = _icon_names()
    assert namen == sorted(namen), "Liste ist nicht sortiert (erschwert Diffs nach Upstream-Updates)"
    assert len(set(namen)) == len(namen), "Liste enthält Duplikate"


def test_icon_liste_enthaelt_keine_praefixe_und_keine_leeren_namen() -> None:
    """Das Backend strippt ``mdi:`` selbst — die Namen stehen ohne Präfix im Mapping."""
    for name in _icon_names():
        assert name, "leerer Icon-Name"
        assert not name.startswith("mdi:"), f"Name mit Präfix: {name}"
        assert " " not in name, f"Name mit Leerzeichen: {name}"


def test_icon_liste_enthaelt_fallback_und_gaengige_namen() -> None:
    namen = set(_icon_names())
    assert FALLBACK_ICON in namen, "Fallback-Icon des Backends fehlt"
    for name in ("lightbulb", "thermometer-water", "garage-variant-lock", "solar-power"):
        assert name in namen, f"gängiges Icon fehlt: {name}"
