"""Datenmodell / Schema der nspanel-lovelace-ui-Konfiguration.

Abgeleitet aus ``luibackend/config.py`` (joBr99) und docs.nspanel.pky.eu. Dieses Modul beschreibt
die *Struktur* der Zielkonfiguration deklarativ, damit Editor (Frontend), Import und Generator sich
auf eine gemeinsame Definition stützen.

Leitidee des Modells: **verlustfrei vor vollständig.** Alles, was das Backend kennt, bekommt ein
benanntes Feld; alles Übrige landet unverändert in einem ``extra``-Dict und wird beim Generieren
wieder herausgeschrieben. Dadurch überlebt auch Konfiguration den Round-Trip, die diese Integration
(noch) nicht versteht — etwa Keys aus einer neueren Backend-Version.
"""

from __future__ import annotations

from typing import Any, Final

# --- Kartentypen -----------------------------------------------------------------------------

# Kartentypen des Upstream-Backends (pages.py). MVP-Priorität: cardEntities, cardGrid.
CARD_TYPES: Final[tuple[str, ...]] = (
    "cardEntities",
    "cardGrid",
    "cardGrid2",
    "cardThermo",
    "cardMedia",
    "cardAlarm",
    "cardQR",
    "cardPower",
    "cardUnlock",
    "cardChart",
)

# Der Screensaver ist im Backend ebenfalls eine Card, nur mit eigenem Typ.
SCREENSAVER_TYPES: Final[tuple[str, ...]] = ("screensaver", "screensaver2")

# Panel-Modelle.
MODELS: Final[tuple[str, ...]] = ("eu", "us-l", "us-p")


# --- Anzeigekapazität je Kartentyp ------------------------------------------------------------

# **Wie viele Einträge der `entities`-Liste das Display tatsächlich anzeigt.**
#
# Weder Backend noch Generator kürzen die Liste — überzählige Entities werden mitgesendet und vom
# Nextion-Display schlicht ignoriert. Ein zu langer `entities`-Block ist deshalb ein *stiller*
# Fehler: in der YAML steht alles, auf dem Panel fehlt es. Genau dafür sind diese Zahlen da.
#
# Quelle sind die Slot-Komponenten der HMI-Seiten (`HMI/n2t-out-visual/*.txt` bzw.
# `HMI/US/{landscape,portrait}/n2t-out-visual/*.txt` im Upstream-Repo joBr99/nspanel-lovelace-ui)
# und für die Screensaver der Nextion-Codegenerator `HMI/code_gen/pages/screensaver{,2}.py`,
# der den `weatherUpdate~`-String in 6er-Blöcken auf feste Slots verteilt. Nachgezählt, nicht
# geschätzt — Stand 2026-07-26.
CARD_CAPACITY: Final[dict[str, dict[str, int]]] = {
    # cardEntities/cardGrid2 sind die einzigen Karten, deren Kapazität vom Modell abhängt.
    "cardEntities": {"eu": 4, "us-l": 4, "us-p": 6},
    "cardGrid": {"eu": 6, "us-l": 6, "us-p": 6},
    "cardGrid2": {"eu": 8, "us-l": 8, "us-p": 9},
    "cardQR": {"eu": 2, "us-l": 2, "us-p": 2},
    # Untere Symbolreihe. Die Lautsprecherauswahl hängt das Backend selbst hinten an.
    "cardMedia": {"eu": 6, "us-l": 6, "us-p": 6},
    # 2 in der Mitte (tHome/tHome2) + 6 außen (t0…t5).
    "cardPower": {"eu": 8, "us-l": 8, "us-p": 8},
    # 1 Haupt + 4 Forecast + 1 weitere, die das alternative Layout auslöst.
    "screensaver": {"eu": 6, "us-l": 6, "us-p": 6},
    # 1 Haupt + 3 (Icon/Wert) + 6 (Icon/Name/Wert) + 5 (nur Icon).
    "screensaver2": {"eu": 15, "us-l": 15, "us-p": 15},
}

# Karten *ohne* Entity-Liste (sie tragen genau eine Entity flach auf der Karte) bzw. ganz ohne
# Entities. Bewusst getrennt von CARD_CAPACITY, damit "keine Liste" nicht mit "0 Slots" verwechselt
# wird.
CARDS_WITHOUT_ENTITY_LIST: Final[tuple[str, ...]] = (
    "cardThermo",
    "cardAlarm",
    "cardChart",
    "cardUnlock",
)

# Das Backend wechselt selbstständig von cardGrid auf cardGrid2, sobald mehr als 6 Entities
# konfiguriert sind (pages.py: ``if card.cardType == "cardGrid" and len(card.entities) > 6``).
# Ein cardGrid mit 7–8 Einträgen verliert also nichts, es sieht nur anders aus als erwartet.
GRID_AUTO_SWITCH_AT: Final[int] = 6

# Wie sich die Plätze innerhalb einer Karte aufteilen — als Klartext für den Editor, weil die reine
# Zahl nicht erklärt, *wo* die Einträge landen.
CAPACITY_LAYOUT_NOTES: Final[dict[str, str]] = {
    "cardEntities": "Eine Zeile je Entity, von oben nach unten.",
    "cardGrid": "3×2-Raster. Ab dem 7. Eintrag stellt das Backend automatisch auf cardGrid2 um.",
    "cardGrid2": "4×2-Raster (us-p: 3×3) mit kleineren Kacheln.",
    "cardQR": "Zwei Textzeilen neben dem QR-Code.",
    "cardMedia": "Untere Symbolreihe. Das Backend hängt die Lautsprecherauswahl automatisch an; "
    "mit 6 eigenen Einträgen (notfalls `entity: delete`) verdrängt man sie.",
    "cardPower": "Die ersten beiden Entities stehen in der Mitte, die restlichen sechs außen herum. "
    "`entity: delete` hält einen Außenplatz frei.",
    "screensaver": "1. Entity = großes Hauptsymbol, 2.–5. = die vier Vorhersagespalten. "
    "Eine 6. Entity schaltet das Display auf das alternative Layout um: der Hauptbereich "
    "trägt dann zwei Textblöcke (1. und 6. Entity). Quer (eu, us-l) blendet das HMI dafür "
    "die erste Vorhersagespalte aus und rückt die übrigen nach rechts — die 5. Entity "
    "verliert dadurch ihren Platz. Hochkant (us-p) stehen die Textblöcke nebeneinander, "
    "dort bleiben alle sechs sichtbar.",
    "screensaver2": "1. Entity = großer Hauptbereich. 2.–4. = drei Einträge mit Symbol und Wert, "
    "untereinander an derselben Seite. 5.–10. = sechs Kacheln mit Symbol, Name und Wert in einer "
    "eigenen Reihe. 11.–15. = fünf reine Symbole, wieder in einer eigenen Reihe — sie stehen auf "
    "dem eu-Panel *über* den Kacheln, nicht darunter. Die Vorschau zeigt die genaue Lage.",
}

