"""Authentifizierte HTTP-API für das Panel.

Endpunkte:
  GET  /api/nspanel_ui_config/config    → aktuelles Config-Modell (JSON)
  POST /api/nspanel_ui_config/config    → Modell speichern (JSON)
  POST /api/nspanel_ui_config/generate  → YAML erzeugen und in den Ausgabepfad schreiben
"""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import API_CONFIG, API_GENERATE, CONF_OUTPUT_PATH, DOMAIN
from .generator import write_config_yaml

_LOGGER = logging.getLogger(__name__)


def async_register_http_api(hass: HomeAssistant) -> None:
    """Registriere die API-Views (idempotent genug für einen einzelnen Entry)."""
    hass.http.register_view(NsPanelConfigView(hass))
    hass.http.register_view(NsPanelGenerateView(hass))


def _first_entry_data(hass: HomeAssistant) -> dict[str, Any] | None:
    """Liefere die Datenablage des (einzigen) Config-Entrys."""
    for data in hass.data.get(DOMAIN, {}).values():
        return data
    return None


class NsPanelConfigView(HomeAssistantView):
    """Lädt und speichert das interne Config-Modell."""

    url = API_CONFIG
    name = "api:nspanel_ui_config:config"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request: web.Request) -> web.Response:
        data = _first_entry_data(self.hass)
        if data is None:
            return self.json_message("Integration nicht eingerichtet", HTTPStatus_400)
        return self.json(data.get("model", {}))

    async def post(self, request: web.Request) -> web.Response:
        data = _first_entry_data(self.hass)
        if data is None:
            return self.json_message("Integration nicht eingerichtet", HTTPStatus_400)
        try:
            model = await request.json()
        except ValueError:
            return self.json_message("Ungültiges JSON", HTTPStatus_400)
        data["model"] = model
        await data["store"].async_save(model)
        return self.json({"ok": True})


class NsPanelGenerateView(HomeAssistantView):
    """Erzeugt die nspanel-YAML aus dem Modell und schreibt sie in den Ausgabepfad."""

    url = API_GENERATE
    name = "api:nspanel_ui_config:generate"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def post(self, request: web.Request) -> web.Response:
        data = _first_entry_data(self.hass)
        if data is None:
            return self.json_message("Integration nicht eingerichtet", HTTPStatus_400)
        output_path = data["options"].get(CONF_OUTPUT_PATH)
        try:
            written = await self.hass.async_add_executor_job(
                write_config_yaml, data.get("model", {}), output_path
            )
        except OSError as err:
            _LOGGER.error("Schreiben der nspanel-YAML fehlgeschlagen: %s", err)
            return self.json_message(f"Schreiben fehlgeschlagen: {err}", HTTPStatus_500)
        return self.json({"ok": True, "path": written})


# HA liefert http.HTTPStatus über aiohttp; kleine lokale Aliase halten die Views schlank.
HTTPStatus_400 = 400
HTTPStatus_500 = 500
