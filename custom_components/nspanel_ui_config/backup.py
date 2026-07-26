"""Sicherungen der erzeugten nspanel-YAML.

**Warum es das gibt:** die Integration schreibt in eine Datei, die im Konfigurationsverzeichnis des
Nutzers liegt und von AppDaemon gelesen wird. Vor v0.8 hat jedes Generieren die Vorgängerversion
ersatzlos überschrieben — ein Fehlgriff im Editor (Karte gelöscht, Entity-Liste geleert) war damit
nicht mehr rückholbar, und wer versehentlich einen Ausgabepfad auf eine *fremde* Datei setzt,
verliert diese beim ersten Klick.

Deshalb gilt jetzt: **vor jedem Überschreiben wird der bisherige Stand gesichert.** Scheitert die
Sicherung, wird auch nicht geschrieben — eine nicht sicherbare Datei ist genau die, die man am
wenigsten überschreiben will.

Die Sicherungen liegen in einem Unterverzeichnis neben der Ausgabedatei. AppDaemon liest über den
``!include`` nur die eine Datei, ein Nebenverzeichnis stört dort also nicht.

Das Modul hängt bewusst **nur an der Standardbibliothek** — kein Home Assistant, kein PyYAML. So
lässt sich die Logik testen, an der ein Datenverlust hängen würde.
"""

from __future__ import annotations

import os
import re
import shutil
import time
from typing import Any, Final

# Unterverzeichnis neben der Ausgabedatei.
BACKUP_DIRNAME: Final = "backups"

# <name>.<JJJJ-MM-TT_hh-mm-ss-mmm>.bak
#
# Die Millisekunden sind kein Schmuck: mit sekundengenauem Namen und einem Kollisionszähler
# (…-1, …-2) entstünde beim Aufräumen eine Lücke, die der nächste Lauf wieder belegt — die frische
# Sicherung hieße dann wie die älteste und würde als Nächstes weggeräumt. Mit Millisekunden sind
# die Namen streng monoton, und Sortierung wie Rotation stimmen ohne Sonderfälle.
BACKUP_SUFFIX: Final = ".bak"
_TIMESTAMP_FORMAT: Final = "%Y-%m-%d_%H-%M-%S"
# Millisekunden optional, damit ein von Hand angelegter oder umbenannter Stand nicht aus der Liste
# fällt; er gilt dann als der älteste innerhalb seiner Sekunde.
_TIMESTAMP_PATTERN: Final = re.compile(
    r"\.(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})(?:-(\d{3}))?\.bak$"
)

# Wie viele Sicherungen aufgehoben werden, wenn nichts anderes eingestellt ist.
DEFAULT_BACKUP_COUNT: Final = 10


def backup_dir(output_path: str) -> str:
    """Verzeichnis, in dem die Sicherungen zu ``output_path`` liegen."""
    return os.path.join(os.path.dirname(output_path) or ".", BACKUP_DIRNAME)


def _sort_key(name: str) -> tuple[str, int]:
    """Sortierschlüssel einer Sicherung: Sekunde und Millisekunde.

    Getrennt statt als eine Zeichenkette, damit ein Name ohne Millisekunden (‑1) eindeutig vor
    allen Namen derselben Sekunde einsortiert wird, statt lexikografisch dahinter zu rutschen.
    """
    match = _TIMESTAMP_PATTERN.search(name)
    if not match:
        return ("", -1)
    return (match.group(1), int(match.group(2)) if match.group(2) else -1)


def _timestamp_of(name: str) -> str:
    match = _TIMESTAMP_PATTERN.search(name)
    if not match:
        return ""
    return match.group(1) + (f"-{match.group(2)}" if match.group(2) else "")


def list_backups(output_path: str) -> list[dict[str, Any]]:
    """Vorhandene Sicherungen, neueste zuerst.

    Fehlt das Verzeichnis, ist das kein Fehler — dann gab es schlicht noch nichts zu sichern.
    """
    directory = backup_dir(output_path)
    prefix = os.path.basename(output_path) + "."
    try:
        names = os.listdir(directory)
    except OSError:
        return []

    entries: list[dict[str, Any]] = []
    for name in names:
        if not name.startswith(prefix) or not name.endswith(BACKUP_SUFFIX):
            continue
        full = os.path.join(directory, name)
        try:
            stat = os.stat(full)
        except OSError:
            continue
        entries.append(
            {
                "name": name,
                "path": full,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "timestamp": _timestamp_of(name),
            }
        )
    # Nach dem Namen sortieren, nicht nach mtime: create_backup übernimmt per copy2 die mtime des
    # *Originals*, die also gar nicht sagt, wann gesichert wurde.
    entries.sort(key=lambda item: _sort_key(item["name"]), reverse=True)
    return entries


