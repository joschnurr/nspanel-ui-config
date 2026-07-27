"""Import einer bestehenden nspanel-lovelace-ui-Konfiguration als Startpunkt.

Liest den ``config:``-Block aus einer AppDaemon-``apps.yaml`` (oder einer bereits ausgelagerten
Include-Datei) und überführt ihn in das interne Modell (global/screensaver/cards/hiddenCards).

Der Import ist bewusst **verlustfrei**: bekannte Keys bekommen ein benanntes Feld, alle übrigen
landen unverändert im ``extra``-Dict der jeweiligen Ebene. ``generator.build_config_dict`` dreht das
wieder zurück, sodass Import → Editieren → Generieren rundläuft (siehe ``tests/test_roundtrip.py``).

Was der Import *nicht* leisten kann: YAML-Kommentare und Formatierung gehen verloren — die Zieldatei
wird ohnehin maschinell erzeugt und trägt einen entsprechenden Warnhinweis im Kopf.
"""

from __future__ import annotations

from typing import Any

import yaml

from .schema import (
    CARD_ENTITIES_FIELD,
    ENTITY_KNOWN_FIELDS,
    ENTITY_LIKE_CARD_FIELDS,
    STRUCTURED_KEYS,
    card_known_fields,
    empty_model,
    entity_like_known_fields,
)


def find_apps(text: str) -> list[str]:
    """Namen aller Apps in einer apps.yaml, die einen ``config``-Block haben.

    Für die Auswahl im Editor, wenn eine apps.yaml mehrere NSPanels bedient.
    """
    parsed = yaml.safe_load(text) or {}
    if not isinstance(parsed, dict):
        return []
    return [
        name
        for name, value in parsed.items()
        if isinstance(value, dict) and isinstance(value.get("config"), dict)
    ]


def parse_apps_yaml(text: str, app_name: str | None = None) -> dict[str, Any]:
    """Extrahiere den ``config``-Block aus apps.yaml-Text und liefere das interne Modell.

    ``app_name`` wählt bei mehreren Apps gezielt eine aus; ohne Angabe wird die erste App mit einem
    ``config``-Block genommen.
    """
    parsed = yaml.safe_load(text) or {}
    config_block = _find_config_block(parsed, app_name)
    return config_block_to_model(config_block)


def _find_config_block(parsed: Any, app_name: str | None) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        return {}
    # Fall A: bereits die reine Include-Datei (config-Inhalt auf Top-Level).
    if any(key in parsed for key in STRUCTURED_KEYS) and "config" not in parsed:
        return parsed
    # Fall B: vollständige apps.yaml – App(s) mit config-Block.
    if app_name is not None:
        app = parsed.get(app_name)
        return app.get("config", {}) if isinstance(app, dict) else {}
    for value in parsed.values():
        if isinstance(value, dict) and isinstance(value.get("config"), dict):
            return value["config"]
    return {}


def config_block_to_model(config: Any) -> dict[str, Any]:
    """Überführe einen config-Block in das interne Modell.

    Die globalen Settings werden übernommen wie vorgefunden — Backend-Defaults werden bewusst
    *nicht* eingemischt, sonst stünden beim Generieren plötzlich Keys in der Datei, die der Nutzer
    nie gesetzt hat.
    """
    if not isinstance(config, dict):
        return empty_model()

    model: dict[str, Any] = {
        "global": {key: value for key, value in config.items() if key not in STRUCTURED_KEYS},
        "screensaver": None,
        "cards": [],
        "hiddenCards": [],
    }

    screensaver = config.get("screensaver")
    if screensaver is not None:
        model["screensaver"] = normalize_card(screensaver, default_type="screensaver")
    if isinstance(config.get("cards"), list):
        model["cards"] = [normalize_card(card) for card in config["cards"]]
    if isinstance(config.get("hiddenCards"), list):
        model["hiddenCards"] = [normalize_card(card) for card in config["hiddenCards"]]
    return model


def normalize_entity(raw: Any, known: tuple[str, ...] = ENTITY_KNOWN_FIELDS) -> Any:
    """Zerlege eine Entity-Zeile in bekannte Felder + ``extra``.

    ``known`` weicht nur bei den entity-artigen Karten-Feldern ab: das Status-Symbol der
    Ruheanzeige kennt zusätzlich ``altFont`` (siehe ``schema.entity_like_known_fields``).

    Nicht-Dicts (fehlerhafte Konfiguration) werden unverändert durchgereicht, damit der Import an
    kaputtem YAML nicht scheitert und der Editor den Fehler anzeigen kann.
    """
    if not isinstance(raw, dict):
        return raw
    entity: dict[str, Any] = {key: raw[key] for key in known if key in raw}
    entity["extra"] = {key: value for key, value in raw.items() if key not in known}
    return entity


def normalize_card(raw: Any, default_type: str | None = None) -> Any:
    """Zerlege eine Karte in bekannte Felder + ``extra``; verschachtelte Entities inklusive."""
    if not isinstance(raw, dict):
        return raw

    card_type = raw.get("type", default_type)
    known = card_known_fields(card_type, has_flat_entity="entity" in raw)

    card: dict[str, Any] = {key: raw[key] for key in known if key in raw}
    card["extra"] = {key: value for key, value in raw.items() if key not in known}

    if isinstance(raw.get(CARD_ENTITIES_FIELD), list):
        card[CARD_ENTITIES_FIELD] = [normalize_entity(entity) for entity in raw[CARD_ENTITIES_FIELD]]
    for field in ENTITY_LIKE_CARD_FIELDS:
        if isinstance(card.get(field), dict):
            card[field] = normalize_entity(card[field], entity_like_known_fields(field))
    return card
