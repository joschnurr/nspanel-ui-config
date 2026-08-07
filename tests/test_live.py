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


def _karte(titel: str) -> str:
    return (
        f"entityUpd~{titel}~button~navigate.prev~<~65535~~~button~navigate.next~>~65535~~"
        "~light~light.a~A~17299~Licht~1"
    )


def test_jede_karte_wird_einzeln_gemerkt() -> None:
    """Der Kern der Live-Ansicht: ein Panel steht meist im Ruhezustand.

    Ohne Gedächtnis je Karte sähe man beim Bearbeiten immer nur den Screensaver – die Funktion wäre
    praktisch nutzlos. Wer einmal durchblättert, hat danach jede Karte hier.
    """
    zustand = live.LiveState()
    zustand.handle("pageType~cardEntities")
    zustand.handle(_karte("Garage Pool"), jetzt=1000.0)
    zustand.handle("pageType~cardGrid")
    zustand.handle(_karte("Wohnzimmer"), jetzt=1010.0)
    # Danach geht das Panel in den Ruhezustand.
    zustand.handle("weatherUpdate~~~~65535~Wetter~8°C", jetzt=1020.0)

    garage = zustand.as_dict(jetzt=1100.0, title="Garage Pool", card_type="cardEntities")
    assert garage["matched"] is True
    assert garage["message"]["title"] == "Garage Pool"
    assert garage["ageSeconds"] == 100

    wohnzimmer = zustand.as_dict(jetzt=1100.0, title="Wohnzimmer", card_type="cardGrid")
    assert wohnzimmer["matched"] is True
    assert wohnzimmer["message"]["title"] == "Wohnzimmer"


def test_eine_nie_gezeigte_karte_wird_als_solche_gemeldet() -> None:
    zustand = live.LiveState()
    zustand.handle("pageType~cardEntities")
    zustand.handle(_karte("Garage Pool"), jetzt=1000.0)

    antwort = zustand.as_dict(jetzt=1000.0, title="Küche", card_type="cardGrid")
    assert antwort["matched"] is False
    # Statt gar nichts zu zeigen: was zuletzt lief – der Editor kann das erklären.
    assert antwort["message"]["title"] == "Garage Pool"
    assert antwort["showing"] == "Garage Pool"


def test_der_screensaver_wird_ueber_seine_bauart_gefunden() -> None:
    """Screensaver haben keinen Titel; gesucht wird deshalb über den Kartentyp."""
    zustand = live.LiveState()
    zustand.handle("pageType~screensaver2")
    zustand.handle("weatherUpdate~~~~65535~Wetter~8°C", jetzt=500.0)

    antwort = zustand.as_dict(jetzt=500.0, title="", card_type="screensaver2")
    assert antwort["matched"] is True
    assert antwort["message"]["cardType"] == "screensaver2"
    # Auch die andere Bauart findet den Mitschnitt – welche läuft, entscheidet das Backend.
    assert zustand.as_dict(jetzt=500.0, card_type="screensaver")["matched"] is True


def test_die_liste_der_bekannten_karten_kommt_mit() -> None:
    zustand = live.LiveState()
    zustand.handle("pageType~cardEntities")
    zustand.handle(_karte("Garage Pool"), jetzt=1000.0)
    zustand.handle("pageType~cardGrid")
    zustand.handle(_karte("Wohnzimmer"), jetzt=1005.0)

    titel = {eintrag["title"] for eintrag in zustand.as_dict(jetzt=1005.0)["known"]}
    assert titel == {"Garage Pool", "Wohnzimmer"}


def test_status_symbole_kommen_in_die_antwort() -> None:
    zustand = live.LiveState()
    assert zustand.handle("statusUpdate~A 45.2 °C~17299~B~65504~True~", jetzt=1000.0) is True

    antwort = zustand.as_dict(jetzt=1010.0)
    assert antwort["statusIcons"][0]["iconChar"] == "A 45.2 °C"
    assert antwort["statusIcons"][1]["iconChar"] == "B"
    assert antwort["statusIconsAgeSeconds"] == 10


def test_status_symbole_ueberleben_den_kartenwechsel() -> None:
    """Sie gehören keiner Karte: eine neue Karte darf sie weder ersetzen noch löschen."""
    zustand = live.LiveState()
    zustand.handle("statusUpdate~A~17299~B~65504~~", jetzt=1000.0)
    zustand.handle("pageType~cardEntities")
    zustand.handle(_karte("Garage Pool"), jetzt=1005.0)

    antwort = zustand.as_dict(jetzt=1005.0, title="Garage Pool", card_type="cardEntities")
    assert antwort["message"]["title"] == "Garage Pool"
    assert antwort["statusIcons"][0]["iconChar"] == "A"
    # Und umgekehrt: die Statusnachricht überschreibt den Karten-Mitschnitt nicht.
    zustand.handle("statusUpdate~C~17299~D~65504~~", jetzt=1010.0)
    assert zustand.message["title"] == "Garage Pool"
    assert zustand.as_dict(jetzt=1010.0)["statusIcons"][0]["iconChar"] == "C"


def test_ohne_statusnachricht_bleibt_das_feld_leer() -> None:
    """Ein Panel ohne konfigurierte Status-Symbole sendet nie ein statusUpdate."""
    zustand = live.LiveState()
    zustand.handle("pageType~cardEntities")
    zustand.handle(_karte("Garage Pool"), jetzt=1000.0)

    antwort = zustand.as_dict(jetzt=1000.0)
    assert antwort["statusIcons"] is None
    assert antwort["statusIconsAgeSeconds"] is None


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


def test_die_navigationsnachricht_sieht_aus_wie_ein_tastendruck() -> None:
    """So findet das Backend die Karte: button_press mit einem Ziel, das mit navigate. beginnt."""
    import json

    nutzlast = json.loads(live.navigate_payload("garage"))
    assert nutzlast["CustomRecv"] == "event,buttonPress2,navigate.garage,button"
    # Die Navigationsleiste des Panels selbst nutzt uuids – dieselbe Form muss durchgehen.
    nutzlast = json.loads(live.navigate_payload("uuid.cUYCmkbrg5"))
    assert nutzlast["CustomRecv"] == "event,buttonPress2,navigate.uuid.cUYCmkbrg5,button"


def test_das_empfangs_topic_kommt_aus_dem_modell() -> None:
    """Gesendet wird auf dem Topic, auf dem sonst das Panel seine Tastendrücke meldet."""
    modell = {"global": {"panelRecvTopic": " NSPanel_1/tele/RESULT "}}
    assert live.recv_topic_of(modell) == "NSPanel_1/tele/RESULT"
    assert live.recv_topic_of({"global": {}}) is None
    assert live.recv_topic_of(None) is None


def test_unlock_teilt_sich_den_schluessel_mit_alarm() -> None:
    """`cardUnlock` wird am Geraet als `cardAlarm` gezeichnet – sonst findet der Editor sie nie.

    Das Backend schreibt den Typ in `page_type()` um, bevor er ans Panel geht; im Mitschnitt steht
    also immer `cardAlarm`. Suchte der Editor unter `cardUnlock|<Titel>`, bliebe die Ansicht leer,
    obwohl die Nachricht da ist.
    """
    assert live.card_key({"cardType": "cardUnlock", "title": "Entsperren"}) == live.card_key(
        {"cardType": "cardAlarm", "title": "Entsperren"}
    )
