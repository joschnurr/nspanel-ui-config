"""Authentifizierte HTTP-API für das Panel.

Endpunkte (alle nur für Admins):
  GET  /api/nspanel_ui_config/schema    → Feld-/Kartentyp-Schema für die Editor-Formulare
  GET  /api/nspanel_ui_config/config    → aktuelles Config-Modell (JSON)
  POST /api/nspanel_ui_config/config    → Modell speichern (JSON)
  POST /api/nspanel_ui_config/import    → bestehende apps.yaml einlesen (Pfad oder Text)
  POST /api/nspanel_ui_config/yaml      → YAML zum übergebenen Stand, nur zum Ansehen
  POST /api/nspanel_ui_config/generate  → YAML erzeugen, schreiben und AppDaemon neu laden
  GET  /api/nspanel_ui_config/backups   → vorhandene Sicherungen der Ausgabedatei
  POST /api/nspanel_ui_config/backups/restore → eine Sicherung zurückspielen
  GET  /api/nspanel_ui_config/live      → was das Backend zuletzt ans Display geschickt hat
  POST /api/nspanel_ui_config/show      → das Panel auf eine bestimmte Karte bitten
"""

from __future__ import annotations

import logging
from http import HTTPStatus
from pathlib import Path
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from . import live
from .backup import list_backups, restore_backup
from .const import (
    API_BACKUP_RESTORE,
    API_BACKUPS,
    API_CONFIG,
    API_GENERATE,
    API_IMPORT,
    API_LIVE,
    API_SCHEMA,
    API_SHOW,
    API_YAML,
    CONF_BACKUP_COUNT,
    CONF_IMPORT_YAML_PATH,
    CONF_OUTPUT_PATH,
    CONF_RELOAD_MODE,
    DEFAULT_BACKUP_COUNT,
    DOMAIN,
)
from .generator import dump_config_yaml, write_config_yaml
from .importer import find_apps, parse_apps_yaml
from .reload import ReloadError, async_trigger_reload
from .schema import empty_model, schema_payload, validate_model

_LOGGER = logging.getLogger(__name__)


def async_register_http_api(hass: HomeAssistant) -> None:
    """Registriere die API-Views (idempotent genug für einen einzelnen Entry)."""
    hass.http.register_view(NsPanelSchemaView(hass))
    hass.http.register_view(NsPanelConfigView(hass))
    hass.http.register_view(NsPanelImportView(hass))
    hass.http.register_view(NsPanelYamlView(hass))
    hass.http.register_view(NsPanelGenerateView(hass))
    hass.http.register_view(NsPanelBackupsView(hass))
    hass.http.register_view(NsPanelBackupRestoreView(hass))
    hass.http.register_view(NsPanelLiveView(hass))
    hass.http.register_view(NsPanelShowView(hass))


def _backup_count(options: dict[str, Any]) -> int:
    """Eingestellte Anzahl Sicherungen; unbrauchbare Werte fallen auf den Standard zurück."""
    value = options.get(CONF_BACKUP_COUNT, DEFAULT_BACKUP_COUNT)
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return DEFAULT_BACKUP_COUNT


def _first_entry_data(hass: HomeAssistant) -> dict[str, Any] | None:
    """Liefere die Datenablage des (einzigen) Config-Entrys."""
    for data in hass.data.get(DOMAIN, {}).values():
        return data
    return None


class _NsPanelView(HomeAssistantView):
    """Gemeinsame Basis: Admin-Prüfung und Zugriff auf die Entry-Daten.

    ``requires_auth`` allein prüft nur ein gültiges Token — diese Endpunkte schreiben aber
    Konfigurationsdateien, deshalb zusätzlich die Admin-Prüfung.
    """

    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    def _require_admin(self, request: web.Request) -> web.Response | None:
        user = request.get("hass_user")
        if user is None or not user.is_admin:
            return self.json_message("Nur für Administratoren", HTTPStatus.FORBIDDEN)
        return None

    def _entry_data(self, request: web.Request) -> tuple[dict[str, Any] | None, web.Response | None]:
        error = self._require_admin(request)
        if error is not None:
            return None, error
        data = _first_entry_data(self.hass)
        if data is None:
            return None, self.json_message("Integration nicht eingerichtet", HTTPStatus.BAD_REQUEST)
        return data, None


class NsPanelSchemaView(_NsPanelView):
    """Liefert die Schema-Beschreibung, aus der das Panel seine Formulare baut.

    Bewusst *ohne* Config-Entry-Zwang: der Editor soll das Schema auch dann laden können, wenn die
    Integration gerade neu eingerichtet wird — sonst zeigt er statt Formularen nur einen Fehler.
    """

    url = API_SCHEMA
    name = "api:nspanel_ui_config:schema"

    async def get(self, request: web.Request) -> web.Response:
        error = self._require_admin(request)
        if error is not None:
            return error
        return self.json(schema_payload())