# Einzeiler zum Kartentyp selbst — was die Karte überhaupt darstellt.
CARD_TYPE_NOTES: Final[dict[str, str]] = {
    "cardEntities": "Liste mit einer bedienbaren Zeile je Entity (Schalter, Regler, Rollladen …).",
    "cardGrid": "Kachelraster mit Symbol und Name — kompakter als cardEntities, dafür ohne Regler.",
    "cardGrid2": "Wie cardGrid, nur mit mehr und kleineren Kacheln.",
    "cardThermo": "Thermostatseite für genau eine `climate`-Entity (Soll-/Ist-Temperatur, Modi).",
    "cardMedia": "Medienseite für genau einen `media_player` samt Lautstärke und Titelanzeige.",
    "cardAlarm": "Bedienfeld für eine `alarm_control_panel`-Entity mit Zifferntastatur.",
    "cardQR": "QR-Code (typischerweise WLAN-Zugang) mit zwei Textzeilen daneben.",
    "cardPower": "Energiefluss-Darstellung: Verbraucher/Erzeuger um einen Mittelpunkt herum, "
    "verbunden durch animierte Punkte (`speed`).",
    "cardUnlock": "PIN-Eingabe, die auf eine versteckte Karte weiterleitet.",
    "cardChart": "Balkendiagramm für eine Entity.",
    "screensaver": "Klassische Ruheanzeige: großes Wettersymbol, Uhrzeit, Datum, vier "
    "Vorhersagespalten.",
    "screensaver2": "Alternative Ruheanzeige (ab Backend 4.0) mit deutlich mehr Kacheln.",
}


# --- Entity-Felder ---------------------------------------------------------------------------

# Felder, die ``config.py::Entity`` ausliest. Reihenfolge = Ausgabereihenfolge im Generator.
ENTITY_FIELDS: Final[tuple[str, ...]] = (
    "entity",          # entity_id oder Spezial-Präfix (iText., navigate., …)
    "name",            # Anzeigename (nameOverride)
    "icon",            # mdi-Icon; kann {on, off} sein
    "color",           # RGB-Liste [r,g,b], {on, off} oder Jinja-Template
    "value",           # angezeigter Wert / Template
    "type",            # stype (z. B. input_select, button …)
    "state",           # condState
    "state_not",       # condStateNot
    "state_template",  # condTemplate
    "assumed_state",
    "status",          # zusätzliche Status-Entity
    "font",            # Font-Override
    "data",            # freies dict für kartentyp-spezifische Extras
)

# Felder, die die Renderer direkt aus ``entity_input_config`` lesen, ohne dass ``Entity`` sie kennt.
ENTITY_RENDERER_FIELDS: Final[tuple[str, ...]] = (
    "effectList",  # pages.py: Licht-Effektliste
    "speed",       # pages.py: Lüfter-Geschwindigkeit
)

ENTITY_KNOWN_FIELDS: Final[tuple[str, ...]] = ENTITY_FIELDS + ENTITY_RENDERER_FIELDS

# Entity-artige Karten-Keys: eigenständige Dicts, die wie eine Entity-Zeile aufgebaut sind.
ENTITY_LIKE_CARD_FIELDS: Final[tuple[str, ...]] = (
    "navItem1",
    "navItem2",
    "statusIcon1",
    "statusIcon2",
)

# Keys, die nur an *einem bestimmten* dieser Dicts etwas bewirken. ``altFont`` liest der
# Screensaver-Renderer direkt aus dem Status-Symbol; auf einer gewöhnlichen Entity-Zeile bliebe es
# wirkungslos — deshalb nicht in ENTITY_RENDERER_FIELDS, sondern hier je Feld.
ENTITY_LIKE_EXTRA_FIELDS: Final[dict[str, tuple[str, ...]]] = {
    "statusIcon1": ("altFont",),
    "statusIcon2": ("altFont",),
}


def entity_like_known_fields(field: Any) -> tuple[str, ...]:
    """Bekannte Keys eines entity-artigen Karten-Feldes: Entity-Felder plus dessen Zusatzkeys."""
    if not isinstance(field, str):
        return ENTITY_KNOWN_FIELDS
    return ENTITY_KNOWN_FIELDS + ENTITY_LIKE_EXTRA_FIELDS.get(field, ())


# --- Karten-Felder ---------------------------------------------------------------------------

# Von ``config.py::Card`` für *jede* Karte ausgelesen.
CARD_COMMON_FIELDS: Final[tuple[str, ...]] = (
    "type",
    "key",
    "title",
    "navItem1",
    "navItem2",
    "sleepTimeout",
    "cooldown",
)

# Kartentyp-spezifische Keys, die die Renderer aus ``raw_config`` ziehen (pages.py).
CARD_TYPE_FIELDS: Final[dict[str, tuple[str, ...]]] = {
    "cardEntities": ("temperatureUnit",),
    "cardGrid": ("temperatureUnit",),
    "cardGrid2": ("temperatureUnit",),
    "cardThermo": ("temperatureUnit", "supportedModes"),
    "cardMedia": ("mediaControl",),
    "cardAlarm": ("alarmControl", "supportedModes"),
    "cardQR": ("qrCode",),
    "cardPower": (),
    "cardUnlock": ("pin", "destination"),
    "cardChart": (),
    "screensaver": (
        "theme",
        "weatherUnit",
        "forecastSkip",
        "weatherOverrideForecast1",
        "weatherOverrideForecast2",
        "weatherOverrideForecast3",
        "weatherOverrideForecast4",
        "doubleTapToUnlock",
        "alternativeLayout",
        "defaultCard",
        "statusIcon1",
        "statusIcon2",
    ),
}
CARD_TYPE_FIELDS["screensaver2"] = CARD_TYPE_FIELDS["screensaver"]

# Die Entity-Liste steht im generierten YAML immer am Ende (längster Block).
CARD_ENTITIES_FIELD: Final[str] = "entities"

# Karten mit *einer* Entity, die flach auf der Karte liegt (das Backend baut dort ``Entity(card)``).
SINGLE_ENTITY_CARD_TYPES: Final[tuple[str, ...]] = ("cardThermo", "cardMedia", "cardAlarm")
# Der Screensaver trägt zusätzlich zur flachen Entity noch eine ``entities``-Liste.
FLAT_ENTITY_CARD_TYPES: Final[tuple[str, ...]] = SINGLE_ENTITY_CARD_TYPES + SCREENSAVER_TYPES


# --- Globale Settings ------------------------------------------------------------------------

# Defaults des Backends (``config.py::_DEFAULT_CONFIG``, ohne die strukturierten Blöcke).
# Dienen dem Editor als Platzhalter/Anzeige — sie werden beim Import *nicht* ins Modell gemischt,
# damit generiertes YAML nur enthält, was auch wirklich gesetzt wurde.
GLOBAL_DEFAULTS: Final[dict[str, Any]] = {
    "panelRecvTopic": "tele/tasmota_your_mqtt_topic/RESULT",
    "panelSendTopic": "cmnd/tasmota_your_mqtt_topic/CustomSend",
    "updateMode": "auto-notify",
    "model": "eu",
    "sleepTimeout": 20,
    "sleepBrightness": 20,
    "screenBrightness": 100,
    "defaultBackgroundColor": "ha-dark",
    "featureExperimentalSliders": False,
    "sleepTracking": None,
    "sleepTrackingZones": ["not_home", "off"],
    "sleepOverride": None,
    "locale": "en_US",
    "quiet": True,
    "timeFormat": "%H:%M",
    "dateFormatBabel": "full",
    "dateAdditionalTemplate": "",
    "timeAdditionalTemplate": "",
    "dateFormat": "%A, %d. %B %Y",
    # Die folgenden Keys stehen nicht in ``_DEFAULT_CONFIG`` des Backends, werden aber sehr wohl
    # ausgewertet (``pages.py`` bzw. ``nspanel.py``) — ohne Eintrag hier kennt sie der Editor nicht
    # und der Anwender erfährt nie, dass es sie gibt.
    "timezone": None,
    "displayURL-EU": None,
    "displayURL-US-L": None,
    "displayURL-US-P": None,
    "berryURL": None,
}

