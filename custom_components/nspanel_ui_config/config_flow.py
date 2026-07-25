"""Config- und Options-Flow für NSPanel UI Config."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback

from .const import (
    CONF_IMPORT_YAML_PATH,
    CONF_OUTPUT_PATH,
    CONF_RELOAD_CONTAINER,
    CONF_RELOAD_MODE,
    CONF_RELOAD_TOUCH_PATH,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_RELOAD_CONTAINER,
    DEFAULT_RELOAD_MODE,
    DOMAIN,
    RELOAD_MODES,
)

# Die beiden Reload-Felder gehören jeweils nur zu einem Modus; sie stehen bewusst trotzdem immer im
# Formular, weil HAs Options-Flow keine abhängigen Felder ohne zweiten Schritt kann — und ein
# zweiter Schritt wäre für zwei Textfelder mehr Umweg als Gewinn.
_STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_OUTPUT_PATH, default=DEFAULT_OUTPUT_PATH): str,
        vol.Required(CONF_RELOAD_MODE, default=DEFAULT_RELOAD_MODE): vol.In(RELOAD_MODES),
        vol.Optional(CONF_RELOAD_TOUCH_PATH, default=""): str,
        vol.Optional(CONF_RELOAD_CONTAINER, default=DEFAULT_RELOAD_CONTAINER): str,
        vol.Optional(CONF_IMPORT_YAML_PATH, default=""): str,
    }
)


class NsPanelUiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Erst-Einrichtung. Ein einzelner Entry genügt (ein Konfigurator pro HA)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Fragt Ausgabepfad, Reload-Weg und optionalen Import ab."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title="NSPanel UI Config",
                data={},
                options={
                    CONF_OUTPUT_PATH: user_input[CONF_OUTPUT_PATH],
                    CONF_RELOAD_MODE: user_input[CONF_RELOAD_MODE],
                    CONF_RELOAD_TOUCH_PATH: user_input.get(CONF_RELOAD_TOUCH_PATH, ""),
                    CONF_RELOAD_CONTAINER: user_input.get(
                        CONF_RELOAD_CONTAINER, DEFAULT_RELOAD_CONTAINER
                    ),
                    CONF_IMPORT_YAML_PATH: user_input.get(CONF_IMPORT_YAML_PATH, ""),
                },
            )

        return self.async_show_form(step_id="user", data_schema=_STEP_USER_SCHEMA)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return NsPanelUiConfigOptionsFlow()


class NsPanelUiConfigOptionsFlow(OptionsFlow):
    """Nachträgliche Änderung von Ausgabepfad, Reload-Weg und Importpfad."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        current = self.config_entry.options

        if user_input is not None:
            # Bestehende Optionen zusammenführen statt ersetzen: async_create_entry schreibt das
            # übergebene Dict vollständig zurück. Wird das Formular je um einen Key erweitert oder
            # verkleinert, verschwänden sonst genau die Optionen, die es gerade nicht anzeigt.
            return self.async_create_entry(title="", data={**current, **user_input})

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_OUTPUT_PATH,
                    default=current.get(CONF_OUTPUT_PATH, DEFAULT_OUTPUT_PATH),
                ): str,
                vol.Required(
                    CONF_RELOAD_MODE,
                    default=current.get(CONF_RELOAD_MODE, DEFAULT_RELOAD_MODE),
                ): vol.In(RELOAD_MODES),
                vol.Optional(
                    CONF_RELOAD_TOUCH_PATH,
                    default=current.get(CONF_RELOAD_TOUCH_PATH, ""),
                ): str,
                vol.Optional(
                    CONF_RELOAD_CONTAINER,
                    default=current.get(CONF_RELOAD_CONTAINER, DEFAULT_RELOAD_CONTAINER),
                ): str,
                vol.Optional(
                    CONF_IMPORT_YAML_PATH,
                    default=current.get(CONF_IMPORT_YAML_PATH, ""),
                ): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