class NsPanelConfigView(_NsPanelView):
    """Lädt und speichert das interne Config-Modell."""

    url = API_CONFIG
    name = "api:nspanel_ui_config:config"

    async def get(self, request: web.Request) -> web.Response:
        data, error = self._entry_data(request)
        if error is not None:
            return error
        model = data.get("model") or {}
        # Ohne gespeichertes Modell ein leeres Gerüst liefern, damit der Editor sofort eine gültige
        # Struktur hat. ``stored`` sagt ihm, dass noch nichts persistiert ist (Hinweis auf Import).
        stored = bool(model)
        if not stored:
            model = empty_model()
        return self.json(
            {"model": model, "stored": stored, "findings": validate_model(model)}
        )

    async def post(self, request: web.Request) -> web.Response:
        data, error = self._entry_data(request)
        if error is not None:
            return error
        try:
            model = await request.json()
        except ValueError:
            return self.json_message("Ungültiges JSON", HTTPStatus.BAD_REQUEST)
        if not isinstance(model, dict):
            return self.json_message("Modell muss ein Objekt sein", HTTPStatus.BAD_REQUEST)
        data["model"] = model
        await data["store"].async_save(model)
        # Mit dem Modell kann sich das Sende-Topic ändern – ein Abo auf dem alten wäre still
        # wirkungslos, deshalb hier erneuern.
        await live.async_restart(self.hass, data)
        return self.json({"ok": True, "findings": validate_model(model)})


class NsPanelImportView(_NsPanelView):
    """Liest eine bestehende apps.yaml ein und liefert das daraus abgeleitete Modell.

    Body: ``{"text": "<yaml>"}`` oder ``{"path": "/pfad/apps.yaml"}`` (ohne beides: der beim
    Einrichten hinterlegte Importpfad), optional ``{"app_name": "nspanel-1"}`` und
    ``{"save": true}``. Das Ergebnis wird nur auf Wunsch gespeichert — der Editor soll erst
    anzeigen können, was der Import ergeben hat.
    """

    url = API_IMPORT
    name = "api:nspanel_ui_config:import"

    async def post(self, request: web.Request) -> web.Response:
        data, error = self._entry_data(request)
        if error is not None:
            return error
        try:
            payload = await request.json()
        except ValueError:
            return self.json_message("Ungültiges JSON", HTTPStatus.BAD_REQUEST)
        if not isinstance(payload, dict):
            payload = {}

        text = payload.get("text")
        if not isinstance(text, str):
            path = payload.get("path") or data["options"].get(CONF_IMPORT_YAML_PATH)
            if not path:
                return self.json_message("Weder 'text' noch 'path' angegeben", HTTPStatus.BAD_REQUEST)
            # Der Pfad kommt aus dem Request – daher die HA-Allowlist (allowlist_external_dirs)
            # erzwingen, statt beliebige Dateien lesbar zu machen.
            if not self.hass.config.is_allowed_path(path):
                return self.json_message(
                    f"Pfad nicht freigegeben: {path} (allowlist_external_dirs in configuration.yaml)",
                    HTTPStatus.FORBIDDEN,
                )
            try:
                text = await self.hass.async_add_executor_job(
                    lambda: Path(path).read_text(encoding="utf-8")
                )
            except OSError as err:
                _LOGGER.error("apps.yaml konnte nicht gelesen werden (%s): %s", path, err)
                return self.json_message(f"Lesen fehlgeschlagen: {err}", HTTPStatus.BAD_REQUEST)

        try:
            apps = await self.hass.async_add_executor_job(find_apps, text)
            model = await self.hass.async_add_executor_job(
                parse_apps_yaml, text, payload.get("app_name")
            )
        except Exception as err:  # noqa: BLE001 – YAML-Fehler des Nutzers, nicht unserer
            _LOGGER.error("apps.yaml konnte nicht geparst werden: %s", err)
            return self.json_message(f"YAML nicht lesbar: {err}", HTTPStatus.BAD_REQUEST)

        if payload.get("save"):
            data["model"] = model
            await data["store"].async_save(model)

        return self.json(
            {
                "ok": True,
                "apps": apps,
                "model": model,
                "findings": validate_model(model),
                "saved": bool(payload.get("save")),
            }
        )