# Reihenfolge der globalen Settings im generierten YAML. Nicht gelistete Keys folgen dahinter.
GLOBAL_FIELD_ORDER: Final[tuple[str, ...]] = tuple(GLOBAL_DEFAULTS)

# Blöcke, die nicht zu den globalen Settings zählen.
STRUCTURED_KEYS: Final[frozenset[str]] = frozenset({"screensaver", "cards", "hiddenCards"})


# --- Widget-Hinweise für den Editor -----------------------------------------------------------

# Bevorzugtes Eingabe-Widget je Feldname. **Nur ein Vorschlag für skalare Werte:** trägt ein Feld
# tatsächlich ein Dict oder eine Liste (``icon: {on, off}``, ``sleepBrightness`` als Zeitplan,
# ``color`` als [r,g,b]), schaltet der Editor unabhängig vom Hinweis auf den JSON-Modus. So kann
# kein Wert dadurch verlorengehen, dass die Tabelle hier eine Vereinfachung annimmt.
#
# Typen: string | number | boolean | entity | icon | color | json | entity_object | select
FIELD_HINTS: Final[dict[str, str]] = {
    # Entity-Zeile
    "entity": "entity",
    "name": "string",
    "icon": "icon",
    "color": "color",
    "value": "string",
    "state": "string",
    "state_not": "string",
    "state_template": "string",
    "assumed_state": "boolean",
    "status": "entity",
    "font": "select",
    "data": "json",
    "effectList": "json",
    "speed": "number",
    # Karte
    "type": "select",
    "key": "string",
    "title": "string",
    "navItem1": "entity_object",
    "navItem2": "entity_object",
    "statusIcon1": "entity_object",
    "statusIcon2": "entity_object",
    # Zusatzkey *innerhalb* der Status-Symbole (ENTITY_LIKE_EXTRA_FIELDS), keine Kartenzeile.
    "altFont": "boolean",
    "sleepTimeout": "number",
    "cooldown": "number",
    "temperatureUnit": "select",
    "supportedModes": "json",
    "mediaControl": "json",
    "alarmControl": "entity",
    "qrCode": "string",
    "pin": "string",
    "destination": "string",
    "theme": "json",
    "weatherUnit": "select",
    "forecastSkip": "number",
    "weatherOverrideForecast1": "json",
    "weatherOverrideForecast2": "json",
    "weatherOverrideForecast3": "json",
    "weatherOverrideForecast4": "json",
    "doubleTapToUnlock": "boolean",
    "alternativeLayout": "boolean",
    "defaultCard": "string",
    # Globale Settings
    "panelRecvTopic": "string",
    "panelSendTopic": "string",
    "updateMode": "select",
    "model": "select",
    "sleepBrightness": "number",
    "screenBrightness": "number",
    "defaultBackgroundColor": "select",
    "featureExperimentalSliders": "boolean",
    "sleepTracking": "entity",
    "sleepTrackingZones": "json",
    # Dict aus ``entity`` und ``brightness`` (controller.py), kein einzelner entity_id.
    "sleepOverride": "json",
    "locale": "select",
    "quiet": "boolean",
    "timeFormat": "string",
    "dateFormatBabel": "select",
    "dateAdditionalTemplate": "string",
    "timeAdditionalTemplate": "string",
    "dateFormat": "string",
    "timezone": "select",
    "displayURL-EU": "string",
    "displayURL-US-L": "string",
    "displayURL-US-P": "string",
    "berryURL": "string",
}

# Felder, die das Backend als Jinja-Template rendert — nachgesehen an den ``render_template``-Aufrufen
# des Backends, nicht geraten:
#   name                   pages.py (nameOverride)
#   value                  pages.py — rendert nur bis zum *letzten* ``}`` und hängt den Rest wörtlich
#                          an; genau so entstehen Suffixe wie "…°C"
#   color                  helper.py (rgb_dec565 rendert Strings, bevor es sie als RGB liest)
#   icon                   icon_mapping.py (Sonderformen ``ha:`` und ``<I>…</I>``)
#   state_template         pages.py (condTemplate — als Bedingung ausgewertet)
#   defaultCard            config.py / controller.py
#   qrCode, speed          pages.py
#   date/timeAdditionalTemplate  pages.py (Zusatztext in Screensaver-Datum/-Zeit)
TEMPLATE_FIELDS: Final[tuple[str, ...]] = (
    "name",
    "value",
    "color",
    "icon",
    "state_template",
    "defaultCard",
    "qrCode",
    "speed",
    "dateAdditionalTemplate",
    "timeAdditionalTemplate",
)

# Diese zwei rendert das Backend nur bis zum letzten ``}`` und hängt den Rest unverändert an. Der
# Editor muss das in der Vorschau nachbilden, sonst zeigt sie etwas anderes als das Panel.
TEMPLATE_SUFFIX_FIELDS: Final[tuple[str, ...]] = ("value", "icon")

# Felder, in denen ein Sprungziel steht (``navigate.<key>``). Der Editor schlägt dort die Keys der
# konfigurierten Karten vor, statt sie aus dem Gedächtnis zu verlangen.
#
# Bei den entity-artigen Feldern (``navItem1``/``navItem2``) gilt das für deren ``entity``-Unterfeld
# — dort ist laut Doku (docs.nspanel.pky.eu/subpages) auch eine gewöhnliche entity_id erlaubt, ein
# Navigationsplatz kann also ebenso gut ein Licht schalten. Bei den übrigen für das Feld selbst.
NAVIGATION_FIELDS: Final[tuple[str, ...]] = (
    "navItem1",
    "navItem2",
    "defaultCard",
    "destination",
)


