"""Die Kennung, die an der Adresse des Editor-Panels hängt.

**Das Problem, das dieses Modul löst.** Home Assistant merkt sich die Adresse des Custom-Panels so,
wie sie beim Einrichten des Config-Entries angemeldet wurde, und hängt von sich aus nichts daran.
Wer die Dateien einer laufenden Instanz austauscht — genau das ist hier der übliche Weg, weil HACS
neue Fassungen stundenlang nicht anbietet —, bekommt deshalb weiter die alte Adresse serviert.

Bisher kam die Version dafür aus ``async_get_integration``. Die liest Home Assistant **einmal beim
Start** und hält sie im Zwischenspeicher; ein Dateiaustausch ändert daran nichts. Praktisch heißt
das: Der Editor lädt entweder das alte Modul aus dem Browser-Zwischenspeicher, oder er lädt das neue
und zeigt in der Kopfzeile trotzdem die alte Nummer. Beides sieht aus wie ein Update, das nicht
angekommen ist. Genau diese Verwechslung hat hier schon mehrfach Zeit gekostet — zuletzt, als die
neuen Laufbalken auf ``cardPower`` scheinbar fehlten, während sie längst auf der Platte lagen.

Deshalb kommt beides **von der Platte**: die Version direkt aus ``manifest.json`` statt aus HAs
Zwischenspeicher, dazu ein kurzer Fingerabdruck über die ausgelieferten Panel-Dateien. Ändert sich
eines von beidem, ändert sich die Adresse — und ein *Neuladen des Config-Entries* genügt, um eine
neue Fassung des Editors auszuliefern. Ein voller Neustart ist dafür nicht mehr nötig.

Bewusst frei von Home Assistant, damit es ohne dessen Testumgebung prüfbar bleibt.
"""

from __future__ import annotations

import json
from hashlib import blake2s
from pathlib import Path

__all__ = ["panel_kennung"]


def panel_kennung(paket: Path) -> str:
    """Die Abfrage für die Panel-URL, z. B. ``v=0.24.0&b=1a2b3c4d``.

    ``v`` steht getrennt, damit die Kopfzeile des Editors eine lesbare Versionsnummer zeigen kann
    und nicht den Fingerabdruck.

    Fehlt oder klemmt eine Datei, bleibt die betroffene Stelle ``dev``. Das ist die sichere Seite:
    Eine Adresse, die sich nicht wiederholt, lädt höchstens einmal zu viel — eine, die sich
    fälschlich wiederholt, liefert veralteten Code aus.
    """
    try:
        version = json.loads((paket / "manifest.json").read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError, TypeError):
        version = "dev"

    try:
        # Größe und mtime jeder ausgelieferten Datei. Das ändert sich bei jedem Austausch, ohne
        # dass die Dateien dafür gelesen werden müssten.
        marken = sorted(
            f"{pfad.name}:{pfad.stat().st_size}:{pfad.stat().st_mtime_ns}"
            for pfad in (paket / "www" / "panel").glob("*.js")
        )
    except OSError:
        marken = []

    stand = (
        blake2s("|".join(marken).encode("utf-8"), digest_size=4).hexdigest() if marken else "dev"
    )
    return f"v={version}&b={stand}"
