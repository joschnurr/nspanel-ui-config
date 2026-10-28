"""Backend „standalone“: panels.yaml direkt bedienen – Rückweg, Zusammenführen, Schreiben.

Beide Editoren – dieser und der Web-Editor des neuen Backends – arbeiten dann auf derselben Datei.
Dafür muss (1) eine panels.yaml wieder zum Modell werden, (2) beim Schreiben alles stehen bleiben, was
nicht unser Panel ist (Verbindungsdaten, fremde Panels), und (3) der Rundlauf Modell → Datei → Modell
stabil sein. Entity-IDs erfunden.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from nspanel_ui_config import importer, panels_export

FIXTURE = Path(__file__).parent / "fixtures" / "apps_full.yaml"

PANELS_YAML = """
home_assistant_address: http://homeassistant.beispiel:8123
home_assistant_token: nicht-echt
mqtt_server: 192.0.2.10
mqtt_port: 1883
nspanels:
  kueche:
    panelRecvTopic: tele/nspanel_kueche/RESULT
    panelSendTopic: cmnd/nspanel_kueche/CustomSend
    locale: de_DE
    timeZone: Europe/Berlin
    timeFormat: "%H:%M"
    dateFormat: full
    featExperimentalSliders: 1
    temp_unit: fahrenheit
    defaultCard: navigate.heizung
    screensaver:
      type: screensaver2
      statusIcon1:
        entity: sensor.beispiel_temp
        icon: 'ha:<I>mdi:thermometer</I> {{ states("sensor.beispiel_temp") }} °C'
      entities:
        - entity: weather.beispiel
    cards:
      - type: cardGrid
        title: Licht
        entities:
          - entity: light.beispiel
            color: "ha:{{ '[255,0,0]' }}"
      - type: cardThermo
        key: heizung
        entity: climate.beispiel
        supported_modes: [heat, "off"]
  flur:
    panelRecvTopic: tele/nspanel_flur/RESULT
    panelSendTopic: cmnd/nspanel_flur/CustomSend
    locale: de_DE
    timeFormat: "%H:%M"
    dateFormat: full
    screensaver: {entities: []}
    cards: [{type: cardGrid, entities: []}]
