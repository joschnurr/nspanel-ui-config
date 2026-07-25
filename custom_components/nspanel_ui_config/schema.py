"""Datenmodell / Schema der nspanel-lovelace-ui-Konfiguration.

Abgeleitet aus ``luibackend/config.py`` (joBr99) und docs.nspanel.pky.eu. Dieses Modul beschreibt
die *Struktur* der Zielkonfiguration deklarativ, damit Editor (Frontend), Import und Generator sich
auf eine gemeinsame Definition stützen.

Leitidee des Modells: **verlustfrei vor vollständig.** Alles, was das Backend kennt, bekommt ein
benanntes Feld; alles Übrige landet unverändert in einem ``extra``-Dict und wird beim Generieren
wieder herausgeschrieben. Dadurch überlebt auch Konfiguration den Round-Trip, die diese Integration
(noch) nicht versteht — etwa Keys aus einer neueren Backend-Version.
"""

from __future__ import annotations

from typing import Any, Final

# --- Kartentypen -----------------------------------------------------------------------------

# Kartentypen des Upstream-Backends (pages.py). MVP-Priorität: cardEntities, cardGrid.
CARD_TYPES: Final[tuple[str, ...]] = (
    "cardEntities",
    "cardGrid",
    "cardGrid2",
    "cardThermo",
    "cardMedia",
    "cardAlarm",
    "cardQR",
    "cardPower",
    "cardUnlock",
    "cardChart",
)

# Der Screensaver ist im Backend ebenfalls eine Card, nur mit eigenem Typ.
SCREENSAVER_TYPES: Final[tuple[str, ...]] = ("screensaver", "screensaver2")

# Panel-Modelle.
MODELS: Final[tuple[str, ...]] = ("eu", "us-l", "us-p")


# --- Entity-Felder ---------------------------------------------------------------------------

# Felder, die ``config.py::Entity`` ausliest. Reihenfolge = Ausgabereihenfolge im Generator.
ENTITY_FIELDS: Final[tuple[str, ...]] = (
    "entity",          # entity_id oder Spezial-Präfix (iText., navigate., …)
    "name",            # Anzeigename (nameOverride)
    "icon",            # mdi-Icon; kann {on, off} sein
    "color",           # RGB-Liste [r,g,b], {on, off} oder Jinja-Template
    "value",           # angezeigter Wert / Template
    "type",            # stype (z. B. input_select, button …)
    "state",           # condState
    "state_not",       # condStateNot
    "state_template",  # condTemplate
    "assumed_state",
    "status",          # zusätzliche Status-Entity
    "font",            # Font-Override
    "data",            # freies dict für kartentyp-spezifische Extras
)

# Felder, die die Renderer direkt aus ``entity_input_config`` lesen, ohne dass ``Entity`` sie kennt.
ENTITY_RENDERER_FIELDS: Final[tuple[str, ...]] = (
    "effectList",  # pages.py: Licht-Effektliste
    "speed",       # pages.py: Lüfter-Geschwindigkeit
)

ENTITY_KNOWN_FIELDS: Final[tuple[str, ...]] = ENTITY_FIELDS + ENTITY_RENDERER_FIELDS

# Entity-artige Karten-Keys: eigenständige Dicts, die wie eine Entity-Zeile aufgebaut sind.
ENTITY_LIKE_CARD_FIELDS: Final[tuple[str, ...]] = (
    "navItem1",
    "navItem2",
    "statusIcon1",
    "statusIcon2",
)


# --- Karten-Felder ---------------------------------------------------------------------------

# Von ``config.py::Card`` für *jede* Karte ausgelesen.
CARD_COMMON_FIELDS: Final[tuple[str, ...]] = (
    "type",
    "key",
    "title",
    "navItem1",
    "navItem2",
    "sleepTimeout",
    "cooldown",
)