# Auswahllisten für Felder mit Hinweis ``select``. Der Editor lässt trotzdem freie Eingabe zu —
# das Backend kennt womöglich mehr Werte als wir.
FIELD_OPTIONS: Final[dict[str, tuple[str, ...]]] = {
    "model": MODELS,
    "updateMode": ("auto-notify", "auto", "manual"),
    "type": CARD_TYPES,
    "temperatureUnit": ("celsius", "fahrenheit"),
    "weatherUnit": ("celsius", "fahrenheit"),
    "defaultBackgroundColor": ("ha-dark", "black"),
    "dateFormatBabel": ("full", "long", "medium", "short"),
    # Schriftgröße der Symbole auf cardGrid. Das Backend übersetzt diese Namen in Font-IDs und
    # akzeptiert daneben auch direkt eine Zahl (pages.py) — die Liste ist deshalb ein Vorschlag.
    "font": ("small", "medium-icon", "medium", "large"),
    # Von babel unterstützte Sprachen laut docs.nspanel.pky.eu (config-overview). Bestimmt sowohl
    # das Datumsformat als auch die Übersetzung der Beschriftungen auf dem Panel.
    "locale": (
        "de_DE", "en_US", "af_ZA", "ar_SY", "bg_BG", "ca_ES", "cs_CZ", "da_DK", "el_GR", "es_ES",
        "et_EE", "fa_IR", "fi_FI", "fr_FR", "he_IL", "hr_xx", "hu_HU", "hy_AM", "id_ID", "is_IS",
        "it_IT", "lb_xx", "lt_LT", "lv_LV", "nb_NO", "nl_NL", "nn_NO", "pl_PL", "pt_PT", "ro_RO",
        "ru_RU", "sk_SK", "sl_SI", "sv_SE", "th_TH", "tr_TR", "uk_UA", "vi_VN", "zh_CN", "zh_TW",
    ),
    # Nur eine Handreichung für den häufigsten Fall; erlaubt ist jeder tz-Datenbank-Bezeichner.
    "timezone": ("Europe/Berlin", "Europe/Vienna", "Europe/Zurich", "UTC"),
}

# Was das Feld bewirkt — ein Satz, im Zweifel aus der Sicht dessen, was auf dem Panel passiert.
# Quellen: docs.nspanel.pky.eu (config-overview, config-screensaver, entities, card-*) und, wo die
# Doku schweigt oder von der eingesetzten Backend-Version abweicht, der Backend-Quelltext selbst.
FIELD_DESCRIPTIONS: Final[dict[str, str]] = {
    # --- Entity-Zeile ---
    "entity": "Welche Home-Assistant-Entity die Zeile anzeigt und bedient.",
    "name": "Überschreibt den angezeigten Namen (sonst der friendly_name aus HA).",
    "icon": "Überschreibt das Symbol. Auch je Zustand möglich, z. B. on/off getrennt.",
    "color": "Überschreibt die Farbe des Symbols.",
    "value": "Überschreibt den angezeigten Wert rechts in der Zeile.",
    "type": "Erzwingt die Behandlung als ein bestimmter Entity-Typ statt sie aus der entity_id "
    "abzuleiten. Beim Screensaver stattdessen die Nummer der Vorhersagespalte (0–3).",
    "state": "Zeile nur anzeigen, wenn der Zustand exakt diesem Wert entspricht.",
    "state_not": "Zeile nur anzeigen, wenn der Zustand nicht diesem Wert entspricht.",
    "state_template": "Zeile nur anzeigen, wenn dieses Template wahr ergibt.",
    "assumed_state": "Nur für Rollläden: Auf/Stopp/Ab dauerhaft anzeigen, statt sie aus dem "
    "gemeldeten Zustand abzuleiten.",
    "status": "Zusätzliche Entity, deren Zustand Symbol und Farbe bestimmt — gedacht für "
    "navigate.- und service.-Einträge, die selbst keinen Zustand haben.",
    "font": "Schriftgröße des Symbols auf cardGrid.",
    "data": "Zusätzliche Daten für service.-Einträge, z. B. entity_id und Parameter des Aufrufs.",
    "effectList": "Nur für Licht: Auswahl an Effekten, die auf der Detailseite erscheinen soll.",
    "speed": "Nur cardPower: Richtung und Tempo des Laufpunkts zu dieser Entity. "
    "Negative Werte laufen zur Mitte hin.",
    # --- Karte ---
    "key": "Eigener Name für diese Karte, damit navigate.<key> sie ansteuern kann.",
    "title": "Überschrift am oberen Rand der Karte.",
    "navItem1": "Ersetzt die linke Navigationsschaltfläche dieser Karte (Aufbau wie eine Entity).",
    "navItem2": "Ersetzt die rechte Navigationsschaltfläche dieser Karte (Aufbau wie eine Entity).",
    "sleepTimeout": "Überschreibt für diese Karte, nach wie vielen Sekunden der Screensaver kommt.",
    "cooldown": "Frühestens nach so vielen Sekunden neu zeichnen — beruhigt Karten mit schnell "
    "wechselnden Werten.",
    "temperatureUnit": "Einheit, die auf der Karte hinter Temperaturen steht.",
    "supportedModes": "Schränkt die auf der Karte angebotenen Betriebs- bzw. Scharfschaltmodi ein.",
    "mediaControl": "Ersetzt die Aktion der Schaltfläche links oben auf der Medienkarte.",
    "alarmControl": "Ersetzt die Aktion der Schaltfläche links unten. Ohne Angabe zeigt sie nach "
    "einem fehlgeschlagenen Scharfschalten die offenen Sensoren.",
    "qrCode": "Inhalt des QR-Codes. Für WLAN: WIFI:S:<SSID>;T:WPA;P:<Passwort>;; — "
    "wird als Template ausgewertet, das Passwort kann also aus HA kommen.",
    "pin": "PIN, die zum Entsperren eingegeben werden muss.",
    "destination": "Ziel nach erfolgreicher PIN-Eingabe, als navigate.<key> der versteckten Karte.",
    # --- Screensaver ---
    "theme": "Farben der einzelnen Screensaver-Elemente, je Element als [r, g, b].",
    "weatherUnit": "Einheit der Temperaturen auf dem Screensaver.",
    "forecastSkip": "Überspringt so viele Vorhersageeinträge — z. B. 1, um die aktuelle Stunde "
    "auszulassen.",
    "weatherOverrideForecast1": "Ersetzt die erste Vorhersagespalte durch eine eigene Entity.",
    "weatherOverrideForecast2": "Ersetzt die zweite Vorhersagespalte durch eine eigene Entity.",
    "weatherOverrideForecast3": "Ersetzt die dritte Vorhersagespalte durch eine eigene Entity.",
    "weatherOverrideForecast4": "Ersetzt die vierte Vorhersagespalte durch eine eigene Entity.",
    "doubleTapToUnlock": "Verlangt zwei Berührungen zum Verlassen des Screensavers — schützt vor "
    "versehentlichem Schalten.",
    "alternativeLayout": "Alternatives Screensaver-Layout. Es schaltet sich ohnehin selbst ein, "
    "sobald eine 6. Entity konfiguriert ist.",
    "statusIcon1": "Kleines Symbol links neben dem Datum. Aufbau wie eine Entity; zusätzlich hat "
    "es das Feld altFont.",
    "statusIcon2": "Kleines Symbol rechts neben dem Datum. Aufbau wie statusIcon1.",
    "altFont": "Größere Schrift für dieses Status-Symbol. Nur die Status-Symbole der Ruheanzeige "
    "werten den Key aus — auf einer gewöhnlichen Entity-Zeile bleibt er wirkungslos.",
    "defaultCard": "Karte, die nach dem Aufwachen erscheint, als navigate.<key>. Ohne Angabe die "
    "erste Karte. Wird als Template ausgewertet.",
    # --- Globale Settings ---
    "panelRecvTopic": "MQTT-Topic, auf dem Tasmota meldet, was am Panel passiert.",
    "panelSendTopic": "MQTT-Topic, über das die Befehle ans Panel gehen.",
    "updateMode": "Wie die Display-Firmware aktualisiert wird, wenn das Backend neuer ist.",
    "model": "Bauform des Panels. Bestimmt mit, wie viele Einträge auf eine Karte passen.",
    "sleepTimeout": "Sekunden ohne Berührung bis zum Screensaver. 0 schaltet ihn ab.",
    "sleepBrightness": "Helligkeit im Screensaver. Auch als Tagesplan oder als entity_id möglich.",
    "screenBrightness": "Helligkeit während der Bedienung. Gleiche Schreibweisen wie "
    "sleepBrightness.",
    "defaultBackgroundColor": "Hintergrund aller Karten.",
    "featureExperimentalSliders": "Schaltet experimentelle Schieberegler frei.",
    "sleepTracking": "Anwesenheits-Entity. Ist sie abwesend/aus, geht das Display ganz aus. "
    "Hat Vorrang vor sleepOverride.",
    "sleepTrackingZones": "Zustände, die für sleepTracking als abwesend gelten.",
    "sleepOverride": "Hebt die Screensaver-Helligkeit an, solange eine Entity an ist — etwa "
    "damit das Panel bei Licht im Raum sichtbar bleibt.",
    "locale": "Sprache der Panel-Beschriftungen und Grundlage des Datumsformats.",
    "quiet": "Unterdrückt ausführliche Log-Ausgaben des Backends.",
    "timeFormat": "Uhrzeitformat. Was hinter einem ? steht, landet in einem eigenen kleineren "
    "Textfeld — so bekommt man AM/PM klein gesetzt.",
    "dateFormatBabel": "Ausführlichkeit des Datums, wenn babel installiert ist (Normalfall).",
    "dateAdditionalTemplate": "Zusatztext hinter dem Datum, Template erlaubt.",
    "timeAdditionalTemplate": "Zusatztext unter der Uhrzeit, Template erlaubt.",
    "dateFormat": "Datumsformat als Ausweichlösung, falls babel fehlt.",
    "timezone": "Zeitzone für die Uhr auf dem Panel. Ohne Angabe die Zeit des AppDaemon-Servers.",
    "displayURL-EU": "Eigene Bezugsquelle für die Display-Firmware des EU-Modells — nur nötig, "
    "wenn das Panel nicht ins Internet darf.",
    "displayURL-US-L": "Wie displayURL-EU, für das US-Modell im Querformat.",
    "displayURL-US-P": "Wie displayURL-EU, für das US-Modell im Hochformat.",
    "berryURL": "Eigene Bezugsquelle für das Tasmota-Berry-Skript (autoexec.be).",
}