class NsPanelYamlView(_NsPanelView):
    """Liefert die YAML zum aktuellen Stand — **ohne** zu schreiben und ohne Reload.

    Body optional: ``{"model": {…}}``. Der Editor schickt seinen *gerade bearbeiteten* Stand mit,
    auch den ungespeicherten: gezeigt werden soll, was beim nächsten Speichern in der Datei landen
    würde, nicht was zuletzt gespeichert wurde. Ohne Body gilt das gespeicherte Modell.

    ``path`` sagt dazu, wohin diese YAML beim Speichern geschrieben wird — im Editor steht die
    Ansicht sonst ohne Bezug da.
    """

    url = API_YAML
    name = "api:nspanel_ui_config:yaml"

    async def post(self, request: web.Request) -> web.Response:
        data, error = self._entry_data(request)
        if error is not None:
            return error
        try:
            payload = await request.json()
        except ValueError:
            payload = {}  # leerer Body ist erlaubt: dann der gespeicherte Stand
        if not isinstance(payload, dict):
            payload = {}

        model = payload.get("model")
        if not isinstance(model, dict):
            model = data.get("model") or {}

        try:
            text = await self.hass.async_add_executor_job(dump_config_yaml, model)
        except Exception as err:  # noqa: BLE001 – kaputtes Modell des Nutzers, nicht unseres
            _LOGGER.error("YAML-Vorschau fehlgeschlagen: %s", err)
            return self.json_message(f"YAML nicht erzeugbar: {err}", HTTPStatus.BAD_REQUEST)

        return self.json(
            {
                "text": text,
                "path": data["options"].get(CONF_OUTPUT_PATH),
                "findings": validate_model(model),
            }
        )


class NsPanelGenerateView(_NsPanelView):
    """Erzeugt die nspanel-YAML aus dem Modell, schreibt sie und lädt das Backend neu.

    Body optional: ``{"reload": false}`` überspringt den konfigurierten Reload (zum Schreiben
    ohne Nebenwirkung, etwa beim Vergleichen der Ausgabe).
    """

    url = API_GENERATE
    name = "api:nspanel_ui_config:generate"

    async def post(self, request: web.Request) -> web.Response:
        data, error = self._entry_data(request)
        if error is not None:
            return error
        try:
            payload = await request.json()
        except ValueError:
            payload = {}  # leerer Body ist der Normalfall
        if not isinstance(payload, dict):
            payload = {}

        # Der Ausgabepfad stammt aus den Entry-Optionen (Admin-gesetzt), nicht aus dem Request.
        output_path = data["options"].get(CONF_OUTPUT_PATH)
        model = data.get("model", {})
        try:
            result = await self.hass.async_add_executor_job(
                write_config_yaml, model, output_path, _backup_count(data["options"])
            )
        except OSError as err:
            # Schließt den Fall ein, dass sich der bisherige Stand nicht sichern ließ — dann wurde
            # bewusst nicht überschrieben.
            _LOGGER.error("Schreiben der nspanel-YAML fehlgeschlagen: %s", err)
            return self.json_message(f"Schreiben fehlgeschlagen: {err}", HTTPStatus.INTERNAL_SERVER_ERROR)
        written = result["path"]

        # Die Datei steht schon auf der Platte — ein gescheiterter Reload ist deshalb eine Warnung
        # in der Antwort und kein Fehlschlag des Generierens.
        if payload.get("reload") is False:
            reload_result: dict[str, Any] = {"mode": "skipped", "ok": True, "detail": "Reload übersprungen"}
        else:
            try:
                reload_result = await async_trigger_reload(self.hass, dict(data["options"]))
            except ReloadError as err:
                _LOGGER.warning("YAML geschrieben, aber AppDaemon-Reload fehlgeschlagen: %s", err)
                reload_result = {
                    "mode": data["options"].get(CONF_RELOAD_MODE),
                    "ok": False,
                    "detail": str(err),
                }

        return self.json(
            {
                "ok": True,
                "path": written,
                "changed": result["changed"],
                "backup": result["backup"],
                "findings": validate_model(model),
                "reload": reload_result,
            }
        )


class NsPanelBackupsView(_NsPanelView):
    """Listet die Sicherungen der Ausgabedatei, neueste zuerst."""

    url = API_BACKUPS
    name = "api:nspanel_ui_config:backups"

    async def get(self, request: web.Request) -> web.Response:
        data, error = self._entry_data(request)
        if error is not None:
            return error
        output_path = data["options"].get(CONF_OUTPUT_PATH)
        if not output_path:
            return self.json({"path": None, "keep": 0, "backups": []})

        entries = await self.hass.async_add_executor_job(list_backups, output_path)
        return self.json(
            {
                "path": output_path,
                "keep": _backup_count(data["options"]),
                "backups": entries,
            }
        )