# Kartentyp-spezifische Keys, die die Renderer aus ``raw_config`` ziehen (pages.py).
CARD_TYPE_FIELDS: Final[dict[str, tuple[str, ...]]] = {
    "cardEntities": ("temperatureUnit",),
    "cardGrid": ("temperatureUnit",),
    "cardGrid2": ("temperatureUnit",),
    "cardThermo": ("temperatureUnit", "supportedModes"),
    "cardMedia": ("mediaControl",),
    "cardAlarm": ("alarmControl", "supportedModes"),
    "cardQR": ("qrCode",),
    "cardPower": (),
    "cardUnlock": ("pin", "destination"),
    "cardChart": (),
    "screensaver": (
        "theme",
        "weatherUnit",
        "forecastSkip",
        "weatherOverrideForecast1",
        "weatherOverrideForecast2",
        "weatherOverrideForecast3",
        "weatherOverrideForecast4",
        "doubleTapToUnlock",
        "alternativeLayout",
        "defaultCard",
        "statusIcon1",
        "statusIcon2",
    ),
}
CARD_TYPE_FIELDS["screensaver2"] = CARD_TYPE_FIELDS["screensaver"]

# Die Entity-Liste steht im generierten YAML immer am Ende (längster Block).
CARD_ENTITIES_FIELD: Final[str] = "entities"

# Karten mit *einer* Entity, die flach auf der Karte liegt (das Backend baut dort ``Entity(card)``).
SINGLE_ENTITY_CARD_TYPES: Final[tuple[str, ...]] = ("cardThermo", "cardMedia", "cardAlarm")
# Der Screensaver trägt zusätzlich zur flachen Entity noch eine ``entities``-Liste.
FLAT_ENTITY_CARD_TYPES: Final[tuple[str, ...]] = SINGLE_ENTITY_CARD_TYPES + SCREENSAVER_TYPES


# --- Globale Settings ------------------------------------------------------------------------

# Defaults des Backends (``config.py::_DEFAULT_CONFIG``, ohne die strukturierten Blöcke).
# Dienen dem Editor als Platzhalter/Anzeige — sie werden beim Import *nicht* ins Modell gemischt,
# damit generiertes YAML nur enthält, was auch wirklich gesetzt wurde.
GLOBAL_DEFAULTS: Final[dict[str, Any]] = {
    "panelRecvTopic": "tele/tasmota_your_mqtt_topic/RESULT",
    "panelSendTopic": "cmnd/tasmota_your_mqtt_topic/CustomSend",
    "updateMode": "auto-notify",
    "model": "eu",
    "sleepTimeout": 20,
    "sleepBrightness": 20,
    "screenBrightness": 100,
    "defaultBackgroundColor": "ha-dark",
    "featureExperimentalSliders": False,
    "sleepTracking": None,
    "sleepTrackingZones": ["not_home", "off"],
    "sleepOverride": None,
    "locale": "en_US",
    "quiet": True,
    "timeFormat": "%H:%M",
    "dateFormatBabel": "full",
    "dateAdditionalTemplate": "",
    "timeAdditionalTemplate": "",
    "dateFormat": "%A, %d. %B %Y",
}

# Reihenfolge der globalen Settings im generierten YAML. Nicht gelistete Keys folgen dahinter.
GLOBAL_FIELD_ORDER: Final[tuple[str, ...]] = tuple(GLOBAL_DEFAULTS)

# Blöcke, die nicht zu den globalen Settings zählen.
STRUCTURED_KEYS: Final[frozenset[str]] = frozenset({"screensaver", "cards", "hiddenCards"})


# --- Widget-Hinweise für den Editor -----------------------------------------------------------

