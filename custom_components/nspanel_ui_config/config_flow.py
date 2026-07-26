"""Config- und Options-Flow für NSPanel UI Config.

Der Einrichtungsdialog richtet sich nach der **Installationsart**: bei Home Assistant OS läuft
AppDaemon als Add-on und wird über den Supervisor neu gestartet, bei einer Container-Installation
sind es zwei Docker-Container mit getrennten Volumes, bei Core teilen sich beide das Dateisystem.
Die Vorgaben unterscheiden sich entsprechend — siehe ``install_profile.py``. Erkannt wird die Art
über Home Assistants ``installation_type``; die Felder bleiben trotzdem frei editierbar, damit
ungewöhnliche Aufbauten nicht ausgesperrt sind.
"""

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
    CONF_BACKUP_COUNT,
    CONF_IMPORT_YAML_PATH,
    CONF_OUTPUT_PATH,
    CONF_RELOAD_ADDON,
    CONF_RELOAD_CONTAINER,
    CONF_RELOAD_MODE,
    CONF_RELOAD_TOUCH_PATH,
    DEFAULT_BACKUP_COUNT,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_RELOAD_ADDON,
    DEFAULT_RELOAD_CONTAINER,
    DEFAULT_RELOAD_MODE,
    DOMAIN,
    RELOAD_MODES,
)
from .install_profile import async_detect_profile, profile_defaults

# Die Reload-Felder gehören jeweils nur zu einem Modus; sie stehen bewusst trotzdem alle im
# Formular, weil HAs Options-Flow keine abhängigen Felder ohne zweiten Schritt kann — und ein
# zweiter Schritt wäre für drei Textfelder mehr Umweg als Gewinn. Die Vorbelegung sorgt dafür, dass
# das zur Installationsart passende Feld gefüllt ist und die anderen leer bleiben.


def _schema(werte: dict[str, Any]) -> vol.Schema:
    """Formular für Einrichtung und Optionen – identische Felder, nur andere Vorbelegung."""
    return vol.Schema(
        {
            vol.Required(CONF_OUTPUT_PATH, default=werte[CONF_OUTPUT_PATH]): str,
            vol.Required(CONF_RELOAD_MODE, default=werte[CONF_RELOAD_MODE]): vol.In(RELOAD_MODES),
            vol.Optional(CONF_RELOAD_ADDON, default=werte[CONF_RELOAD_ADDON]): str,
            vol.Optional(CONF_RELOAD_TOUCH_PATH, default=werte[CONF_RELOAD_TOUCH_PATH]): str,
            vol.Optional(CONF_RELOAD_CONTAINER, default=werte[CONF_RELOAD_CONTAINER]): str,
            vol.Optional(CONF_IMPORT_YAML_PATH, default=werte[CONF_IMPORT_YAML_PATH]): str,
            vol.Optional(CONF_BACKUP_COUNT, default=werte[CONF_BACKUP_COUNT]): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=100)
            ),
        }
    )


def _options_from_input(user_input: dict[str, Any]) -> dict[str, Any]:
    return {
        CONF_OUTPUT_PATH: user_input[CONF_OUTPUT_PATH],
        CONF_RELOAD_MODE: user_input[CONF_RELOAD_MODE],
        CONF_RELOAD_ADDON: user_input.get(CONF_RELOAD_ADDON, ""),
        CONF_RELOAD_TOUCH_PATH: user_input.get(CONF_RELOAD_TOUCH_PATH, ""),
        CONF_RELOAD_CONTAINER: user_input.get(CONF_RELOAD_CONTAINER, ""),
        CONF_IMPORT_YAML_PATH: user_input.get(CONF_IMPORT_YAML_PATH, ""),
        CONF_BACKUP_COUNT: user_input.get(CONF_BACKUP_COUNT, DEFAULT_BACKUP_COUNT),
    }


class NsPanelUiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Erst-Einrichtung. Ein einzelner Entry genügt (ein Konfigurator pro HA)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Fragt Ausgabepfad, Reload-Weg und optionalen Import ab – passend zur Installationsart."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title="NSPanel UI Config",
                data={},
                options=_options_from_input(user_input),
            )

        profile, installation_type = await async_detect_profile(self.hass)
        vorgabe = profile_defaults(profile)
        werte = {
            CONF_OUTPUT_PATH: vorgabe["output_path"],
            CONF_RELOAD_MODE: vorgabe["reload_mode"],
            CONF_RELOAD_ADDON: vorgabe["reload_addon"],
            CONF_RELOAD_TOUCH_PATH: vorgabe["reload_touch_path"],
            CONF_RELOAD_CONTAINER: vorgabe["reload_container"],
            CONF_IMPORT_YAML_PATH: "",
            CONF_BACKUP_COUNT: DEFAULT_BACKUP_COUNT,
        }

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(werte),
            description_placeholders={
                # Erkannte Installationsart und der dazu passende Hinweis stehen über dem Formular,
                # damit man nicht raten muss, welches der Reload-Felder für einen gilt.
                "installation": installation_type or vorgabe["label"],
                "hinweis": vorgabe["hint"],
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return NsPanelUiConfigOptionsFlow()


class NsPanelUiConfigOptionsFlow(OptionsFlow):
    """Nachträgliche Änderung von Ausgabepfad, Reload-Weg, Importpfad und Sicherungstiefe."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        current = self.config_entry.options

        if user_input is not None:
            # Bestehende Optionen zusammenführen statt ersetzen: async_create_entry schreibt das
            # übergebene Dict vollständig zurück. Wird das Formular je um einen Key erweitert oder
            # verkleinert, verschwänden sonst genau die Optionen, die es gerade nicht anzeigt.
            return self.async_create_entry(title="", data={**current, **user_input})

        # Hier zählen die gespeicherten Werte, nicht das Profil – wer bewusst abweicht, soll seine
        # Einstellung wiederfinden. Das Profil liefert nur den erklärenden Text.
        profile, installation_type = await async_detect_profile(self.hass)
        vorgabe = profile_defaults(profile)
        werte = {
            CONF_OUTPUT_PATH: current.get(CONF_OUTPUT_PATH, DEFAULT_OUTPUT_PATH),
            CONF_RELOAD_MODE: current.get(CONF_RELOAD_MODE, DEFAULT_RELOAD_MODE),
            CONF_RELOAD_ADDON: current.get(CONF_RELOAD_ADDON, DEFAULT_RELOAD_ADDON),
            CONF_RELOAD_TOUCH_PATH: current.get(CONF_RELOAD_TOUCH_PATH, ""),
            CONF_RELOAD_CONTAINER: current.get(CONF_RELOAD_CONTAINER, DEFAULT_RELOAD_CONTAINER),
            CONF_IMPORT_YAML_PATH: current.get(CONF_IMPORT_YAML_PATH, ""),
            CONF_BACKUP_COUNT: current.get(CONF_BACKUP_COUNT, DEFAULT_BACKUP_COUNT),
        }

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(werte),
            description_placeholders={
                "installation": installation_type or vorgabe["label"],
                "hinweis": vorgabe["hint"],
            },
        )
