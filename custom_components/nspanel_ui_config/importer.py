"""Import einer bestehenden nspanel-lovelace-ui-Konfiguration als Startpunkt.

Liest den ``config:``-Block aus einer AppDaemon-``apps.yaml`` (oder einer bereits ausgelagerten
Include-Datei) und überführt ihn in das interne Modell (global/screensaver/cards/hiddenCards).

Stand v0.1: Grundgerüst. Der eigentliche Feld-für-Feld-Abgleich wird zusammen mit dem Generator
ausgebaut, damit Import → Editieren → Generieren verlustfrei rundläuft (Round-Trip-Ziel).
"""

from __future__ import annotations

from typing import Any

import yaml

from .schema import empty_model

# Keys, die als globale Settings gelten (alles außer den strukturierten Blöcken).
_STRUCTURED_KEYS = {"screensaver", "cards", "hiddenCards"}


def parse_apps_yaml(text: str, app_name: str | None = None) -> dict[str, Any]:
    """Extrahiere den ``config``-Block aus apps.yaml-Text und liefere das interne Modell.

    ``app_name`` wählt bei mehreren Apps gezielt eine aus; ohne Angabe wird die erste App mit einem
    ``config``-Block genommen.
    """
    parsed = yaml.safe_load(text) or {}
    config_block = _find_config_block(parsed, app_name)
    return config_block_to_model(config_block)


def _find_config_block(parsed: dict[str, Any], app_name: str | None) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        return {}
    # Fall A: bereits die reine Include-Datei (config-Inhalt auf Top-Level).
    if any(key in parsed for key in _STRUCTURED_KEYS) and "config" not in parsed:
        return parsed
    # Fall B: vollständige apps.yaml – App(s) mit config-Block.
    if app_name and app_name in parsed:
        return parsed[app_name].get("config", {})
    for value in parsed.values():
        if isinstance(value, dict) and isinstance(value.get("config"), dict):
            return value["config"]
    return {}


def config_block_to_model(config: dict[str, Any]) -> dict[str, Any]:
    """Überführe einen config-Block in das interne Modell."""
    model = empty_model()
    if not isinstance(config, dict):
        return model

    global_settings: dict[str, Any] = {}
    for key, value in config.items():
        if key in _STRUCTURED_KEYS:
            continue
        global_settings[key] = value

    model["global"] = {**model["global"], **global_settings}
    if isinstance(config.get("screensaver"), dict):
        model["screensaver"] = config["screensaver"]
    if isinstance(config.get("cards"), list):
        model["cards"] = config["cards"]
    if isinstance(config.get("hiddenCards"), list):
        model["hiddenCards"] = config["hiddenCards"]
    return model
