"""Export des Modells als ``panels.yaml`` für das neue nspanel-lovelace-ui-Backend.

Seit v4.8.0 (25.10.2026) erklärt joBr99 das AppDaemon-Backend für abgekündigt; Nachfolger ist das
Home-Assistant-Add-on bzw. derselbe Code als eigenständiger Container
(``ghcr.io/jobr99/nspanel-lovelace-ui``). Der liest keine ``apps.yaml`` mehr, sondern eine
``panels.yaml`` mit der Struktur ``nspanels: {<name>: {…}}`` — fast dieselben Keys wie bisher, aber
nicht ganz. Dieses Modul schreibt das Modell des Editors in genau diese Form und sagt dabei, was
unterwegs verloren geht oder nachgearbeitet werden muss.

Jede Umsetzregel steht mit ihrem Beleg im Backend-Quelltext (Stand v4.8.4, Verzeichnis
``nspanel-lovelace-ui/rootfs/usr/bin/mqtt-manager/``) oder in dessen Doku (``docs/``), geprüft am
27.10.2026:

* Kartentypen: ``config_manager.py:14`` kennt ``cardEntities, cardGrid, cardQR, cardPower,
  cardMedia, cardThermo, cardAlarm, cardUnlock``. ``cardGrid2`` ist kein Typ mehr — ``cardGrid``
  schaltet ab 7 Einträgen von selbst um (``docs/cards.md:35``). ``cardChart`` gibt es dort nicht.
* ``navItem1``/``navItem2`` und ``cooldown`` kommen im neuen Backend nirgends vor (nur noch in
  ``docs/legacy-subpages.md``); sie würden nichts tun und fallen hier weg.
* Templates werden nur mit Präfix ``ha:`` ausgewertet — ``docs/entities.md`` „Template-based
  values": ``icon``, ``color``, ``value``, ``qrCode``; der Code dazu in ``ha_cards.py:81-86,307,390``.
* ``state``, ``state_not``, ``state_template``, ``action_name``, ``berryURL``,
  ``dateAdditionalTemplate``, ``timeAdditionalTemplate``: „retained, but unsupported by the add-on
  runtime" (``config_manager.py:196``). Bleiben stehen, wirken aber nicht.
* Helligkeitspläne: nur ``"HH:MM"``/``"HH:MM:SS"``, „Sunrise/sunset expressions are not
  supported" (``docs/config-migration-standalone.md:52``).
* Umbenennungen, wie sie der Importer des Backends selbst vornimmt (``config_manager.py``,
  ``import_yaml``): ``timezone``→``timeZone``, ``dateFormatBabel``→``dateFormat``,
  ``featureExperimentalSliders``→``featExperimentalSliders``, ``screensaver.defaultCard``→
  Panel-``defaultCard``, Karten-``temperatureUnit``→Panel-``temp_unit`` (gemischte Einheiten sind
  dort ein Fehler), ``supportedModes``→``supported_modes`` (``docs/cards.md``),
  ``screensaver.alternativeLayout: true``→``type: screensaver2`` (``config_manager.py:178``).
* Wetter: die Ruheanzeige kennt kein Legacy-``entity`` mehr, nur die explizite ``entities``-Liste
  mit ``attribute``/``day``/``hour`` (``docs/config-screensaver.md``); ``weatherUnit``,
  ``forecastSkip`` und ``weatherOverrideForecast*`` werden beibehalten, sollen aber geprüft werden
  (``config_manager.py:198``).

Die Verbindungsdaten (``home_assistant_address``/``_token``, ``mqtt_*``) gehören in die
``panels.yaml`` des neuen Backends, nicht in dieses Modell — sie stehen als auskommentierte
Platzhalter im Kopf der Datei, Geheimnisse schreibt der Editor nirgends hin.
"""

from __future__ import annotations

import copy
import re
from typing import Any

import yaml

from .generator import _ConfigDumper, _MAX_LINE_WIDTH, denormalize_card

# Kartentypen des neuen Backends (config_manager.py:14).
NEW_CARD_TYPES: tuple[str, ...] = (
    "cardEntities",
    "cardGrid",
    "cardQR",
    "cardPower",
    "cardMedia",
    "cardThermo",
    "cardAlarm",
    "cardUnlock",
)

# Globale Keys, die das neue Backend unter anderem Namen führt.
GLOBAL_RENAMES: dict[str, str] = {
    "timezone": "timeZone",
    "featureExperimentalSliders": "featExperimentalSliders",
}

