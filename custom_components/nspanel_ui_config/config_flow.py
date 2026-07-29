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
)
from .install_profile import (
    async_detect_profile,
    profile_defaults,
    profile_reload_fields,
    profile_reload_modes,
)

# **Nur zeigen, was hier laufen kann.** Welcher Reload-Weg auf der erkannten Installationsart
# überhaupt funktioniert, steht in `install_profile.PROFILE_RELOAD_MODES`; das Formular bietet nur
# diese an und blendet die Textfelder der übrigen aus. Ein Weg, den es auf diesem System nicht gibt,
# ist keine Wahlmöglichkeit, sondern eine Falle: Man stellt ihn ein, das Generieren meldet nichts,
# und am Panel ändert sich trotzdem nichts.
#
# Abhängig von der *gerade getroffenen* Auswahl lässt sich ein Feld nicht ein- oder ausblenden — HAs
# Formulare kennen keine solche Abhängigkeit ohne zweiten Schritt. Die Installationsart steht aber
# schon vor dem Öffnen fest, und genau daran hängt die Auswahl hier.


def _schema(werte: dict[str, Any], modi: list[str]) -> vol.Schema:
    """Formular für Einrichtung und Optionen – gleiche Felder, gefiltert nach Installationsart."""
    felder: dict[Any, Any] = {
        vol.Required(CONF_OUTPUT_PATH, default=werte[CONF_OUTPUT_PATH]): str,
        vol.Required(CONF_RELOAD_MODE, default=werte[CONF_RELOAD_MODE]): vol.In(modi),
    }
    for feld in profile_reload_fields(modi):
        felder[vol.Optional(feld, default=werte[feld])] = str
    felder[vol.Optional(CONF_IMPORT_YAML_PATH, default=werte[CONF_IMPORT_YAML_PATH])] = str
    felder[vol.Optional(CONF_BACKUP_COUNT, default=werte[CONF_BACKUP_COUNT])] = vol.All(
        vol.Coerce(int), vol.Range(min=0, max=100)
    )
    return vol.Schema(felder)


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
            data_schema=_schema(werte, profile_reload_modes(profile)),
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

        # Der gespeicherte Modus kommt mit in die Auswahl, auch wenn er nicht zum Profil passt —
        # nach einem Umzug ließe sich der Dialog sonst nicht einmal mehr öffnen.
        modi = profile_reload_modes(profile, werte[CONF_RELOAD_MODE])

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(werte, modi),
            description_placeholders={
                "installation": installation_type or vorgabe["label"],
                "hinweis": vorgabe["hint"],
            },
        )
