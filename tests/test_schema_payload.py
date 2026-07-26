"""Tests der Schema-Beschreibung, aus der das Panel seine Formulare baut.

Der Editor rendert seine Felder ausschließlich aus ``schema_payload()``. Fehlt dort ein Feld oder
ein Widget-Hinweis, merkt man das im Browser — nicht im Round-Trip-Test. Diese Tests schließen die
Lücke: sie halten Schema und Editor-Erwartungen zusammen.
"""

from __future__ import annotations

import json

from nspanel_ui_config import schema  # via conftest.py registriert

PAYLOAD = schema.schema_payload()

# Schlüssel, die das Panel (www/panel/nspanel-ui-config-panel.js) tatsächlich liest.
KEYS_USED_BY_PANEL = (
    "cardTypes",
    "screensaverTypes",
    "cardCommonFields",
    "cardTypeFields",
    "entityFields",
    "entitiesField",
    "globalFieldOrder",
    "globalDefaults",
    "fieldHints",
    "fieldOptions",
    "fieldDescriptions",
    "fieldValueHints",
    "cardFieldDescriptions",
    "cardCapacity",
    "capacityLayoutNotes",
    "cardTypeNotes",
    "cardsWithoutEntityList",
    "gridAutoSwitchAt",
    "flatEntityCardTypes",
    "singleEntityCardTypes",
    "templateFields",
    "templateSuffixFields",
)


def test_payload_enthaelt_alles_was_das_panel_liest() -> None:
    fehlend = [key for key in KEYS_USED_BY_PANEL if key not in PAYLOAD]
    assert not fehlend, f"Das Panel liest Schlüssel, die das Schema nicht liefert: {fehlend}"


def test_payload_ist_json_serialisierbar() -> None:
    """Geht über die HTTP-API — ein nicht serialisierbarer Wert wäre erst zur Laufzeit sichtbar."""
    assert json.loads(json.dumps(PAYLOAD)) == PAYLOAD


def test_jedes_gerenderte_feld_hat_einen_widget_hinweis() -> None:
    """Ohne Hinweis fällt der Editor auf ein Textfeld zurück — für Listen/Dicts wäre das falsch."""
    gerendert: set[str] = set(PAYLOAD["cardCommonFields"])
    gerendert |= set(PAYLOAD["entityFields"])
    gerendert |= set(PAYLOAD["globalFieldOrder"])
    for felder in PAYLOAD["cardTypeFields"].values():
        gerendert |= set(felder)
    # `entities` ist keine Formularzeile, sondern die eigene Entity-Liste.
    gerendert.discard(PAYLOAD["entitiesField"])

    ohne_hinweis = sorted(gerendert - set(PAYLOAD["fieldHints"]))
    assert not ohne_hinweis, f"Felder ohne Widget-Hinweis: {ohne_hinweis}"


def test_widget_hinweise_sind_dem_editor_bekannt() -> None:
    erlaubt = {"string", "number", "boolean", "entity", "icon", "color", "json", "entity_object", "select"}
    unbekannt = {name: hint for name, hint in PAYLOAD["fieldHints"].items() if hint not in erlaubt}
    assert not unbekannt, f"Unbekannte Widget-Typen: {unbekannt}"


def test_auswahllisten_passen_zu_den_erlaubten_werten() -> None:
    assert set(PAYLOAD["fieldOptions"]["model"]) == set(PAYLOAD["models"])
    assert set(PAYLOAD["fieldOptions"]["type"]) == set(PAYLOAD["cardTypes"])
    # Jedes Feld mit Auswahlliste sollte auch als 'select' markiert sein.
    for name in PAYLOAD["fieldOptions"]:
        assert PAYLOAD["fieldHints"].get(name) == "select", f"'{name}' hat Optionen, aber keinen select-Hinweis"


def test_flache_und_einzel_entity_karten_sind_konsistent() -> None:
    flach = set(PAYLOAD["flatEntityCardTypes"])
    einzel = set(PAYLOAD["singleEntityCardTypes"])
    assert einzel <= flach, "Karten mit einer Entity müssen auch als 'flach' gelten"
    # Der Screensaver trägt eine flache Entity *und* eine entities-Liste.
    assert set(PAYLOAD["screensaverTypes"]) <= flach
    assert not (set(PAYLOAD["screensaverTypes"]) & einzel)


