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
    Setzt die mtime einer Datei neu, die AppDaemon *bereits* überwacht — typischerweise sein
    App-Modul ``apps/nspanel.py`` oder die ``apps.yaml`` selbst. Feingranular (nur die betroffene
    App wird neu geladen), setzt aber voraus, dass HA diese Datei überhaupt sieht: AppDaemons
    ``apps/``-Verzeichnis muss in den HA-Container gemountet sein (die Volumes sind getrennt).

``restart_container``
    Startet den AppDaemon-Container über die Docker-API neu. Braucht keinen zusätzlichen Mount,
    dafür ``/var/run/docker.sock`` im HA-Container — und ist grob: alle AppDaemon-Apps starten neu.

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
    CONF_RELOAD_CONTAINER,
    CONF_RELOAD_MODE,
    CONF_RELOAD_TOUCH_PATH,
    DEFAULT_RELOAD_CONTAINER,
    DOCKER_SOCKET,
    RELOAD_MODE_NONE,
    RELOAD_MODE_RESTART,
    RELOAD_MODE_TOUCH,
)

if TYPE_CHECKING:  # pragma: no cover - nur für Typprüfung, hält Home Assistant aus den Tests
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Docker gibt dem Neustart eines Containers Zeit; darunter läuft ein SIGTERM + Wartezeit.
_DOCKER_TIMEOUT = 60


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
                "'reload_touch_path' die von AppDaemon überwachte Datei angeben "
                "(z. B. /appdaemon-apps/nspanel.py)"
            )
        await hass.async_add_executor_job(touch_file, path)
        _LOGGER.debug("AppDaemon-Reload: %s angetickt", path)
        return {"mode": mode, "ok": True, "detail": f"{path} angetickt"}

    if mode == RELOAD_MODE_RESTART:
        name = options.get(CONF_RELOAD_CONTAINER) or DEFAULT_RELOAD_CONTAINER
        await async_restart_container(name)
        _LOGGER.debug("AppDaemon-Reload: Container %s neu gestartet", name)
        return {"mode": mode, "ok": True, "detail": f"Container '{name}' neu gestartet"}

    raise ReloadError(f"Unbekannter Reload-Modus: {mode}")
