"""Konstanten für die NSPanel UI Config Integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "nspanel_ui_config"

# Config-Entry-Optionen
CONF_OUTPUT_PATH: Final = "output_path"
CONF_RELOAD_MODE: Final = "reload_mode"
CONF_IMPORT_YAML_PATH: Final = "import_yaml_path"
CONF_RELOAD_TOUCH_PATH: Final = "reload_touch_path"
CONF_RELOAD_CONTAINER: Final = "reload_container"

# Reload-Strategien für das AppDaemon-Backend (siehe docs/architecture.md#reload-trigger und
# reload.py — dort steht, warum ein geänderter !include allein nichts auslöst).
RELOAD_MODE_NONE: Final = "none"
RELOAD_MODE_TOUCH: Final = "touch_module"
RELOAD_MODE_RESTART: Final = "restart_container"
RELOAD_MODES: Final = [RELOAD_MODE_NONE, RELOAD_MODE_TOUCH, RELOAD_MODE_RESTART]

# Docker-Engine-API für RELOAD_MODE_RESTART; der Socket muss im HA-Container liegen.
DOCKER_SOCKET: Final = "/var/run/docker.sock"

# Voreinstellungen
DEFAULT_OUTPUT_PATH: Final = "/nspanel-shared/nspanel_config.yaml"
DEFAULT_RELOAD_MODE: Final = RELOAD_MODE_NONE
DEFAULT_RELOAD_CONTAINER: Final = "appdaemon"

# HA-Store (Persistenz des internen Config-Modells)
STORAGE_KEY: Final = f"{DOMAIN}.model"
STORAGE_VERSION: Final = 1

# Panel / Frontend
PANEL_URL_PATH: Final = "nspanel-ui-config"
PANEL_TITLE: Final = "NSPanel UI"
PANEL_ICON: Final = "mdi:cellphone-cog"
STATIC_URL_BASE: Final = "/nspanel_ui_config_static"

# Custom-Panel: HA lädt dieses Modul und instanziiert darin das gleichnamige Custom-Element.
# Anders als ein iFrame-Panel bekommt es das `hass`-Objekt gesetzt — inklusive Auth-Token für die
# API und `hass.states` für den Entity-Picker.
PANEL_ELEMENT_NAME: Final = "nspanel-ui-config-panel"
PANEL_MODULE_URL: Final = f"{STATIC_URL_BASE}/panel/{PANEL_ELEMENT_NAME}.js"

# HTTP-API-Pfade (authentifiziert, nur für Admins)
API_CONFIG: Final = "/api/nspanel_ui_config/config"
API_GENERATE: Final = "/api/nspanel_ui_config/generate"
API_IMPORT: Final = "/api/nspanel_ui_config/import"
API_SCHEMA: Final = "/api/nspanel_ui_config/schema"
