#!/usr/bin/env python3
"""Zieht die Symbolableitung des Backends nach ``www/panel/icon-rules.js``.

**Wozu:** Steht am Eintrag kein ``icon``, wählt das Backend selbst eines — nach Domäne, Zustand und
``device_class`` (``get_icon_ha`` in ``icons.py``). Die Vorschau borgte sich stattdessen das Symbol,
das Home Assistant für die Entity führt. Bei ganzen Domänen gibt es das aber gar nicht: Ein
Template-Rollladen hat kein ``icon``-Attribut, und die Vorschau zeigte dort den grauen Platzhalter,
während das Gerät eine Jalousie zeichnet.

**Warum erzeugt statt abgeschrieben:** Die Tabellen sind lang (31 Sensor-Geräteklassen, je 27 für
binäre Sensoren an/aus, 11 Rollladenarten …) und ändern sich mit dem Upstream. Von Hand gepflegt
liefen sie unweigerlich auseinander; hier genügt ein erneuter Lauf.

Aufruf mit dem AppDaemon-Verzeichnis des Backends:

    python3 tools/extract_icon_rules.py /pfad/zu/appdaemon/apps/luibackend

Nicht übernommen werden Zweige, die Wissen brauchen, das nur das Backend hat — ``get_icon_ha``
greift für Medienspieler etwa auf ``media_content_type`` zu, das in Home Assistant nur während der
Wiedergabe gesetzt ist. Solche Fälle bleiben der bisherigen Näherung überlassen (Symbol aus HA,
als solches gekennzeichnet).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ZIEL = Path(__file__).resolve().parents[1] / "custom_components/nspanel_ui_config/www/panel/icon-rules.js"

# Die Tabellen, die sich eins zu eins übernehmen lassen: Schlüssel → Symbolname.
EINFACHE_TABELLEN = (
    "simple_type_mapping",
    "weather_mapping",
    "climate_mapping",
    "alarm_control_panel_mapping",
    "sensor_mapping",
    "sensor_mapping_on",
    "sensor_mapping_off",
    "media_content_type_mapping",
)


def tabelle(quelle: str, name: str) -> dict[str, str]:
    """Ein ``name = { … }``-Block als Dict. Kommentare und Zeilenumbrüche stören nicht."""
    treffer = re.search(rf"^{name}\s*=\s*\{{(.*?)^\}}", quelle, re.M | re.S)
    if not treffer:
        return {}
    return {
        schluessel: wert
        for schluessel, wert in re.findall(
            r"['\"]([^'\"]*)['\"]\s*:\s*['\"]([^'\"]+)['\"]", treffer.group(1)
        )
    }


def cover_tabelle(quelle: str) -> dict[str, dict[str, str]]:
    """``cover_mapping`` trägt je Geräteklasse fünf Symbole – gebraucht werden die ersten beiden.

    Die Reihenfolge steht als Kommentar in der Datei selbst:
    ``(icon-open, icon-closed, icon-cover-open, icon-cover-stop, icon-cover-close)``. Die drei
    letzten sind die Bedientasten der Zeile, nicht das Symbol des Eintrags.
    """
    treffer = re.search(r"^cover_mapping\s*=\s*\{(.*?)^\}", quelle, re.M | re.S)
    if not treffer:
        return {}
    ergebnis = {}
    for zeile in treffer.group(1).splitlines():
        m = re.match(r"\s*['\"]([^'\"]+)['\"]\s*:\s*\((.*)\)\s*,?\s*$", zeile)
        if not m:
            continue
        symbole = re.findall(r"['\"]([^'\"]+)['\"]", m.group(2))
        if len(symbole) >= 2:
            ergebnis[m.group(1)] = {"offen": symbole[0], "geschlossen": symbole[1]}
    return ergebnis


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    quelle = (Path(argv[1]) / "icons.py").read_text(encoding="utf-8")

    regeln: dict[str, object] = {t: tabelle(quelle, t) for t in EINFACHE_TABELLEN}
    regeln["cover_mapping"] = cover_tabelle(quelle)

    # Zweige, die im Code stehen statt in einer Tabelle. Sie werden hier bewusst wiederholt und
    # nicht geparst: Es sind fünf Zeilen, und ein Parser dafür wäre schwerer zu prüfen als die
    # Zeilen selbst. Der Test hält sie gegen den Quelltext.
    regeln["feste_zweige"] = {
        "input_boolean": {"on": "check-circle-outline", "sonst": "close-circle-outline"},
        "lock": {"unlocked": "lock-open", "sonst": "lock"},
        "sun": {"above_horizon": "weather-sunset-up", "sonst": "weather-sunset-down"},
        "binary_sensor": {"on": "checkbox-marked-circle", "sonst": "radiobox-blank"},
        "media_player": {"sonst": "speaker-off"},
    }
    regeln["ersatz"] = "alert-circle-outline"
    # Diese beiden entity_ids behandelt das Backend als Wetter, obwohl sie Sensoren sind.
    regeln["wetter_sonderfaelle"] = [
        "sensor.weather_forecast_daily",
        "sensor.weather_forecast_hourly",
    ]

    for name, inhalt in regeln.items():
        if isinstance(inhalt, dict):
            print(f"  {name:28s} {len(inhalt)} Einträge")

    kopf = (
        "// Erzeugt von tools/extract_icon_rules.py — nicht von Hand ändern.\n"
        "//\n"
        "// Die Symbolableitung des Backends (`get_icon_ha` in icons.py) für Einträge ohne eigenes\n"
        "// `icon`. Die Vorschau bildet sie nach, damit dort dasselbe Symbol steht wie am Gerät —\n"
        "// gerade bei Domänen, für die Home Assistant selbst kein Symbolattribut führt.\n"
    )
    ZIEL.write_text(
        kopf + "export const ICON_RULES = " + json.dumps(regeln, ensure_ascii=False, indent=1) + ";\n",
        encoding="utf-8",
    )
    print(f"\n{ZIEL.relative_to(ZIEL.parents[4])} geschrieben ({ZIEL.stat().st_size / 1024:.1f} kB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
