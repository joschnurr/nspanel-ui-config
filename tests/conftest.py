"""Macht ``schema``/``importer``/``generator`` ohne Home-Assistant-Testumgebung importierbar.

Diese drei Module hängen bewusst nur an PyYAML — die HA-Anbindung steckt ausschließlich in
``__init__.py``, ``config_flow.py`` und ``http_api.py``. Würde man das Paket regulär importieren,
liefe ``__init__.py`` mit und zöge Home Assistant herein.

Deshalb wird der Paketordner hier unter dem Kurznamen ``nspanel_ui_config`` als Paket registriert,
*ohne* dessen ``__init__.py`` auszuführen: relative Importe (``from .schema import …``) funktionieren
dadurch weiterhin, die Tests brauchen aber nur pyyaml und pytest.
"""

import sys
import types
from pathlib import Path

PACKAGE_NAME = "nspanel_ui_config"
PACKAGE_DIR = Path(__file__).resolve().parents[1] / "custom_components" / PACKAGE_NAME

if PACKAGE_NAME not in sys.modules:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_DIR)]
    sys.modules[PACKAGE_NAME] = package
