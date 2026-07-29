"""Tests der Installationsart-Erkennung.

Der Einrichtungsdialog stellt sich danach ein, ob AppDaemon als Add-on, als eigener Container oder
im selben Dateisystem läuft. Rät er falsch, führt er den Anwender in eine Einrichtung, die es in
seiner Welt gar nicht gibt — etwa einen Bind-Mount unter Home Assistant OS.

Konvention wie im Rest des Projekts: Standardbibliothek und ``assert``, keine pytest-Fixtures.
"""

from __future__ import annotations

from nspanel_ui_config import install_profile  # via conftest.py registriert
from nspanel_ui_config.const import (
    CONF_RELOAD_ADDON,
    CONF_RELOAD_CONTAINER,
    CONF_RELOAD_TOUCH_PATH,
    RELOAD_MODE_ADDON,
    RELOAD_MODE_NONE,
    RELOAD_MODE_RESTART,
    RELOAD_MODE_TOUCH,
    RELOAD_MODES,
)


def test_home_assistant_os_bekommt_das_addon_profil() -> None:
    assert install_profile.profile_for_installation_type("Home Assistant OS") == (
        install_profile.PROFILE_ADDON
    )
    # Supervised verhält sich für uns gleich: Supervisor vorhanden, AppDaemon als Add-on.
    assert install_profile.profile_for_installation_type("Home Assistant Supervised") == (
        install_profile.PROFILE_ADDON
    )


def test_container_und_core_werden_unterschieden() -> None:
    assert install_profile.profile_for_installation_type("Home Assistant Container") == (
        install_profile.PROFILE_CONTAINER
    )
    assert install_profile.profile_for_installation_type("Home Assistant Core") == (
        install_profile.PROFILE_CORE
    )


def test_unbekanntes_faellt_nicht_auf_docker_zurueck() -> None:
    """Lieber „nicht erkannt“ als eine Vorgabe, die für die Hälfte der Nutzer falsch ist."""
    for eingabe in ("Unknown", "", None, 42, "Irgendwas Neues"):
        assert install_profile.profile_for_installation_type(eingabe) == (
            install_profile.PROFILE_UNKNOWN
        )


def test_jedes_profil_ist_vollstaendig() -> None:
    """Ein fehlender Schlüssel würde erst im Einrichtungsdialog auffallen – mit KeyError."""
    pflicht = {
        "label",
        "hint",
        "output_path",
        "reload_mode",
        "reload_addon",
        "reload_container",
        "reload_touch_path",
    }
    for name, profil in install_profile.PROFILES.items():
        fehlend = pflicht - set(profil)
        assert not fehlend, f"Profil '{name}' fehlt: {sorted(fehlend)}"
        assert profil["reload_mode"] in RELOAD_MODES, f"Profil '{name}': unbekannter Reload-Modus"
        assert profil["output_path"], f"Profil '{name}' ohne Ausgabepfad"
        assert profil["hint"], f"Profil '{name}' ohne Hinweistext"


def test_addon_profil_schlaegt_den_supervisor_weg_vor() -> None:
    """Unter HAOS gibt es weder Docker-Socket noch selbst gelegten Mount."""
    profil = install_profile.profile_defaults(install_profile.PROFILE_ADDON)
    assert profil["reload_mode"] == RELOAD_MODE_ADDON
    assert profil["reload_addon"], "Ohne Slug läuft der Supervisor-Aufruf ins Leere"
    # /share ist der einzige Pfad, den HA und das Add-on gleich benennen.
    assert profil["output_path"].startswith("/share/")
    # Container-spezifische Felder bleiben leer, sonst stehen irreführende Werte im Formular.
    assert profil["reload_container"] == ""
    assert profil["reload_touch_path"] == ""


def test_container_profil_bleibt_beim_bisherigen_weg() -> None:
    profil = install_profile.profile_defaults(install_profile.PROFILE_CONTAINER)
    assert profil["output_path"] == "/nspanel-shared/nspanel_config.yaml"
    assert profil["reload_container"], "Containername gehört vorbelegt"
    assert profil["reload_addon"] == ""
    # Bewusst 'none': welcher Reload klappt, hängt vom Mount ab, den der Nutzer erst anlegen muss.
    assert profil["reload_mode"] == RELOAD_MODE_NONE


def test_core_profil_nutzt_das_gemeinsame_dateisystem() -> None:
    """Bei Core gibt es keinen Container – touch_module ist dort der natürliche Weg."""
    profil = install_profile.profile_defaults(install_profile.PROFILE_CORE)
    assert profil["reload_mode"] == RELOAD_MODE_TOUCH
    assert profil["reload_container"] == ""
    assert profil["reload_addon"] == ""


def test_defaults_sind_eine_kopie() -> None:
    """Der Config-Flow verändert das Dict – das darf nicht auf das Profil durchschlagen."""
    erst = install_profile.profile_defaults(install_profile.PROFILE_ADDON)
    erst["output_path"] = "/verstellt"
    zweit = install_profile.profile_defaults(install_profile.PROFILE_ADDON)
    assert zweit["output_path"] != "/verstellt"


