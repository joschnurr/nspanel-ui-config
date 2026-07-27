"""Zerlegt die Nachrichten, die das Backend ans Display schickt.

**Wozu:** die Vorschau baut aus dem Modell nach, was auf dem Panel erscheinen *wird* — Symbole ohne
eigene Angabe und die Formatierung von Zuständen bleiben dabei Näherung, weil das Backend sie selbst
ableitet. Wer ein laufendes NSPanel hat, kann stattdessen zusehen: das Backend schickt dem Display
über MQTT fertig gerenderte Zeilen. Dieses Modul macht daraus wieder Struktur.

**Rein lesend.** Hier wird nichts erzeugt und nichts gesendet; die Integration abonniert nur.

Aufbau der Nachrichten (aus ``pages.py`` des Backends und ``HMI/README.md`` des Upstream-Repos):

    entityUpd~<Titel>~<Navigation: 2 Einträge>~<Eintrag>~<Eintrag>…
    weatherUpdate~<Eintrag>~<Eintrag>…              (Screensaver, ohne Titel und Navigation)
    statusUpdate~<Symbol1>~<Farbe1>~<Symbol2>~<Farbe2>~<altFont1>~<altFont2>
    pageType~<Kartentyp>                            (sagt, welche Karte gerade gilt)

Ein *Eintrag* ist immer derselbe 6er-Block (``generate_entities_item``):

    ~type~entityId~icon~iconColor~displayName~optionalValue

Abweichungen, die es wirklich gibt: ``cardQR`` schiebt vor die Einträge ein Feld mit dem QR-Text,
``cardPower`` hängt jedem Eintrag ein siebtes Feld an (``speed``). Karten mit eigener Struktur
(``cardThermo``, ``cardMedia``, ``cardAlarm``, ``cardChart``, ``cardUnlock``) baut das Backend nicht
aus diesen Blöcken — für sie liefert dieses Modul bewusst *keine* Einträge, statt eine Struktur zu
erfinden, die es nicht gibt.
"""

from __future__ import annotations

from typing import Any, Final

TRENNER: Final = "~"

# Trennt im Icon-Feld das Symbol von der Schriftgröße (siehe ``_eintrag``).
FONT_TRENNER: Final = "\u00ac"

# Reihenfolge der Felder eines Eintrags.
ENTITY_FIELDS: Final[tuple[str, ...]] = ("type", "entity", "icon", "color", "name", "value")

# Die Navigation belegt zwei vollständige Einträge (Blättern links/rechts).
NAVIGATION_ENTRIES: Final = 2

# So viele Status-Symbole kennt die Ruheanzeige (``for i in range(1,3)`` in pages.py).
STATUS_ICONS: Final = 2

# Karten, deren Einträge diesem Blockaufbau folgen: Vorspann nach dem Titel (zusätzlich zur
# Navigation) und Felder je Eintrag.
PAGE_FORMATS: Final[dict[str, dict[str, int]]] = {
    "cardEntities": {"lead": 0, "fields": 6},
    "cardGrid": {"lead": 0, "fields": 6},
    "cardGrid2": {"lead": 0, "fields": 6},
    # Vor den beiden Textzeilen steht der Inhalt des QR-Codes.
    "cardQR": {"lead": 1, "fields": 6},
    # Jeder Eintrag trägt zusätzlich die Geschwindigkeit der Flussanimation.
    "cardPower": {"lead": 0, "fields": 7},
}

# Karten, die das Backend aus eigenen Feldern zusammensetzt statt aus Einträgen.
UNSTRUCTURED_PAGES: Final[tuple[str, ...]] = (
    "cardThermo",
    "cardMedia",
    "cardAlarm",
    "cardChart",
    "cardUnlock",
)


def rgb565_to_rgb(value: Any) -> list[int] | None:
    """Rechnet die 16-Bit-Farbe des Displays in ``[r, g, b]`` zurück.

    Umkehrung von ``rgb_dec565`` (helper.py im Backend): rot und blau tragen 5 Bit, grün 6. Die
    unteren Bits gehen dabei verloren — zurück kommt der Wert, den das Display wirklich anzeigt,
    nicht der ursprünglich konfigurierte. Genau das ist hier erwünscht.
    """
    try:
        zahl = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if zahl < 0 or zahl > 0xFFFF:
        return None
    rot = (zahl >> 11) & 0x1F
    gruen = (zahl >> 5) & 0x3F
    blau = zahl & 0x1F
    return [round(rot * 255 / 31), round(gruen * 255 / 63), round(blau * 255 / 31)]


