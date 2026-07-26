"""Prüft ``hacs.json`` und ``manifest.json`` gegen HACS' eigene Anforderungen.

**Warum lokal, obwohl es dafür die HACS-Action gibt:** die Action holt die beiden Dateien über die
GitHub-API/raw.githubusercontent — *ohne Token*. Solange das Repo privat ist, bekommt sie 404 und
damit ``None``, und die Prüfungen ``hacsjson`` und ``integration_manifest`` schlagen unabhängig vom
Inhalt fehl. Sie sind im Workflow deshalb vorübergehend ignoriert; diese Tests sind der Ersatz und
laufen ohne Netz.

Die Regeln sind aus HACS' Quellcode übernommen (``custom_components/hacs/utils/validate.py``,
``HACS_MANIFEST_JSON_SCHEMA`` mit ``extra=PREVENT_EXTRA`` und ``INTEGRATION_MANIFEST_JSON_SCHEMA``
mit ``extra=ALLOW_EXTRA``). Ändert HACS die Schemata, muss diese Liste mitwandern — der Preis dafür,
die Prüfung nicht der Action überlassen zu können.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
INTEGRATION = REPO / "custom_components" / "nspanel_ui_config"

# hacs.json: PREVENT_EXTRA — alles außerhalb dieser Liste macht die Datei ungültig.
HACS_JSON_ERLAUBTE_KEYS = {
    "content_in_root",
    "country",
    "filename",
    "hacs",
    "hide_default_branch",
    "homeassistant",
    "persistent_directory",
    "render_readme",
    "zip_release",
    "name",
}

# manifest.json: ALLOW_EXTRA, aber diese Felder verlangt HACS.
MANIFEST_PFLICHTFELDER = ("codeowners", "documentation", "domain", "issue_tracker", "name", "version")


def _lade(pfad: Path) -> dict[str, Any]:
    doc = json.loads(pfad.read_text(encoding="utf-8"))
    assert isinstance(doc, dict), f"{pfad.name} muss ein Objekt enthalten"
    return doc


def test_hacs_json_hat_nur_erlaubte_keys() -> None:
    doc = _lade(REPO / "hacs.json")
    unerlaubt = sorted(set(doc) - HACS_JSON_ERLAUBTE_KEYS)
    assert not unerlaubt, f"HACS lehnt unbekannte Keys ab (PREVENT_EXTRA): {unerlaubt}"


def test_hacs_json_hat_den_pflichtnamen() -> None:
    doc = _lade(REPO / "hacs.json")
    assert isinstance(doc.get("name"), str) and doc["name"], "hacs.json braucht ein 'name' (str)"


def test_manifest_hat_alle_von_hacs_verlangten_felder() -> None:
    doc = _lade(INTEGRATION / "manifest.json")
    fehlend = [feld for feld in MANIFEST_PFLICHTFELDER if feld not in doc]
    assert not fehlend, f"manifest.json fehlen von HACS verlangte Felder: {fehlend}"
    assert isinstance(doc["codeowners"], list), "codeowners muss eine Liste sein"
    for feld in ("documentation", "issue_tracker"):
        assert doc[feld].startswith("https://"), f"{feld} muss eine URL sein"


def test_manifest_version_ist_eine_versionsnummer() -> None:
    """HACS liest die Version mit AwesomeVersion; ein Freitext fliegt dort raus."""
    version = _lade(INTEGRATION / "manifest.json")["version"]
    teile = version.split(".")
    assert len(teile) >= 2 and all(teil.isdigit() for teil in teile), f"unbrauchbare Version: {version}"


def test_domain_passt_zum_verzeichnisnamen() -> None:
    """Sonst findet HA die Integration nicht — und HACS installiert sie ins falsche Verzeichnis."""
    assert _lade(INTEGRATION / "manifest.json")["domain"] == INTEGRATION.name


def test_manifest_keys_sind_sortiert() -> None:
    """Hassfest verlangt: ``domain``, ``name``, dann alphabetisch – und wird sonst rot.

    Eine Formalie, die man beim Ergänzen eines Feldes garantiert übersieht: ``after_dependencies``
    landet intuitiv neben ``dependencies``, gehört aber davor. Hier fällt es ohne CI-Runde auf.
    """
    keys = list(_lade(INTEGRATION / "manifest.json"))
    assert keys[:2] == ["domain", "name"], f"'domain', 'name' müssen zuerst stehen: {keys[:2]}"
    rest = keys[2:]
    assert rest == sorted(rest), (
        "Nach domain/name müssen die Keys alphabetisch stehen. Erwartet:\n  "
        + ", ".join(sorted(rest))
    )


def _png_masse(datei: Path) -> tuple[int, int]:
    """Breite und Höhe aus dem IHDR – ohne Bildbibliothek, die es hier nirgends gibt."""
    kopf = datei.read_bytes()[:24]
    assert kopf[:8] == b"\x89PNG\r\n\x1a\n", f"{datei.name} ist kein PNG"
    return struct.unpack(">II", kopf[16:24])


def test_brand_assets_sind_vorhanden_und_nicht_leer() -> None:
    """Ab HA 2026.3 zeigt HA diese Bilder an der Integration; fehlen sie, kommt der Platzhalter."""
    for name in ("icon.png", "icon@2x.png", "logo.png", "logo@2x.png"):
        datei = INTEGRATION / "brand" / name
        assert datei.is_file(), f"brand/{name} fehlt"
        assert datei.stat().st_size > 1000, f"brand/{name} ist verdächtig klein"
        assert datei.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", f"brand/{name} ist kein PNG"


def test_brand_assets_halten_die_masse_des_brands_repos_ein() -> None:
    """Dieselben Dateien gehen ins home-assistant/brands-Repo – dort gelten feste Maße.

    Icons müssen quadratisch sein (256 bzw. 512), beim Logo zählt die *kürzeste* Seite: 128–256 für
    die normale, 256–512 für die hDPI-Fassung. Wird hier etwas verletzt, fällt es beim PR auf und
    nicht vorher – deshalb der Test.
    """
    breite, hoehe = _png_masse(INTEGRATION / "brand" / "icon.png")
    assert (breite, hoehe) == (256, 256), f"icon.png ist {breite}×{hoehe}"
    breite, hoehe = _png_masse(INTEGRATION / "brand" / "icon@2x.png")
    assert (breite, hoehe) == (512, 512), f"icon@2x.png ist {breite}×{hoehe}"

    for name, unten, oben in (("logo.png", 128, 256), ("logo@2x.png", 256, 512)):
        breite, hoehe = _png_masse(INTEGRATION / "brand" / name)
        kurz = min(breite, hoehe)
        assert unten <= kurz <= oben, f"{name}: kürzeste Seite {kurz}, erlaubt {unten}–{oben}"


# --- Übersetzungen ------------------------------------------------------------------------------


def test_uebersetzungen_enthalten_kein_html() -> None:
    """Hassfest lehnt spitze Klammern in Übersetzungstexten als HTML ab.

    Die Falle sind Platzhalter wie ``<slug>`` – gut gemeint, aber sie machen die CI rot. Statt
    dessen SLUG oder ähnliches schreiben.
    """
    import re

    muster = re.compile(r"<[^>]+>")
    for name in ("strings.json", "translations/de.json", "translations/en.json"):
        pfad = INTEGRATION / name
        daten = json.loads(pfad.read_text(encoding="utf-8"))

        def pruefe(obj: object, pfadangabe: str = "") -> None:
            if isinstance(obj, dict):
                for schluessel, wert in obj.items():
                    pruefe(wert, f"{pfadangabe}.{schluessel}")
            elif isinstance(obj, str):
                assert not muster.search(obj), f"{name}{pfadangabe} enthält HTML-artiges: {obj[:60]}"

        pruefe(daten)


def test_uebersetzungen_decken_dieselben_felder_ab() -> None:
    """Ein Feld nur auf Deutsch beschriftet wäre auf Englisch namenlos."""
    de = json.loads((INTEGRATION / "translations/de.json").read_text(encoding="utf-8"))
    en = json.loads((INTEGRATION / "translations/en.json").read_text(encoding="utf-8"))
    for bereich, schritt in (("config", "user"), ("options", "init")):
        de_felder = set(de[bereich]["step"][schritt].get("data", {}))
        en_felder = set(en[bereich]["step"][schritt].get("data", {}))
        assert de_felder == en_felder, (
            f"{bereich}/{schritt}: nur de {sorted(de_felder - en_felder)}, "
            f"nur en {sorted(en_felder - de_felder)}"
        )