def test_alle_installationstypen_von_home_assistant_sind_abgedeckt() -> None:
    """Die Liste stammt aus homeassistant/helpers/system_info.py – hier gespiegelt.

    Fällt einer davon auf PROFILE_UNKNOWN, sieht der Betreffende einen nichtssagenden Dialog.
    """
    bekannt = (
        "Home Assistant OS",
        "Home Assistant Supervised",
        "Home Assistant Container",
        "Home Assistant Core",
    )
    for typ in bekannt:
        assert install_profile.profile_for_installation_type(typ) != (
            install_profile.PROFILE_UNKNOWN
        ), f"'{typ}' hat kein Profil"


# --- Welche Reload-Wege überhaupt angeboten werden ---------------------------------------------


def test_nur_wege_die_auf_dem_system_laufen_koennen() -> None:
    """Der Kern: ein Weg, den es hier nicht gibt, darf nicht wählbar sein.

    Er wäre eine Falle — eingestellt, ohne Fehlermeldung beim Generieren, und am Panel passiert
    trotzdem nichts.
    """
    addon = install_profile.profile_reload_modes(install_profile.PROFILE_ADDON)
    assert RELOAD_MODE_ADDON in addon, "Add-on-Installation muss den Supervisor-Weg anbieten"
    assert RELOAD_MODE_RESTART not in addon, "ohne Docker-Socket ist der Container-Weg sinnlos"

    container = install_profile.profile_reload_modes(install_profile.PROFILE_CONTAINER)
    assert RELOAD_MODE_RESTART in container
    assert RELOAD_MODE_ADDON not in container, "ohne Supervisor gibt es keine Add-ons"

    core = install_profile.profile_reload_modes(install_profile.PROFILE_CORE)
    assert RELOAD_MODE_ADDON not in core and RELOAD_MODE_RESTART not in core
    # Von Hand neu laden und Anticken gehen überall.
    for modi in (addon, container, core):
        assert RELOAD_MODE_NONE in modi and RELOAD_MODE_TOUCH in modi


def test_unbekannte_installation_schliesst_nichts_aus() -> None:
    """Sonst nähme man dem Anwender womöglich genau den Weg, der bei ihm funktioniert."""
    assert install_profile.profile_reload_modes(install_profile.PROFILE_UNKNOWN) == list(
        RELOAD_MODES
    )


def test_der_gespeicherte_weg_bleibt_waehlbar() -> None:
    """Nach einem Umzug (OS → Docker) steht ein Modus in den Optionen, der nicht mehr passt.

    Fehlte er in der Auswahl, ließe sich der Options-Dialog nicht einmal öffnen: Der vorbelegte Wert
    stünde nicht in der Liste, und der Anwender käme gar nicht erst dazu, ihn umzustellen.
    """
    modi = install_profile.profile_reload_modes(install_profile.PROFILE_CONTAINER, RELOAD_MODE_ADDON)
    assert RELOAD_MODE_ADDON in modi
    # Ein passender Wert taucht deswegen nicht doppelt auf.
    modi = install_profile.profile_reload_modes(install_profile.PROFILE_CONTAINER, RELOAD_MODE_TOUCH)
    assert modi.count(RELOAD_MODE_TOUCH) == 1
    # Leer oder unsinnig ändert nichts.
    for wert in ("", None, 42):
        assert install_profile.profile_reload_modes(install_profile.PROFILE_CORE, wert) == (
            install_profile.profile_reload_modes(install_profile.PROFILE_CORE)
        )


def test_zu_jedem_angebotenen_weg_gehoert_sein_feld() -> None:
    """Und nur seines: ein Textfeld ohne zugehörigen Modus wäre eine Angabe, die niemand ausliest."""
    for profil, erwartet in (
        (install_profile.PROFILE_ADDON, [CONF_RELOAD_TOUCH_PATH, CONF_RELOAD_ADDON]),
        (install_profile.PROFILE_CONTAINER, [CONF_RELOAD_TOUCH_PATH, CONF_RELOAD_CONTAINER]),
        (install_profile.PROFILE_CORE, [CONF_RELOAD_TOUCH_PATH]),
    ):
        modi = install_profile.profile_reload_modes(profil)
        assert sorted(install_profile.profile_reload_fields(modi)) == sorted(erwartet), profil


def test_jedes_profil_bietet_seinen_eigenen_vorschlag_an() -> None:
    """Die Vorbelegung muss in der Auswahl stehen – sonst zeigt das Formular einen ungültigen Wert."""
    for profil in (
        install_profile.PROFILE_ADDON,
        install_profile.PROFILE_CONTAINER,
        install_profile.PROFILE_CORE,
        install_profile.PROFILE_UNKNOWN,
    ):
        vorgabe = install_profile.profile_defaults(profil)["reload_mode"]
        assert vorgabe in install_profile.profile_reload_modes(profil), profil
