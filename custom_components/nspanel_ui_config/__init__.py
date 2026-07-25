"""NSPanel UI Config – Konfigurations-Schicht für nspanel-lovelace-ui (AppDaemon).

Diese Integration erzeugt aus einem in HA gepflegten Modell die nspanel-YAML und stellt sie dem
bestehenden AppDaemon-Backend bereit. Das Rendering-Backend selbst wird NICHT ersetzt.

Stand v0.1: Panel-Registrierung, HA-Store-Persistenz und HTTP-API-Gerüst. Import/Generator/Editor
sind als klar markierte Stubs angelegt und werden schrittweise ausgebaut.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL_PATH,
    STATIC_URL_BASE,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .http_api import async_register_http_api

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Richte die Integration für einen Config-Entry ein."""
    domain_data = hass.data.setdefault(DOMAIN, {})

    # Persistiertes Config-Modell laden (JSON via HA-Store).
    store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    model = await store.async_load() or {}
    domain_data[entry.entry_id] = {"store": store, "model": model, "options": dict(entry.options)}

    # Statische Panel-Assets ausliefern.
    www_dir = Path(__file__).parent / "www"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL_BASE, str(www_dir), cache_headers=False)]
    )

    # Sidebar-Panel registrieren (MVP: iFrame auf statische Assets).
    frontend.async_register_built_in_panel(
        hass,
        component_name="iframe",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path=PANEL_URL_PATH,
        config={"url": f"{STATIC_URL_BASE}/panel/index.html"},
        require_admin=True,
    )

    # Authentifizierte HTTP-API (Modell laden/speichern, Generieren).
    async_register_http_api(hass)

    entry.async_on_unload(entry.add_update_listener(_async_update_options))
    _LOGGER.info("NSPanel UI Config eingerichtet (Panel unter /%s)", PANEL_URL_PATH)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Entlade den Config-Entry und räume das Panel ab."""
    frontend.async_remove_panel(hass, PANEL_URL_PATH)
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Übernehme geänderte Optionen ohne vollständiges Reload."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if data is not None:
        data["options"] = dict(entry.options)