# Keys, die das neue Backend zwar behält, aber nicht auswertet (config_manager.py:196).
RETAINED_UNSUPPORTED: frozenset[str] = frozenset(
    {"berryURL", "dateAdditionalTemplate", "timeAdditionalTemplate", "state", "state_not",
     "state_template", "action_name"}
)

# Wetter-Keys, die beibehalten werden, aber nach der Migration geprüft werden sollen.
WEATHER_REVIEW_KEYS: frozenset[str] = frozenset({"weatherUnit", "forecastSkip"})

# Felder, in denen das neue Backend Templates nur mit Präfix ``ha:`` rendert.
TEMPLATE_PREFIX_FIELDS: tuple[str, ...] = ("icon", "color", "value", "qrCode")

# Reihenfolge der Panel-Keys in der Ausgabe (docs/config-overview.md), Unbekanntes folgt dahinter.
PANEL_FIELD_ORDER: tuple[str, ...] = (
    "panelRecvTopic", "panelSendTopic", "locale", "timeZone", "timeFormat", "dateFormat",
    "model", "temp_unit", "updateMode", "sleepTimeout", "sleepBrightness", "screenBrightness",
    "sleepTracking", "sleepTrackingZones", "sleepOverride", "defaultBackgroundColor",
    "featExperimentalSliders", "defaultCard",
)

# Ersatzzeiten für sunrise/sunset – bewusst grob, damit der Hinweis nicht überlesen wird.
SUN_FALLBACK: dict[str, str] = {"sunrise": "07:00", "sunset": "19:00"}

_TEMPLATE_RE = re.compile(r"\{\{|\{%")
_TIME_RE = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")

_HEADER = (
    "# panels.yaml – erzeugt von der Home-Assistant-Integration 'NSPanel UI Config'\n"
    "# für das nspanel-lovelace-ui-Add-on bzw. den Standalone-Container (ab v4.8.0).\n"
    "#\n"
    "# Verbindungsdaten gehören hier dazu, der Editor kennt sie nicht – bitte ergänzen:\n"
    "# home_assistant_address: http://homeassistant.local:8123\n"
    "# home_assistant_token: <langlebiges Zugriffstoken>\n"
    "# mqtt_server: 192.168.1.10\n"
    "# mqtt_port: 1883\n"
    "# mqtt_username: <optional>\n"
    "# mqtt_password: <optional>\n"
)


def _is_template(value: Any) -> bool:
    return isinstance(value, str) and bool(_TEMPLATE_RE.search(value))


def _prefix_template(value: Any) -> Any:
    """``ha:`` davor, falls der Wert ein Template ist und das Präfix noch fehlt.

    Ein Wert wie ``<I>mdi:…</I> ha:{{ … }}`` (Status-Symbol mit Icon und Text) trägt das Präfix
    schon mitten im String — der bleibt unangetastet, sonst käme ein zweites davor.
    """
    if _is_template(value) and "ha:" not in value:
        return "ha:" + value
    return value


