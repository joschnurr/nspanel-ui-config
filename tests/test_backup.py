"""Tests der Sicherungslogik.

Hier hängt Datenverlust dran, deshalb wird nicht nur der Normalfall geprüft, sondern vor allem:
Wird wirklich *vor* dem Überschreiben gesichert? Bleibt bei einer fehlgeschlagenen Sicherung die
alte Datei stehen? Kann ein Name aus dem Request aus dem Sicherungsverzeichnis herauszeigen?

Konvention wie im Rest des Projekts: Standardbibliothek und ``assert``, keine pytest-Fixtures —
so laufen die Tests auch dort, wo kein pytest installiert ist.
"""

from __future__ import annotations

import os
import tempfile
import time

from nspanel_ui_config import backup  # via conftest.py registriert


def _schreibe(pfad: str, inhalt: str) -> None:
    with open(pfad, "w", encoding="utf-8") as handle:
        handle.write(inhalt)


def _lies(pfad: str) -> str:
    with open(pfad, encoding="utf-8") as handle:
        return handle.read()


def test_ohne_bestehende_datei_gibt_es_nichts_zu_sichern() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ziel = os.path.join(tmp, "nspanel_config.yaml")
        assert backup.create_backup(ziel) is None
        assert backup.list_backups(ziel) == []


def test_sicherung_haelt_den_stand_vor_dem_ueberschreiben_fest() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ziel = os.path.join(tmp, "nspanel_config.yaml")
        _schreibe(ziel, "alt: 1\n")

        info = backup.create_backup(ziel)
        assert info is not None
        # Die Sicherung trägt den *alten* Inhalt – auch nachdem das Original ersetzt wurde.
        _schreibe(ziel, "neu: 2\n")
        assert _lies(info["path"]) == "alt: 1\n"
        assert _lies(ziel) == "neu: 2\n"


def test_sicherungen_liegen_neben_der_datei_und_stoeren_den_include_nicht() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ziel = os.path.join(tmp, "nspanel_config.yaml")
        _schreibe(ziel, "x: 1\n")
        info = backup.create_backup(ziel)

        assert os.path.dirname(info["path"]) == os.path.join(tmp, backup.BACKUP_DIRNAME)
        # Im Verzeichnis der Ausgabedatei liegt weiterhin nur sie selbst plus das Unterverzeichnis.
        assert sorted(os.listdir(tmp)) == [backup.BACKUP_DIRNAME, "nspanel_config.yaml"]


def test_abschalten_mit_keep_null() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ziel = os.path.join(tmp, "nspanel_config.yaml")
        _schreibe(ziel, "x: 1\n")
        assert backup.create_backup(ziel, keep=0) is None
        assert not os.path.isdir(backup.backup_dir(ziel))


def test_mehrere_sicherungen_in_derselben_sekunde_kollidieren_nicht() -> None:
    """Zwei Klicks kurz hintereinander dürfen nicht dieselbe Datei erzeugen."""
    with tempfile.TemporaryDirectory() as tmp:
        ziel = os.path.join(tmp, "nspanel_config.yaml")
        namen = set()
        for i in range(3):
            _schreibe(ziel, f"stand: {i}\n")
            info = backup.create_backup(ziel)
            namen.add(info["name"])
        assert len(namen) == 3, f"Namen kollidieren: {namen}"
        assert len(backup.list_backups(ziel)) == 3


def test_rotation_behaelt_die_juengsten() -> None:
    """Stellt den echten Ablauf nach: erst sichern, *dann* überschreiben."""
    with tempfile.TemporaryDirectory() as tmp:
        ziel = os.path.join(tmp, "nspanel_config.yaml")
        _schreibe(ziel, "stand: 0\n")
        for i in range(1, 6):
            backup.create_backup(ziel, keep=2)
            _schreibe(ziel, f"stand: {i}\n")

        vorhanden = backup.list_backups(ziel)
        assert len(vorhanden) == 2
        # Aufgehoben sind die beiden zuletzt überschriebenen Stände, nicht die ersten.
        assert [_lies(e["path"]) for e in vorhanden] == ["stand: 4\n", "stand: 3\n"]
        assert _lies(ziel) == "stand: 5\n"


def test_liste_sortiert_neueste_zuerst() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ziel = os.path.join(tmp, "nspanel_config.yaml")
        for i in range(3):
            _schreibe(ziel, f"stand: {i}\n")
            backup.create_backup(ziel)
            time.sleep(0.01)

        eintraege = backup.list_backups(ziel)
        inhalte = [_lies(e["path"]) for e in eintraege]
        assert inhalte == ["stand: 2\n", "stand: 1\n", "stand: 0\n"]


def test_liste_ignoriert_fremde_dateien() -> None:
    """Im Sicherungsverzeichnis darf anderes liegen, ohne als Sicherung zu gelten."""
    with tempfile.TemporaryDirectory() as tmp:
        ziel = os.path.join(tmp, "nspanel_config.yaml")
        _schreibe(ziel, "x: 1\n")
        backup.create_backup(ziel)

        verzeichnis = backup.backup_dir(ziel)
        _schreibe(os.path.join(verzeichnis, "notizen.txt"), "hallo")
        _schreibe(os.path.join(verzeichnis, "andere_datei.yaml.2020-01-01_00-00-00.bak"), "fremd")

        namen = [e["name"] for e in backup.list_backups(ziel)]
        assert len(namen) == 1
        assert namen[0].startswith("nspanel_config.yaml.")


# --- Wiederherstellen -------------------------------------------------------------------------


def test_wiederherstellen_sichert_den_aktuellen_stand_zuerst() -> None:
    """Sonst wäre ein versehentliches Zurückspielen genau der Datenverlust, den wir verhindern."""
    with tempfile.TemporaryDirectory() as tmp:
        ziel = os.path.join(tmp, "nspanel_config.yaml")
        _schreibe(ziel, "alt: 1\n")
        gesichert = backup.create_backup(ziel)
        _schreibe(ziel, "aktuell: 2\n")

        ergebnis = backup.restore_backup(ziel, gesichert["name"])

        assert _lies(ziel) == "alt: 1\n"
        # Der überschriebene Stand ist selbst gesichert.
        vorheriger = ergebnis["backup_of_previous"]
        assert vorheriger is not None
        assert _lies(vorheriger["path"]) == "aktuell: 2\n"


def test_wiederherstellen_weist_pfadanteile_ab() -> None:
    """``name`` kommt aus dem Request – er darf nirgendwo sonst hinzeigen können."""
    with tempfile.TemporaryDirectory() as tmp:
        ziel = os.path.join(tmp, "nspanel_config.yaml")
        _schreibe(ziel, "x: 1\n")
        for boeser_name in ("../../etc/passwd", "unter/verzeichnis.bak", "/absolut.bak"):
            try:
                backup.restore_backup(ziel, boeser_name)
            except ValueError:
                continue
            except FileNotFoundError:
                raise AssertionError(f"'{boeser_name}' hätte als ungültig abgelehnt werden müssen")
            raise AssertionError(f"'{boeser_name}' wurde nicht abgelehnt")


def test_wiederherstellen_meldet_unbekannte_sicherung() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ziel = os.path.join(tmp, "nspanel_config.yaml")
        _schreibe(ziel, "x: 1\n")
        try:
            backup.restore_backup(ziel, "nspanel_config.yaml.2000-01-01_00-00-00.bak")
        except FileNotFoundError:
            return
        raise AssertionError("Fehlende Sicherung muss FileNotFoundError auslösen")