def prune_backups(output_path: str, keep: int) -> list[str]:
    """Lösche die ältesten Sicherungen, bis nur noch ``keep`` übrig sind. Gibt die gelöschten zurück."""
    if keep <= 0:
        return []
    entfernt: list[str] = []
    for entry in list_backups(output_path)[keep:]:
        try:
            os.remove(entry["path"])
            entfernt.append(entry["name"])
        except OSError:
            # Eine nicht löschbare alte Sicherung ist kein Grund, das Generieren scheitern zu
            # lassen — sie belegt nur Platz.
            continue
    return entfernt


def _now_stamp() -> str:
    """Zeitstempel auf die Millisekunde genau."""
    now = time.time()
    return f"{time.strftime(_TIMESTAMP_FORMAT, time.localtime(now))}-{int(now % 1 * 1000):03d}"


def _free_backup_path(directory: str, base_name: str) -> str:
    """Freier Sicherungspfad.

    Bei einer Kollision wird kurz gewartet und die Zeit neu geholt, statt einen Zähler anzuhängen —
    so bleiben alle Namen gleich aufgebaut und streng aufsteigend.
    """
    for _ in range(100):
        candidate = os.path.join(directory, f"{base_name}.{_now_stamp()}{BACKUP_SUFFIX}")
        if not os.path.exists(candidate):
            return candidate
        time.sleep(0.002)
    raise OSError(f"Kein freier Sicherungsname für {base_name} in {directory}")


def create_backup(output_path: str, keep: int = DEFAULT_BACKUP_COUNT) -> dict[str, Any] | None:
    """Sichere den *aktuellen* Inhalt von ``output_path``, bevor er überschrieben wird.

    Gibt Angaben zur angelegten Sicherung zurück oder ``None``, wenn keine nötig war (Datei existiert
    noch nicht, oder Sicherungen sind mit ``keep <= 0`` abgeschaltet).

    Wirft ``OSError``, wenn die Sicherung nicht angelegt werden kann. Der Aufrufer darf dann **nicht**
    überschreiben — genau dafür ist sie da.
    """
    if keep <= 0 or not os.path.isfile(output_path):
        return None

    directory = backup_dir(output_path)
    os.makedirs(directory, exist_ok=True)
    target = _free_backup_path(directory, os.path.basename(output_path))
    # copy2 statt copy: Zeitstempel der Originaldatei bleiben erhalten.
    shutil.copy2(output_path, target)

    # Erst nach der neuen Sicherung aufräumen, sonst könnte man bei keep=1 kurzzeitig ohne dastehen.
    entfernt = prune_backups(output_path, keep)
    return {
        "name": os.path.basename(target),
        "path": target,
        "size": os.path.getsize(target),
        "pruned": entfernt,
    }


def restore_backup(output_path: str, name: str, keep: int = DEFAULT_BACKUP_COUNT) -> dict[str, Any]:
    """Spiele eine Sicherung zurück nach ``output_path``.

    Der *aktuelle* Stand wird davor selbst gesichert — sonst wäre ein versehentliches
    Wiederherstellen genau der Datenverlust, den dieses Modul verhindern soll.

    ``name`` ist der reine Dateiname aus :func:`list_backups`; Pfadanteile werden abgewiesen, damit
    kein Wert aus dem Request irgendwohin sonst zeigen kann.
    """
    if not name or os.path.basename(name) != name:
        raise ValueError(f"Ungültiger Sicherungsname: {name!r}")

    source = os.path.join(backup_dir(output_path), name)
    if not os.path.isfile(source):
        raise FileNotFoundError(f"Sicherung nicht gefunden: {name}")

    ersetzt = create_backup(output_path, keep)

    # Gleiche Vorsicht wie beim Generieren: erst danebenschreiben, dann atomar ersetzen.
    tmp_path = f"{output_path}.tmp"
    shutil.copy2(source, tmp_path)
    os.replace(tmp_path, output_path)
    return {"restored": name, "path": output_path, "backup_of_previous": ersetzt}