# Welche Werte zulässig sind — die zweite Hälfte der Frage, die der Feldname nie beantwortet.
# Der Editor zeigt das direkt unter der Beschreibung. Bewusst als Klartext und nicht als
# maschinenlesbare Regel: geprüft wird hier nichts, das Backend bleibt die letzte Instanz.
FIELD_VALUE_HINTS: Final[dict[str, str]] = {
    # --- Entity-Zeile ---
    "entity": "entity_id wie light.wohnzimmer · iText.<text> für festen Text · "
    "navigate.<key> zum Blättern auf eine andere Karte · service.<domain>.<dienst> für einen "
    "Dienstaufruf (Parameter dann unter data) · delete lässt den Platz frei",
    "name": "Freier Text oder Template",
    "icon": "mdi:<name> aus der Icon-Liste des Backends · {on: …, off: …} je Zustand · "
    "text:<text> statt Symbol · ha:<template> für berechnete Inhalte",
    "color": "[r, g, b] mit 0–255 · {on: [r,g,b], off: [r,g,b]} je Zustand · Template, das eine "
    "solche Liste liefert",
    "value": "Freier Text oder Template. Text nach der letzten } bleibt unverändert stehen — so "
    "entstehen Einheiten wie {{ … }} °C",
    "type": "Entity-Typ wie light, switch, sensor, shutter · beim Screensaver 0–3 für die "
    "Vorhersagespalte",
    "state": "Der Zustandswert als Text, z. B. on, off, home",
    "state_not": "Der Zustandswert als Text, z. B. on, off, home",
    "state_template": "Template, das true oder false ergibt",
    "assumed_state": "true oder false",
    "status": "entity_id",
    "font": "small, medium-icon, medium, large — oder direkt eine Font-Nummer",
    "data": "Zuordnung von Parametern, z. B. entity_id: light.küche",
    "effectList": "Liste von Effektnamen, z. B. [Android, Aurora]",
    "speed": "Ganzzahl −100 bis 100, auch als Template",
    # --- Karte ---
    "key": "Kurzer Name ohne Leer- und Sonderzeichen, z. B. wohnzimmer",
    "title": "Freier Text",
    "navItem1": "Aufbau wie eine Entity, üblich sind entity: navigate.<key> und icon",
    "navItem2": "Aufbau wie eine Entity, üblich sind entity: navigate.<key> und icon",
    "sleepTimeout": "Sekunden als Ganzzahl, 0 schaltet den Screensaver ab",
    "cooldown": "Sekunden, auch mit Nachkommastelle (z. B. 0.5)",
    "temperatureUnit": "celsius oder fahrenheit",
    "supportedModes": "Liste, z. B. [heat, off] bei cardThermo oder [arm_away, arm_night] bei "
    "cardAlarm",
    "mediaControl": "Aufbau wie eine Entity",
    "alarmControl": "entity_id",
    "qrCode": "Freier Text oder Template",
    "pin": "Ziffernfolge, Standard 3830",
    "destination": "navigate.<key> einer Karte aus hiddenCards",
    # --- Screensaver ---
    "theme": "Zuordnung von Element zu [r, g, b], z. B. date: [255, 0, 0]. Mögliche Elemente: "
    "background, time, timeAMPM, date, tMainText, bar, tTimeAdd, tMainTextAlt2 sowie "
    "tForecast1–4 und tForecast1Val–4Val",
    "weatherUnit": "celsius oder fahrenheit",
    "forecastSkip": "Ganzzahl ab 0",
    "weatherOverrideForecast1": "Aufbau wie eine Entity",
    "weatherOverrideForecast2": "Aufbau wie eine Entity",
    "weatherOverrideForecast3": "Aufbau wie eine Entity",
    "weatherOverrideForecast4": "Aufbau wie eine Entity",
    "doubleTapToUnlock": "true oder false",
    "alternativeLayout": "true oder false",
    "statusIcon1": "Aufbau wie eine Entity, zusätzlich altFont",
    "statusIcon2": "Aufbau wie eine Entity, zusätzlich altFont",
    "altFont": "true oder false",
    "defaultCard": "navigate.<key>, auch als Template",
    # --- Globale Settings ---
    "panelRecvTopic": "MQTT-Topic, z. B. NSPanel_1/tele/RESULT",
    "panelSendTopic": "MQTT-Topic, z. B. NSPanel_1/cmnd/CustomSend",
    "updateMode": "auto-notify (nachfragen), auto (sofort) oder manual (nie von selbst)",
    "model": "eu, us-l (Querformat) oder us-p (Hochformat)",
    "sleepBrightness": "0–100 · oder eine Liste aus time und value (Uhrzeit, sunrise, "
    "\"sunset + 1:00:00\") · oder die entity_id eines input_number",
    "screenBrightness": "0–100, sonst wie sleepBrightness",
    "defaultBackgroundColor": "ha-dark oder black",
    "featureExperimentalSliders": "true oder false",
    "sleepTracking": "entity_id einer person, eines device_tracker oder einer group",
    "sleepTrackingZones": "Liste von Zuständen, Standard [not_home, off]",
    "sleepOverride": "entity und brightness zusammen, z. B. "
    "{entity: light.schlafzimmer, brightness: 20}",
    "locale": "Sprachcode wie de_DE oder en_US",
    "quiet": "true oder false",
    "timeFormat": "strftime-Muster, z. B. %H:%M — oder \"%I:%M   ?%p\" für 12 Stunden mit AM/PM",
    "dateFormatBabel": "full, long, medium oder short",
    "dateAdditionalTemplate": "Freier Text oder Template",
    "timeAdditionalTemplate": "Freier Text oder Template",
    "dateFormat": "strftime-Muster, z. B. %A, %d. %B %Y",
    "timezone": "Zeitzonenname wie Europe/Berlin",
    "displayURL-EU": "http(s)-Adresse einer .tft-Datei",
    "displayURL-US-L": "http(s)-Adresse einer .tft-Datei",
    "displayURL-US-P": "http(s)-Adresse einer .tft-Datei",
    "berryURL": "http(s)-Adresse einer .be-Datei",
}

