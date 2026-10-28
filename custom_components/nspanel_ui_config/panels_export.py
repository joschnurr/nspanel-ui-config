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
import os
import re
from typing import Any

import yaml

from .backup import DEFAULT_BACKUP_COUNT, create_backup
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
    """``ha:`` ganz nach vorn, falls der Wert ein Template ist.

    Das neue Backend prüft ``startswith("ha:")`` (``ha_cards.py:80/85/306``) und schickt dann den
    *ganzen* String an Home Assistants ``render_template``; Text und ``<I>mdi:…</I>`` bleiben dabei
    stehen, das Präfix entfernt ``get_icon_id`` hinterher. Ein Präfix mitten im String – wie es das
    AppDaemon-Backend bei Status-Symbolen ``<I>mdi:…</I> ha:{{ … }} °C`` erlaubte – wird dort nicht
    gerendert: am Gerät stand wörtlich ``{{ states(…) }}`` (beobachtet 28.10.2026 beim Umstieg).
    Deshalb wandert ein eingebettetes ``ha:`` an den Anfang statt nur verdoppelt zu werden.
    """
    if not _is_template(value):
        return value
    if value.startswith("ha:"):
        return value
    if "ha:" in value:
        return "ha:" + value.replace("ha:", "", 1)
    return "ha:" + value


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


# --- Rückweg: panels.yaml → Modell ---------------------------------------------------------------

# Panel-Keys, die im Modell (AppDaemon-Form) anders heißen – Umkehrung von GLOBAL_RENAMES.
_PANEL_RENAMES_BACK: dict[str, str] = {neu: alt for alt, neu in GLOBAL_RENAMES.items()}

# Top-Level-Keys der panels.yaml, die Verbindung und Betrieb betreffen – nicht Teil des Modells.
CONNECTION_KEYS: frozenset[str] = frozenset(
    {"home_assistant_address", "home_assistant_token", "mqtt_server", "mqtt_port", "mqtt_username",
     "mqtt_password", "use_ha_api"}
)


def _strip_prefix(value: Any) -> Any:
    """``ha:`` am Anfang entfernen – der Editor arbeitet mit nackten Templates (AppDaemon-Form)."""
    if isinstance(value, str) and value.startswith("ha:") and _is_template(value):
        return value[3:]
    if isinstance(value, dict):
        return {k: _strip_prefix(v) for k, v in value.items()}
    return value


def _entity_back(entity: Any) -> Any:
    if not isinstance(entity, dict):
        return entity
    out = dict(entity)
    for field in TEMPLATE_PREFIX_FIELDS:
        if field in out:
            out[field] = _strip_prefix(out[field])
    return out


def _card_back(card: Any, temp_unit: Any = None) -> Any:
    if not isinstance(card, dict):
        return card
    out: dict[str, Any] = {}
    for key, value in card.items():
        if key == "supported_modes":
            key = "supportedModes"
        if key == "qrCode":
            value = _strip_prefix(value)
        if key in ("statusIcon1", "statusIcon2"):
            value = _entity_back(value)
        if key == "entities" and isinstance(value, list):
            value = [_entity_back(e) for e in value]
        out[key] = value
    # temp_unit gilt im neuen Backend je Panel; im Modell hängt es an den Thermostat-Karten.
    if temp_unit is not None and out.get("type") == "cardThermo" and "temperatureUnit" not in out:
        out["temperatureUnit"] = temp_unit
    return out


def panels_to_config_block(data: Any, panel_name: str | None = None) -> dict[str, Any]:
    """Ein Panel aus ``{"nspanels": {...}}`` als config-Block in AppDaemon-Form (für den Importer).

    Umkehrung von ``build_panels_dict``, so weit sie eindeutig ist: Umbenennungen zurück, ``ha:``-Präfix
    ab, ``defaultCard`` zurück in die Ruheanzeige, ``temp_unit`` an die Thermostat-Karten. Was der Export
    entfernt hat (navItem, cooldown, Sonnenzeiten), kommt natürlich nicht zurück. Ohne ``panel_name``
    oder bei unbekanntem Namen gilt das erste Panel.
    """
    if not isinstance(data, dict) or not isinstance(data.get("nspanels"), dict) or not data["nspanels"]:
        return {}
    panels = data["nspanels"]
    panel = panels.get(panel_name) if panel_name in panels else next(iter(panels.values()))
    if not isinstance(panel, dict):
        return {}

    config: dict[str, Any] = {}
    temp_unit = panel.get("temp_unit")
    default_card = panel.get("defaultCard")
    for key, value in panel.items():
        if key in ("temp_unit", "defaultCard", "screensaver", "cards", "hiddenCards"):
            continue
        if key == "dateFormat":
            # Im neuen Backend ist dateFormat die Babel-Stufe; so hieß sie im AppDaemon-Backend.
            config["dateFormatBabel"] = value
            continue
        if key in ("sleepBrightness", "screenBrightness") and isinstance(value, list):
            value = [dict(e) for e in value]
        config[_PANEL_RENAMES_BACK.get(key, key)] = value

    if isinstance(panel.get("screensaver"), dict):
        ss = _card_back(panel["screensaver"])
        ss.setdefault("type", "screensaver")
        if default_card is not None:
            ss["defaultCard"] = default_card
        config["screensaver"] = ss
    config["cards"] = [_card_back(c, temp_unit) for c in panel.get("cards") or []]
    if panel.get("hiddenCards"):
        config["hiddenCards"] = [_card_back(c, temp_unit) for c in panel["hiddenCards"]]
    return config


