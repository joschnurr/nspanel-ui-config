"""Löst nach dem Generieren einen Reload des AppDaemon-Backends aus.

**Warum das überhaupt nötig ist.** AppDaemon überwacht die mtime seiner App-Config- und
Python-Dateien und lädt betroffene Apps neu. Eine per ``!include`` eingebundene Datei steht aber
*nicht* in dieser Liste: der Loader liest sie beim Einlesen der apps.yaml nur inline mit
(``appdaemon/utils.py``, ``_include_yaml``) und merkt sich den Pfad nicht. Nachgemessen am echten
Backend (AppDaemon 4.7.3): nach dem Neuschreiben der Include-Datei erscheint keine einzige Zeile im
AppDaemon-Log — die Karten im Panel bleiben also auf dem alten Stand, bis etwas anderes den Reload
auslöst. Genau das tut dieses Modul.

Die zwei Wege haben unterschiedliche Voraussetzungen, deshalb bleibt der Modus konfigurierbar:

``touch_module``
    Setzt die mtime der ``apps.yaml`` neu, die AppDaemon *bereits* überwacht. Feingranular (nur die
    betroffene App wird neu geladen), setzt aber voraus, dass HA diese Datei überhaupt sieht:
    AppDaemons ``apps/``-Verzeichnis muss in den HA-Container gemountet sein (die Volumes sind
    getrennt).

    **Es muss die apps.yaml sein, nicht das App-Modul.** Tickt man ``apps/nspanel.py`` an, startet
    AppDaemon die App zwar sichtbar neu (*Modified Python files* → *Started*), liest die per
    ``!include`` eingebundene Konfiguration dabei aber **nicht** neu ein — die frisch erzeugte YAML
    bleibt wirkungslos, und das sieht man nur daran, dass sich am Panel nichts ändert. Nachgemessen
    am 2026-07-26: nach dem Anticken der ``.py`` fand das Backend eine neu vergebene ``key`` nicht,
    nach dem Anticken der ``apps.yaml`` sofort.

    **Und AppDaemon darf nicht im ``production_mode`` laufen.** Steht in seiner ``appdaemon.yaml``
    ``production_mode: true``, prüft es überhaupt nicht mehr auf geänderte Dateien
    (``app_management.py``) — die mtime kann sich beliebig oft ändern, es sieht gar nicht hin. Dieser
    Fall ist besonders tückisch, weil *hier* nichts fehlschlägt: Die YAML wird geschrieben, das
    Anticken gelingt, das Generieren meldet Erfolg, und trotzdem läuft das Backend weiter mit seinem
    alten Stand. Nachgemessen am 2026-07-29 an einer laufenden Anlage: Kartentitel im Editor
    geändert, Datei korrekt geschrieben, ``apps.yaml`` angetickt — das Panel bekam beim Kartenaufruf
    weiterhin den alten Titel. Wer ``production_mode`` braucht, nimmt ``restart_container`` bzw.
    ``restart_addon``; ein Neustart liest ohnehin alles neu.

``restart_container``
    Startet den AppDaemon-Container über die Docker-API neu. Braucht keinen zusätzlichen Mount,
    dafür ``/var/run/docker.sock`` im HA-Container — und ist grob: alle AppDaemon-Apps starten neu.

``restart_addon``
    Das Gegenstück für Home Assistant OS und Supervised, wo AppDaemon als **Add-on** läuft und es
    weder einen Docker-Socket noch einen selbst gelegten Mount gibt: der Supervisor startet das
    Add-on über seine eigene API neu. Ebenfalls grob, aber ohne jede Zusatzeinrichtung — der
    Zugangstoken steht dort ohnehin in der Umgebung des HA-Containers.

Der Inhalt der angetickten Datei wird nie verändert (``os.utime``), und ein fehlgeschlagener Reload
lässt die bereits geschriebene YAML unangetastet — der Aufrufer meldet ihn als Warnung, nicht als
Fehlschlag des Generierens.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from .const import (
    CONF_RELOAD_ADDON,
    CONF_RELOAD_CONTAINER,
    CONF_RELOAD_MODE,
    CONF_RELOAD_TOUCH_PATH,
    DEFAULT_RELOAD_ADDON,
    DEFAULT_RELOAD_CONTAINER,
    DOCKER_SOCKET,
    RELOAD_MODE_ADDON,
    RELOAD_MODE_NONE,
    RELOAD_MODE_RESTART,
    RELOAD_MODE_TOUCH,
    SUPERVISOR_TOKEN_ENV,
    SUPERVISOR_URL,
)

if TYPE_CHECKING:  # pragma: no cover - nur für Typprüfung, hält Home Assistant aus den Tests
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Docker gibt dem Neustart eines Containers Zeit; darunter läuft ein SIGTERM + Wartezeit.
_DOCKER_TIMEOUT = 60
# Der Supervisor stoppt und startet das Add-on; das dauert erfahrungsgemäß länger als ein
# nackter Container-Neustart.
_SUPERVISOR_TIMEOUT = 120


class ReloadError(Exception):
    """Der Reload ist fehlgeschlagen. Die Nachricht ist für die Anzeige im Panel gedacht."""


def touch_file(path: str) -> None:
    """Setze die mtime einer bestehenden Datei neu (Blocking-I/O, gehört in den Executor).

    Bewusst nur bestehende Dateien: eine falsch konfigurierte Option soll keine Streudatei in
    AppDaemons ``apps/``-Verzeichnis anlegen, die dort als (kaputte) App-Config gelesen würde.
    """
    file = Path(path)
    if not file.is_file():
        raise ReloadError(f"Datei zum Anticken nicht gefunden: {path}")
    try:
        os.utime(file, None)
    except OSError as err:
        raise ReloadError(f"Anticken fehlgeschlagen ({path}): {err}") from err


async def async_restart_container(
    name: str, socket_path: str = DOCKER_SOCKET, timeout: int = _DOCKER_TIMEOUT
) -> None:
    """Starte einen Container über die Docker-Engine-API auf dem Unix-Socket neu."""
    if not Path(socket_path).exists():
        raise ReloadError(
            f"Docker-Socket nicht verfügbar ({socket_path}) – ist er in den HA-Container gemountet?"
        )

    # Lokaler Import: so bleibt dieses Modul ohne aiohttp importierbar (die Logik-Tests laufen
    # ohne Home-Assistant-Umgebung). HAs gemeinsame Session hilft hier nicht, die kann keine
    # Unix-Sockets.
    import aiohttp

    url = f"http://localhost/containers/{quote(name, safe='')}/restart"
    try:
        connector = aiohttp.UnixConnector(path=socket_path)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                if response.status == 204:
                    return
                if response.status == 404:
                    raise ReloadError(f"Container '{name}' nicht gefunden")
                body = (await response.text())[:200]
                raise ReloadError(f"Docker antwortete {response.status}: {body}")
    except ReloadError:
        raise
    except Exception as err:  # noqa: BLE001 – Netz-/Socket-Fehler jeder Art als Klartext melden
        raise ReloadError(f"Docker-Aufruf fehlgeschlagen: {err}") from err


async def async_restart_addon(slug: str, timeout: int = _SUPERVISOR_TIMEOUT) -> None:
    """Starte ein Add-on über die Supervisor-API neu (Home Assistant OS / Supervised).

    Der Token steht bei diesen Installationsarten als ``SUPERVISOR_TOKEN`` in der Umgebung des
    HA-Containers; fehlt er, läuft Home Assistant nicht unter einem Supervisor und der Modus ist
    schlicht der falsche.
    """
    token = os.environ.get(SUPERVISOR_TOKEN_ENV)
    if not token:
        raise ReloadError(
            "Kein Supervisor gefunden (SUPERVISOR_TOKEN fehlt). Dieser Modus ist nur für "
            "Home Assistant OS und Supervised gedacht – bei einer Container-Installation "
            "stattdessen 'touch_module' oder 'restart_container' verwenden."
        )

    # Lokaler Import aus demselben Grund wie oben: hält aiohttp aus den Logik-Tests heraus.
    import aiohttp

    url = f"{SUPERVISOR_URL}/addons/{quote(slug, safe='')}/restart"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status == 200:
                    return
                if response.status in (400, 404):
                    raise ReloadError(
                        f"Add-on '{slug}' nicht gefunden. Der Slug steht in der URL der "
                        f"Add-on-Seite (…/hassio/addon/SLUG/info)."
                    )
                body = (await response.text())[:200]
                raise ReloadError(f"Supervisor antwortete {response.status}: {body}")
    except ReloadError:
        raise
    except Exception as err:  # noqa: BLE001 – Netzfehler jeder Art als Klartext melden
        raise ReloadError(f"Supervisor-Aufruf fehlgeschlagen: {err}") from err


async def async_trigger_reload(hass: HomeAssistant, options: dict[str, Any]) -> dict[str, Any]:
    """Führe den konfigurierten Reload aus und beschreibe das Ergebnis für die API-Antwort.

    Wirft ``ReloadError``, wenn der Reload nicht durchlief. Der Aufrufer entscheidet, ob das die
    Gesamtantwort rot macht — die YAML ist zu diesem Zeitpunkt schon geschrieben.
    """
    mode = options.get(CONF_RELOAD_MODE) or RELOAD_MODE_NONE

    if mode == RELOAD_MODE_NONE:
        return {"mode": mode, "ok": True, "detail": "Kein Reload konfiguriert"}

    if mode == RELOAD_MODE_TOUCH:
        path = options.get(CONF_RELOAD_TOUCH_PATH)
        if not path:
            raise ReloadError(
                "Kein Pfad zum Anticken konfiguriert – in den Optionen unter "
                "'reload_touch_path' AppDaemons apps.yaml angeben "
                "(z. B. /appdaemon-apps/apps.yaml). Das App-Modul reicht nicht: es lädt den Code "
                "neu, nicht die per !include eingebundene Konfiguration."
            )
        await hass.async_add_executor_job(touch_file, path)
        _LOGGER.debug("AppDaemon-Reload: %s angetickt", path)
        return {"mode": mode, "ok": True, "detail": f"{path} angetickt"}

    if mode == RELOAD_MODE_RESTART:
        name = options.get(CONF_RELOAD_CONTAINER) or DEFAULT_RELOAD_CONTAINER
        await async_restart_container(name)
        _LOGGER.debug("AppDaemon-Reload: Container %s neu gestartet", name)
        return {"mode": mode, "ok": True, "detail": f"Container '{name}' neu gestartet"}

    if mode == RELOAD_MODE_ADDON:
        slug = options.get(CONF_RELOAD_ADDON) or DEFAULT_RELOAD_ADDON
        await async_restart_addon(slug)
        _LOGGER.debug("AppDaemon-Reload: Add-on %s neu gestartet", slug)
        return {"mode": mode, "ok": True, "detail": f"Add-on '{slug}' neu gestartet"}

    raise ReloadError(f"Unbekannter Reload-Modus: {mode}")
