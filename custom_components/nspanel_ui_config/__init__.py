"""NSPanel UI Config – Konfigurations-Schicht für nspanel-lovelace-ui (AppDaemon).

Diese Integration erzeugt aus einem in HA gepflegten Modell die nspanel-YAML und stellt sie dem
bestehenden AppDaemon-Backend bereit. Das Rendering-Backend selbst wird NICHT ersetzt.

Stand v0.6: verlustfreier Import/Generator-Round-Trip (``importer.py``/``generator.py``, abgesichert
in ``tests/test_roundtrip.py``), HA-Store-Persistenz, HTTP-API, ein visueller Editor als
Custom-Panel (``www/panel/``), das seine Formulare aus ``schema.py`` aufbaut, und der Reload des
Backends nach dem Generieren (``reload.py`` — AppDaemon merkt eine geänderte Include-Datei nicht
von selbst).
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
    PANEL_ELEMENT_NAME,
    PANEL_ICON,
    PANEL_MODULE_URL,
    PANEL_TITLE,
    PANEL_URL_PATH,
    STATIC_URL_BASE,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from . import live
from .http_api import async_register_http_api
from .panel_assets import panel_kennung

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

    # Version und Dateistand kommen von der Platte, nicht aus HAs Integrations-Zwischenspeicher —
    # sonst zeigt die Adresse nach einem Dateiaustausch weiter auf die alte Fassung
    # (siehe panel_assets.py). `stat`/`read_text` blockieren, gehören also in den Executor.
    kennung = await hass.async_add_executor_job(panel_kennung, Path(__file__).parent)

    # Sidebar-Panel als Custom-Element registrieren. Anders als ein iFrame-Panel bekommt es das
    # `hass`-Objekt gesetzt — nur damit sind die authentifizierte API und `hass.states` (für den
    # Entity-Picker) aus dem Panel heraus erreichbar.
    module_url = f"{PANEL_MODULE_URL}?{kennung}"
    frontend.async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path=PANEL_URL_PATH,
        config={
            "_panel_custom": {
                "name": PANEL_ELEMENT_NAME,
                "module_url": module_url,
                "embed_iframe": False,
                "trust_external": False,
            }
        },
        require_admin=True,
    )

    # Authentifizierte HTTP-API (Modell laden/speichern, Generieren).
    async_register_http_api(hass)

    # Mitschnitt dessen, was das Backend ans Display schickt — nur lesend und nur, wenn Home
    # Assistant MQTT hat und im Modell ein Sende-Topic steht. Schlägt es fehl, ist das kein Grund,
    # die Integration nicht zu laden: der Editor funktioniert auch ohne Live-Bild.
    unsub_live = await live.async_start(hass, domain_data[entry.entry_id])
    if unsub_live is not None:
        domain_data[entry.entry_id]["live_unsub"] = unsub_live
        entry.async_on_unload(unsub_live)

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
