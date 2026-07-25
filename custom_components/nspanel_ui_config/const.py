"""Konstanten für die NSPanel UI Config Integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "nspanel_ui_config"

# Config-Entry-Optionen
CONF_OUTPUT_PATH: Final = "output_path"
CONF_RELOAD_MODE: Final = "reload_mode"
CONF_IMPORT_YAML_PATH: Final = "import_yaml_path"

# Reload-Strategien für das AppDaemon-Backend (siehe docs/architecture.md#reload-trigger)
RELOAD_MODE_NONE: Final = "none"
RELOAD_MODE_TOUCH: Final = "touch_module"
RELOAD_MODE_RESTART: Final = "restart_container"
RELOAD_MODES: Final = [RELOAD_MODE_NONE, RELOAD_MODE_TOUCH, RELOAD_MODE_RESTART]

# Voreinstellungen
DEFAULT_OUTPUT_PATH: Final = "/nspanel-shared/nspanel_config.yaml"
DEFAULT_RELOAD_MODE: Final = RELOAD_MODE_NONE

# HA-Store (Persistenz des internen Config-Modells)
STORAGE_KEY: Final = f"{DOMAIN}.model"
STORAGE_VERSION: Final = 1

# Panel / Frontend
PANEL_URL_PATH: Final = "nspanel-ui-config"
PANEL_TITLE: Final = "NSPanel UI"
PANEL_ICON: Final = "mdi:cellphone-cog"
STATIC_URL_BASE: Final = "/nspanel_ui_config_static"

# HTTP-API-Pfade (authentifiziert)
API_CONFIG: Final = "/api/nspanel_ui_config/config"
API_GENERATE: Final = "/api/nspanel_ui_config/generate"
