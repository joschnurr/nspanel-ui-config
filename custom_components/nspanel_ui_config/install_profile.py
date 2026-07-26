"""Installationsart erkennen und die Einrichtung passend vorbelegen.

**Warum es das braucht.** Home Assistant und AppDaemon zusammenzubringen sieht je nach
Installationsart völlig anders aus — und die erste Fassung dieser Integration setzte unausgesprochen
eine Docker-Installation voraus (getrennte Volumes, selbst gelegter Bind-Mount, Docker-Socket für
den Reload). Für Home Assistant OS ist das schlicht falsch: dort läuft AppDaemon als Add-on, es gibt
keinen Docker-Socket, und einen Mount muss man auch nicht anlegen — das Add-on sieht ``/share``
ohnehin. Bei einer Core-Installation (venv) liegen beide sogar im selben Dateisystem.

Wer im Einrichtungsdialog nach einem Bind-Mount gefragt wird, den es in seiner Welt gar nicht gibt,
kommt nicht weit. Dieses Modul liefert deshalb je Installationsart ein Profil aus sinnvollen
Vorgaben und einem erklärenden Satz. **Nichts davon ist erzwungen** — alle Felder bleiben frei
editierbar, das Profil setzt nur die Vorbelegung.

Die Erkennung kommt aus Home Assistants eigenem ``async_get_system_info`` (``installation_type``),
also derselben Angabe, die auch unter *Einstellungen → System → Reparaturen → Systeminformationen*
steht.
"""

from __future__ import annotations

from typing import Any, Final, TYPE_CHECKING

from .const import (
    DEFAULT_RELOAD_ADDON,
    DEFAULT_RELOAD_CONTAINER,
    RELOAD_MODE_ADDON,
    RELOAD_MODE_NONE,
    RELOAD_MODE_TOUCH,
)

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.core import HomeAssistant

# Schlüssel der Profile. Bewusst gröber als HAs installation_type: OS und Supervised verhalten sich
# für unsere Zwecke gleich (beide haben einen Supervisor und Add-ons).
PROFILE_ADDON: Final = "addon"
PROFILE_CONTAINER: Final = "container"
PROFILE_CORE: Final = "core"
PROFILE_UNKNOWN: Final = "unknown"

# Zuordnung von HAs installation_type auf unsere Profile.
_BY_INSTALLATION_TYPE: Final[dict[str, str]] = {
    "Home Assistant OS": PROFILE_ADDON,
    "Home Assistant Supervised": PROFILE_ADDON,
    "Home Assistant Container": PROFILE_CONTAINER,
    "Unsupported Third Party Container": PROFILE_CONTAINER,
    "Home Assistant Core": PROFILE_CORE,
}

PROFILES: Final[dict[str, dict[str, Any]]] = {
    PROFILE_ADDON: {
        "label": "Home Assistant OS / Supervised (AppDaemon als Add-on)",
        # /share ist der einzige Ort, den HA und das AppDaemon-Add-on unter *demselben* Pfad sehen
        # (das Add-on hat share:rw). HAs eigene Konfiguration sieht das Add-on zwar auch, aber unter
        # /homeassistant statt /config — das führt beim Einrichten zuverlässig in die Irre.
        "output_path": "/share/nspanel/nspanel_config.yaml",
        "reload_mode": RELOAD_MODE_ADDON,
        "reload_addon": DEFAULT_RELOAD_ADDON,
        "reload_container": "",
        "reload_touch_path": "",
        "hint": (
            "AppDaemon läuft als Add-on. Ein eigener Mount ist nicht nötig: Das Add-on sieht "
            "/share unter demselben Pfad wie Home Assistant. In der apps.yaml des Add-ons "
            "dieselbe Zeile eintragen: config: !include /share/nspanel/nspanel_config.yaml"
        ),
    },
    PROFILE_CONTAINER: {
        "label": "Home Assistant Container (Docker/Compose)",
        "output_path": "/nspanel-shared/nspanel_config.yaml",
        "reload_mode": RELOAD_MODE_NONE,
        "reload_addon": "",
        "reload_container": DEFAULT_RELOAD_CONTAINER,
        "reload_touch_path": "",
        "hint": (
            "Home Assistant und AppDaemon laufen in getrennten Containern ohne gemeinsamen Pfad. "
            "Einmalig denselben Host-Ordner in beide Container mounten (z. B. /nspanel-shared) "
            "und in der apps.yaml eintragen: config: !include /nspanel-shared/nspanel_config.yaml"
        ),
    },
    PROFILE_CORE: {
        "label": "Home Assistant Core (venv/pip)",
        # Alles liegt im selben Dateisystem – der Pfad ist frei wählbar, HAs Konfigurationsordner
        # ist der naheliegende Ort.
        "output_path": "/config/nspanel_config.yaml",
        "reload_mode": RELOAD_MODE_TOUCH,
        "reload_addon": "",
        "reload_container": "",
        "reload_touch_path": "",
        "hint": (
            "Home Assistant und AppDaemon teilen sich das Dateisystem, ein Mount entfällt. Der "
            "Ausgabepfad ist frei wählbar; unter „Datei zum Anticken“ AppDaemons App-Modul "
            "angeben (z. B. /home/appdaemon/conf/apps/apps.yaml – es muss die apps.yaml sein), dann lädt AppDaemon nur diese "
            "eine App neu."
        ),
    },
    PROFILE_UNKNOWN: {
        "label": "Installationsart nicht erkannt",
        "output_path": "/share/nspanel/nspanel_config.yaml",
        "reload_mode": RELOAD_MODE_NONE,
        "reload_addon": "",
        "reload_container": "",
        "reload_touch_path": "",
        "hint": (
            "Die Installationsart ließ sich nicht bestimmen. Maßgeblich ist, dass Home Assistant "
            "und AppDaemon dieselbe Datei sehen – der Pfad gilt aus Sicht von Home Assistant."
        ),
    },
}


def profile_for_installation_type(installation_type: Any) -> str:
    """Ordne HAs ``installation_type`` einem Profil zu."""
    if not isinstance(installation_type, str):
        return PROFILE_UNKNOWN
    return _BY_INSTALLATION_TYPE.get(installation_type, PROFILE_UNKNOWN)


def profile_defaults(profile: str) -> dict[str, Any]:
    """Vorbelegung für ein Profil (Kopie, damit Aufrufer sie gefahrlos verändern können)."""
    return dict(PROFILES.get(profile, PROFILES[PROFILE_UNKNOWN]))


async def async_detect_profile(hass: HomeAssistant) -> tuple[str, str]:
    """Ermittle Profil und die von Home Assistant gemeldete Installationsart.

    Schlägt die Abfrage fehl, wird das nicht zum Problem gemacht: dann greift schlicht das
    Unbekannt-Profil, und der Anwender füllt die Felder selbst aus.
    """
    try:
        from homeassistant.helpers.system_info import async_get_system_info

        info = await async_get_system_info(hass)
        installation_type = info.get("installation_type", "")
    except Exception:  # noqa: BLE001 – eine misslungene Erkennung darf die Einrichtung nicht blockieren
        return PROFILE_UNKNOWN, ""
    return profile_for_installation_type(installation_type), installation_type