def _eintrag(felder: list[str]) -> dict[str, Any]:
    """Ein Feldblock als Dict — mit dem, was die Vorschau zum Zeichnen braucht."""
    eintrag: dict[str, Any] = {}
    for name, wert in zip(ENTITY_FIELDS, felder):
        eintrag[name] = wert
    eintrag["rgb"] = rgb565_to_rgb(eintrag.get("color"))
    # Das Symbol kommt als Zeichen des Nextion-Icon-Fonts; den Namen dazu kennt erst das Frontend
    # (www/panel/icon-chars.js). Leere Zeichen bedeuten "kein Symbol".
    # **Schriftgröße im Icon-Feld.** Ist am Eintrag ein ``font`` konfiguriert, hängt das Backend sie
    # als ``¬<nummer>`` an das Symbol an (``pages.py``: ``icon_id = f'{icon_id}¬{font}'``). Ohne das
    # Abtrennen stünde auf dem Raster wörtlich "19¬0" statt der Zahl.
    symbol = eintrag.get("icon") or ""
    if FONT_TRENNER in symbol:
        symbol, _, nummer = symbol.partition(FONT_TRENNER)
        eintrag["font"] = int(nummer) if nummer.strip().isdigit() else None
    eintrag["iconChar"] = symbol or None
    # Alles jenseits der sechs Standardfelder (cardPower: speed) bleibt erhalten.
    if len(felder) > len(ENTITY_FIELDS):
        eintrag["extra"] = felder[len(ENTITY_FIELDS) :]
    # **Ob ein Platz belegt ist, entscheidet sein Inhalt — nicht das type-Feld.** Beim Screensaver
    # rendert das Backend mit ``mask=["type", "entityId"]`` (pages.py): beide Felder kommen dann
    # leer an, obwohl Symbol, Name und Wert gefüllt sind. Wer nur auf ``type`` schaut, hält eine
    # vollständig belegte Ruheanzeige für leer. ``delete`` bleibt der explizit freigehaltene Platz.
    inhalt_leer = not any(eintrag.get(feld) for feld in ("icon", "name", "value"))
    eintrag["leer"] = eintrag.get("type") == "delete" or inhalt_leer
    return eintrag


def parse_entity_upd(payload: str, card_type: str | None) -> dict[str, Any] | None:
    """Zerlegt eine ``entityUpd~``-Nachricht.

    ``card_type`` muss von außen kommen: die Nachricht selbst sagt nicht, welche Karte sie füllt —
    das steht in dem ``pageType~``-Kommando, das das Backend davor schickt.
    """
    if not isinstance(payload, str) or not payload.startswith("entityUpd" + TRENNER):
        return None
    teile = payload.split(TRENNER)
    ergebnis: dict[str, Any] = {
        "instruction": "entityUpd",
        "cardType": card_type,
        "title": teile[1] if len(teile) > 1 else "",
        "entities": [],
        "navigation": [],
    }

    aufbau = PAGE_FORMATS.get(card_type or "")
    if aufbau is None:
        # Unbekannte oder eigenständig aufgebaute Karte: Titel ja, Einträge nein.
        ergebnis["strukturiert"] = False
        return ergebnis
    ergebnis["strukturiert"] = True

    rest = teile[2:]
    for _ in range(NAVIGATION_ENTRIES):
        if len(rest) < 6:
            break
        ergebnis["navigation"].append(_eintrag(rest[:6]))
        rest = rest[6:]

    if aufbau["lead"]:
        ergebnis["lead"] = rest[: aufbau["lead"]]
        rest = rest[aufbau["lead"] :]

    breite = aufbau["fields"]
    while len(rest) >= breite:
        ergebnis["entities"].append(_eintrag(rest[:breite]))
        rest = rest[breite:]
    # Ein angebrochener letzter Block ist kein Fehler: das Backend hängt bei manchen Karten
    # Zusatzfelder an (etwa die Lautsprecherauswahl auf cardMedia).
    if rest:
        ergebnis["rest"] = rest
    return ergebnis


