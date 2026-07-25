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
