#!/usr/bin/env python3
"""Erzeugt ``www/panel/icon-names.js`` und ``icon-chars.js`` aus dem ``icon_mapping.py`` des Backends.

**Warum die Liste überhaupt mitkommt:** das Backend rendert nur Icons, die in seinem Mapping stehen —
und fällt bei allem anderen *still* auf ``alert-circle-outline`` zurück (``get_icon_id`` in
``icon_mapping.py``). Ein Tippfehler im Icon-Namen fällt also erst am Panel auf, und dort sieht man
nur ein Warndreieck. Der Editor prüft deshalb gegen diese Liste, statt jeden String durchzulassen.

**Warum zusätzlich die Zeichen:** das Mapping bildet jeden Namen auf ein Zeichen des Nextion-Icon-
Fonts ab (Private-Use-Bereich, ``U+E000``…``U+FAEF``) — und *dieses Zeichen* schickt das Backend
übers MQTT-Protokoll ans Display. Die Live-Vorschau bekommt also Zeichen, keine Namen, und braucht
den Rückweg. ``icon-chars.js`` steht in derselben Reihenfolge wie ``icon-names.js``: gleicher Index,
gleiches Icon.

Mitgeliefert statt zur Laufzeit gelesen: HA und AppDaemon laufen in getrennten Containern, die
Integration kann das Mapping also nicht einfach öffnen.

Aufruf (Pfad zeigt auf das Backend, das man unterstützen will):

    python3 tools/extract_icon_names.py /pfad/zu/appdaemon/apps/luibackend/icon_mapping.py

Nach einem Upstream-Update erneut laufen lassen; der Diff zeigt dann, welche Icons dazugekommen sind.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Die Zeilen im Mapping sehen aus wie:  'ab-testing': '',
NAME_PATTERN = re.compile(r"^\s*'([^']+)':\s*'", re.MULTILINE)

# Dieselbe Zeile, diesmal mit dem Zeichen dahinter.
PAIR_PATTERN = re.compile(r"^\s*'([^']+)':\s*'(.)'", re.MULTILINE)

PANEL_DIR = Path(__file__).resolve().parents[1] / "custom_components/nspanel_ui_config/www/panel"
TARGET = PANEL_DIR / "icon-names.js"
CHARS_TARGET = PANEL_DIR / "icon-chars.js"

CHARS_HEADER = """// AUTOMATISCH ERZEUGT von tools/extract_icon_names.py \u2013 nicht von Hand editieren.
//
// Zu jedem Namen in icon-names.js das Zeichen, mit dem das Backend dieses Icon \u00fcbertr\u00e4gt
// (Nextion-Icon-Font, Private-Use-Bereich). **Gleicher Index, gleiches Icon** \u2013 die
// Live-Vorschau bekommt \u00fcber MQTT nur das Zeichen und findet dar\u00fcber den Namen f\u00fcr
// <ha-icon>.
//
// Als \\uXXXX-Escapes statt roher Zeichen: der Private-Use-Bereich \u00fcbersteht nicht jeden
// Editor, jede Konsole und jeden Diff unbeschadet.
"""

HEADER = """// AUTOMATISCH ERZEUGT von tools/extract_icon_names.py – nicht von Hand editieren.
//
// Quelle: nspanel-lovelace-ui, appdaemon/apps/luibackend/icon_mapping.py ({count} Namen).
// Das Backend kennt ausschließlich diese Namen (ohne "mdi:"-Präfix) und fällt bei allem anderen
// still auf 'alert-circle-outline' zurück – deshalb prüft der Editor dagegen.
//
// Kommagetrennt statt als JSON-Array, das spart hier ~20 kB Anführungszeichen.
"""


def extract(mapping_file: Path) -> list[str]:
    names = NAME_PATTERN.findall(mapping_file.read_text(encoding="utf-8"))
    if not names:
        raise SystemExit(f"Keine Icon-Namen in {mapping_file} gefunden \u2013 falsche Datei?")
    unique = sorted(set(names))
    if "alert-circle-outline" not in unique:
        # Ohne den Fallback-Namen ist es fast sicher nicht das Mapping des Backends.
        raise SystemExit("Fallback-Icon 'alert-circle-outline' fehlt \u2013 unerwartetes Format")
    return unique


def extract_chars(mapping_file: Path, names: list[str]) -> list[str]:
    """Zu jedem Namen sein Zeichen \u2013 in genau der Reihenfolge der Namensliste.

    Steht ein Name mehrfach im Mapping, gilt das erste Zeichen; fehlt zu einem Namen eines
    (kommt nicht vor, w\u00e4re aber kein Grund abzubrechen), bleibt der Platz leer und die
    Live-Vorschau zeigt f\u00fcr dieses Icon eben keinen Namen an.
    """
    paare = PAIR_PATTERN.findall(mapping_file.read_text(encoding="utf-8"))
    je_name: dict[str, str] = {}
    for name, zeichen in paare:
        je_name.setdefault(name, zeichen)
    return [je_name.get(name, "") for name in names]


def render(names: list[str]) -> str:
    joined = ",".join(names)
    return (
        HEADER.format(count=len(names))
        + f"\nexport const ICON_COUNT = {len(names)};\n"
        + f'export const ICON_NAMES = "{joined}".split(",");\n'
    )


def render_chars(chars: list[str]) -> str:
    escaped = "".join(f"\\u{ord(z):04x}" if z else "\\u0000" for z in chars)
    return (
        CHARS_HEADER
        + f'\nexport const ICON_CHARS = "{escaped}";\n'
    )


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    quelle = Path(argv[1])
    names = extract(quelle)
    TARGET.write_text(render(names), encoding="utf-8")
    chars = extract_chars(quelle, names)
    CHARS_TARGET.write_text(render_chars(chars), encoding="utf-8")
    ohne = sum(1 for z in chars if not z)
    print(f"{TARGET.name}: {len(names)} Icon-Namen geschrieben")
    print(f"{CHARS_TARGET.name}: {len(chars) - ohne} Zeichen geschrieben" + (f" ({ohne} ohne)" if ohne else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
