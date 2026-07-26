"""Tests der Reload-Auslösung nach dem Generieren.

Laufen ohne Home Assistant *und* ohne aiohttp: ``reload.py`` importiert aiohttp erst innerhalb der
Docker-Funktion, und ``hass`` wird hier durch ein Minimal-Double ersetzt, das nur
``async_add_executor_job`` kann. Wie die übrigen Tests hier kommen sie ohne pytest-Fixtures aus
(stdlib + plain assert), damit sie sich auch ohne installiertes pytest ausführen lassen.

Nicht abgedeckt: der eigentliche HTTP-Aufruf an den Docker-Socket — der braucht eine echte
Umgebung mit gemountetem ``docker.sock``.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from nspanel_ui_config import reload as reload_mod  # via conftest.py registriert
from nspanel_ui_config.const import (
    CONF_RELOAD_ADDON,
    CONF_RELOAD_CONTAINER,
    CONF_RELOAD_MODE,
    CONF_RELOAD_TOUCH_PATH,
    RELOAD_MODE_ADDON,
    RELOAD_MODE_NONE,
    RELOAD_MODE_RESTART,
    RELOAD_MODE_TOUCH,
    RELOAD_MODES,
    SUPERVISOR_TOKEN_ENV,
)


class FakeHass:
    """Nur das, was ``async_trigger_reload`` von hass benutzt."""

    async def async_add_executor_job(self, func: Callable[..., Any], *args: Any) -> Any:
        return func(*args)


def trigger(options: dict[str, Any]) -> dict[str, Any]:
    return asyncio.run(reload_mod.async_trigger_reload(FakeHass(), options))


def erwarte_fehler(fragment: str, func: Callable[[], Any]) -> None:
    """Wie ``pytest.raises(ReloadError, match=…)``, nur ohne pytest."""
    try:
        func()
    except reload_mod.ReloadError as err:
        assert fragment in str(err), f"Fehlermeldung nennt '{fragment}' nicht: {err}"
        return
    raise AssertionError(f"ReloadError mit '{fragment}' erwartet, aber keiner geworfen")


def test_modus_none_tut_nichts() -> None:
    result = trigger({CONF_RELOAD_MODE: RELOAD_MODE_NONE})
    assert result["ok"] is True
    assert result["mode"] == RELOAD_MODE_NONE


def test_fehlende_option_bedeutet_none() -> None:
    """Ein Entry aus einer älteren Version hat den Key gar nicht — das darf nicht knallen."""
    result = trigger({})
    assert result["ok"] is True
    assert result["mode"] == RELOAD_MODE_NONE


def test_unbekannter_modus_meldet_klartext() -> None:
    erwarte_fehler("Unbekannter Reload-Modus", lambda: trigger({CONF_RELOAD_MODE: "vielleicht"}))


def test_touch_ohne_pfad_erklaert_was_fehlt() -> None:
    erwarte_fehler(
        "reload_touch_path", lambda: trigger({CONF_RELOAD_MODE: RELOAD_MODE_TOUCH})
    )


def test_touch_auf_fehlende_datei_legt_keine_an() -> None:
    """Sonst entstünde in AppDaemons apps/-Verzeichnis eine leere Datei, die dort gelesen wird."""
    with tempfile.TemporaryDirectory() as tmp:
        ziel = Path(tmp) / "nspanel.py"
        erwarte_fehler(
            "nicht gefunden",
            lambda: trigger(
                {CONF_RELOAD_MODE: RELOAD_MODE_TOUCH, CONF_RELOAD_TOUCH_PATH: str(ziel)}
            ),
        )
        assert not ziel.exists()


def test_touch_setzt_nur_die_mtime_und_laesst_den_inhalt_stehen() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ziel = Path(tmp) / "nspanel.py"
        ziel.write_text("# AppDaemon-App\n", encoding="utf-8")
        alt = time.time() - 3600
        os.utime(ziel, (alt, alt))

        result = trigger(
            {CONF_RELOAD_MODE: RELOAD_MODE_TOUCH, CONF_RELOAD_TOUCH_PATH: str(ziel)}
        )

        assert result["ok"] is True
        assert ziel.stat().st_mtime > alt
        assert ziel.read_text(encoding="utf-8") == "# AppDaemon-App\n"


def test_touch_auf_ein_verzeichnis_wird_abgelehnt() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        erwarte_fehler(
            "nicht gefunden",
            lambda: trigger(
                {CONF_RELOAD_MODE: RELOAD_MODE_TOUCH, CONF_RELOAD_TOUCH_PATH: tmp}
            ),
        )


def test_restart_ohne_docker_socket_nennt_den_grund() -> None:
    """Der Socket-Check läuft *vor* dem aiohttp-Import — sonst wäre dieser Test nicht möglich."""
    with tempfile.TemporaryDirectory() as tmp:
        fehlender_socket = str(Path(tmp) / "docker.sock")
        erwarte_fehler(
            "Docker-Socket nicht verfügbar",
            lambda: asyncio.run(
                reload_mod.async_restart_container("appdaemon", socket_path=fehlender_socket)
            ),
        )


def _mit_fake_restart(options: dict[str, Any]) -> list[str]:
    """Ersetzt den Docker-Aufruf und gibt zurück, welcher Containername angefragt wurde."""
    gerufen: list[str] = []

    async def fake_restart(name: str) -> None:
        gerufen.append(name)

    original = reload_mod.async_restart_container
    reload_mod.async_restart_container = fake_restart  # type: ignore[assignment]
    try:
        result = trigger(options)
        assert result["ok"] is True
    finally:
        reload_mod.async_restart_container = original  # type: ignore[assignment]
    return gerufen


def test_restart_nutzt_den_standardcontainer_wenn_keiner_gesetzt_ist() -> None:
    assert _mit_fake_restart({CONF_RELOAD_MODE: RELOAD_MODE_RESTART}) == ["appdaemon"]


def test_restart_nimmt_den_konfigurierten_containernamen() -> None:
    options = {CONF_RELOAD_MODE: RELOAD_MODE_RESTART, CONF_RELOAD_CONTAINER: "appdaemon-test"}
    assert _mit_fake_restart(options) == ["appdaemon-test"]


# --- Home Assistant OS / Supervised: AppDaemon als Add-on ---------------------------------------


def _ohne_supervisor_token() -> str | None:
    """Entfernt den Token aus der Umgebung und gibt den alten Wert zum Zurücksetzen zurück."""
    return os.environ.pop(SUPERVISOR_TOKEN_ENV, None)


def _token_zuruecksetzen(alt: str | None) -> None:
    if alt is not None:
        os.environ[SUPERVISOR_TOKEN_ENV] = alt


def test_addon_modus_ohne_supervisor_erklaert_sich() -> None:
    """Wer restart_addon auf einer Container-Installation wählt, soll den Grund lesen können."""
    alt = _ohne_supervisor_token()
    try:
        erwarte_fehler(
            "SUPERVISOR_TOKEN",
            lambda: trigger({CONF_RELOAD_MODE: RELOAD_MODE_ADDON}),
        )
        # Der Text muss auf die passende Alternative verweisen, sonst hilft er nicht weiter.
        try:
            trigger({CONF_RELOAD_MODE: RELOAD_MODE_ADDON})
        except reload_mod.ReloadError as err:
            assert "restart_container" in str(err) or "touch_module" in str(err), str(err)
    finally:
        _token_zuruecksetzen(alt)


def test_addon_modus_ist_verdrahtet() -> None:
    """Der Modus darf nicht in 'Unbekannter Reload-Modus' laufen."""
    alt = _ohne_supervisor_token()
    try:
        try:
            trigger({CONF_RELOAD_MODE: RELOAD_MODE_ADDON, CONF_RELOAD_ADDON: "a0d7b954_appdaemon"})
        except reload_mod.ReloadError as err:
            assert "Unbekannter Reload-Modus" not in str(err), str(err)
    finally:
        _token_zuruecksetzen(alt)


def test_jeder_angebotene_modus_wird_behandelt() -> None:
    """Was im Einrichtungsdialog zur Auswahl steht, muss reload.py auch kennen.

    Die Optionen sind so gewählt, dass **nichts wirklich passiert**: ein Containername, den es
    nicht gibt, ein Pfad, den es nicht gibt, und kein Supervisor-Token. Auf einem CI-Runner ist
    ein Docker-Socket durchaus vorhanden — ohne diese Vorsicht könnte der Test dort einen echten
    Container neu starten.

    Abgefangen wird jede Exception, nicht nur ReloadError: Ob ein Modus am fehlenden ``aiohttp``
    scheitert, ist hier gleichgültig; geprüft wird allein, dass keiner in den
    „Unbekannter Reload-Modus"-Zweig fällt.
    """
    alt = _ohne_supervisor_token()
    optionen = {
        CONF_RELOAD_CONTAINER: "nspanel-ui-config-existiert-nicht",
        CONF_RELOAD_TOUCH_PATH: "/nicht/vorhanden/nspanel.py",
        CONF_RELOAD_ADDON: "nspanel-ui-config-existiert-nicht",
    }
    try:
        for modus in RELOAD_MODES:
            try:
                trigger({CONF_RELOAD_MODE: modus, **optionen})
            except Exception as err:  # noqa: BLE001 – siehe Docstring
                assert "Unbekannter Reload-Modus" not in str(err), f"'{modus}' fehlt in reload.py"
    finally:
        _token_zuruecksetzen(alt)
