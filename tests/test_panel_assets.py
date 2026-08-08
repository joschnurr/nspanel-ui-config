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


def test_panel_importiert_die_nebenmodule_unter_dem_ausgelieferten_namen() -> None:
    """Der Importpfad ist relativ zum statischen Verzeichnis — ein Tippfehler bricht das Panel.

    Die Nebenmodule werden **dynamisch** geladen, damit die Versions-Query der Panel-URL
    weitergereicht werden kann (sonst hängt der Browser nach einem Update an der alten Datei).
    Geprüft wird deshalb das Template-Literal, nicht die statische Importzeile.
    """
    quelle = PANEL_MODULE.read_text(encoding="utf-8")
    treffer = re.findall(r'await import\(`(\./[^`$]+)\$\{MODUL_VERSION\}`\)', quelle)
    assert treffer, "Das Panel lädt keine Nebenmodule – Icon-Liste nicht eingebunden?"
    for pfad in treffer:
        assert (PANEL_DIR / pfad[2:]).is_file(), f"Geladene Datei fehlt: {pfad}"


def test_nebenmodule_bekommen_die_versions_query_mit() -> None:
    """Ohne sie liefe man nach jedem Update Gefahr, neues Panel mit alter Geometrie zu mischen."""
    quelle = PANEL_MODULE.read_text(encoding="utf-8")
    assert "const MODUL_VERSION = new URL(import.meta.url).search;" in quelle
    # Kein statischer Import mehr, sonst rutscht ein Modul ohne Parameter durch.
    assert not re.search(r'^import .*? from "\./', quelle, re.MULTILINE), (
        "statischer Import gefunden – der bekäme keine Versions-Query"
    )


def test_kein_panel_modul_laedt_ein_nachbarmodul_statisch() -> None:
    """Die Kennung muss **durch die ganze Kette** reichen, nicht nur bis zur ersten Ebene.

    Der Test darüber sah nur die Hauptdatei an — und genau daran ist es vorbeigelaufen:
    ``preview-layouts.js`` wurde mit Kennung geladen, holte sich ``layouts.js`` daneben aber per
    statischem ``import``. Ein statischer Import löst relativ zur importierenden Datei auf und
    lässt die Query fallen; der Browser nahm also seine alte, zwischengespeicherte Geometrie. Das
    Ergebnis war ein Panel, dem die Laufbalken von ``cardPower`` fehlten, obwohl alle Dateien
    aktuell auf der Platte lagen — ein Fehlerbild, das wie ein nicht installiertes Update aussieht
    und keinem Test auffiel.
    """
    for modul in sorted(PANEL_DIR.glob("*.js")):
        quelle = modul.read_text(encoding="utf-8")
        statisch = re.findall(r'^import\s.*?\sfrom\s+["\']\./([^"\']+)["\']', quelle, re.MULTILINE)
        assert not statisch, (
            f"{modul.name} lädt {statisch} statisch – ohne Kennung, also womöglich aus dem "
            f"Zwischenspeicher. Dynamisch laden und die Query aus import.meta.url anhängen."
        )


def test_jedes_dynamisch_geladene_modul_bekommt_eine_kennung() -> None:
    """Ein dynamischer Import ohne Query wäre genauso still veraltet wie ein statischer."""
    for modul in sorted(PANEL_DIR.glob("*.js")):
        quelle = modul.read_text(encoding="utf-8")
        for treffer in re.findall(r"await import\(`\./([^`]+)`\)", quelle):
            pfad, _, query = treffer.partition("$")
            assert query, f"{modul.name}: import von {pfad} ohne Versions-Query"
            assert (PANEL_DIR / pfad).is_file(), f"{modul.name}: geladene Datei fehlt: {pfad}"


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