# Felder, deren Bedeutung sich je Kartentyp ändert. Überschreiben FIELD_DESCRIPTIONS für genau
# diesen Typ; alles Übrige bleibt bei der allgemeinen Beschreibung.
CARD_FIELD_DESCRIPTIONS: Final[dict[str, dict[str, str]]] = {
    "cardThermo": {"entity": "Die climate-Entity, die diese Karte steuert."},
    "cardMedia": {
        "entity": "Der media_player, den diese Karte steuert.",
        "status": "Zusätzliche Entity für Symbol und Farbe links oben.",
    },
    "cardAlarm": {"entity": "Die alarm_control_panel-Entity, die diese Karte bedient."},
    "cardChart": {"entity": "Die Entity, deren Verlauf das Diagramm zeigt."},
    "screensaver": {
        "entity": "Die Wetter-Entity des Screensavers. Ohne entities-Liste baut das Backend daraus "
        "automatisch Hauptsymbol und vier Vorhersagespalten.",
        "theme": "Farben der Screensaver-Elemente.",
    },
    "screensaver2": {
        "entity": "Die Wetter-Entity des Screensavers.",
        # Der color~-Befehl adressiert die Elemente des klassischen Layouts; screensaver2 hat
        # andere Bausteine, deshalb greift theme dort bestenfalls teilweise.
        "theme": "Für dieses Layout nicht vorgesehen — die Farbschlüssel gehören zum klassischen "
        "Screensaver. Der Wert bleibt erhalten, wirkt hier aber allenfalls teilweise.",
    },
}

# Keys, die immer wieder gesetzt werden, obwohl das Backend sie nirgends liest — sie stehen dann
# wirkungslos in der YAML. Der Editor weist darauf hin, löscht aber nichts.
KNOWN_IGNORED_FIELDS: Final[dict[str, str]] = {
    "unit": "Das Backend liest kein unit. Die Einheit kommt aus dem Attribut unit_of_measurement "
    "der Entity in Home Assistant; für eigenen Text stattdessen value verwenden, z. B. "
    "\"{{ states('sensor.x') }} kWh\".",
    "unit_of_measurement": "Wird aus Home Assistant übernommen und hier nicht ausgewertet — "
    "für eigenen Text stattdessen value verwenden.",
}


def schema_payload() -> dict[str, Any]:
    """Maschinenlesbare Schema-Beschreibung für den Editor im Frontend.

    Damit bleibt ``schema.py`` die einzige Quelle der Wahrheit: das Panel baut seine Formulare aus
    dieser Antwort, statt die Feldlisten in JavaScript zu duplizieren (und dort veralten zu lassen).
    """
    return {
        "cardTypes": list(CARD_TYPES),
        "screensaverTypes": list(SCREENSAVER_TYPES),
        "models": list(MODELS),
        "cardCommonFields": list(CARD_COMMON_FIELDS),
        "cardTypeFields": {key: list(value) for key, value in CARD_TYPE_FIELDS.items()},
        "entityFields": list(ENTITY_KNOWN_FIELDS),
        "entityLikeCardFields": list(ENTITY_LIKE_CARD_FIELDS),
        # Zusatzkeys je entity-artigem Feld — der Editor hängt sie unter die Entity-Felder.
        "entityLikeExtraFields": {
            key: list(value) for key, value in ENTITY_LIKE_EXTRA_FIELDS.items()
        },
        "entitiesField": CARD_ENTITIES_FIELD,
        "globalFieldOrder": list(GLOBAL_FIELD_ORDER),
        "globalDefaults": GLOBAL_DEFAULTS,
        "fieldHints": FIELD_HINTS,
        "fieldOptions": {key: list(value) for key, value in FIELD_OPTIONS.items()},
        "fieldDescriptions": FIELD_DESCRIPTIONS,
        # Zulässige Werte je Feld, als Klartext unter der Beschreibung.
        "fieldValueHints": FIELD_VALUE_HINTS,
        # Beschreibungen, die nur für einen bestimmten Kartentyp gelten.
        "cardFieldDescriptions": CARD_FIELD_DESCRIPTIONS,
        # Wie viele Entities das Display je Kartentyp und Modell wirklich zeigt.
        "cardCapacity": {key: dict(value) for key, value in CARD_CAPACITY.items()},
        "capacityLayoutNotes": CAPACITY_LAYOUT_NOTES,
        "cardTypeNotes": CARD_TYPE_NOTES,
        "cardsWithoutEntityList": list(CARDS_WITHOUT_ENTITY_LIST),
        "gridAutoSwitchAt": GRID_AUTO_SWITCH_AT,
        "knownIgnoredFields": KNOWN_IGNORED_FIELDS,
        # Felder, für die der Editor den Template-Modus anbietet (siehe TEMPLATE_FIELDS).
        "templateFields": list(TEMPLATE_FIELDS),
        "templateSuffixFields": list(TEMPLATE_SUFFIX_FIELDS),
        # Felder, für die der Editor die Keys der konfigurierten Karten vorschlägt.
        "navigationFields": list(NAVIGATION_FIELDS),
        # Karten, die ihre eine Entity flach auf der Karte tragen (siehe card_known_fields).
        "flatEntityCardTypes": list(FLAT_ENTITY_CARD_TYPES),
        # Davon die, die *nur* diese eine Entity haben — für sie blendet der Editor die
        # Entity-Liste aus. Der Screensaver hat beides: flache Entity *und* entities-Liste.
        "singleEntityCardTypes": list(SINGLE_ENTITY_CARD_TYPES),
    }


def capacity_for(card_type: Any, model: Any = None) -> int | None:
    """Wie viele Entities dieser Kartentyp auf diesem Panel-Modell anzeigt.

    ``None`` heißt "unbekannt oder keine Entity-Liste" — dann macht der Editor keine Aussage,
    statt eine zu erfinden. Unbekannte Modelle fallen auf ``eu`` zurück, weil das der Standard des
    Backends ist.
    """
    if not isinstance(card_type, str):
        return None
    by_model = CARD_CAPACITY.get(card_type)
    if by_model is None:
        return None
    if not isinstance(model, str) or model not in by_model:
        model = "eu"
    return by_model[model]