def test_flache_karten_bekommen_die_entity_felder() -> None:
    """card_known_fields muss für flache Karten die Entity-Felder mitliefern."""
    for card_type in PAYLOAD["singleEntityCardTypes"]:
        felder = schema.card_known_fields(card_type, has_flat_entity=True)
        assert "entity" in felder, f"{card_type} ohne 'entity'"
        assert "icon" in felder, f"{card_type} ohne 'icon'"


def test_beschreibungen_verweisen_nur_auf_existierende_felder() -> None:
    bekannt = set(PAYLOAD["fieldHints"])
    verwaist = sorted(set(PAYLOAD["fieldDescriptions"]) - bekannt)
    assert not verwaist, f"Beschreibung für unbekannte Felder: {verwaist}"


def test_globale_defaults_decken_die_feldreihenfolge_ab() -> None:
    assert set(PAYLOAD["globalFieldOrder"]) == set(PAYLOAD["globalDefaults"])


def test_template_felder_sind_dem_editor_bekannt() -> None:
    """Ein Tippfehler hier würde den Template-Umschalter still an keinem Feld erscheinen lassen."""
    bekannt = set(PAYLOAD["fieldHints"])
    unbekannt = sorted(set(PAYLOAD["templateFields"]) - bekannt)
    assert not unbekannt, f"templateFields nennt Felder ohne Widget-Hinweis: {unbekannt}"
    # Die beiden Felder, um die es dem Nutzer am häufigsten geht.
    for feld in ("color", "value"):
        assert feld in PAYLOAD["templateFields"], f"{feld} muss template-fähig sein"


def test_suffix_felder_sind_eine_teilmenge_der_template_felder() -> None:
    """Nur ``value``/``icon`` rendert das Backend bis zum letzten ``}`` – und beide sind Templates."""
    suffix = set(PAYLOAD["templateSuffixFields"])
    assert suffix <= set(PAYLOAD["templateFields"])
    assert suffix == {"value", "icon"}


# --- Beschreibungen und Wertebereiche ---------------------------------------------------------


def test_wertebereiche_verweisen_nur_auf_existierende_felder() -> None:
    """Ein Tippfehler hier bliebe unsichtbar: die Zeile erschiene einfach an keinem Feld."""
    verwaist = sorted(set(PAYLOAD["fieldValueHints"]) - set(PAYLOAD["fieldHints"]))
    assert not verwaist, f"Wertebereich für unbekannte Felder: {verwaist}"


def test_jedes_gerenderte_feld_ist_erklaert() -> None:
    """Der eigentliche Zweck dieser Runde: kein Eingabefeld ohne Beschreibung *und* Wertebereich."""
    gerendert: set[str] = set(PAYLOAD["cardCommonFields"])
    gerendert |= set(PAYLOAD["entityFields"])
    gerendert |= set(PAYLOAD["globalFieldOrder"])
    for felder in PAYLOAD["cardTypeFields"].values():
        gerendert |= set(felder)
    gerendert.discard(PAYLOAD["entitiesField"])
    # `type` erklärt sich über die Kartentyp-Notiz und die Auswahlliste.
    gerendert.discard("type")

    ohne_beschreibung = sorted(gerendert - set(PAYLOAD["fieldDescriptions"]))
    assert not ohne_beschreibung, f"Felder ohne Beschreibung: {ohne_beschreibung}"
    ohne_werte = sorted(gerendert - set(PAYLOAD["fieldValueHints"]))
    assert not ohne_werte, f"Felder ohne Angabe der möglichen Werte: {ohne_werte}"


def test_kartenspezifische_beschreibungen_gelten_echten_karten() -> None:
    gueltig = set(PAYLOAD["cardTypes"]) | set(PAYLOAD["screensaverTypes"])
    for card_type, felder in PAYLOAD["cardFieldDescriptions"].items():
        assert card_type in gueltig, f"Beschreibung für unbekannten Kartentyp '{card_type}'"
        unbekannt = sorted(set(felder) - set(PAYLOAD["fieldHints"]))
        assert not unbekannt, f"{card_type} beschreibt unbekannte Felder: {unbekannt}"


# --- Anzeigekapazität -------------------------------------------------------------------------


def test_kapazitaet_ist_fuer_jedes_modell_angegeben() -> None:
    for card_type, by_model in PAYLOAD["cardCapacity"].items():
        assert set(by_model) == set(PAYLOAD["models"]), f"{card_type} deckt nicht alle Modelle ab"
        for model, limit in by_model.items():
            assert isinstance(limit, int) and limit > 0, f"{card_type}/{model}: {limit!r}"


