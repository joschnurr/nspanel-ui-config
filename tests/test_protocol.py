"""Prüft den Parser der Display-Nachrichten gegen die Beispiele aus dem Upstream-Protokoll.

Die Strings hier sind nicht ausgedacht: sie stammen aus ``HMI/README.md`` von
joBr99/nspanel-lovelace-ui bzw. sind nach ``pages.py`` gebaut. Geht das Format kaputt, zeigt die
Live-Vorschau Unsinn – und zwar überzeugend aussehenden, weil die Felder ja irgendwo landen.
"""

from __future__ import annotations

from nspanel_ui_config import protocol

# Beispiel aus HMI/README.md (cardEntities mit vier Einträgen), Symbole hier als Buchstaben.
CARD_ENTITIES = (
    "entityUpd~LightTest~button~navigate.prev~<~65535~~~button~navigate.next~>~65535~~"
    "~light~light.bed_light~A~17299~Bed Light~0"
    "~light~light.ceiling_lights~B~52231~Ceiling Lights~1"
    "~switch~switch.ac~C~17299~AC~0"
    "~switch~switch.decorative_lights~D~65222~Decorative Lights~1"
)


def test_titel_navigation_und_eintraege_werden_getrennt() -> None:
    ergebnis = protocol.parse_message(CARD_ENTITIES, "cardEntities")
    assert ergebnis["title"] == "LightTest"
    assert len(ergebnis["navigation"]) == 2
    assert ergebnis["navigation"][0]["entity"] == "navigate.prev"
    assert len(ergebnis["entities"]) == 4


def test_ein_eintrag_traegt_alle_sechs_felder() -> None:
    eintrag = protocol.parse_message(CARD_ENTITIES, "cardEntities")["entities"][1]
    assert eintrag["type"] == "light"
    assert eintrag["entity"] == "light.ceiling_lights"
    assert eintrag["iconChar"] == "B"
    assert eintrag["name"] == "Ceiling Lights"
    assert eintrag["value"] == "1"
    assert eintrag["leer"] is False


def test_delete_eintraege_sind_als_leer_erkennbar() -> None:
    payload = (
        "entityUpd~Test~button~navigate.prev~<~65535~~~button~navigate.next~>~65535~~"
        "~delete~~~~~"
        "~text~sensor.x~A~17299~Sensor~21 °C"
    )
    eintraege = protocol.parse_message(payload, "cardGrid")["entities"]
    assert eintraege[0]["leer"] is True
    assert eintraege[1]["leer"] is False
    assert eintraege[1]["value"] == "21 °C"


def test_maskierte_screensaver_eintraege_gelten_nicht_als_leer() -> None:
    """Der Fall, der an der echten Anlage aufflog: die ganze Ruheanzeige wirkte leer.

    Für den Screensaver rendert das Backend mit ``mask=["type", "entityId"]`` (pages.py) — beide
    Felder kommen leer an, obwohl Symbol, Name und Wert gefüllt sind. Ob ein Platz belegt ist,
    entscheidet deshalb sein *Inhalt*, nicht das type-Feld. In der Testinstanz fiel das nicht auf:
    dort existierten die Entities nicht, und der Not-found-Zweig des Backends sendet ein ``type``.
    """
    payload = (
        "weatherUpdate"
        "~~~~31728~Wetter Seebach~20.9°C"
        "~~~~17299~PV Heute~0.0 kWh"
    )
    eintraege = protocol.parse_message(payload, "screensaver2")["entities"]
    assert [e["leer"] for e in eintraege] == [False, False]
    assert eintraege[0]["name"] == "Wetter Seebach"
    assert eintraege[0]["value"] == "20.9°C"
    assert eintraege[0]["type"] == ""


def test_wirklich_leere_bloecke_bleiben_leer() -> None:
    payload = "weatherUpdate~~~~~~" + "~text~sensor.x~A~65535~Name~Wert"
    eintraege = protocol.parse_message(payload, "screensaver")["entities"]
    assert eintraege[0]["leer"] is True
    assert eintraege[1]["leer"] is False


def test_cardqr_schiebt_den_qr_text_vor_die_eintraege() -> None:
    payload = (
        "entityUpd~Guest Wifi~button~navigate.prev~<~65535~~~button~navigate.next~>~65535~~"
        "~WIFI:S:test_ssid;T:WPA;P:test_pw;;"
        "~text~iText.test_ssid~A~17299~Name~test_ssid"
        "~text~iText.test_pw~B~17299~Password~test_pw"
    )
    ergebnis = protocol.parse_message(payload, "cardQR")
    assert ergebnis["lead"] == ["WIFI:S:test_ssid;T:WPA;P:test_pw;;"]
    assert len(ergebnis["entities"]) == 2
    assert ergebnis["entities"][0]["value"] == "test_ssid"


