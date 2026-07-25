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