# Bevorzugtes Eingabe-Widget je Feldname. **Nur ein Vorschlag für skalare Werte:** trägt ein Feld
# tatsächlich ein Dict oder eine Liste (``icon: {on, off}``, ``sleepBrightness`` als Zeitplan,
# ``color`` als [r,g,b]), schaltet der Editor unabhängig vom Hinweis auf den JSON-Modus. So kann
# kein Wert dadurch verlorengehen, dass die Tabelle hier eine Vereinfachung annimmt.
#
# Typen: string | number | boolean | entity | icon | color | json | entity_object | select
FIELD_HINTS: Final[dict[str, str]] = {
    # Entity-Zeile
    "entity": "entity",
    "name": "string",
    "icon": "icon",
    "color": "color",
    "value": "string",
    "state": "string",
    "state_not": "string",
    "state_template": "string",
    "assumed_state": "boolean",
    "status": "entity",
    "font": "number",
    "data": "json",
    "effectList": "json",
    "speed": "number",
    # Karte
    "type": "select",
    "key": "string",
    "title": "string",
    "navItem1": "entity_object",
    "navItem2": "entity_object",
    "statusIcon1": "entity_object",
    "statusIcon2": "entity_object",
    "sleepTimeout": "number",
    "cooldown": "number",
    "temperatureUnit": "string",
    "supportedModes": "json",
    "mediaControl": "json",
    "alarmControl": "entity",
    "qrCode": "string",
    "pin": "string",
    "destination": "string",
    "theme": "json",
    "weatherUnit": "string",
    "forecastSkip": "number",
    "weatherOverrideForecast1": "json",
    "weatherOverrideForecast2": "json",
    "weatherOverrideForecast3": "json",
    "weatherOverrideForecast4": "json",
    "doubleTapToUnlock": "boolean",
    "alternativeLayout": "boolean",
    "defaultCard": "string",
    # Globale Settings
    "panelRecvTopic": "string",
    "panelSendTopic": "string",
    "updateMode": "select",
    "model": "select",
    "sleepBrightness": "number",
    "screenBrightness": "number",
    "defaultBackgroundColor": "string",
    "featureExperimentalSliders": "boolean",
    "sleepTracking": "entity",
    "sleepTrackingZones": "json",
    "sleepOverride": "entity",
    "locale": "string",
    "quiet": "boolean",
    "timeFormat": "string",
    "dateFormatBabel": "string",
    "dateAdditionalTemplate": "string",
    "timeAdditionalTemplate": "string",
    "dateFormat": "string",
}

# Auswahllisten für Felder mit Hinweis ``select``. Der Editor lässt trotzdem freie Eingabe zu —
# das Backend kennt womöglich mehr Werte als wir.
FIELD_OPTIONS: Final[dict[str, tuple[str, ...]]] = {
    "model": MODELS,
    "updateMode": ("auto-notify", "auto", "manual"),
    "type": CARD_TYPES,
}

# Kurzbeschreibungen, die der Editor als Hilfetext neben dem Feld zeigt. Bewusst knapp und nur
# dort, wo der Feldname allein nicht trägt.
FIELD_DESCRIPTIONS: Final[dict[str, str]] = {
    "entity": "entity_id oder Spezial-Präfix (iText., navigate., delete, …)",
    "key": "Optionaler eindeutiger Schlüssel für die Navigation zu dieser Karte",
    "value": "Angezeigter Wert; Jinja-Template erlaubt",
    "color": "[r, g, b], je Zustand {on, off} – oder ein Jinja-Template, das eine RGB-Liste liefert",
    "state_template": "Bedingung als Template — Zeile nur zeigen, wenn wahr",
    "font": "Font-Index des Nextion-Displays",
    "sleepTimeout": "Sekunden bis zum Screensaver (0 = nie)",
    "navItem1": "Linkes Navigationssymbol der Karte",
    "navItem2": "Rechtes Navigationssymbol der Karte",
    "defaultCard": "Karte, zu der der Screensaver beim Aufwachen springt (key)",
    "panelRecvTopic": "MQTT-Topic, auf dem Tasmota die Panel-Ereignisse meldet",
    "panelSendTopic": "MQTT-Topic, über das Befehle ans Panel gehen",
    "sleepTracking": "Personen-/Geräte-Entity; Panel bleibt wach, solange jemand da ist",
    "dateFormatBabel": "Babel-Datumsformat (full, long, medium, short)",
}


def schema_payload() -> dict[str, Any]:
    """Maschinenlesbare Schema-Beschreibung für den Editor im Frontend.

    Damit bleibt ``schema.py`` die einzige Quelle der Wahrheit: das Panel baut seine Formulare aus
    dieser Antwort, statt die Feldlisten in JavaScript zu duplizieren (und dort veralten zu lassen).
    """
    return {
        "cardTypes": list(CARD_TYPES),
        "screensaverTypes": list(SCREENSAVER_TYPES),
        "models": list(MODELS),
        "cardCommonFields": list(CARD_COMMON_FIELDS),
        "cardTypeFields": {key: list(value) for key, value in CARD_TYPE_FIELDS.items()},
        "entityFields": list(ENTITY_KNOWN_FIELDS),
        "entityLikeCardFields": list(ENTITY_LIKE_CARD_FIELDS),
        "entitiesField": CARD_ENTITIES_FIELD,
        "globalFieldOrder": list(GLOBAL_FIELD_ORDER),
        "globalDefaults": GLOBAL_DEFAULTS,
        "fieldHints": FIELD_HINTS,
        "fieldOptions": {key: list(value) for key, value in FIELD_OPTIONS.items()},
        "fieldDescriptions": FIELD_DESCRIPTIONS,
        # Karten, die ihre eine Entity flach auf der Karte tragen (siehe card_known_fields).
        "flatEntityCardTypes": list(FLAT_ENTITY_CARD_TYPES),
        # Davon die, die *nur* diese eine Entity haben — für sie blendet der Editor die
        # Entity-Liste aus. Der Screensaver hat beides: flache Entity *und* entities-Liste.
        "singleEntityCardTypes": list(SINGLE_ENTITY_CARD_TYPES),
    }