"""


def test_import_erkennt_panels_yaml_und_waehlt_panel():
    model = importer.parse_apps_yaml(PANELS_YAML, "kueche")
    g = model["global"]
    assert g["panelRecvTopic"] == "tele/nspanel_kueche/RESULT"
    assert g["timezone"] == "Europe/Berlin" and "timeZone" not in g
    assert g["dateFormatBabel"] == "full" and "dateFormat" not in g
    assert g["featureExperimentalSliders"] == 1
    assert "temp_unit" not in g and "defaultCard" not in g
    assert model["screensaver"]["defaultCard"] == "navigate.heizung"
    assert model["screensaver"]["type"] == "screensaver2"
    # ha:-Präfix ab – der Editor arbeitet mit nackten Templates
    assert model["screensaver"]["statusIcon1"]["icon"].startswith("<I>mdi:thermometer</I> {{")
    assert model["cards"][0]["entities"][0]["color"].startswith("{{")
    thermo = model["cards"][1]
    assert thermo["supportedModes"] == ["heat", "off"] and "supported_modes" not in thermo.get("extra", {})
    assert thermo["temperatureUnit"] == "fahrenheit"


def test_import_ohne_panelname_nimmt_erstes_panel():
    model = importer.parse_apps_yaml(PANELS_YAML)
    assert model["global"]["panelRecvTopic"] == "tele/nspanel_kueche/RESULT"
    model = importer.parse_apps_yaml(PANELS_YAML, "gibt_es_nicht")
    assert model["global"]["panelRecvTopic"] == "tele/nspanel_kueche/RESULT"


def test_rundlauf_panels_yaml_ist_stabil():
    """Datei → Modell → Datei muss dasselbe Panel ergeben (sonst „ändert“ jeder Klick etwas)."""
    data = yaml.safe_load(PANELS_YAML)
    model = importer.parse_apps_yaml(PANELS_YAML, "kueche")
    neu, warnings = panels_export.build_panels_dict(model, "kueche")
    assert neu["nspanels"]["kueche"] == data["nspanels"]["kueche"]
    assert warnings == []


def test_merge_behaelt_verbindung_und_fremde_panels():
    existing = yaml.safe_load(PANELS_YAML)
    model = importer.parse_apps_yaml(str(FIXTURE.read_text(encoding="utf-8")), "nspanel-1")
    out, warnings = panels_export.merge_panels_yaml(model, existing, "kueche")
    assert out["home_assistant_token"] == "nicht-echt"
    assert out["mqtt_server"] == "192.0.2.10"
    assert list(out["nspanels"]) == ["kueche", "flur"]
    assert out["nspanels"]["flur"] == existing["nspanels"]["flur"]
    assert out["nspanels"]["kueche"]["panelRecvTopic"] == "NSPanel_1/tele/RESULT"
    assert not any("Verbindungsdaten" in w for w in warnings)


def test_merge_ohne_datei_warnt_vor_fehlender_verbindung():
    model = importer.parse_apps_yaml(str(FIXTURE.read_text(encoding="utf-8")), "nspanel-1")
    out, warnings = panels_export.merge_panels_yaml(model, None, "nspanel-1")
    assert list(out) == ["nspanels"]
    assert any("Verbindungsdaten" in w for w in warnings)


def test_write_panels_yaml_schreibt_sichert_und_ist_idempotent(tmp_path):
    ziel = tmp_path / "panels.yaml"
    ziel.write_text(PANELS_YAML, encoding="utf-8")
    os.chmod(ziel, 0o600)
    model = importer.parse_apps_yaml(str(FIXTURE.read_text(encoding="utf-8")), "nspanel-1")

    erg = panels_export.write_panels_yaml(model, str(ziel), "kueche", backup_count=5)
    assert erg["changed"] is True and erg["backup"] is not None
    assert oct(ziel.stat().st_mode & 0o777) == "0o600"  # Rechte der Datei mit dem Token bleiben
    daten = yaml.safe_load(ziel.read_text(encoding="utf-8"))
    assert daten["home_assistant_token"] == "nicht-echt"
    assert set(daten["nspanels"]) == {"kueche", "flur"}
    assert daten["nspanels"]["kueche"]["cards"][0]["title"] == model["cards"][0]["title"]
    assert (tmp_path / "backups").is_dir()

    erg2 = panels_export.write_panels_yaml(model, str(ziel), "kueche", backup_count=5)
    assert erg2["changed"] is False and erg2["backup"] is None


def test_write_panels_yaml_neue_datei(tmp_path):
    ziel = tmp_path / "unter" / "panels.yaml"
    model = importer.parse_apps_yaml(str(FIXTURE.read_text(encoding="utf-8")), "nspanel-1")
    erg = panels_export.write_panels_yaml(model, str(ziel), "nspanel-1")
    assert erg["changed"] is True
    assert oct(ziel.stat().st_mode & 0o777) == "0o600"
    assert any("Verbindungsdaten" in w for w in erg["warnings"])
    assert list(yaml.safe_load(ziel.read_text(encoding="utf-8"))["nspanels"]) == ["nspanel-1"]


def test_preview_entspricht_dem_was_geschrieben_wuerde(tmp_path):
    ziel = tmp_path / "panels.yaml"
    ziel.write_text(PANELS_YAML, encoding="utf-8")
    model = importer.parse_apps_yaml(str(FIXTURE.read_text(encoding="utf-8")), "nspanel-1")
    text, _ = panels_export.preview_panels_yaml(model, str(ziel), "kueche")
    panels_export.write_panels_yaml(model, str(ziel), "kueche")
    assert ziel.read_text(encoding="utf-8") == text