def effective_card_type(card_type: Any, entity_count: int) -> Any:
    """Der Kartentyp, den das Backend daraus tatsächlich macht.

    Einziger Fall: ``cardGrid`` mit mehr als ``GRID_AUTO_SWITCH_AT`` Entities wird vom Backend
    selbst auf ``cardGrid2`` umgestellt (pages.py). Wer das nicht weiß, wundert sich über ein
    plötzlich anderes Layout — und über eine Kapazitätswarnung, die gar keine sein dürfte.
    """
    if card_type == "cardGrid" and entity_count > GRID_AUTO_SWITCH_AT:
        return "cardGrid2"
    return card_type


def card_known_fields(card_type: Any, has_flat_entity: bool = False) -> tuple[str, ...]:
    """Alle Keys, die für diesen Kartentyp ein benanntes Feld bekommen (in Ausgabereihenfolge).

    ``has_flat_entity``: Karten mit *einer* Entity (cardThermo, cardMedia, cardAlarm, Screensaver …)
    tragen deren Felder flach auf der Karte selbst — das Backend baut dort ``Entity(card_config)``.
    """
    fields: list[str] = list(CARD_COMMON_FIELDS)
    if isinstance(card_type, str):
        fields.extend(CARD_TYPE_FIELDS.get(card_type, ()))
    if has_flat_entity:
        fields.extend(ENTITY_KNOWN_FIELDS)
    fields.append(CARD_ENTITIES_FIELD)
    # Reihenfolge des ersten Auftretens beibehalten, Duplikate raus.
    return tuple(dict.fromkeys(fields))


def empty_model() -> dict[str, Any]:
    """Leeres, aber strukturell gültiges Ausgangsmodell für einen frischen Editor."""
    return {
        "global": {
            "panelRecvTopic": GLOBAL_DEFAULTS["panelRecvTopic"],
            "panelSendTopic": GLOBAL_DEFAULTS["panelSendTopic"],
            "model": "eu",
            "updateMode": "auto-notify",
            "locale": "de_DE",
            "timeFormat": "%H:%M",
            "dateFormat": "%A, %d. %B %Y",
        },
        "screensaver": {"type": "screensaver2", "entities": [], "extra": {}},
        "cards": [],
        "hiddenCards": [],
    }


def _navigation_targets(card: Any) -> list[tuple[str, str]]:
    """Alle ``navigate.<ziel>`` einer Karte als ``(ziel, quelle)``.

    Gegenstück zu ``www/panel/nav-tree.js`` – dort für die Baumansicht, hier für die Prüfung.
    """
    if not isinstance(card, dict):
        return []
    targets: list[tuple[str, str]] = []
    for entity in card.get(CARD_ENTITIES_FIELD) or []:
        value = entity.get("entity") if isinstance(entity, dict) else None
        if isinstance(value, str) and value.strip().startswith("navigate."):
            targets.append((value.strip()[len("navigate.") :], "entities"))
    for field in ("navItem1", "navItem2"):
        value = card.get(field)
        if isinstance(value, dict):
            value = value.get("entity")
        if isinstance(value, str) and value.strip().startswith("navigate."):
            targets.append((value.strip()[len("navigate.") :], field))
    return targets


def _card_aliases(card: Any) -> set[str]:
    """Unter welchen Namen ``navigate.<…>`` diese Karte findet.

    ``search_card`` (config.py im Backend) probiert erst die zusammengesetzte ``card.id``
    ``<typ>_<key>`` und danach den blanken ``key`` – beide Schreibweisen sind gültig.
    """
    if not isinstance(card, dict):
        return set()
    key = card.get("key")
    if not isinstance(key, str) or not key:
        return set()
    aliases = {key}
    card_type = card.get("type")
    if isinstance(card_type, str):
        legacy = f"{card_type}_{key}"
        for zeichen in ".~ ":
            legacy = legacy.replace(zeichen, "_")
        aliases.add(legacy)
    return aliases


def _check_navigation(model: dict[str, Any]) -> list[dict[str, str]]:
    """Prüfe, ob am Gerät jede Karte erreichbar ist.

    Das ist der stille Fehler, der einer gültigen YAML nicht anzusehen ist: Sichtbare Karten hängen
    über die beiden oberen Blättertasten zusammen, versteckte Karten erreicht man **nur** über ein
    ``navigate.<key>``. Wer nun eine Blättertaste mit ``navItem1``/``navItem2`` überschreibt, kappt
    die Kette – alle Karten dahinter sind weg, ohne dass irgendetwas eine Fehlermeldung ausgibt.
    Genau so gingen in einer echten Konfiguration drei Karten verloren.
    """
    findings: list[dict[str, str]] = []
    visible = [c for c in (model.get("cards") or []) if isinstance(c, dict)]
    hidden = [c for c in (model.get("hiddenCards") or []) if isinstance(c, dict)]
    screensaver = model.get("screensaver")

    # 1. Doppelte Keys: ``navigate.<key>`` trifft dann immer nur die erste Karte (config.py,
    #    ``search_card`` liefert den ersten Treffer), die zweite ist so nicht mehr ansprechbar.
    by_key: dict[str, str] = {}
    for path, cards in (("cards", visible), ("hiddenCards", hidden)):
        for index, card in enumerate(cards):
            key = card.get("key")
            if not isinstance(key, str) or not key:
                continue
            where = f"{path}[{index}]"
            if key in by_key:
                findings.append(
                    {
                        "level": "error",
                        "path": f"{where}.key",
                        "message": f"Key '{key}' ist schon bei {by_key[key]} vergeben. "
                        f"'navigate.{key}' führt immer zur ersten Karte – diese hier ist so nicht "
                        f"erreichbar.",
                    }
                )
            else:
                by_key[key] = where

    known: set[str] = set()
    for card in [*visible, *hidden, screensaver]:
        known |= _card_aliases(card)

    # 2. Sprungziele, zu denen es keine Karte gibt. ``uuid.``-Ziele vergibt das Backend zur
    #    Laufzeit selbst; die stehen nie im Modell und werden deshalb übersprungen.
    reached: set[str] = set()
    quellen: list[tuple[str, Any]] = [
        *((f"cards[{i}]", c) for i, c in enumerate(visible)),
        *((f"hiddenCards[{i}]", c) for i, c in enumerate(hidden)),
    ]
    default_card = (screensaver or {}).get("defaultCard") if isinstance(screensaver, dict) else None
    if isinstance(default_card, str) and default_card.strip().startswith("navigate."):
        quellen.append(("screensaver", {"entities": [{"entity": default_card}]}))

    for path, card in quellen:
        for target, source in _navigation_targets(card):
            reached.add(target)
            if target.startswith("uuid.") or target in known:
                continue
            findings.append(
                {
                    "level": "error",
                    "path": f"{path}.{source}" if path != "screensaver" else "screensaver.defaultCard",
                    "message": f"'navigate.{target}' zeigt auf keine Karte – es gibt keine Karte "
                    f"mit dem Key '{target}'. Die Taste bleibt wirkungslos.",
                }
            )

    # 3. Versteckte Karten, die niemand verlinkt: am Gerät schlicht nicht aufrufbar. Sie tauchen in
    #    keiner Blätterkette auf – ein ``navigate.…`` ist der einzige Weg dorthin.
    for index, card in enumerate(hidden):
        key = card.get("key")
        if isinstance(key, str) and key and _card_aliases(card) & reached:
            continue
        if isinstance(key, str) and key:
            hinweis = f"Keine Karte enthält 'navigate.{key}'."
        else:
            hinweis = "Sie hat keinen 'key', über den ein 'navigate.…' sie ansprechen könnte."
        label = card.get("title") or key or f"hiddenCards[{index}]"
        findings.append(
            {
                "level": "warning",
                "path": f"hiddenCards[{index}]",
                "message": f"Versteckte Karte „{label}“ ist am Panel nicht erreichbar. {hinweis}",
            }
        )

    # 4. Beide Blättertasten überschrieben – die Ursache von Fall 3. Eine einzelne Überschreibung
    #    ist normal (ein „zurück"-Knopf), aber wer beide belegt, kappt die Kette: von dieser Karte
    #    aus kommt man zu den folgenden sichtbaren Karten überhaupt nicht mehr.
    for index, card in enumerate(visible):
        if len(visible) < 3 or card.get("navItem1") is None or card.get("navItem2") is None:
            continue
        findings.append(
            {
                "level": "warning",
                "path": f"cards[{index}].navItem1",
                "message": "navItem1 und navItem2 ersetzen beide Blättertasten. Die Kette durch die "
                "sichtbaren Karten endet hier – die folgenden Karten sind nur noch über ein "
                "'navigate.…' erreichbar, nicht mehr durch Blättern.",
            }
        )

    return findings


