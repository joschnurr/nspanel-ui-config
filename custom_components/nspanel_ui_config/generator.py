"""Erzeugt aus dem internen Modell die nspanel-lovelace-ui-YAML.

Das Modell trennt ``global`` / ``screensaver`` / ``cards`` / ``hiddenCards``. Das Backend erwartet
diese Keys flach unter dem ``config:``-Block seiner App. Der ``!include`` in AppDaemons apps.yaml
zeigt genau auf die hier geschriebene Datei, d. h. wir schreiben den *Inhalt* dieses config-Blocks.

``build_config_dict`` ist die exakte Umkehrung von ``importer.config_block_to_model``: benannte
Felder kommen in kanonischer Reihenfolge heraus, das ``extra``-Dict jeder Ebene wird wieder
eingemischt. Einzige beabsichtigte Abweichung: ein config-Block ganz ohne ``cards`` bekommt beim
Generieren ein leeres ``cards: []``, weil das Backend sonst auf seine eingebaute Demo-Karte
zurückfällt — sobald der Editor die Karten verwaltet, ist das nie erwünscht.
"""

from __future__ import annotations

import os
from typing import Any

import yaml

from .schema import (
    CARD_ENTITIES_FIELD,
    ENTITY_KNOWN_FIELDS,
    ENTITY_LIKE_CARD_FIELDS,
    GLOBAL_FIELD_ORDER,
    card_known_fields,
)

_HEADER = (
    "# AUTOMATISCH ERZEUGT von der Home-Assistant-Integration 'NSPanel UI Config'.\n"
    "# Nicht von Hand editieren – Änderungen werden beim nächsten Generieren überschrieben.\n"
)

# Jinja-Templates und Icon-Strings werden lang; Umbrüche wären zwar gültiges YAML, aber unlesbar.
_MAX_LINE_WIDTH = 4096

# Kurze Skalar-Listen (typisch RGB-Farben) bleiben einzeilig, statt auf drei Zeilen zu zerfallen.
_FLOW_LIST_MAX_ITEMS = 4
_FLOW_LIST_MAX_STR_LEN = 24


class _ConfigDumper(yaml.SafeDumper):
    """SafeDumper, dessen Ausgabe wie handgeschriebene AppDaemon-YAML aussieht.

    Die Datei wird zwar maschinell erzeugt, aber sie landet in der Konfiguration des Nutzers und
    wird dort gelesen (und beim Debuggen mit der ursprünglichen apps.yaml verglichen).
    """

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        # PyYAML setzt Listen bündig unter ihren Key; hier werden sie eingerückt.
        return super().increase_indent(flow, False)


def _represent_list(dumper: yaml.SafeDumper, data: list[Any]) -> yaml.Node:
    inline = (
        len(data) <= _FLOW_LIST_MAX_ITEMS
        and all(item is None or isinstance(item, (int, float, bool, str)) for item in data)
        and all(len(item) <= _FLOW_LIST_MAX_STR_LEN for item in data if isinstance(item, str))
    )
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=inline)


def _represent_str(dumper: yaml.SafeDumper, data: str) -> yaml.Node:
    # Jinja-Templates enthalten fast immer Apostrophe. In einfachen Quotes müsste PyYAML jeden davon
    # verdoppeln ('' statt '), was Templates praktisch unlesbar macht — also doppelte Quotes, solange
    # der String das ohne Escaping zulässt.
    if "'" in data and not any(char in data for char in '"\\\n'):
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_ConfigDumper.add_representer(list, _represent_list)
_ConfigDumper.add_representer(str, _represent_str)


def denormalize_entity(entity: Any) -> Any:
    """Setze eine Entity-Zeile aus benannten Feldern + ``extra`` wieder zusammen."""
    if not isinstance(entity, dict):
        return entity
    out: dict[str, Any] = {key: entity[key] for key in ENTITY_KNOWN_FIELDS if key in entity}
    out.update(entity.get("extra") or {})
    return out


def denormalize_card(card: Any) -> Any:
    """Setze eine Karte wieder zusammen; ``entities`` steht als längster Block am Ende."""
    if not isinstance(card, dict):
        return card

    known = card_known_fields(card.get("type"), has_flat_entity="entity" in card)
    out: dict[str, Any] = {}
    for key in known:
        if key == CARD_ENTITIES_FIELD or key not in card:
            continue
        value = card[key]
        if key in ENTITY_LIKE_CARD_FIELDS and isinstance(value, dict):
            value = denormalize_entity(value)
        out[key] = value

    out.update(card.get("extra") or {})

    if CARD_ENTITIES_FIELD in card:
        entities = card[CARD_ENTITIES_FIELD]
        out[CARD_ENTITIES_FIELD] = (
            [denormalize_entity(entity) for entity in entities]
            if isinstance(entities, list)
            else entities
        )
    return out


def build_config_dict(model: dict[str, Any]) -> dict[str, Any]:
    """Bilde das interne Modell auf die vom Backend erwartete config-Struktur ab."""
    out: dict[str, Any] = {}

    # Globale Settings kommen flach in den config-Block, bekannte zuerst in kanonischer Reihenfolge.
    global_settings = model.get("global") or {}
    for key in GLOBAL_FIELD_ORDER:
        if key in global_settings:
            out[key] = global_settings[key]
    for key, value in global_settings.items():
        out.setdefault(key, value)

    if model.get("screensaver") is not None:
        out["screensaver"] = denormalize_card(model["screensaver"])
    out["cards"] = [denormalize_card(card) for card in model.get("cards") or []]
    if model.get("hiddenCards"):
        out["hiddenCards"] = [denormalize_card(card) for card in model["hiddenCards"]]
    return out


def dump_config_yaml(model: dict[str, Any]) -> str:
    """Serialisiere das Modell als YAML-Text (inkl. Kopfzeilen-Warnung)."""
    text = yaml.dump(
        build_config_dict(model),
        Dumper=_ConfigDumper,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=_MAX_LINE_WIDTH,
    )
    return _HEADER + text


def write_config_yaml(model: dict[str, Any], output_path: str) -> str:
    """Schreibe die generierte YAML atomar an ``output_path`` und gib den Pfad zurück.

    Läuft im Executor (Blocking-I/O). Wirft ``OSError`` bei Schreibfehlern.
    """
    if not output_path:
        raise OSError("Kein Ausgabepfad konfiguriert")

    text = dump_config_yaml(model)

    directory = os.path.dirname(output_path) or "."
    os.makedirs(directory, exist_ok=True)
    tmp_path = f"{output_path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(tmp_path, output_path)
    return output_path