def test_kein_platz_wird_von_der_platzhalter_tabelle_verdeckt() -> None:
    """Was eine eigene Zeichenfunktion hat, darf nicht vorher als Platzhalter abgefangen werden.

    Die Platzhalter-Tabelle steht am Anfang von ``_slotElement`` und greift, sobald sie den
    ``kind`` kennt — sie kommt also **vor** jeder spezialisierten Abfrage. Stand dort noch ein
    Eintrag für eine Art, die inzwischen richtig gezeichnet wird, blieb der graue Kasten stehen
    und die neue Funktion lief nie an. Genau so blieb der QR-Code nach v0.30 zunächst unsichtbar.
    """
    quelle = PANEL_MODULE.read_text(encoding="utf-8")
    tabelle = re.search(r"const platzhalter = \{(.*?)\}\[slot\.kind\];", quelle, re.DOTALL)
    assert tabelle, "Platzhalter-Tabelle nicht gefunden – wurde sie umbenannt?"
    # Schlüssel der Tabelle (nur die oberste Ebene, verschachtelte Werte gehören zu flat-main).
    platzhalter_arten = set(re.findall(r'^\s{6}"?([a-zA-Z-]+)"?:', tabelle.group(1), re.MULTILINE))

    # Arten mit eigener Zeichenfunktion. Gezählt wird erst **hinter** dem Platzhalter-Block,
    # der mit der Titel-Abfrage endet: Innerhalb des Blocks steht noch eine `flat-main`-Abfrage,
    # die lediglich den Entity-Namen anhängt — die ist kein Konflikt, sondern Teil des
    # Platzhalters selbst.
    beginn = quelle.find('if (slot.kind === "title")', tabelle.end())
    assert beginn > 0, "Titel-Abfrage nicht gefunden – Aufbau von _slotElement geändert?"
    danach = quelle[beginn:]
    eigene = set(re.findall(r'slot\.kind === "([a-zA-Z-]+)"', danach))
    eigene |= {p.rstrip("-") for p in re.findall(r'slot\.kind\.startsWith\("([a-zA-Z-]+)"\)', danach)}

    kollision = platzhalter_arten & eigene
    assert not kollision, (
        f"Diese Arten stehen als Platzhalter UND haben eine eigene Zeichenfunktion: "
        f"{sorted(kollision)} – der Platzhalter gewinnt, weil er zuerst geprüft wird."
    )


def test_die_symbolregeln_decken_sich_mit_dem_backend() -> None:
    """`icon-rules.js` ist ein Erzeugnis aus `icons.py` — hier faellt eine vergessene Neuerzeugung auf.

    Geprueft wird gegen das Backend, das auf dieser Installation laeuft. Fehlt es (etwa in CI),
    ueberspringt der Test sich selbst: Die Datei liegt im Repo, das Backend nicht.
    """
    import json
    from pathlib import Path

    backend = Path("/home/johannes/smarthome/appdaemon/apps/luibackend/icons.py")
    if not backend.is_file():
        return  # kein Backend zur Hand – nichts zu vergleichen

    regeln_js = PANEL_DIR / "icon-rules.js"
    assert regeln_js.is_file(), "icon-rules.js fehlt – tools/extract_icon_rules.py ausfuehren"
    text = regeln_js.read_text(encoding="utf-8")
    regeln = json.loads(text[text.index("{") : text.rindex("}") + 1])

    quelle = backend.read_text(encoding="utf-8")
    # Stichproben ueber alle Tabellenarten – Schluessel UND Wert muessen stimmen.
    for tabelle, schluessel, erwartet in (
        ("simple_type_mapping", "switch", "light-switch"),
        ("simple_type_mapping", "light", "lightbulb"),
        ("climate_mapping", "heat", "fire"),
        ("alarm_control_panel_mapping", "disarmed", "shield-off"),
        ("sensor_mapping", "temperature", "thermometer"),
        ("sensor_mapping_on", "door", "door-open"),
        ("sensor_mapping_off", "door", "door-closed"),
    ):
        assert regeln[tabelle].get(schluessel) == erwartet, (
            f"{tabelle}[{schluessel}] ist {regeln[tabelle].get(schluessel)!r}, erwartet {erwartet!r}"
        )
        assert f'"{erwartet}"' in quelle or f"'{erwartet}'" in quelle, (
            f"{erwartet} steht nicht im Backend – icon-rules.js ist veraltet"
        )

    # Rollladen: das Backend haelt fuenf Symbole je Geraeteklasse, uebernommen werden die ersten
    # beiden (offen/geschlossen). Die drei uebrigen sind die Bedientasten der Zeile.
    assert regeln["cover_mapping"]["shutter"] == {
        "offen": "window-shutter-open",
        "geschlossen": "window-shutter",
    }
    # Die Zahl der Eintraege muss mitwachsen, sonst faellt ein Upstream-Zuwachs nicht auf.
    import re

    treffer = re.search(r"^sensor_mapping\s*=\s*\{(.*?)^\}", quelle, re.M | re.S)
    im_backend = len(re.findall(r"['\"][^'\"]*['\"]\s*:", treffer.group(1)))
    assert len(regeln["sensor_mapping"]) == im_backend, (
        f"sensor_mapping: {len(regeln['sensor_mapping'])} in icon-rules.js, {im_backend} im Backend"
    )