def parse_weather_update(payload: str, card_type: str | None = None) -> dict[str, Any] | None:
    """Zerlegt eine ``weatherUpdate~``-Nachricht (die Ruheanzeige).

    **Welcher der beiden Screensaver es ist, steht nicht in der Nachricht** — beide Bauarten füllen
    dieselben 6er-Blöcke, nur mit unterschiedlich vielen. Maßgeblich ist deshalb der zuletzt
    gemeldete ``pageType``; ohne den gilt der klassische ``screensaver``. Das ist keine Feinheit:
    ``screensaver2`` hat 15 Plätze statt 6, die Vorschau würde sonst zwei Drittel wegwerfen.
    """
    if not isinstance(payload, str) or not payload.startswith("weatherUpdate" + TRENNER):
        return None
    teile = payload.split(TRENNER)[1:]
    eintraege = []
    while len(teile) >= 6:
        eintraege.append(_eintrag(teile[:6]))
        teile = teile[6:]
    return {
        "instruction": "weatherUpdate",
        "cardType": card_type if card_type in ("screensaver", "screensaver2") else "screensaver",
        "title": "",
        "entities": eintraege,
        "navigation": [],
        "strukturiert": True,
    }


def parse_status_update(payload: str) -> list[dict[str, Any]] | None:
    """Zerlegt eine ``statusUpdate~``-Nachricht: die beiden Status-Symbole der Ruheanzeige.

    **Eine eigene Nachricht, kein Teil von** ``weatherUpdate``: ``update_status_icons`` (pages.py)
    sendet erst beide Symbole je mit ihrer Farbe und danach für beide das ``altFont``-Kennzeichen —
    daher die Reihenfolge Symbol/Farbe, Symbol/Farbe, altFont, altFont. Ein nicht konfiguriertes
    Status-Symbol kommt als leeres Feldpaar an; die Stelle bleibt auf dem Display dann leer.

    Im Symbolfeld steht **nicht zwingend nur ein Symbol**: ``icon_mapping.get_icon_id`` ersetzt in
    einem Feld wie ``<I>mdi:fire</I> ha:{{ … }} °C`` nur den ``<I>…</I>``-Teil durch das Zeichen und
    rendert das Template — heraus kommt Zeichen *und* Text. Getrennt wird das erst im Frontend, das
    das Zeichen-Mapping kennt.
    """
    if not isinstance(payload, str) or not payload.startswith("statusUpdate" + TRENNER):
        return None
    felder = payload.split(TRENNER)[1:]

    def feld(index: int) -> str:
        return felder[index] if 0 <= index < len(felder) else ""

    ergebnis = []
    for i in range(STATUS_ICONS):
        symbol = feld(2 * i)
        farbe = feld(2 * i + 1)
        ergebnis.append(
            {
                "iconChar": symbol or None,
                "color": farbe,
                "rgb": rgb565_to_rgb(farbe),
                # Das Backend reicht den YAML-Wert unverändert durch (``True``/leer).
                "altFont": feld(2 * STATUS_ICONS + i).strip().lower() in ("true", "1", "yes", "on"),
                "leer": not symbol,
            }
        )
    return ergebnis


def parse_message(payload: str, card_type: str | None = None) -> dict[str, Any] | None:
    """Erkennt die Nachrichtenart und zerlegt sie – oder gibt ``None`` zurück.

    ``None`` heißt "für die Vorschau uninteressant" (Helligkeit, Zeitsignal, Tastendrücke). Das ist
    der Normalfall: über dasselbe Topic läuft der gesamte Verkehr zum Panel.
    """
    if not isinstance(payload, str):
        return None
    if payload.startswith("entityUpd" + TRENNER):
        return parse_entity_upd(payload, card_type)
    if payload.startswith("weatherUpdate" + TRENNER):
        return parse_weather_update(payload, card_type)
    return None


def parse_page_type(payload: str) -> str | None:
    """Der Kartentyp aus einem ``pageType~``-Kommando."""
    if not isinstance(payload, str) or not payload.startswith("pageType" + TRENNER):
        return None
    teile = payload.split(TRENNER, 1)
    typ = teile[1].strip() if len(teile) > 1 else ""
    return typ or None
