"""Die Kennung an der Panel-Adresse – der Grund, warum Updates „nicht ankommen".

Home Assistant meldet die Adresse des Panels einmal beim Einrichten des Config-Entries an und hängt
von sich aus nichts daran. Kam die Version aus HAs Zwischenspeicher, blieb sie nach einem
Dateiaustausch stehen — der Editor lieferte altes JavaScript aus oder zeigte zumindest die falsche
Nummer in der Kopfzeile. Diese Tests halten fest, dass die Kennung den Dateien folgt.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs

from nspanel_ui_config.panel_assets import panel_kennung  # via conftest.py registriert

REPO = Path(__file__).resolve().parents[1]
INTEGRATION = REPO / "custom_components" / "nspanel_ui_config"


def _paket(tmp_path: Path, version: str = "1.2.3", inhalt: str = "// eins") -> Path:
    paket = tmp_path / "paket"
    (paket / "www" / "panel").mkdir(parents=True)
    (paket / "manifest.json").write_text(json.dumps({"version": version}), encoding="utf-8")
    (paket / "www" / "panel" / "panel.js").write_text(inhalt, encoding="utf-8")
    return paket


def test_kennung_traegt_version_und_dateistand(tmp_path: Path) -> None:
    felder = parse_qs(panel_kennung(_paket(tmp_path)))
    assert felder["v"] == ["1.2.3"]
    # `v` steht getrennt, damit die Kopfzeile eine lesbare Nummer zeigt statt des Fingerabdrucks.
    assert len(felder["b"]) == 1 and felder["b"][0] != "dev"


def test_geaenderte_panel_datei_aendert_die_kennung(tmp_path: Path) -> None:
    """Der eigentliche Zweck: neue Dateien, neue Adresse – auch ohne neue Versionsnummer.

    Genau hier lief es vorher schief. Wer eine laufende Instanz aktualisiert, ohne die Version zu
    erhöhen (oder ohne Neustart), bekam dieselbe Adresse und damit das alte Modul.
    """
    paket = _paket(tmp_path)
    vorher = panel_kennung(paket)

    datei = paket / "www" / "panel" / "panel.js"
    datei.write_text("// zwei – deutlich länger als vorher", encoding="utf-8")

    nachher = panel_kennung(paket)
    assert nachher != vorher
    assert parse_qs(nachher)["v"] == parse_qs(vorher)["v"], "die Version soll dabei stehen bleiben"


def test_neue_version_aendert_die_kennung_ebenfalls(tmp_path: Path) -> None:
    paket = _paket(tmp_path, version="1.2.3")
    vorher = panel_kennung(paket)
    (paket / "manifest.json").write_text(json.dumps({"version": "1.3.0"}), encoding="utf-8")
    assert panel_kennung(paket) != vorher


def test_kennung_ist_stabil_wenn_sich_nichts_aendert(tmp_path: Path) -> None:
    """Sonst lüde der Browser bei jedem Neustart alles neu, ohne dass es etwas Neues gäbe."""
    paket = _paket(tmp_path)
    assert panel_kennung(paket) == panel_kennung(paket)


def test_fehlendes_paket_liefert_dev_statt_eines_absturzes(tmp_path: Path) -> None:
    """Eine kaputte Installation soll die Integration nicht am Laden hindern."""
    felder = parse_qs(panel_kennung(tmp_path / "gibt-es-nicht"))
    assert felder == {"v": ["dev"], "b": ["dev"]}


def test_kennung_der_echten_installation_nennt_die_manifest_version() -> None:
    """Gegenprobe am echten Paket: die Nummer stammt aus der Datei, nicht aus einem Zwischenstand."""
    version = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))["version"]
    felder = parse_qs(panel_kennung(INTEGRATION))
    assert felder["v"] == [version]
    assert felder["b"][0] != "dev", "die Panel-Dateien müssen gefunden werden"
