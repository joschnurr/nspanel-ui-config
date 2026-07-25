"""Datenmodell / Schema der nspanel-lovelace-ui-Konfiguration.

Abgeleitet aus ``luibackend/config.py`` (joBr99) und docs.nspanel.pky.eu. Dieses Modul beschreibt
die *Struktur* der Zielkonfiguration deklarativ, damit Editor (Frontend), Import und Generator sich
auf eine gemeinsame Definition stützen. Noch bewusst schlank – wird mit den Kartentypen erweitert.
"""

from __future__ import annotations

from typing import Final

# Kartentypen des Upstream-Backends. MVP-Priorität: cardEntities, cardGrid.
CARD_TYPES: Final[tuple[str, ...]] = (
    "cardEntities",
    "cardGrid",
    "cardThermo",
    "cardMedia",
    "cardAlarm",
    "cardQR",
    "cardPower",
    "cardUnlock",
)

# Panel-Modelle.
MODELS: Final[tuple[str, ...]] = ("eu", "us-l", "us-p")

# Felder einer Entity-Zeile (aus config.py: class Entity).
ENTITY_FIELDS: Final[tuple[str, ...]] = (
    "entity",          # entity_id oder Spezial-Präfix (iText., navigate., …)
    "name",            # Anzeigename (nameOverride)
    "icon",            # mdi-Icon; kann {on, off} sein
    "color",           # RGB-Liste [r,g,b] oder Jinja-Template
    "value",           # angezeigter Wert / Template
    "type",            # stype (z. B. input_select, button …)
    "state",           # condState
    "state_not",       # condStateNot
    "state_template",  # condTemplate
    "status",          # zusätzliche Status-Entity
    "font",            # Font-Override
    "data",            # freies dict für kartentyp-spezifische Extras
)

# Globale Settings mit Defaults (Teilmenge von _DEFAULT_CONFIG in config.py).
GLOBAL_DEFAULTS: Final[dict[str, object]] = {
    "model": "eu",
    "updateMode": "auto-notify",
    "sleepTimeout": 20,
    "sleepBrightness": 20,
    "screenBrightness": 100,
    "locale": "de_DE",
    "timeFormat": "%H:%M",
    "dateFormat": "%A, %d. %B %Y",
    "defaultBackgroundColor": "ha-dark",
}


def empty_model() -> dict[str, object]:
    """Leeres, aber strukturell gültiges Ausgangsmodell für einen frischen Editor."""
    return {
        "global": dict(GLOBAL_DEFAULTS),
        "screensaver": {"type": "screensaver2", "entities": []},
        "cards": [],
        "hiddenCards": [],
    }