def is_panels_yaml(parsed: Any) -> bool:
    """Erkennt die Datei des neuen Backends an ihrer Wurzel ``nspanels``."""
    return isinstance(parsed, dict) and isinstance(parsed.get("nspanels"), dict)


# --- Schreiben: panels.yaml direkt bedienen -------------------------------------------------------

def _read_yaml(path: str) -> dict[str, Any] | None:
    try:
        with open(path, encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def merge_panels_yaml(model: dict[str, Any], existing: dict[str, Any] | None, panel_name: str) -> tuple[dict[str, Any], list[str]]:
    """Unser Panel in eine bestehende panels.yaml einsetzen, ohne den Rest anzutasten.

    Erhalten bleiben alle Top-Level-Keys der bestehenden Datei (Verbindungsdaten, ``use_ha_api``, globale
    Vorgaben) und alle *anderen* Panels unter ``nspanels``. Nur ``nspanels.<panel_name>`` wird ersetzt.
    Der Editor kennt die Zugangsdaten nicht und schreibt sie deshalb auch nie – er lässt sie stehen.
    """
    neu, warnings = build_panels_dict(model, panel_name)
    out: dict[str, Any] = {}
    if existing:
        for key, value in existing.items():
            if key != "nspanels":
                out[key] = value
    nspanels: dict[str, Any] = {}
    if existing and isinstance(existing.get("nspanels"), dict):
        nspanels.update(existing["nspanels"])
    nspanels[panel_name] = neu["nspanels"][panel_name]
    out["nspanels"] = nspanels
    if not existing or not any(k in CONNECTION_KEYS for k in existing):
        warnings.append(
            "Die Datei enthält keine Verbindungsdaten (home_assistant_address/-token, mqtt_*) – im neuen "
            "Backend nachtragen, sonst verbindet es sich nicht."
        )
    return out, warnings


def dump_merged_panels_yaml(data: dict[str, Any], warnings: list[str]) -> str:
    body = yaml.dump(data, Dumper=_ConfigDumper, allow_unicode=True, sort_keys=False,
                     default_flow_style=False, width=_MAX_LINE_WIDTH)
    kopf = (
        "# panels.yaml – von der Home-Assistant-Integration 'NSPanel UI Config' geschrieben.\n"
        "# Verbindungsdaten und fremde Panels werden beim Schreiben übernommen, nicht erzeugt.\n"
    )
    hinweise = "".join(f"# - {w}\n" for w in warnings)
    if hinweise:
        kopf += "#\n# Beim Umsetzen aufgefallen:\n" + hinweise
    return kopf + "\n" + body


def write_panels_yaml(
    model: dict[str, Any],
    output_path: str,
    panel_name: str = "nspanel",
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> dict[str, Any]:
    """Modell als unser Panel in die panels.yaml des neuen Backends schreiben (atomar, mit Sicherung).

    Gleiche Verträge wie ``generator.write_config_yaml``: erst sichern, dann ersetzen; unveränderter
    Inhalt wird nicht geschrieben. Das Backend bemerkt die Änderung über seine Datei-Überwachung und
    lädt selbst neu – ein Reload-Schritt ist nicht nötig. Rückgabe zusätzlich mit ``warnings``.
    """
    if not output_path:
        raise OSError("Kein Ausgabepfad konfiguriert")
    existing = _read_yaml(output_path)
    data, warnings = merge_panels_yaml(model, existing, panel_name)
    text = dump_merged_panels_yaml(data, warnings)

    try:
        with open(output_path, encoding="utf-8") as handle:
            if handle.read() == text:
                return {"path": output_path, "changed": False, "backup": None, "warnings": warnings}
    except (OSError, UnicodeDecodeError):
        pass

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    backup_info = create_backup(output_path, backup_count)
    tmp_path = f"{output_path}.tmp"
    # Die Datei trägt das HA-Token: neue Datei nur für den Besitzer lesbar, bestehende Rechte bleiben.
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    try:
        os.chmod(tmp_path, os.stat(output_path).st_mode & 0o777)
    except OSError:
        pass
    os.replace(tmp_path, output_path)
    return {"path": output_path, "changed": True, "backup": backup_info, "warnings": warnings}


def preview_panels_yaml(model: dict[str, Any], output_path: str | None, panel_name: str = "nspanel") -> tuple[str, list[str]]:
    """Der Text, der beim nächsten Schreiben in der panels.yaml landen würde (liest die bestehende Datei)."""
    existing = _read_yaml(output_path) if output_path else None
    data, warnings = merge_panels_yaml(model, existing, panel_name)
    return dump_merged_panels_yaml(data, warnings), warnings