class NsPanelBackupRestoreView(_NsPanelView):
    """Spielt eine Sicherung zurück (``{"name": "<dateiname>"}``).

    Der aktuelle Stand wird davor selbst gesichert, siehe ``backup.restore_backup``. Nach dem
    Zurückspielen ist die Datei auf der Platte älter als das Modell im Editor — das Panel weist
    darauf hin, statt stillschweigend beides auseinanderlaufen zu lassen.
    """

    url = API_BACKUP_RESTORE
    name = "api:nspanel_ui_config:backups:restore"

    async def post(self, request: web.Request) -> web.Response:
        data, error = self._entry_data(request)
        if error is not None:
            return error
        try:
            payload = await request.json()
        except ValueError:
            return self.json_message("Ungültiges JSON", HTTPStatus.BAD_REQUEST)
        if not isinstance(payload, dict) or not payload.get("name"):
            return self.json_message("'name' fehlt", HTTPStatus.BAD_REQUEST)

        output_path = data["options"].get(CONF_OUTPUT_PATH)
        if not output_path:
            return self.json_message("Kein Ausgabepfad konfiguriert", HTTPStatus.BAD_REQUEST)

        try:
            result = await self.hass.async_add_executor_job(
                restore_backup, output_path, payload["name"], _backup_count(data["options"])
            )
        except ValueError as err:
            return self.json_message(str(err), HTTPStatus.BAD_REQUEST)
        except FileNotFoundError as err:
            return self.json_message(str(err), HTTPStatus.NOT_FOUND)
        except OSError as err:
            _LOGGER.error("Wiederherstellen fehlgeschlagen: %s", err)
            return self.json_message(
                f"Wiederherstellen fehlgeschlagen: {err}", HTTPStatus.INTERNAL_SERVER_ERROR
            )

        _LOGGER.info("Sicherung '%s' nach %s zurückgespielt", payload["name"], output_path)
        return self.json({"ok": True, **result})


class NsPanelLiveView(_NsPanelView):
    """Was das Backend zuletzt ans Display geschickt hat.

    Die Antwort sagt auch, *warum* nichts da ist (kein MQTT in HA, kein Sende-Topic im Modell,
    noch nichts gehört) — sonst steht der Nutzer vor einer leeren Vorschau ohne Erklärung.
    """

    url = API_LIVE
    name = "api:nspanel_ui_config:live"

    async def get(self, request: web.Request) -> web.Response:
        data, error = self._entry_data(request)
        if error is not None:
            return error
        zustand = data.get("live")
        if zustand is None:
            return self.json(
                {
                    "available": False,
                    "reason": data.get("live_reason", "Mitschnitt nicht aktiv."),
                    "topic": live.send_topic_of(data.get("model")),
                }
            )
        # Mit ``?card=<Titel>&type=<Kartentyp>`` kommt der zuletzt gesehene Stand *dieser* Karte.
        # Ohne das wäre die Ansicht kaum brauchbar: ein Panel steht die meiste Zeit im Ruhezustand
        # und sendet dann nur den Screensaver.
        antwort = zustand.as_dict(
            title=request.query.get("card"), card_type=request.query.get("type")
        )
        antwort["available"] = True
        if antwort.get("message") is None:
            # Abonniert, aber noch nichts gehört: das Panel sendet erst, wenn sich etwas ändert
            # oder man eine Karte aufruft.
            antwort["reason"] = (
                "Abonniert, aber noch keine Anzeige-Nachricht empfangen. Am Panel eine Karte "
                "aufrufen oder auf die nächste Aktualisierung warten."
            )
        return self.json(antwort)


class NsPanelShowView(_NsPanelView):
    """Bittet das Panel, eine bestimmte Karte anzuzeigen.

    Body: ``{"key": "<key der Karte>"}``. Damit lässt sich die Live-Ansicht gezielt füllen, statt
    auf das zu warten, was das Gerät zufällig anzeigt — im Ruhezustand ist das immer der
    Screensaver. **Das echte Panel wechselt dabei sichtbar die Anzeige**, deshalb passiert es nur
    auf ausdrückliche Anforderung aus dem Editor.
    """

    url = API_SHOW
    name = "api:nspanel_ui_config:show"

    async def post(self, request: web.Request) -> web.Response:
        data, error = self._entry_data(request)
        if error is not None:
            return error
        try:
            payload = await request.json()
        except ValueError:
            return self.json_message("Ungültiges JSON", HTTPStatus.BAD_REQUEST)
        key = payload.get("key") if isinstance(payload, dict) else None
        if not isinstance(key, str) or not key.strip():
            return self.json_message("'key' fehlt", HTTPStatus.BAD_REQUEST)

        try:
            await live.async_show_card(self.hass, data, key.strip())
        except live.LiveError as err:
            return self.json_message(str(err), HTTPStatus.BAD_REQUEST)
        return self.json({"ok": True, "key": key.strip()})
