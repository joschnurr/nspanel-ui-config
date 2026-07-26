"""Round-Trip-Tests: apps.yaml → Modell → YAML → apps.yaml-Inhalt.

Kernzusage der Import-/Generator-Schicht: **was hineingeht, kommt wieder heraus.** Der Editor darf
Konfiguration nicht stillschweigend verlieren, nur weil diese Integration einen Key noch nicht
kennt. Diese Tests sichern das ab — auf Datenebene, nicht auf Textebene (Kommentare und Einrückung
der Quelldatei gehen bewusst verloren, die Zieldatei wird maschinell erzeugt).

Ausführen: ``pytest`` im Repo-Wurzelverzeichnis. Für einen Test gegen die eigene, echte apps.yaml:
``NSPANEL_REAL_APPS_YAML=/pfad/zu/apps.yaml pytest``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from nspanel_ui_config import generator, importer, schema  # via conftest.py registriert

FIXTURE = Path(__file__).parent / "fixtures" / "apps_full.yaml"
REAL_APPS_YAML = os.environ.get("NSPANEL_REAL_APPS_YAML")


def _fixture_text() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def _config_block(text: str, app_name: str) -> dict[str, Any]:
    """Der rohe config-Block, wie das Backend ihn sähe — Vergleichsmaßstab für den Round-Trip."""
    return yaml.safe_load(text)[app_name]["config"]


def _roundtrip(config_block: dict[str, Any]) -> dict[str, Any]:
    """config-Block → Modell → YAML-Text → wieder geladener config-Block."""
    model = importer.config_block_to_model(config_block)
    return yaml.safe_load(generator.dump_config_yaml(model))


# --- Import ----------------------------------------------------------------------------------


def test_find_apps_listet_nur_apps_mit_config() -> None:
    assert importer.find_apps(_fixture_text()) == ["nspanel-1"]


def test_parse_apps_yaml_waehlt_app_ohne_angabe() -> None:
    model = importer.parse_apps_yaml(_fixture_text())
    assert model["global"]["panelRecvTopic"] == "NSPanel_1/tele/RESULT"
    assert len(model["cards"]) == 9


def test_parse_apps_yaml_mit_unbekannter_app_liefert_leeres_modell() -> None:
    model = importer.parse_apps_yaml(_fixture_text(), app_name="gibt-es-nicht")
    assert model["cards"] == []


def test_include_datei_wird_auch_ohne_app_wrapper_erkannt() -> None:
    """Wer die Include-Datei selbst importiert, hat den config-Inhalt auf Top-Level."""
    block = _config_block(_fixture_text(), "nspanel-1")
    model = importer.parse_apps_yaml(yaml.safe_dump(block, allow_unicode=True))
    assert len(model["cards"]) == 9


# --- Round-Trip ------------------------------------------------------------------------------


def test_roundtrip_ueber_modell_ist_verlustfrei() -> None:
    block = _config_block(_fixture_text(), "nspanel-1")
    model = importer.config_block_to_model(block)
    assert generator.build_config_dict(model) == block


def test_roundtrip_ueber_yaml_text_ist_verlustfrei() -> None:
    block = _config_block(_fixture_text(), "nspanel-1")
    assert _roundtrip(block) == block


def test_roundtrip_ist_stabil_bei_wiederholung() -> None:
    """Zweimal generieren darf nichts weiter verändern (kein schleichendes Umformen)."""
    block = _config_block(_fixture_text(), "nspanel-1")
    once = _roundtrip(block)
    assert _roundtrip(once) == once


def test_on_off_keys_ueberleben_den_dump() -> None:
    """Klassische YAML-1.1-Falle: unquoted on/off wären Booleans."""
    block = {
        "cards": [
            {
                "type": "cardEntities",
                "entities": [
                    {
                        "entity": "binary_sensor.garage",
                        "icon": {"on": "mdi:garage-lock", "off": "mdi:garage-open"},
                        "color": {"on": [0, 255, 0], "off": [255, 0, 0]},
                    }
                ],
            }
        ]
    }
    icon = _roundtrip(block)["cards"][0]["entities"][0]["icon"]
    assert set(icon) == {"on", "off"}


def test_jinja_template_ueberlebt_unveraendert() -> None:
    template = "{{ iif(states('sensor.x') | float(0) < 35, '[0, 120, 255]', '[255, 0, 0]') }}"
    block = {"cards": [{"type": "cardGrid", "entities": [{"entity": "sensor.x", "color": template}]}]}
    assert _roundtrip(block)["cards"][0]["entities"][0]["color"] == template


def test_nicht_dict_entity_geht_nicht_verloren() -> None:
    """Kaputte Konfiguration darf den Import nicht sprengen — der Editor soll sie anzeigen können."""
    block = {"cards": [{"type": "cardEntities", "entities": ["light.kaputt"]}]}
    assert _roundtrip(block) == block


def test_key_namens_extra_kollidiert_nicht_mit_dem_modell() -> None:
    """``extra`` ist ein Modell-Feld — ein gleichnamiger Quell-Key darf trotzdem überleben."""
    block = {"cards": [{"type": "cardEntities", "extra": "ein wert", "entities": []}]}
    assert _roundtrip(block) == block


# --- Verhalten der Modellschicht -------------------------------------------------------------


def test_unbekannte_keys_landen_in_extra() -> None:
    model = importer.parse_apps_yaml(_fixture_text())
    zukunft = next(card for card in model["cards"] if card.get("title") == "Zukunft")
    assert zukunft["extra"] == {"futureCardOption": "wird-noch-nicht-verstanden"}
    assert zukunft["entities"][0]["extra"] == {"foo": "bar"}


def test_bekannte_keys_bekommen_benannte_felder() -> None:
    model = importer.parse_apps_yaml(_fixture_text())
    zukunft = next(card for card in model["cards"] if card.get("title") == "Zukunft")
    # effectList/speed liest das Backend direkt aus der Entity-Config – also bekannt, nicht extra.
    assert zukunft["entities"][0]["effectList"] == ["Rainbow", "Solid"]
    assert zukunft["entities"][1]["speed"] == 3
    assert zukunft["entities"][1]["extra"] == {}


def test_einzel_entity_karte_behaelt_flache_entity_felder() -> None:
    model = importer.parse_apps_yaml(_fixture_text())
    thermo = next(card for card in model["cards"] if card["type"] == "cardThermo")
    assert thermo["entity"] == "climate.living_room"
    assert thermo["name"] == "Wohnzimmer"
    assert thermo["supportedModes"] == ["heat", "off"]
    assert thermo["extra"] == {}


def test_screensaver_status_icons_werden_als_entities_normalisiert() -> None:
    model = importer.parse_apps_yaml(_fixture_text())
    status_icon = model["screensaver"]["statusIcon1"]
    assert status_icon["entity"] == "sensor.buffer_top"
    assert status_icon["extra"] == {"altFont": True}  # altFont kennt nur der Renderer


def test_backend_defaults_werden_nicht_eingemischt() -> None:
    """Sonst stünden nach dem ersten Speichern Keys in der Datei, die nie jemand gesetzt hat."""
    block = {"model": "eu", "cards": []}
    generated = generator.build_config_dict(importer.config_block_to_model(block))
    assert "screenBrightness" not in generated
    assert "quiet" not in generated
    assert generated == block


def test_fehlende_cards_werden_zu_leerer_liste() -> None:
    """Einzige bewusste Abweichung: ohne cards fiele das Backend auf seine Demo-Karte zurück."""
    generated = generator.build_config_dict(importer.config_block_to_model({"model": "eu"}))
    assert generated == {"model": "eu", "cards": []}


def test_leeres_modell_ist_generierbar() -> None:
    generated = generator.build_config_dict(schema.empty_model())
    assert generated["cards"] == []
    assert generated["screensaver"]["type"] == "screensaver2"


# --- Lesbarkeit der erzeugten Datei ------------------------------------------------------------


def test_erzeugte_yaml_bleibt_lesbar() -> None:
    text = generator.dump_config_yaml(importer.parse_apps_yaml(_fixture_text()))
    assert text.startswith("# AUTOMATISCH ERZEUGT")
    # RGB-Listen einzeilig statt auf drei Zeilen zerlegt …
    assert "[0, 255, 0]" in text
    # … Listen unter ihrem Key eingerückt …
    assert "\n  entities:\n    - entity: weather.forecast_home\n" in text
    # … und lange Jinja-Templates in einer Zeile, ohne verdoppelte Apostrophe.
    template_lines = [line for line in text.splitlines() if "iif(" in line]
    assert template_lines
    assert all(line.rstrip().endswith('}}"') for line in template_lines)
    assert "''" not in text


# --- Validierung -------------------------------------------------------------------------------


def test_validate_model_meldet_echte_fehler() -> None:
    model = importer.config_block_to_model(
        {
            "model": "gibt-es-nicht",
            "cards": [
                {"type": "cardEntities", "entities": [{"name": "ohne entity"}]},
                {"type": "cardPhantasie", "entities": []},
                {"title": "ohne typ"},
            ],
        }
    )
    findings = schema.validate_model(model)
    messages = {(finding["path"], finding["level"]) for finding in findings}
    assert ("cards[0].entities[0]", "error") in messages
    assert ("cards[1]", "warning") in messages
    assert ("cards[2]", "error") in messages
    assert ("global.model", "warning") in messages


def test_validate_model_meldet_bei_gueltiger_config_nur_das_wirkungslose_unit() -> None:
    """Die Fixture ist gültig – bis auf das absichtlich enthaltene ``unit``.

    ``unit`` steht dort seit jeher als Beispiel für einen Key, den diese Integration nicht kennt.
    Inzwischen ist er *bekannt wirkungslos*: das Backend liest ihn nirgends, die Einheit kommt aus
    ``unit_of_measurement``. Genau ein Hinweis ist also zu erwarten – und weiterhin kein Fehler.
    """
    findings = schema.validate_model(importer.parse_apps_yaml(_fixture_text()))
    assert [finding for finding in findings if finding["level"] == "error"] == []
    assert len(findings) == 1, f"Unerwartete Befunde: {findings}"
    assert findings[0]["path"] == "screensaver.entities"
    assert "'unit'" in findings[0]["message"]


# --- Optional: gegen die echte apps.yaml -------------------------------------------------------


def test_roundtrip_gegen_echte_apps_yaml() -> None:
    """Läuft nur mit ``NSPANEL_REAL_APPS_YAML=<pfad>`` — die eigene Config ist der beste Testfall."""
    if not REAL_APPS_YAML:
        return
    text = Path(REAL_APPS_YAML).read_text(encoding="utf-8")
    apps = importer.find_apps(text)
    assert apps, f"Keine App mit config-Block in {REAL_APPS_YAML}"
    for app_name in apps:
        block = _config_block(text, app_name)
        assert _roundtrip(block) == block, f"Round-Trip verliert Daten in App '{app_name}'"
