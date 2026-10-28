"""Export als panels.yaml für das neue nspanel-lovelace-ui-Backend (Add-on/Standalone ab v4.8.0).

Jeder Test steht für eine Regel, die am 27.10.2026 gegen den Backend-Quelltext v4.8.4 geprüft
wurde (Belege in ``panels_export.py``). Die Fixture ist dieselbe wie beim Round-Trip, enthält also
Sonnenzeiten im Helligkeitsplan, Templates ohne Präfix, navItem, cardGrid2-nahe Fälle und ein
Legacy-Wetter-``entity`` neben einer ``entities``-Liste – genau die Stellen, an denen der
Umstieg ohne Hilfe schiefgeht.
"""

from __future__ import annotations

import copy
from pathlib import Path

import yaml

from nspanel_ui_config import importer, panels_export  # via conftest.py registriert

FIXTURE = Path(__file__).parent / "fixtures" / "apps_full.yaml"


def _modell():
    return importer.parse_apps_yaml(FIXTURE.read_text(encoding="utf-8"), "nspanel-1")


def _panel(model=None, name="nspanel"):
    data, warnings = panels_export.build_panels_dict(model or _modell(), name)
    return data["nspanels"][name], warnings


def test_struktur_nspanels_mit_panelname():
    """Das neue Backend erwartet ``nspanels.<name>``; der Name kommt vom Aufrufer."""
    data, _ = panels_export.build_panels_dict(_modell(), "wohnzimmer")
    assert list(data) == ["nspanels"]
    assert list(data["nspanels"]) == ["wohnzimmer"]
    panel = data["nspanels"]["wohnzimmer"]
    assert panel["panelRecvTopic"] == "NSPanel_1/tele/RESULT"
    assert "cards" in panel and "screensaver" in panel and "hiddenCards" in panel


def test_globale_umbenennungen():
    """timezone→timeZone, featureExperimentalSliders→featExperimentalSliders, Babel-Datum."""
    model = _modell()
    model["global"]["timezone"] = "Europe/Berlin"
    model["global"]["dateFormatBabel"] = "long"
    panel, warnings = _panel(model)
    assert panel["timeZone"] == "Europe/Berlin"
    assert "timezone" not in panel
    assert panel["featExperimentalSliders"] is True
    assert "featureExperimentalSliders" not in panel
    assert panel["dateFormat"] == "long"
    assert "dateFormatBabel" not in panel
    assert any("dateFormat (strftime) entfällt" in w for w in warnings)


def test_strftime_datum_ohne_babel_wird_full():
    """Ein reines strftime-Muster würde das neue Backend nicht verstehen."""
    panel, warnings = _panel()
    assert panel["dateFormat"] == "full"
    assert any("strftime" in w for w in warnings)


def test_sonnenzeiten_werden_ersetzt_und_gemeldet():
    """Helligkeitsplan: sunrise/sunset sind im neuen Backend nicht erlaubt (Doku Migration, Z. 52)."""
    panel, warnings = _panel()
    zeiten = [e["time"] for e in panel["sleepBrightness"]]
    assert zeiten == ["07:00", "19:00"]
    assert sum("sunrise" in w or "sunset" in w for w in warnings) == 2


def test_templates_bekommen_ha_praefix():
    """icon/color/value/qrCode-Templates rendert das Backend nur mit ``ha:`` (docs/entities.md)."""
    panel, _ = _panel()
    ss = panel["screensaver"]
    feuchte = next(e for e in ss["entities"] if e.get("name") == "Luftfeuchte")
    assert feuchte["value"].startswith("ha:{{")
    assert feuchte["color"].startswith("ha:{{")
    heizung = next(c for c in panel["cards"] if c.get("key") == "heizung")
    oben = next(e for e in heizung["entities"] if e.get("name") == "oben")
    assert oben["color"].startswith("ha:{{")
    # Statusicon: das Präfix stand mitten im Wert (AppDaemon-Form) – es muss nach vorn, nicht doppelt.
    assert ss["statusIcon1"]["icon"].count("ha:") == 1
    assert ss["statusIcon1"]["icon"].startswith("ha:<I>")
    assert ss["statusIcon1"]["color"].startswith("ha:{{")


def test_praefix_ist_idempotent():
    """Zweimal exportieren darf kein ``ha:ha:`` erzeugen."""
    panel, _ = _panel()
    model = {"global": {}, "cards": [{"type": "cardEntities", "entities": [
        {"entity": "sensor.a", "value": panel["screensaver"]["entities"][3]["value"]}]}]}
    panel2, _ = _panel(model)
    assert panel2["cards"][0]["entities"][0]["value"].startswith("ha:{{")
    assert "ha:ha:" not in panel2["cards"][0]["entities"][0]["value"]