def test_cardpower_haengt_jedem_eintrag_die_geschwindigkeit_an() -> None:
    """Sieben Felder statt sechs – wer das übersieht, verschiebt alle folgenden Einträge."""
    payload = (
        "entityUpd~PowerTest~button~navigate.prev~<~65535~~~button~navigate.next~>~65535~~"
        "~text~sensor.a~A~17299~Verbrauch~100W~1"
        "~text~sensor.b~B~17299~Erzeugung~200W~-30"
    )
    eintraege = protocol.parse_message(payload, "cardPower")["entities"]
    assert len(eintraege) == 2
    assert eintraege[0]["name"] == "Verbrauch"
    assert eintraege[0]["extra"] == ["1"]
    assert eintraege[1]["extra"] == ["-30"]


def test_karten_mit_eigenem_aufbau_liefern_keine_erfundenen_eintraege() -> None:
    payload = "entityUpd~Heizung~nav~nav~~~~~~~~~~~~climate.wohnzimmer~21.5 °C~22~heat"
    ergebnis = protocol.parse_message(payload, "cardThermo")
    assert ergebnis["strukturiert"] is False
    assert ergebnis["entities"] == []
    assert ergebnis["title"] == "Heizung"


def test_der_screensaver_kommt_ohne_titel_und_navigation() -> None:
    payload = (
        "weatherUpdate"
        "~weather~weather.home~A~65535~Zuhause~8.1°C"
        "~text~sensor.f1~B~65535~Mi~16.8°"
        "~text~sensor.f2~C~65535~Do~17.2°"
    )
    ergebnis = protocol.parse_message(payload)
    assert ergebnis["cardType"] == "screensaver"
    assert len(ergebnis["entities"]) == 3
    assert ergebnis["entities"][0]["value"] == "8.1°C"


def test_welcher_screensaver_es_ist_sagt_der_pagetype() -> None:
    """Beide Bauarten füllen dieselben 6er-Blöcke – der Unterschied steht nicht in der Nachricht.

    Gefunden beim ersten Mitschnitt an einer echten Instanz: dort lief `screensaver2` mit 14
    Einträgen, erkannt wurde `screensaver` mit 6 Plätzen. Zwei Drittel wären weggefallen.
    """
    payload = "weatherUpdate" + "~text~sensor.x~A~65535~Name~Wert" * 12
    assert protocol.parse_message(payload, "screensaver2")["cardType"] == "screensaver2"
    assert protocol.parse_message(payload, "screensaver")["cardType"] == "screensaver"
    # Ohne bekannten pageType bleibt es beim klassischen Screensaver.
    assert protocol.parse_message(payload)["cardType"] == "screensaver"
    # Ein Kartentyp, der gar kein Screensaver ist, darf nicht durchschlagen.
    assert protocol.parse_message(payload, "cardGrid")["cardType"] == "screensaver"


def test_farben_werden_aus_dem_display_format_zurueckgerechnet() -> None:
    """65535 ist weiß, 0 schwarz – und 17299 der Blauton, den das Backend als Standard nimmt."""
    assert protocol.rgb565_to_rgb(65535) == [255, 255, 255]
    assert protocol.rgb565_to_rgb(0) == [0, 0, 0]
    rot, gruen, blau = protocol.rgb565_to_rgb(17299)
    assert blau > rot and blau > gruen, "17299 sollte bläulich sein"
    # Was nicht in 16 Bit passt oder gar keine Zahl ist, ergibt keine Farbe statt einer falschen.
    assert protocol.rgb565_to_rgb("") is None
    assert protocol.rgb565_to_rgb("ha:template") is None
    assert protocol.rgb565_to_rgb(70000) is None


def test_verlust_beim_zurueckrechnen_ist_gewollt() -> None:
    """Das Display kennt nur 5/6/5 Bit – zurück kommt, was es zeigt, nicht was konfiguriert war."""
    # 255,165,0 (orange) → dec565 → zurück: nahe dran, aber nicht identisch.
    dec565 = ((255 >> 3) << 11) | ((165 >> 2) << 5) | (0 >> 3)
    zurueck = protocol.rgb565_to_rgb(dec565)
    assert zurueck[0] == 255
    assert abs(zurueck[1] - 165) <= 4
    assert zurueck[2] == 0


def test_andere_nachrichten_werden_ignoriert() -> None:
    """Über dasselbe Topic läuft der gesamte Verkehr zum Panel – das meiste geht die Vorschau nichts an."""
    for payload in ("dimmode~10~100~6371", "time~12:30", "pageType~cardGrid", "", "notify~Kopf~Text"):
        assert protocol.parse_message(payload, "cardGrid") is None


def test_pagetype_sagt_welche_karte_gilt() -> None:
    assert protocol.parse_page_type("pageType~cardGrid") == "cardGrid"
    assert protocol.parse_page_type("pageType~screensaver") == "screensaver"
    assert protocol.parse_page_type("pageType~") is None
    assert protocol.parse_page_type("entityUpd~x") is None