def test_kapazitaet_und_karten_ohne_liste_ueberschneiden_sich_nicht() -> None:
    """Eine Karte hat entweder Plätze in einer Liste oder gar keine Liste – nie beides."""
    mit = set(PAYLOAD["cardCapacity"])
    ohne = set(PAYLOAD["cardsWithoutEntityList"])
    assert not (mit & ohne), f"Widersprüchlich eingeordnet: {sorted(mit & ohne)}"
    # Zusammen müssen sie jeden Kartentyp abdecken, sonst schweigt der Editor grundlos.
    alle = set(PAYLOAD["cardTypes"]) | set(PAYLOAD["screensaverTypes"])
    assert alle <= (mit | ohne), f"Ohne Aussage zur Kapazität: {sorted(alle - mit - ohne)}"


def test_kapazitaet_haengt_am_modell() -> None:
    """Die beiden Karten, bei denen us-p mehr zeigt als eu – der Grund für die Modellabhängigkeit."""
    assert schema.capacity_for("cardEntities", "eu") == 4
    assert schema.capacity_for("cardEntities", "us-p") == 6
    assert schema.capacity_for("cardGrid2", "us-p") == 9
    # Unbekanntes Modell fällt auf den Backend-Standard 'eu' zurück, statt zu raten.
    assert schema.capacity_for("cardEntities", "unsinn") == 4
    assert schema.capacity_for("cardEntities", None) == 4
    # Karten ohne Liste machen keine Aussage.
    assert schema.capacity_for("cardThermo", "eu") is None
    assert schema.capacity_for(None, "eu") is None


def test_grid_wechselt_selbst_auf_grid2() -> None:
    """Das Backend tut das (pages.py) – eine Warnung ab 7 Entities wäre schlicht falsch."""
    assert schema.effective_card_type("cardGrid", 6) == "cardGrid"
    assert schema.effective_card_type("cardGrid", 7) == "cardGrid2"
    assert schema.effective_card_type("cardEntities", 99) == "cardEntities"


def test_layout_notizen_gehoeren_zu_karten_mit_kapazitaet() -> None:
    verwaist = sorted(set(PAYLOAD["capacityLayoutNotes"]) - set(PAYLOAD["cardCapacity"]))
    assert not verwaist, f"Layout-Notiz ohne Kapazitätsangabe: {verwaist}"


def test_jeder_kartentyp_hat_eine_erklaerung() -> None:
    alle = set(PAYLOAD["cardTypes"]) | set(PAYLOAD["screensaverTypes"])
    fehlend = sorted(alle - set(PAYLOAD["cardTypeNotes"]))
    assert not fehlend, f"Kartentypen ohne Erklärung: {fehlend}"


# --- Validierung ------------------------------------------------------------------------------


def test_zu_lange_entity_liste_wird_gemeldet() -> None:
    model = {
        "global": {"model": "eu"},
        "cards": [{"type": "cardEntities", "entities": [{"entity": f"sensor.x{i}"} for i in range(5)]}],
    }
    meldungen = [f["message"] for f in schema.validate_model(model) if f["path"] == "cards[0].entities"]
    assert meldungen, "Fünf Entities auf cardEntities/eu müssen auffallen"
    assert "4" in meldungen[0]


def test_gleiche_liste_auf_us_p_ist_in_ordnung() -> None:
    """Dieselbe Karte, anderes Modell – die Warnung darf dann nicht kommen."""
    model = {
        "global": {"model": "us-p"},
        "cards": [{"type": "cardEntities", "entities": [{"entity": f"sensor.x{i}"} for i in range(5)]}],
    }
    assert not schema.validate_model(model)


def test_grid_mit_sieben_entities_wird_nicht_bemaengelt() -> None:
    model = {
        "global": {"model": "eu"},
        "cards": [{"type": "cardGrid", "entities": [{"entity": f"sensor.x{i}"} for i in range(7)]}],
    }
    assert not schema.validate_model(model)


def test_wirkungslose_keys_werden_gebuendelt_gemeldet() -> None:
    """Ein Hinweis je Karte, nicht je Zeile – sonst steht dieselbe Erklärung fünfmal untereinander."""
    model = {
        "global": {"model": "eu"},
        "cards": [
            {
                "type": "cardEntities",
                "entities": [{"entity": f"sensor.x{i}", "unit": "kWh"} for i in range(3)],
            }
        ],
    }
    unit_meldungen = [f for f in schema.validate_model(model) if "'unit'" in f["message"]]
    assert len(unit_meldungen) == 1, "Wirkungslose Keys sollen je Karte gebündelt werden"
    assert "1, 2, 3" in unit_meldungen[0]["message"]
