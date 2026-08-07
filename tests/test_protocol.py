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
        "~~~~31728~Wetter Zuhause~20.9°C"
        "~~~~17299~PV Heute~0.0 kWh"
    )
    eintraege = protocol.parse_message(payload, "screensaver2")["entities"]
    assert [e["leer"] for e in eintraege] == [False, False]
    assert eintraege[0]["name"] == "Wetter Zuhause"
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
    """Für Karten ohne Eintragsblöcke gibt es Titel, aber keine Liste.

    `cardThermo` steht hier seit v0.28 nicht mehr dabei – sein Format ist inzwischen bekannt und
    wird gelesen (siehe `test_thermo_wird_zerlegt_statt_uebergangen`).
    """
    for card_type in ("cardMedia", "cardAlarm", "cardChart", "cardUnlock"):
        payload = "entityUpd~Wohnzimmer~nav~nav~~~~~~~~~~~~media_player.tv~an"
        ergebnis = protocol.parse_message(payload, card_type)
        assert ergebnis["strukturiert"] is False, card_type
        assert ergebnis["entities"] == [], card_type
        assert ergebnis["title"] == "Wohnzimmer", card_type


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

    Solange die Zahl der Blöcke auch auf den klassischen passt, ist der pageType die einzige
    Auskunft – und ohne ihn bleibt es beim klassischen.
    """
    wenige = "weatherUpdate" + "~text~sensor.x~A~65535~Name~Wert" * 3
    assert protocol.parse_message(wenige, "screensaver2")["cardType"] == "screensaver2"
    assert protocol.parse_message(wenige, "screensaver")["cardType"] == "screensaver"
    assert protocol.parse_message(wenige)["cardType"] == "screensaver"
    # Ein Kartentyp, der gar kein Screensaver ist, darf nicht durchschlagen.
    assert protocol.parse_message(wenige, "cardGrid")["cardType"] == "screensaver"


def test_mehr_eintraege_als_plaetze_verraten_screensaver2_ohne_pagetype() -> None:
    """Der Fall, der in der Praxis auffiel: nach einem Neustart fehlt der pageType.

    Im Ruhezustand schickt das Backend die Wetteraktualisierung immer wieder, den ``pageType`` aber
    nur beim *Wechsel* in die Ruheanzeige. Nach einem Neustart der Integration ist er deshalb
    unbekannt, und die Live-Ansicht zeichnete `screensaver2` als klassischen Screensaver – mit 6
    statt 15 Plätzen, sichtbar an abgeschnittenen Beschriftungen.

    Zwölf Blöcke kann der klassische nicht zeigen. Das ist hart entscheidbar und schlägt deshalb
    auch einen anderslautenden pageType.
    """
    viele = "weatherUpdate" + "~text~sensor.x~A~65535~Name~Wert" * 12
    assert protocol.parse_message(viele)["cardType"] == "screensaver2"
    assert protocol.parse_message(viele, "cardGrid")["cardType"] == "screensaver2"
    assert protocol.parse_message(viele, "screensaver")["cardType"] == "screensaver2"
    assert protocol.parse_message(viele, "screensaver2")["cardType"] == "screensaver2"

    # Genau an der Grenze: sechs Blöcke passen noch auf den klassischen, sieben nicht mehr.
    grenze = "weatherUpdate" + "~text~sensor.x~A~65535~Name~Wert" * 6
    assert protocol.parse_message(grenze)["cardType"] == "screensaver"
    darueber = "weatherUpdate" + "~text~sensor.x~A~65535~Name~Wert" * 7
    assert protocol.parse_message(darueber)["cardType"] == "screensaver2"


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


# Nach ``update_status_icons`` (pages.py): erst beide Symbole je mit Farbe, dann beide altFont-Werte.
# Symbol 1 trägt hier — wie in einer echten Konfiguration mit ``<I>…</I> ha:{{ … }} °C`` — Zeichen
# *und* Text; Symbol 2 ist ein reines Zeichen.
STATUS = "statusUpdate~A 45.2 °C~17299~B~65504~True~"


def test_status_symbole_werden_mit_farbe_und_altfont_gelesen() -> None:
    eins, zwei = protocol.parse_status_update(STATUS)
    assert eins["iconChar"] == "A 45.2 °C"
    assert eins["rgb"] == protocol.rgb565_to_rgb(17299)
    assert eins["altFont"] is True
    assert eins["leer"] is False
    assert zwei["iconChar"] == "B"
    assert zwei["altFont"] is False


def test_nicht_konfigurierte_status_symbole_kommen_als_leeres_paar() -> None:
    """``update_status_icons`` sendet dann ``~~`` – die Stelle bleibt auf dem Display leer."""
    eintraege = protocol.parse_status_update("statusUpdate~~~~~~")
    assert len(eintraege) == 2
    assert all(eintrag["leer"] for eintrag in eintraege)
    assert all(eintrag["iconChar"] is None for eintrag in eintraege)


def test_abgeschnittene_status_nachricht_ergibt_trotzdem_zwei_eintraege() -> None:
    """Fehlende Felder dürfen nicht in einen IndexError laufen – sonst bliebe die Vorschau leer."""
    eintraege = protocol.parse_status_update("statusUpdate~A~17299")
    assert len(eintraege) == 2
    assert eintraege[0]["iconChar"] == "A"
    assert eintraege[1]["leer"] is True


def test_status_nachricht_ist_keine_karten_nachricht() -> None:
    """Sie gehört keiner Karte – ``parse_message`` muss sie deshalb liegen lassen."""
    assert protocol.parse_message(STATUS, "screensaver2") is None
    assert protocol.parse_status_update("weatherUpdate~~~~65535~Wetter~8°C") is None


def test_die_schriftgroesse_wird_vom_symbol_getrennt() -> None:
    """Auf dem Raster hängt das Backend die Font-Nummer ans Symbol – mit ``¬`` als Trenner.

    Steht am Eintrag ein ``font``, sendet ``pages.py`` ``icon_id = f'{icon_id}¬{font}'``. Wer das
    nicht abtrennt, zeigt auf dem Raster wörtlich "19¬0" statt der Zahl.
    """
    payload = (
        "entityUpd~Sensoren~button~navigate.prev~<~65535~~~button~navigate.next~>~65535~~"
        "~text~sensor.a~19¬2~2016~Außentemp.~"
        "~text~sensor.b~100~2016~Luftdruck~"
    )
    eintraege = protocol.parse_message(payload, "cardGrid2")["entities"]
    assert eintraege[0]["iconChar"] == "19"
    assert eintraege[0]["font"] == 2
    # Ohne Angabe bleibt das Feld unangetastet und ohne Schriftgröße.
    assert eintraege[1]["iconChar"] == "100"
    assert "font" not in eintraege[1] or eintraege[1]["font"] is None


def test_thermo_wird_zerlegt_statt_uebergangen() -> None:
    """Die Thermostatkarte hat ein eigenes Format – und wird trotzdem vollständig gelesen.

    Die Feldnummern stammen aus dem Seitencode des HMI-Dumps (``spstr … "~",15`` für die
    Ist-Temperatur, 17 für den Zustand, 21 + n·4 für die Betriebsarten), nicht aus einer Zählung
    am Beispiel.
    """
    nav = "~".join(["delete"] + [""] * 5 + ["delete"] + [""] * 5)
    modi = ""
    for name, farbe, aktiv in (("off", 35921, 0), ("heat", 64512, 1), ("cool", 11487, 0)):
        modi += f"~\ue000~{farbe}~{aktiv}~{name}"
    modi += "~~~~" * 5
    roh = (
        f"entityUpd~Heizung~{nav}~climate.wohnzimmer~21.4 \u00b0C~225~heizt\r\n(heat)"
        f"~50~300~5{modi}~Aktuell~Zustand~Betrieb~\ue001~~0"
    )
    d = protocol.parse_message(roh, "cardThermo")
    assert d["strukturiert"] is True, "cardThermo darf nicht mehr als unstrukturiert gelten"
    assert d["title"] == "Heizung"
    assert d["entity"] == "climate.wohnzimmer"
    t = d["thermo"]
    assert t["current"] == "21.4 \u00b0C", "die Ist-Temperatur kommt fertig samt Einheit"
    assert t["target"] == 22.5, "Sollwerte kommen als Ganzzahl mal zehn"
    assert t["state"] == "heizt\r\n(heat)"
    assert (t["min"], t["max"], t["step"]) == (5.0, 30.0, 0.5)
    assert t["target2"] is None, "ohne zweiten Sollwert bleibt das Feld leer, nicht 0"
    assert t["detailPage"] == "0"
    assert t["labels"] == {"currently": "Aktuell", "state": "Zustand", "action": "Betrieb"}


def test_thermo_meldet_nur_die_belegten_betriebsarten() -> None:
    """Acht Bloecke kommen immer – gezeigt werden nur die belegten.

    Das Backend fuellt die Nachricht stets auf acht Tasten auf; die ungenutzten sind vier leere
    Felder und am Geraet ausgeblendet. Als leere Kaestchen zu erscheinen waere eine Behauptung.
    """
    nav = "~".join(["delete"] + [""] * 5 + ["delete"] + [""] * 5)
    modi = "~\ue000~35921~0~off" + "~\ue001~64512~1~heat" + "~~~~" * 6
    roh = f"entityUpd~T~{nav}~climate.x~20 C~200~an~50~300~5{modi}~a~b~c~~~1"
    t = protocol.parse_message(roh, "cardThermo")["thermo"]
    assert len(t["modes"]) == 2
    assert [m["modus"] for m in t["modes"]] == ["off", "heat"]
    assert [m["aktiv"] for m in t["modes"]] == [False, True]
    # Die Farbe kommt als RGB565 und wird zurueckgerechnet – das ist die Farbe, die das Geraet zeigt.
    assert t["modes"][1]["rgb"] == protocol.rgb565_to_rgb(64512)


def test_thermo_mit_zwei_sollwerten() -> None:
    """Ein gesetzter zweiter Sollwert ist das Kennzeichen des Bereichsthermostats."""
    nav = "~".join(["delete"] + [""] * 5 + ["delete"] + [""] * 5)
    roh = f"entityUpd~T~{nav}~climate.x~20 C~240~an~50~300~5{'~~~~' * 8}~a~b~c~~180~1"
    t = protocol.parse_message(roh, "cardThermo")["thermo"]
    assert t["target"] == 24.0
    assert t["target2"] == 18.0
