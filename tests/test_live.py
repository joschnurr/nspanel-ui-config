"""Prüft den Mitschnitt: welche Nachricht wann gilt, und was daraus in die API geht.

Der Zustand ist bewusst ohne Home-Assistant-Bezug gebaut, damit genau das prüfbar bleibt, was leicht
schiefgeht: die Reihenfolge. Das Backend schickt erst ``pageType~<karte>`` und dann den Inhalt — wer
den Inhalt ohne den vorherigen ``pageType`` zerlegt, ordnet die Felder falsch zu.
"""

from __future__ import annotations

from nspanel_ui_config import live

ENTITIES = (
    "entityUpd~Küche~button~navigate.prev~<~65535~~~button~navigate.next~>~65535~~"
    "~light~light.kueche~A~17299~Küche~1"
    "~switch~switch.kaffee~B~17299~Kaffee~0"
)


def test_pagetype_allein_aendert_die_anzeige_nicht() -> None:
    """Sonst flackerte die Vorschau bei jedem Kartenwechsel kurz leer."""
    zustand = live.LiveState("cmnd/NSPanel_1/CustomSend")
    assert zustand.handle("pageType~cardGrid") is False
    assert zustand.card_type == "cardGrid"
    assert zustand.message is None


def test_inhalt_wird_der_zuletzt_gemeldeten_karte_zugeordnet() -> None:
    zustand = live.LiveState()
    zustand.handle("pageType~cardEntities")
    assert zustand.handle(ENTITIES, jetzt=1000.0) is True
    assert zustand.message["cardType"] == "cardEntities"
    assert len(zustand.message["entities"]) == 2
    assert zustand.message["entities"][0]["name"] == "Küche"
    assert zustand.seen == 1000.0


def test_ohne_vorherigen_pagetype_bleiben_die_eintraege_leer() -> None:
    """Ehrlicher als raten: ohne Kartentyp ist der Aufbau der Nachricht nicht bekannt."""
    zustand = live.LiveState()
    assert zustand.handle(ENTITIES) is True
    assert zustand.message["strukturiert"] is False
    assert zustand.message["entities"] == []
    assert zustand.message["title"] == "Küche"


def test_der_screensaver_meldet_sich_ohne_pagetype() -> None:
    zustand = live.LiveState()
    assert zustand.handle("weatherUpdate~weather~weather.home~A~65535~Zuhause~8.1°C") is True
    assert zustand.card_type == "screensaver"
    assert len(zustand.message["entities"]) == 1


def test_fremde_nachrichten_werden_gezaehlt_statt_verarbeitet() -> None:
    """Über dasselbe Topic läuft der gesamte Verkehr zum Panel."""
    zustand = live.LiveState()
    for payload in ("dimmode~10~100", "time~12:30", "notify~Kopf~Text"):
        assert zustand.handle(payload) is False
    assert zustand.ignoriert == 3
    assert zustand.message is None


def test_alter_und_frische_stehen_in_der_antwort() -> None:
    zustand = live.LiveState("cmnd/NSPanel_1/CustomSend")
    zustand.handle("pageType~cardGrid")
    zustand.handle(ENTITIES, jetzt=1000.0)

    frisch = zustand.as_dict(jetzt=1010.0)
    assert frisch["ageSeconds"] == 10
    assert frisch["fresh"] is True
    assert frisch["topic"] == "cmnd/NSPanel_1/CustomSend"

    # Ein Panel im Ruhezustand sendet nichts – der alte Stand bleibt sichtbar, aber gekennzeichnet.
    alt = zustand.as_dict(jetzt=1000.0 + live.FRISCH_SEKUNDEN + 1)
    assert alt["fresh"] is False


def test_ohne_mitschnitt_ist_die_antwort_leer_aber_gueltig() -> None:
    leer = live.LiveState().as_dict(jetzt=1.0)
    assert leer["message"] is None
    assert leer["ageSeconds"] is None
    assert leer["fresh"] is False


def test_das_sende_topic_kommt_aus_dem_modell() -> None:
    modell = {"global": {"panelSendTopic": "cmnd/NSPanel_1/CustomSend"}}
    assert live.send_topic_of(modell) == "cmnd/NSPanel_1/CustomSend"
    # Geraten wird nichts: ohne Topic kein Abo, sonst hörte die Integration still ins Leere.
    assert live.send_topic_of({"global": {}}) is None
    assert live.send_topic_of({"global": {"panelSendTopic": "   "}}) is None
    assert live.send_topic_of({}) is None
    assert live.send_topic_of(None) is None


def test_leerzeichen_um_das_topic_werden_entfernt() -> None:
    modell = {"global": {"panelSendTopic": "  cmnd/NSPanel_1/CustomSend \n"}}
    assert live.send_topic_of(modell) == "cmnd/NSPanel_1/CustomSend"
