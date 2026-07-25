"""Authentifizierte HTTP-API für das Panel.

Endpunkte (alle nur für Admins):
  GET  /api/nspanel_ui_config/config    → aktuelles Config-Modell (JSON)
  POST /api/nspanel_ui_config/config    → Modell speichern (JSON)
  POST /api/nspanel_ui_config/import    → bestehende apps.yaml einlesen (Pfad oder Text)
  POST /api/nspanel_ui_config/generate  → YAML erzeugen und in den Ausgabepfad schreiben
"""

from __future__ import annotations

import logging
from http import HTTPStatus
from pathlib import Path
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import (
    API_CONFIG,
    API_GENERATE,
    API_IMPORT,
    CONF_IMPORT_YAML_PATH,
    CONF_OUTPUT_PATH,
    DOMAIN,
)
from .generator import write_config_yaml
from .importer import find_apps, parse_apps_yaml
from .schema import validate_model

_LOGGER = logging.getLogger(__name__)


def async_register_http_api(hass: HomeAssistant) -> None:
    """Registriere die API-Views (idempotent genug für einen einzelnen Entry)."""
    hass.http.register_view(NsPanelConfigView(hass))
    hass.http.register_view(NsPanelImportView(hass))
    hass.http.register_view(NsPanelGenerateView(hass))


def _first_entry_data(hass: HomeAssistant) -> dict[str, Any] | None:
    """Liefere die Datenablage des (einzigen) Config-Entrys."""
    for data in hass.data.get(DOMAIN, {}).values():
        return data
    return None


class _NsPanelView(HomeAssistantView):
    """Gemeinsame Basis: Admin-Prüfung und Zugriff auf die Entry-Daten.

    ``requires_auth`` allein prüft nur ein gültiges Token — diese Endpunkte schreiben aber
    Konfigurationsdateien, deshalb zusätzlich die Admin-Prüfung.
    """

    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    def _entry_data(self, request: web.Request) -> tuple[dict[str, Any] | None, web.Response | None]:
        user = request.get("hass_user")
        if user is None or not user.is_admin:
            return None, self.json_message("Nur für Administratoren", HTTPStatus.FORBIDDEN)
        data = _first_entry_data(self.hass)
        if data is None:
            return None, self.json_message("Integration nicht eingerichtet", HTTPStatus.BAD_REQUEST)
        return data, None


class NsPanelConfigView(_NsPanelView):
    """Lädt und speichert das interne Config-Modell."""

    url = API_CONFIG
    name = "api:nspanel_ui_config:config"

    async def get(self, request: web.Request) -> web.Response:
        data, error = self._entry_data(request)
        if error is not None:
            return error
        model = data.get("model", {})
        return self.json({"model": model, "findings": validate_model(model) if model else []})

    async def post(self, request: web.Request) -> web.Response:
        data, error = self._entry_data(request)
        if error is not None:
            return error
        try:
            model = await request.json()
        except ValueError:
            return self.json_message("Ungültiges JSON", HTTPStatus.BAD_REQUEST)
        if not isinstance(model, dict):
            return self.json_message("Modell muss ein Objekt sein", HTTPStatus.BAD_REQUEST)
        data["model"] = model
        await data["store"].async_save(model)
        return self.json({"ok": True, "findings": validate_model(model)})


class NsPanelImportView(_NsPanelView):
    """Liest eine bestehende apps.yaml ein und liefert das daraus abgeleitete Modell.

    Body: ``{"text": "<yaml>"}`` oder ``{"path": "/pfad/apps.yaml"}`` (ohne beides: der beim
    Einrichten hinterlegte Importpfad), optional ``{"app_name": "nspanel-1"}`` und
    ``{"save": true}``. Das Ergebnis wird nur auf Wunsch gespeichert — der Editor soll erst
    anzeigen können, was der Import ergeben hat.
    """

    url = API_IMPORT
    name = "api:nspanel_ui_config:import"

    async def post(self, request: web.Request) -> web.Response:
        data, error = self._entry_data(request)
        if error is not None:
            return error
        try:
            payload = await request.json()
        except ValueError:
            return self.json_message("Ungültiges JSON", HTTPStatus.BAD_REQUEST)
        if not isinstance(payload, dict):
            payload = {}

        text = payload.get("text")
        if not isinstance(text, str):
            path = payload.get("path") or data["options"].get(CONF_IMPORT_YAML_PATH)
            if not path:
                return self.json_message("Weder 'text' noch 'path' angegeben", HTTPStatus.BAD_REQUEST)
            # Der Pfad kommt aus dem Request – daher die HA-Allowlist (allowlist_external_dirs)
            # erzwingen, statt beliebige Dateien lesbar zu machen.
            if not self.hass.config.is_allowed_path(path):
                return self.json_message(
                    f"Pfad nicht freigegeben: {path} (allowlist_external_dirs in configuration.yaml)",
                    HTTPStatus.FORBIDDEN,
                )
            try:
                text = await self.hass.async_add_executor_job(
                    lambda: Path(path).read_text(encoding="utf-8")
                )
            except OSError as err:
                _LOGGER.error("apps.yaml konnte nicht gelesen werden (%s): %s", path, err)
                return self.json_message(f"Lesen fehlgeschlagen: {err}", HTTPStatus.BAD_REQUEST)

        try:
            apps = await self.hass.async_add_executor_job(find_apps, text)
            model = await self.hass.async_add_executor_job(
                parse_apps_yaml, text, payload.get("app_name")
            )
        except Exception as err:  # noqa: BLE001 – YAML-Fehler des Nutzers, nicht unserer
            _LOGGER.error("apps.yaml konnte nicht geparst werden: %s", err)
            return self.json_message(f"YAML nicht lesbar: {err}", HTTPStatus.BAD_REQUEST)

        if payload.get("save"):
            data["model"] = model
            await data["store"].async_save(model)

        return self.json(
            {
                "ok": True,
                "apps": apps,
                "model": model,
                "findings": validate_model(model),
                "saved": bool(payload.get("save")),
            }
        )


class NsPanelGenerateView(_NsPanelView):
    """Erzeugt die nspanel-YAML aus dem Modell und schreibt sie in den Ausgabepfad."""

    url = API_GENERATE
    name = "api:nspanel_ui_config:generate"

    async def post(self, request: web.Request) -> web.Response:
        data, error = self._entry_data(request)
        if error is not None:
            return error
        # Der Ausgabepfad stammt aus den Entry-Optionen (Admin-gesetzt), nicht aus dem Request.
        output_path = data["options"].get(CONF_OUTPUT_PATH)
        model = data.get("model", {})
        try:
            written = await self.hass.async_add_executor_job(write_config_yaml, model, output_path)
        except OSError as err:
            _LOGGER.error("Schreiben der nspanel-YAML fehlgeschlagen: %s", err)
            return self.json_message(f"Schreiben fehlgeschlagen: {err}", HTTPStatus.INTERNAL_SERVER_ERROR)
        return self.json({"ok": True, "path": written, "findings": validate_model(model)})
