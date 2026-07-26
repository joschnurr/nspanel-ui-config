"""Mitschnitt dessen, was das Backend gerade ans Display schickt.

**Warum das die Vorschau besser macht:** aus dem Modell lässt sich nachbauen, *wo* etwas erscheint —
aber nicht alles, *was* dort steht. Symbole ohne eigene Angabe leitet das Backend aus Domain und
Zustand ab, Werte formatiert es selbst. Wer ein laufendes Panel hat, muss das nicht nachbauen: über
MQTT geht die fertig gerenderte Zeile ohnehin ans Display. Die Integration hört mit und zeigt sie.

**Ausschließlich lesend.** Hier wird abonniert, nie veröffentlicht. Das ist kein Zufall, sondern der
Grund, warum das gefahrlos auch am produktiven Broker läuft: eine einzige Nachricht auf dem
Sende-Topic würde das echte Panel umschalten.

Was mitgeschnitten wird, steht in ``protocol.py``. Hier geht es nur darum, *wann* welche Nachricht
gilt: das Backend schickt erst ``pageType~<karte>`` und dann den Inhalt, und ohne den vorherigen
``pageType`` lässt sich der Inhalt nicht zuordnen.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from .protocol import parse_message, parse_page_type

_LOGGER = logging.getLogger(__name__)

# Wie lange ein Mitschnitt als "aktuell" gilt. Danach wird er weiter angezeigt, aber als alt
# gekennzeichnet — ein Panel, das seit Stunden im Ruhezustand ist, hat nichts Neues gesendet.
FRISCH_SEKUNDEN = 300


class LiveState:
    """Der zuletzt beobachtete Stand des Displays.

    Bewusst ohne Home-Assistant-Bezug: so lässt sich das Zusammenspiel von ``pageType`` und Inhalt
    testen, ohne MQTT oder HA zu starten.
    """

    def __init__(self, topic: str | None = None) -> None:
        self.topic = topic
        self.card_type: str | None = None
        self.message: dict[str, Any] | None = None
        self.seen: float | None = None
        self.page_seen: float | None = None
        self.ignoriert = 0

    def handle(self, payload: str, jetzt: float | None = None) -> bool:
        """Verarbeite eine Nachricht. Rückgabe: hat sich der angezeigte Stand geändert?"""
        jetzt = time.time() if jetzt is None else jetzt

        seite = parse_page_type(payload)
        if seite is not None:
            # Der Kartenwechsel allein ändert die Anzeige noch nicht — der Inhalt kommt gleich
            # hinterher. Bis dahin gilt der alte Mitschnitt, sonst flackert die Vorschau leer.
            self.card_type = seite
            self.page_seen = jetzt
            return False

        geparst = parse_message(payload, self.card_type)
        if geparst is None:
            self.ignoriert += 1
            return False

        self.message = geparst
        self.seen = jetzt
        # Der Screensaver meldet sich mit eigener Nachricht, ohne vorherigen pageType.
        if geparst.get("cardType"):
            self.card_type = geparst["cardType"]
        return True

    def as_dict(self, jetzt: float | None = None) -> dict[str, Any]:
        """Der Stand als JSON-taugliches Dict für die API."""
        jetzt = time.time() if jetzt is None else jetzt
        alter = None if self.seen is None else max(0.0, jetzt - self.seen)
        return {
            "topic": self.topic,
            "cardType": self.card_type,
            "message": self.message,
            "ageSeconds": alter,
            "fresh": alter is not None and alter <= FRISCH_SEKUNDEN,
            "ignored": self.ignoriert,
        }


def send_topic_of(model: dict[str, Any] | None) -> str | None:
    """Das Topic, auf dem das Backend ans Panel sendet — aus dem gepflegten Modell.

    Genau dieses Topic trägt die gerenderten Zeilen. Steht keines im Modell, gibt es nichts
    mitzuhören; geraten wird nicht, denn ein falsches Abo wäre still wirkungslos.
    """
    if not isinstance(model, dict):
        return None
    global_settings = model.get("global")
    if not isinstance(global_settings, dict):
        return None
    topic = global_settings.get("panelSendTopic")
    return topic.strip() if isinstance(topic, str) and topic.strip() else None


async def async_start(hass: Any, data: dict[str, Any]) -> Callable[[], None] | None:
    """Abonniere das Sende-Topic, wenn Home Assistant MQTT hat und ein Topic bekannt ist.

    Rückgabe ist die Abmeldefunktion — oder ``None``, wenn nicht abonniert wurde. Der Grund dafür
    steht danach in ``data["live_reason"]``, damit das Panel erklären kann, warum es nichts sieht,
    statt nur nichts anzuzeigen.
    """
    topic = send_topic_of(data.get("model"))
    if topic is None:
        data["live_reason"] = "Kein panelSendTopic im Modell – erst importieren oder eintragen."
        return None
    if "mqtt" not in getattr(hass.config, "components", set()):
        data["live_reason"] = "Die MQTT-Integration ist in Home Assistant nicht eingerichtet."
        return None

    # Erst hier importieren: ohne MQTT-Integration existiert das Modul nicht, und die Tests sollen
    # ohne Home Assistant laufen (gleiche Überlegung wie beim aiohttp-Import in reload.py).
    from homeassistant.components import mqtt  # noqa: PLC0415

    zustand = LiveState(topic)
    data["live"] = zustand

    @callback_kompatibel
    def _empfangen(msg: Any) -> None:
        nutzlast = getattr(msg, "payload", None)
        if isinstance(nutzlast, bytes):
            nutzlast = nutzlast.decode("utf-8", errors="replace")
        zustand.handle(nutzlast)

    try:
        unsubscribe = await mqtt.async_subscribe(hass, topic, _empfangen, qos=0)
    except Exception as err:  # noqa: BLE001 – Broker weg, keine Rechte, Topic ungültig …
        data["live_reason"] = f"Abonnement fehlgeschlagen: {err}"
        _LOGGER.warning("Live-Mitschnitt nicht möglich: %s", err)
        return None

    data.pop("live_reason", None)
    _LOGGER.info("Live-Mitschnitt hört auf %s mit", topic)
    return unsubscribe


async def async_restart(hass: Any, data: dict[str, Any]) -> None:
    """Melde ein bestehendes Abo ab und richte es neu ein.

    Nötig nach jedem Speichern: mit dem Modell kann sich das Sende-Topic ändern, und ein Abo auf
    dem alten Topic bliebe still wirkungslos.
    """
    alt = data.pop("live_unsub", None)
    if alt is not None:
        try:
            alt()
        except Exception:  # noqa: BLE001 – beim Abmelden ist nichts mehr zu retten
            _LOGGER.debug("Abmelden vom alten Topic fehlgeschlagen", exc_info=True)
    data.pop("live", None)
    unsub = await async_start(hass, data)
    if unsub is not None:
        data["live_unsub"] = unsub


def callback_kompatibel(func):
    """Markiert den Empfänger als HA-Callback, ohne dass die Tests Home Assistant brauchen."""
    try:
        from homeassistant.core import callback  # noqa: PLC0415

        return callback(func)
    except ImportError:
        return func
