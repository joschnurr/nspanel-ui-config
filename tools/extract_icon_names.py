#!/usr/bin/env python3
"""Erzeugt ``www/panel/icon-names.js`` aus dem ``icon_mapping.py`` des Backends.

**Warum die Liste überhaupt mitkommt:** das Backend rendert nur Icons, die in seinem Mapping stehen —
und fällt bei allem anderen *still* auf ``alert-circle-outline`` zurück (``get_icon_id`` in
``icon_mapping.py``). Ein Tippfehler im Icon-Namen fällt also erst am Panel auf, und dort sieht man
nur ein Warndreieck. Der Editor prüft deshalb gegen diese Liste, statt jeden String durchzulassen.

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

TARGET = Path(__file__).resolve().parents[1] / (
    "custom_components/nspanel_ui_config/www/panel/icon-names.js"
)

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
        raise SystemExit(f"Keine Icon-Namen in {mapping_file} gefunden – falsche Datei?")
    unique = sorted(set(names))
    if "alert-circle-outline" not in unique:
        # Ohne den Fallback-Namen ist es fast sicher nicht das Mapping des Backends.
        raise SystemExit("Fallback-Icon 'alert-circle-outline' fehlt – unerwartetes Format")
    return unique


def render(names: list[str]) -> str:
    joined = ",".join(names)
    return (
        HEADER.format(count=len(names))
        + f"\nexport const ICON_COUNT = {len(names)};\n"
        + f'export const ICON_NAMES = "{joined}".split(",");\n'
    )


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    names = extract(Path(argv[1]))
    TARGET.write_text(render(names), encoding="utf-8")
    print(f"{TARGET.relative_to(TARGET.parents[4])}: {len(names)} Icon-Namen geschrieben")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