class _Export:
    """Ein Exportlauf: sammelt Hinweise, während das Modell umgebaut wird."""

    def __init__(self, panel_name: str) -> None:
        self.panel_name = panel_name
        self.warnings: list[str] = []
        self.temp_units: set[str] = set()

    def warn(self, text: str) -> None:
        if text not in self.warnings:
            self.warnings.append(text)

    # --- Entities -------------------------------------------------------------------------

    def entity(self, entity: Any, wo: str) -> Any:
        if not isinstance(entity, dict):
            return entity
        out = dict(entity)
        for field in TEMPLATE_PREFIX_FIELDS:
            if field in out:
                out[field] = self._prefix_field(out[field])
        if _is_template(out.get("name")):
            self.warn(
                f"{wo}: Template im Feld 'name' ({out.get('entity')}) – das neue Backend rendert "
                "Templates nur in icon, color, value und qrCode; der Name erscheint wörtlich."
            )
        for key in sorted(RETAINED_UNSUPPORTED & set(out)):
            self.warn(
                f"{wo}: '{key}' an {out.get('entity')} bleibt stehen, wird im neuen Backend aber "
                "nicht ausgewertet (bedingte Sichtbarkeit gibt es dort nicht)."
            )
        if isinstance(out.get("entity"), str) and out["entity"].startswith("service."):
            self.warn(
                f"{wo}: Service-Eintrag '{out['entity']}' – das neue Backend kennt keine "
                "service.-Einträge, bitte durch ein Skript oder einen Button ersetzen."
            )
        return out

    def _prefix_field(self, value: Any) -> Any:
        # icon/color dürfen ein {on, off}-Mapping sein; darin können wieder Templates stehen.
        if isinstance(value, dict):
            return {k: _prefix_template(v) for k, v in value.items()}
        return _prefix_template(value)

    # --- Karten ---------------------------------------------------------------------------

    def card(self, card: Any, wo: str, screensaver: bool = False) -> Any:
        if not isinstance(card, dict):
            return card
        raw = denormalize_card(card)
        out: dict[str, Any] = {}
        typ = raw.get("type")
        titel = raw.get("title") or raw.get("key") or typ
        stelle = f"{wo} „{titel}“"

        for key, value in raw.items():
            if key == "type" and not screensaver:
                if value == "cardGrid2":
                    value = "cardGrid"
                    self.warn(
                        f"{stelle}: Typ cardGrid2 → cardGrid; das neue Backend schaltet ab 7 "
                        "Einträgen von selbst auf das Grid2-Layout."
                    )
                elif value not in NEW_CARD_TYPES:
                    self.warn(
                        f"{stelle}: Kartentyp '{value}' gibt es im neuen Backend nicht – die Karte "
                        "wird dort abgelehnt und muss entfernt oder ersetzt werden."
                    )
            if key in ("navItem1", "navItem2"):
                self.warn(
                    f"{stelle}: '{key}' entfällt – eigene Blättertasten kennt das neue Backend nicht."
                )
                continue
            if key == "cooldown":
                self.warn(f"{stelle}: 'cooldown' entfällt – im neuen Backend ohne Wirkung.")
                continue
            if key == "temperatureUnit":
                self.temp_units.add(str(value))
                continue
            if key == "supportedModes":
                key = "supported_modes"
            if key == "qrCode":
                value = _prefix_template(value)
            if key in ("statusIcon1", "statusIcon2"):
                value = self.entity(value, f"{stelle} {key}")
            if key == "entities" and isinstance(value, list):
                value = [self.entity(e, stelle) for e in value]
            if key in WEATHER_REVIEW_KEYS or str(key).startswith("weatherOverrideForecast"):
                self.warn(
                    f"{stelle}: '{key}' bleibt stehen – die Wettereinträge der Ruheanzeige nach "
                    "dem Import im neuen Backend prüfen (attribute/day/hour)."
                )
            if key in ("mediaControl", "alarmControl", "theme"):
                self.warn(
                    f"{stelle}: '{key}' bleibt stehen, ist für das neue Backend aber nicht "
                    "dokumentiert – am Gerät prüfen."
                )
            out[key] = value

        if screensaver:
            out.pop("defaultCard", None)  # wandert auf Panel-Ebene (siehe build_panels_dict)
            # alternativeLayout gibt es nicht mehr, das Layout steckt im Typ (config_manager.py:178,
            # docs/config-migration-standalone.md:48).
            if out.pop("alternativeLayout", None):
                out["type"] = "screensaver2"
                self.warn(f"{stelle}: 'alternativeLayout' → type screensaver2; Layout am Gerät prüfen.")
            if "entity" in out and isinstance(out.get("entities"), list):
                self.warn(
                    f"{stelle}: Legacy-Wetter 'entity' entfernt, die Ruheanzeige nutzt die "
                    "explizite entities-Liste; Vorhersage-Einträge dort prüfen."
                )
                out.pop("entity")
            elif "entity" in out:
                self.warn(
                    f"{stelle}: Legacy-Wetter 'entity' in einen entities-Eintrag umgesetzt – "
                    "Vorhersagetage (day/hour) nach Bedarf ergänzen."
                )
                out["entities"] = [{"entity": out.pop("entity")}]
        return out

    # --- Helligkeit -----------------------------------------------------------------------

    def brightness(self, value: Any, key: str) -> Any:
        if not isinstance(value, list):
            return value
        out = []
        for eintrag in value:
            if not isinstance(eintrag, dict):
                out.append(eintrag)
                continue
            zeit = eintrag.get("time")
            neu = dict(eintrag)
            if isinstance(zeit, str) and zeit.lower() in SUN_FALLBACK:
                neu["time"] = SUN_FALLBACK[zeit.lower()]
                self.warn(
                    f"{key}: '{zeit}' ersetzt durch {neu['time']} – Sonnenauf-/untergang kennt das "
                    "neue Backend nicht, nur feste Uhrzeiten oder einen Sensor."
                )
            elif isinstance(zeit, str) and not _TIME_RE.match(zeit):
                self.warn(f"{key}: Zeit '{zeit}' ist kein HH:MM – das neue Backend lehnt sie ab.")
            elif zeit is not None:
                neu["time"] = str(zeit)
            out.append(neu)
        return out