def test_navitem_und_cooldown_entfallen_mit_hinweis():
    """Beides kommt im neuen Backend nirgends vor (grep mqtt-manager, 27.10.2026)."""
    model = _modell()
    model["cards"][1]["extra"] = {"cooldown": 5}
    panel, warnings = _panel(model)
    heizung = next(c for c in panel["cards"] if c.get("key") == "heizung")
    assert "navItem1" not in heizung and "cooldown" not in heizung
    assert any("navItem1" in w for w in warnings)
    assert any("cooldown" in w for w in warnings)


def test_cardgrid2_wird_cardgrid_und_cardchart_gemeldet():
    model = {"global": {}, "cards": [
        {"type": "cardGrid2", "title": "Rollos", "entities": [{"entity": "cover.a"}]},
        {"type": "cardChart", "title": "Kurve", "entities": [{"entity": "sensor.a"}]},
    ]}
    panel, warnings = _panel(model)
    assert panel["cards"][0]["type"] == "cardGrid"
    assert panel["cards"][1]["type"] == "cardChart"
    assert any("cardGrid2 → cardGrid" in w for w in warnings)
    assert any("cardChart" in w and "abgelehnt" in w for w in warnings)


def test_temperatureunit_wandert_auf_panelebene():
    """Drei Karten mit celsius → ``temp_unit: celsius``, keine Karte trägt den Key noch."""
    panel, _ = _panel()
    assert panel["temp_unit"] == "celsius"
    assert all("temperatureUnit" not in c for c in panel["cards"] + panel["hiddenCards"])


def test_gemischte_temperatureunit_wird_gemeldet():
    model = {"global": {}, "cards": [
        {"type": "cardGrid", "temperatureUnit": "celsius", "entities": []},
        {"type": "cardGrid", "temperatureUnit": "fahrenheit", "entities": []},
    ]}
    panel, warnings = _panel(model)
    assert panel["temp_unit"] == "celsius"
    assert any("Gemischte temperatureUnit" in w for w in warnings)


def test_supported_modes_und_defaultcard():
    """supportedModes→supported_modes (docs/cards.md); screensaver.defaultCard wird Panel-Key."""
    model = _modell()
    model["screensaver"]["defaultCard"] = "navigate.wohnzimmer"
    panel, _ = _panel(model)
    thermo = next(c for c in panel["cards"] if c["type"] == "cardThermo")
    assert thermo["supported_modes"] == ["heat", "off"]
    assert "supportedModes" not in thermo
    assert panel["defaultCard"] == "navigate.wohnzimmer"
    assert "defaultCard" not in panel["screensaver"]


def test_legacy_wetter_entity_wird_entfernt():
    """Fixture hat ``entity`` und ``entities``: die Liste gewinnt, der Hinweis bleibt."""
    panel, warnings = _panel()
    assert "entity" not in panel["screensaver"]
    assert panel["screensaver"]["entities"][0]["entity"] == "weather.forecast_home"
    assert any("Legacy-Wetter" in w for w in warnings)


def test_legacy_wetter_ohne_liste_wird_zur_liste():
    model = {"global": {}, "screensaver": {"type": "screensaver", "entity": "weather.beispiel_zuhause"},
             "cards": [{"type": "cardGrid", "entities": []}]}
    panel, warnings = _panel(model)
    assert panel["screensaver"]["entities"] == [{"entity": "weather.beispiel_zuhause"}]
    assert "entity" not in panel["screensaver"]


def test_alternative_layout_wird_screensaver2():
    """config_manager.py:178 – das Layout steckt im neuen Backend im Typ, nicht in einem Schalter."""
    model = {"global": {}, "screensaver": {"type": "screensaver", "alternativeLayout": True,
             "entities": [{"entity": "sensor.beispiel"}]}, "cards": [{"type": "cardGrid", "entities": []}]}
    panel, warnings = _panel(model)
    assert panel["screensaver"]["type"] == "screensaver2"
    assert "alternativeLayout" not in panel["screensaver"]
    assert any("screensaver2" in w for w in warnings)


def test_unsupported_entityfelder_bleiben_mit_hinweis():
    """state/state_not/state_template bleiben stehen (``retained``), aber mit Warnung."""
    panel, warnings = _panel()
    zukunft = next(c for c in panel["cards"] if c.get("title") == "Zukunft")
    fan = next(e for e in zukunft["entities"] if e["entity"] == "fan.ceiling")
    assert fan["state_not"] == "unavailable"
    assert any("state_not" in w for w in warnings)
    assert any("state_template" in w for w in warnings)


def test_modell_bleibt_unveraendert():
    """Der Export ist eine Ansicht, kein Umbau des Editor-Modells."""
    model = _modell()
    vorher = copy.deepcopy(model)
    panels_export.build_panels_dict(model)
    assert model == vorher


def test_yaml_text_hat_kopf_und_hinweise_und_ist_ladbar():
    text, warnings = panels_export.dump_panels_yaml(_modell(), "nspanel")
    assert text.startswith("# panels.yaml")
    assert "# home_assistant_token:" in text
    assert "# Beim Export aufgefallen" in text
    geladen = yaml.safe_load(text)
    assert list(geladen) == ["nspanels"]
    assert len(warnings) >= 4