def card_known_fields(card_type: Any, has_flat_entity: bool = False) -> tuple[str, ...]:
    """Alle Keys, die für diesen Kartentyp ein benanntes Feld bekommen (in Ausgabereihenfolge).

    ``has_flat_entity``: Karten mit *einer* Entity (cardThermo, cardMedia, cardAlarm, Screensaver …)
    tragen deren Felder flach auf der Karte selbst — das Backend baut dort ``Entity(card_config)``.
    """
    fields: list[str] = list(CARD_COMMON_FIELDS)
    if isinstance(card_type, str):
        fields.extend(CARD_TYPE_FIELDS.get(card_type, ()))
    if has_flat_entity:
        fields.extend(ENTITY_KNOWN_FIELDS)
    fields.append(CARD_ENTITIES_FIELD)
    # Reihenfolge des ersten Auftretens beibehalten, Duplikate raus.
    return tuple(dict.fromkeys(fields))


def empty_model() -> dict[str, Any]:
    """Leeres, aber strukturell gültiges Ausgangsmodell für einen frischen Editor."""
    return {
        "global": {
            "panelRecvTopic": GLOBAL_DEFAULTS["panelRecvTopic"],
            "panelSendTopic": GLOBAL_DEFAULTS["panelSendTopic"],
            "model": "eu",
            "updateMode": "auto-notify",
            "locale": "de_DE",
            "timeFormat": "%H:%M",
            "dateFormat": "%A, %d. %B %Y",
        },
        "screensaver": {"type": "screensaver2", "entities": [], "extra": {}},
        "cards": [],
        "hiddenCards": [],
    }


def validate_model(model: dict[str, Any]) -> list[dict[str, str]]:
    """Prüfe das Modell auf Auffälligkeiten und liefere eine Liste von Befunden.

    Kein Blocker für das Generieren — das Backend ist tolerant und unbekannte Keys sind gewollt
    erlaubt. Die Befunde sind für den Editor gedacht (Hinweise neben dem betroffenen Feld).
    Level: ``error`` = Backend läuft damit sicher in einen Fehler, ``warning`` = vermutlich Tippfehler.
    """
    findings: list[dict[str, str]] = []

    def check_card(card: Any, path: str) -> None:
        if not isinstance(card, dict):
            findings.append({"level": "error", "path": path, "message": "Karte ist kein Objekt"})
            return
        card_type = card.get("type")
        if not isinstance(card_type, str):
            findings.append({"level": "error", "path": path, "message": "Karte ohne 'type'"})
        elif card_type not in CARD_TYPES and card_type not in SCREENSAVER_TYPES:
            findings.append(
                {"level": "warning", "path": path, "message": f"Unbekannter Kartentyp '{card_type}'"}
            )
        for index, entity in enumerate(card.get(CARD_ENTITIES_FIELD) or []):
            entity_path = f"{path}.entities[{index}]"
            if not isinstance(entity, dict):
                findings.append(
                    {"level": "error", "path": entity_path, "message": "Entity-Zeile ist kein Objekt"}
                )
            elif not entity.get("entity"):
                findings.append(
                    {"level": "error", "path": entity_path, "message": "Entity-Zeile ohne 'entity'"}
                )

    if model.get("screensaver") is not None:
        check_card(model["screensaver"], "screensaver")
    for index, card in enumerate(model.get("cards") or []):
        check_card(card, f"cards[{index}]")
    for index, card in enumerate(model.get("hiddenCards") or []):
        check_card(card, f"hiddenCards[{index}]")

    global_settings = model.get("global") or {}
    panel_model = global_settings.get("model")
    if panel_model is not None and panel_model not in MODELS:
        findings.append(
            {"level": "warning", "path": "global.model", "message": f"Unbekanntes Panel-Modell '{panel_model}'"}
        )
    return findings