def build_panels_dict(model: dict[str, Any], panel_name: str = "nspanel") -> tuple[dict[str, Any], list[str]]:
    """Modell → ``{"nspanels": {name: panel}}`` plus Hinweise, was nachzuarbeiten ist."""
    model = copy.deepcopy(model or {})
    lauf = _Export(panel_name)
    panel: dict[str, Any] = {}

    global_settings = dict(model.get("global") or {})

    # dateFormatBabel ersetzt dateFormat: das neue Backend erwartet dort die Babel-Stufen
    # (full/long/medium/short), kein strftime-Muster mehr.
    if "dateFormatBabel" in global_settings:
        if "dateFormat" in global_settings:
            lauf.warn(
                "dateFormat (strftime) entfällt zugunsten von dateFormatBabel – das neue Backend "
                "kennt nur noch die Babel-Stufen full/long/medium/short."
            )
        global_settings["dateFormat"] = global_settings.pop("dateFormatBabel")
    elif isinstance(global_settings.get("dateFormat"), str) and "%" in global_settings["dateFormat"]:
        lauf.warn(
            "dateFormat ist ein strftime-Muster – das neue Backend erwartet full/long/medium/short; "
            "auf 'full' gesetzt."
        )
        global_settings["dateFormat"] = "full"

    for alt, neu in GLOBAL_RENAMES.items():
        if alt in global_settings:
            global_settings[neu] = global_settings.pop(alt)

    for key in ("sleepBrightness", "screenBrightness"):
        if key in global_settings:
            global_settings[key] = lauf.brightness(global_settings[key], key)

    for key in sorted(RETAINED_UNSUPPORTED & set(global_settings)):
        lauf.warn(f"'{key}' bleibt stehen, wird im neuen Backend aber nicht ausgewertet.")

    if "quiet" in global_settings:
        global_settings.pop("quiet")  # AppDaemon-Logging-Schalter, im neuen Backend ohne Bedeutung

    screensaver = model.get("screensaver")
    default_card = None
    if isinstance(screensaver, dict):
        default_card = screensaver.get("defaultCard")
    if default_card is not None:
        global_settings["defaultCard"] = default_card

    cards = [lauf.card(c, "Karte") for c in model.get("cards") or []]
    hidden = [lauf.card(c, "Unterseite") for c in model.get("hiddenCards") or []]
    screensaver_out = lauf.card(screensaver, "Ruheanzeige", screensaver=True) if isinstance(screensaver, dict) else None

    if len(lauf.temp_units) > 1:
        lauf.warn(
            f"Gemischte temperatureUnit ({', '.join(sorted(lauf.temp_units))}) – das neue Backend "
            "kennt nur eine temp_unit je Panel; die erste gewinnt."
        )
    if lauf.temp_units:
        global_settings["temp_unit"] = sorted(lauf.temp_units)[0]

    for key in PANEL_FIELD_ORDER:
        if key in global_settings:
            panel[key] = global_settings[key]
    for key, value in global_settings.items():
        panel.setdefault(key, value)

    if screensaver_out is not None:
        panel["screensaver"] = screensaver_out
    if not cards:
        lauf.warn("Keine Karten – das neue Backend verlangt mindestens eine Karte.")
    panel["cards"] = cards
    if hidden:
        panel["hiddenCards"] = hidden

    return {"nspanels": {panel_name: panel}}, lauf.warnings


def dump_panels_yaml(model: dict[str, Any], panel_name: str = "nspanel") -> tuple[str, list[str]]:
    """YAML-Text der panels.yaml samt Kopfzeilen und den Hinweisen als Kommentar."""
    data, warnings = build_panels_dict(model, panel_name)
    body = yaml.dump(
        data,
        Dumper=_ConfigDumper,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=_MAX_LINE_WIDTH,
    )
    hinweise = ""
    if warnings:
        hinweise = "#\n# Beim Export aufgefallen – bitte nacharbeiten:\n" + "".join(
            f"# - {w}\n" for w in warnings
        )
    return _HEADER + hinweise + "\n" + body, warnings
