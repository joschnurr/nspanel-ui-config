"""Erzeugt aus dem internen Modell die nspanel-lovelace-ui-YAML.

Das Modell trennt ``global`` / ``screensaver`` / ``cards`` / ``hiddenCards``. Das Backend erwartet
diese Keys flach unter dem ``config:``-Block seiner App. Der ``!include`` in AppDaemons apps.yaml
zeigt genau auf die hier geschriebene Datei, d. h. wir schreiben den *Inhalt* dieses config-Blocks.

Stand v0.1: schreibt das Modell strukturtreu als YAML. Feineres Mapping/Validierung folgt mit dem
Ausbau der einzelnen Kartentypen.
"""

from __future__ import annotations

import os
from typing import Any

import yaml


def build_config_dict(model: dict[str, Any]) -> dict[str, Any]:
    """Bilde das interne Modell auf die vom Backend erwartete config-Struktur ab."""
    out: dict[str, Any] = {}
    # Globale Settings kommen flach in den config-Block.
    out.update(model.get("global", {}))
    if "screensaver" in model:
        out["screensaver"] = model["screensaver"]
    out["cards"] = model.get("cards", [])
    if model.get("hiddenCards"):
        out["hiddenCards"] = model["hiddenCards"]
    return out


def write_config_yaml(model: dict[str, Any], output_path: str) -> str:
    """Schreibe die generierte YAML atomar an ``output_path`` und gib den Pfad zurück.

    Läuft im Executor (Blocking-I/O). Wirft ``OSError`` bei Schreibfehlern.
    """
    if not output_path:
        raise OSError("Kein Ausgabepfad konfiguriert")

    config_dict = build_config_dict(model)
    text = yaml.safe_dump(config_dict, allow_unicode=True, sort_keys=False, default_flow_style=False)
    header = (
        "# AUTOMATISCH ERZEUGT von der Home-Assistant-Integration 'NSPanel UI Config'.\n"
        "# Nicht von Hand editieren – Änderungen werden beim nächsten Generieren überschrieben.\n"
    )

    directory = os.path.dirname(output_path) or "."
    os.makedirs(directory, exist_ok=True)
    tmp_path = f"{output_path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        handle.write(header)
        handle.write(text)
    os.replace(tmp_path, output_path)
    return output_path