def validate_model(model: dict[str, Any]) -> list[dict[str, str]]:
    """Prüfe das Modell auf Auffälligkeiten und liefere eine Liste von Befunden.

    Kein Blocker für das Generieren — das Backend ist tolerant und unbekannte Keys sind gewollt
    erlaubt. Die Befunde sind für den Editor gedacht (Hinweise neben dem betroffenen Feld).
    Level: ``error`` = Backend läuft damit sicher in einen Fehler, ``warning`` = vermutlich Tippfehler.
    """
    findings: list[dict[str, str]] = []
    panel_model = (model.get("global") or {}).get("model")

    def check_card(card: Any, path: str) -> None:
        if not isinstance(card, dict):
            findings.append({"level": "error", "path": path, "message": "Karte ist kein Objekt"})
            return
        card_type = card.get("type")
        if not isinstance(card_type, str):
            findings.append({"level": "error", "path": path, "message": "Karte ohne 'type'"})
        elif card_type not in CARD_TYPES and card_type not in SCREENSAVER_TYPES:
            findings.append(
                {"level": "warning", "path": path, "message": f"Unbekannter Kartentyp '{card_type}'"}
            )
        entities = card.get(CARD_ENTITIES_FIELD) or []
        # Wirkungslose Keys je Karte sammeln statt je Zeile melden – sonst steht dieselbe
        # Erklärung fünfmal untereinander.
        ignored_rows: dict[str, list[int]] = {}
        for index, entity in enumerate(entities):
            entity_path = f"{path}.entities[{index}]"
            if not isinstance(entity, dict):
                findings.append(
                    {"level": "error", "path": entity_path, "message": "Entity-Zeile ist kein Objekt"}
                )
                continue
            if not entity.get("entity"):
                findings.append(
                    {"level": "error", "path": entity_path, "message": "Entity-Zeile ohne 'entity'"}
                )
            # Wichtig: unbekannte Keys stehen nach dem Import nicht direkt auf der Entity, sondern
            # in ihrem ``extra``-Dict (importer.entity_to_model). Genau dort landet auch ``unit``.
            vorhanden = set(entity) | set(entity.get("extra") or {})
            for key in KNOWN_IGNORED_FIELDS:
                if key in vorhanden:
                    ignored_rows.setdefault(key, []).append(index + 1)
        for key, rows in ignored_rows.items():
            positions = ", ".join(str(row) for row in rows)
            findings.append(
                {
                    "level": "warning",
                    "path": f"{path}.entities",
                    "message": f"'{key}' in Zeile {positions} bleibt wirkungslos. "
                    f"{KNOWN_IGNORED_FIELDS[key]}",
                }
            )

        # Zu viele Entities sind der stille Fehler schlechthin: die YAML ist gültig, das Backend
        # meldet nichts, und auf dem Panel fehlen die überzähligen Einträge einfach.
        shown_type = effective_card_type(card_type, len(entities))
        capacity = capacity_for(shown_type, panel_model)
        if capacity is not None and len(entities) > capacity:
            model_note = f" (Modell {panel_model})" if isinstance(panel_model, str) else ""
            switch_note = (
                f" – bei über {GRID_AUTO_SWITCH_AT} Entities zeigt das Backend die Karte als "
                f"{shown_type}"
                if shown_type != card_type
                else ""
            )
            findings.append(
                {
                    "level": "warning",
                    "path": f"{path}.entities",
                    "message": f"{len(entities)} Entities, aber {shown_type} zeigt auf diesem "
                    f"Panel nur {capacity}{model_note}{switch_note}. Ab Nummer {capacity + 1} "
                    f"erscheint nichts mehr auf dem Display.",
                }
            )
        # Der Screensaver hat einen zweiten stillen Fall: mit sechs Entities schaltet das Display
        # quer auf das alternative Layout und blendet dabei die erste Vorhersagespalte aus. Die
        # fünfte Entity ist dann konfiguriert, wird gesendet — und trotzdem nirgends angezeigt.
        if (
            card_type == "screensaver"
            and len(entities) >= 6
            and panel_model in (None, "eu", "us-l")
        ):
            findings.append(
                {
                    "level": "warning",
                    "path": f"{path}.entities",
                    "message": "Ab der 6. Entity schaltet das Display auf das alternative Layout: "
                    "die 1. und die 6. Entity bilden dann den Hauptbereich, die erste "
                    "Vorhersagespalte entfällt und die übrigen rücken nach rechts. Die 5. Entity "
                    "verliert dadurch ihren Platz (nur quer – auf us-p bleiben alle sichtbar).",
                }
            )

        if capacity is None and entities and card_type in CARDS_WITHOUT_ENTITY_LIST:
            findings.append(
                {
                    "level": "warning",
                    "path": f"{path}.entities",
                    "message": f"{card_type} wertet keine entities-Liste aus – die Karte zeigt "
                    f"nur die eine Entity, die direkt auf ihr konfiguriert ist.",
                }
            )

    if model.get("screensaver") is not None:
        check_card(model["screensaver"], "screensaver")
    for index, card in enumerate(model.get("cards") or []):
        check_card(card, f"cards[{index}]")
    for index, card in enumerate(model.get("hiddenCards") or []):
        check_card(card, f"hiddenCards[{index}]")

    findings.extend(_check_navigation(model))

    global_settings = model.get("global") or {}
    panel_model = global_settings.get("model")
    if panel_model is not None and panel_model not in MODELS:
        findings.append(
            {"level": "warning", "path": "global.model", "message": f"Unbekanntes Panel-Modell '{panel_model}'"}
        )
    return findings
