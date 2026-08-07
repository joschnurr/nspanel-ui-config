// Tests der Vorschau – Geometrie (preview-layouts.js) und Inhalt (previewContent & Co.).
//
// Beides ist bewusst DOM-frei gehalten, damit genau das prüfbar ist, woran die Vorschau falsch
// werden könnte: zu viele oder zu wenige Plätze, eine verschobene Reihenfolge, ein erfundener Wert.
// Das Zeichnen selbst (ha-icon, Positionierung) sieht man nur im Browser.

import assert from "node:assert/strict";
import { test } from "node:test";

const panel = await import(
  "../custom_components/nspanel_ui_config/www/panel/nspanel-ui-config-panel.js"
);
const layouts = await import(
  "../custom_components/nspanel_ui_config/www/panel/preview-layouts.js"
);

const { previewSlots, entitySlots, SCREEN } = layouts;
const icons = await import(
  "../custom_components/nspanel_ui_config/www/panel/icon-names.js"
);
const iconChars = await import(
  "../custom_components/nspanel_ui_config/www/panel/icon-chars.js"
);

const {
  entityKind,
  previewColor,
  previewContent,
  wetterDarstellung,
  iconFromRendered,
  iconNameFromChar,
  istIconZeichen,
  gridSensorText,
  liveContent,
  statusIconTeile,
  liveStatusContent,
  joinTemplates,
  splitTemplateResult,
} = panel;

// Die Kapazitätstabelle aus schema.py – hier nur als *Eingabe* der Tests. Die Vorschau kennt sie
// nicht; sie bekommt die Zahl übergeben, damit Schema und Darstellung nicht auseinanderlaufen können.
const KAPAZITAET = {
  cardEntities: { eu: 4, "us-l": 4, "us-p": 6 },
  cardGrid: { eu: 6, "us-l": 6, "us-p": 6 },
  cardGrid2: { eu: 8, "us-l": 8, "us-p": 9 },
  cardQR: { eu: 2, "us-l": 2, "us-p": 2 },
  cardMedia: { eu: 6, "us-l": 6, "us-p": 6 },
  cardPower: { eu: 8, "us-l": 8, "us-p": 8 },
  screensaver2: { eu: 15, "us-l": 15, "us-p": 15 },
};

// Der Screensaver steht bewusst nicht in der Tabelle oben: seine Plätze hängen nicht nur an der
// Kapazität, sondern auch daran, wie viele Entities konfiguriert sind *und* wie das Display steht.
// Er wird deshalb unten eigens geprüft.

/** Ein Zeichen aus dem Symbolbereich, das im Mapping des Backends *nicht* vorkommt. */
function freiesIconZeichen() {
  for (let punkt = 0xfaf0; punkt < 0xfb50; punkt++) {
    const zeichen = String.fromCodePoint(punkt);
    if (!iconChars.ICON_CHARS.includes(zeichen)) return zeichen;
  }
  throw new Error("kein freies Zeichen gefunden");
}

// --- Geometrie --------------------------------------------------------------------------------

test("jede Karte bekommt genau so viele Plätze, wie das Schema angibt", () => {
  for (const [cardType, jeModell] of Object.entries(KAPAZITAET)) {
    for (const [model, capacity] of Object.entries(jeModell)) {
      const ergebnis = previewSlots({ cardType, capacity, filled: capacity, model });
      assert.equal(
        entitySlots(ergebnis).length,
        capacity,
        `${cardType} auf ${model}: ${entitySlots(ergebnis).length} statt ${capacity} Plätze`
      );
    }
  }
});

test("die Plätze tragen die Listenpositionen 0…n-1 in Reihenfolge", () => {
  for (const [cardType, jeModell] of Object.entries(KAPAZITAET)) {
    const capacity = jeModell.eu;
    const slots = entitySlots(previewSlots({ cardType, capacity, filled: capacity, model: "eu" }));
    const indizes = slots.map((slot) => slot.index).sort((a, b) => a - b);
    assert.deepEqual(
      indizes,
      Array.from({ length: capacity }, (unused, i) => i),
      `${cardType}: unerwartete Positionen ${JSON.stringify(indizes)}`
    );
  }
});

test("kein Platz ragt über die Displayfläche hinaus", () => {
  for (const [cardType, jeModell] of Object.entries(KAPAZITAET)) {
    for (const [model, capacity] of Object.entries(jeModell)) {
      for (const slot of previewSlots({ cardType, capacity, filled: capacity, model }).slots) {
        assert.ok(slot.x >= 0 && slot.y >= 0, `${cardType}/${model}: negative Position`);
        assert.ok(
          slot.x + slot.w <= 100.01 && slot.y + slot.h <= 100.01,
          `${cardType}/${model}: Platz ragt hinaus (${slot.kind} ${slot.x}+${slot.w} / ${slot.y}+${slot.h})`
        );
        assert.ok(slot.w > 0 && slot.h > 0, `${cardType}/${model}: leere Fläche`);
      }
    }
  }
});

test("weniger Entities als Plätze lassen die Plätze stehen – sie bleiben nur leer", () => {
  const voll = entitySlots(previewSlots({ cardType: "cardGrid", capacity: 6, filled: 6 }));
  const leer = entitySlots(previewSlots({ cardType: "cardGrid", capacity: 6, filled: 1 }));
  assert.equal(leer.length, voll.length);
});

test("der Screensaver zeigt ohne sechste Entity ein Hauptsymbol und vier Vorhersagen", () => {
  for (const model of ["eu", "us-l", "us-p"]) {
    const slots = entitySlots(previewSlots({ cardType: "screensaver", capacity: 6, filled: 5, model }));
    assert.deepEqual(
      slots.map((slot) => slot.index),
      [0, 1, 2, 3, 4],
      `${model}: unerwartete Plätze`
    );
  }
});

test("die sechste Entity schaltet quer das alternative Layout ein – und verdrängt dabei die fünfte", () => {
  // Im HMI: tForecast1 wird ausgeblendet und die übrigen Spalten rücken nach rechts
  // (tForecast4 = tForecast3 …). Die vierte Vorhersage hat danach keinen Platz mehr.
  for (const model of ["eu", "us-l"]) {
    const slots = entitySlots(previewSlots({ cardType: "screensaver", capacity: 6, filled: 6, model }));
    assert.deepEqual(
      slots.map((slot) => slot.index).sort((a, b) => a - b),
      [0, 1, 2, 3, 5],
      `${model}: Eintrag 5 (Index 4) müsste verdrängt sein`
    );
  }
});

test("hochkant bleiben alle sechs sichtbar – dort entfällt die Verschiebung", () => {
  // Die Verschiebung steckt im HMI hinter `if(p0.w!=320)`; bei 320 px Breite greift sie nicht,
  // die beiden Textblöcke stehen stattdessen nebeneinander.
  const slots = entitySlots(
    previewSlots({ cardType: "screensaver", capacity: 6, filled: 6, model: "us-p" })
  );
  assert.deepEqual(slots.map((slot) => slot.index).sort((a, b) => a - b), [0, 1, 2, 3, 4, 5]);
});

test("Screensaver haben keinen Rahmen, Karten schon", () => {
  // Screensaver füllen das Display ganz aus – kein Titel, keine Blättertasten.
  assert.equal(previewSlots({ cardType: "screensaver", capacity: 6 }).chrome, false);
  assert.equal(previewSlots({ cardType: "screensaver2", capacity: 15 }).chrome, false);
  // Bei abgemessenen Karten steht der Rahmen als eigene Plätze in der Liste (aus dem Dump),
  // bei nachempfundenen zeichnet ihn die Vorschau selbst.
  const gemessen = previewSlots({ cardType: "cardEntities", capacity: 4 });
  assert.equal(gemessen.gemessen, true);
  assert.equal(gemessen.slots.some((slot) => slot.kind === "title"), true);
  assert.equal(gemessen.slots.filter((slot) => slot.kind === "navbtn").length, 2);
  // cardAlarm hat kein abgemessenes Layout – dort zeichnet die Vorschau den Rahmen selbst.
  assert.equal(previewSlots({ cardType: "cardAlarm", capacity: 0 }).chrome, true);
});

test("abgemessene Plätze tragen ihre Bestandteile mit sich", () => {
  const slots = entitySlots(previewSlots({ cardType: "cardEntities", capacity: 4, model: "eu" }));
  for (const slot of slots) {
    assert.ok(slot.parts, "jeder Platz braucht seine Bestandteile");
    assert.ok(slot.parts.icon && slot.parts.name, "Symbol und Name gehören dazu");
    // Relativ zum Platz: die Bestandteile liegen innerhalb, nicht daneben.
    for (const teil of Object.values(slot.parts)) {
      assert.ok(teil.left >= -0.01 && teil.left + teil.width <= 100.01, "Bestandteil ragt seitlich hinaus");
      assert.ok(teil.top >= -0.01 && teil.top + teil.height <= 100.01, "Bestandteil ragt hinaus");
      assert.equal(teil.px.length, 2, "Pixelmaße für die Schriftgröße fehlen");
    }
  }
});

test("cardGrid-Kacheln liegen nebeneinander, nicht untereinander", () => {
  // Sanity-Check gegen ein vertauschtes Muster im Extraktionswerkzeug: die ersten drei Kacheln
  // teilen sich eine Zeile, die vierte beginnt weiter unten.
  const slots = entitySlots(previewSlots({ cardType: "cardGrid", capacity: 6, model: "eu" }));
  assert.equal(slots[0].y, slots[1].y);
  assert.ok(slots[1].x > slots[0].x);
  assert.ok(slots[3].y > slots[0].y);
});

test("us-p steht hochkant, eu und us-l liegen quer", () => {
  assert.deepEqual(SCREEN["us-p"], { w: 320, h: 480 });
  assert.deepEqual(SCREEN.eu, { w: 480, h: 320 });
  assert.equal(previewSlots({ cardType: "cardGrid", capacity: 6, model: "us-p" }).screen.h, 480);
});

test("Karten ohne Entity-Liste zeigen die Fläche des Backends, nicht erfundene Plätze", () => {
  // cardThermo ist seit v0.27 abgemessen und steht deshalb nicht mehr in dieser Liste.
  for (const cardType of ["cardAlarm", "cardUnlock", "cardChart"]) {
    const ergebnis = previewSlots({ cardType, capacity: 0, filled: 0 });
    assert.equal(entitySlots(ergebnis).length, 0, `${cardType} sollte keine Listenplätze haben`);
    assert.equal(ergebnis.slots.length, 1);
    assert.equal(ergebnis.slots[0].index, "flat");
  }
});

test("cardThermo ist abgemessen und hat keine Listenplätze", () => {
  const ergebnis = previewSlots({ cardType: "cardThermo", capacity: 0, filled: 0 });
  assert.equal(ergebnis.gemessen, true);
  assert.equal(ergebnis.chrome, false, "der Rahmen steht als eigene Plätze in der Liste");
  // Die Karte zeigt eine Entity, aber nicht als Listeneintrag – `entitySlots` bleibt leer.
  assert.equal(entitySlots(ergebnis).length, 0);
  assert.equal(ergebnis.slots.some((slot) => slot.kind === "title"), true);
  assert.equal(ergebnis.slots.filter((slot) => slot.kind === "navbtn").length, 2);
});

test("cardThermo zeigt ein Bedienbild – entweder einen Sollwert oder zwei", () => {
  const einer = previewSlots({ cardType: "cardThermo", zielwerte: 1, betriebsarten: 0 });
  const rollen = (e) => e.slots.map((s) => s.rolle).filter(Boolean);
  assert.ok(rollen(einer).includes("dest"), "ein Sollwert: die mittige Zahl");
  assert.ok(rollen(einer).includes("up") && rollen(einer).includes("down"));
  // Die Tasten des Zwei-Sollwert-Bildes dürfen daneben nicht auftauchen – das Gerät blendet
  // sie aus (`vis btUp1,0` …), beides gleichzeitig gibt es dort nie.
  assert.equal(rollen(einer).includes("destHigh"), false);
  assert.equal(rollen(einer).includes("upHigh"), false);

  const zwei = previewSlots({ cardType: "cardThermo", zielwerte: 2, betriebsarten: 0 });
  assert.ok(rollen(zwei).includes("destHigh") && rollen(zwei).includes("destLow"));
  assert.ok(["upHigh", "downHigh", "upLow", "downLow"].every((r) => rollen(zwei).includes(r)));
  assert.equal(rollen(zwei).includes("dest"), false);
  assert.equal(rollen(zwei).includes("up"), false);
});

test("cardThermo zeigt nur so viele Betriebsarten, wie die Entity hat", () => {
  const modi = (n) =>
    previewSlots({ cardType: "cardThermo", betriebsarten: n }).slots.filter(
      (s) => s.kind === "thermo-modus"
    );
  assert.equal(modi(0).length, 0, "ohne Entity keine Tasten – nicht acht erfundene");
  assert.equal(modi(3).length, 3);
  assert.equal(modi(8).length, 8);
  // Mehr als acht kann das Display nicht: der Rest wird abgeschnitten, nicht gestapelt.
  assert.equal(modi(12).length, 8);
  assert.deepEqual(
    modi(4).map((s) => s.modus),
    [0, 1, 2, 3],
    "die Tasten stehen in der Reihenfolge der hvac_modes"
  );
});

test("cardThermo passt auf alle drei Displays", () => {
  for (const model of ["eu", "us-l", "us-p"]) {
    const ergebnis = previewSlots({ cardType: "cardThermo", model, betriebsarten: 8 });
    const { w, h } = ergebnis.screen;
    assert.deepEqual({ w, h }, SCREEN[model]);
    for (const slot of ergebnis.slots) {
      assert.ok(
        slot.x >= -0.01 && slot.y >= -0.01 && slot.x + slot.w <= 100.01 && slot.y + slot.h <= 100.01,
        `${model}: ${slot.kind}/${slot.rolle ?? slot.modus} ragt über die Fläche hinaus`
      );
    }
  }
});

test("ein unbekannter Kartentyp wird als Liste dargestellt, statt zu scheitern", () => {
  const ergebnis = previewSlots({ cardType: "cardWasAuchImmer", capacity: 3, filled: 3 });
  assert.equal(entitySlots(ergebnis).length, 3);
});

// --- Inhalt -----------------------------------------------------------------------------------

test("entityKind trennt echte Entities von den Sonderformen des Backends", () => {
  assert.equal(entityKind("light.kueche"), "state");
  assert.equal(entityKind("iText.Guten Morgen"), "text");
  assert.equal(entityKind("navigate.kueche"), "navigate");
  assert.equal(entityKind("service.script.turn_on"), "service");
  assert.equal(entityKind("delete"), "delete");
  assert.equal(entityKind(""), "empty");
  assert.equal(entityKind(undefined), "empty");
});

test("ohne eigene Angaben kommen Name, Wert und Symbol aus Home Assistant", () => {
  const inhalt = previewContent(
    { entity: "sensor.puffer" },
    {
      "sensor.puffer": {
        state: "48.2",
        attributes: { friendly_name: "Puffer oben", unit_of_measurement: "°C", icon: "mdi:thermometer" },
      },
    }
  );
  assert.equal(inhalt.name, "Puffer oben");
  assert.equal(inhalt.value, "48.2 °C");
  assert.equal(inhalt.icon, "mdi:thermometer");
  // Wichtig: gekennzeichnet, denn das Backend leitet sein Symbol selbst ab (icon_mapping.py).
  assert.equal(inhalt.iconAbgeleitet, true);
});

test("eigene Angaben schlagen Home Assistant", () => {
  const inhalt = previewContent(
    { entity: "sensor.puffer", name: "Puffer", value: "warm", icon: "fire" },
    { "sensor.puffer": { state: "48.2", attributes: { friendly_name: "Puffer oben" } } }
  );
  assert.equal(inhalt.name, "Puffer");
  assert.equal(inhalt.value, "warm");
  assert.equal(inhalt.icon, "mdi:fire");
  assert.equal(inhalt.iconAbgeleitet, false);
});

test("eine Entity, die es in Home Assistant nicht gibt, wird als solche gemeldet", () => {
  const inhalt = previewContent({ entity: "light.tippfehler" }, {});
  assert.equal(inhalt.zustandFehlt, true);
  assert.equal(inhalt.name, "light.tippfehler");
  assert.equal(inhalt.value, "");
});

test("Sonderformen haben keinen Zustand und melden deshalb auch keinen fehlenden", () => {
  const text = previewContent({ entity: "iText.Guten Morgen" }, {});
  assert.equal(text.value, "Guten Morgen");
  assert.equal(text.zustandFehlt, false);

  const nav = previewContent({ entity: "navigate.kueche", icon: "arrow-right" }, {});
  assert.equal(nav.zustandFehlt, false);
  assert.equal(nav.name, "navigate.kueche");
});

test("das Wettersymbol kommt aus dem Zustand, nicht aus einem Attribut", () => {
  // weather.*-Entities tragen kein icon-Attribut. Ohne Nachbildung stand im Screensaver der
  // Platzhalter, während das Gerät ein Wettersymbol zeigte – dort das größte Element überhaupt.
  const states = { "weather.zuhause": { state: "sunny", attributes: { friendly_name: "Wetter" } } };
  const inhalt = previewContent({ entity: "weather.zuhause" }, states);

  assert.equal(inhalt.icon, "mdi:weather-sunny");
  assert.equal(inhalt.iconAbgeleitet, true, "abgeleitet, nicht selbst gesetzt");
  assert.equal(inhalt.color, "#ffff00", "die Sonne färbt das Backend gelb");
});

test("ein selbst gesetztes Symbol schlägt die Wetter-Ableitung", () => {
  const states = { "weather.zuhause": { state: "rainy", attributes: {} } };
  const inhalt = previewContent({ entity: "weather.zuhause", icon: "mdi:umbrella" }, states);
  assert.equal(inhalt.icon, "mdi:umbrella");
  assert.equal(inhalt.iconAbgeleitet, false);

  // Ebenso die Farbe: eine eigene Angabe gewinnt.
  const eigen = previewContent(
    { entity: "weather.zuhause", color: [1, 2, 3] },
    states
  );
  assert.equal(eigen.color, "#010203");
});

test("wetterDarstellung bildet die Tabellen des Backends nach", () => {
  assert.deepEqual(wetterDarstellung("weather.x", "rainy"), {
    icon: "mdi:weather-rainy",
    color: "#6361ff",
  });
  // exceptional ist im Backend bewusst kein Wettersymbol, sondern ein Warnzeichen.
  assert.equal(wetterDarstellung("weather.x", "exceptional").icon, "mdi:alert-circle-outline");
  // windy-variant: im Backend steht dort `icon_color: …` statt `=` – die Zeile setzt nichts, das
  // Gerät zeigt die Standardfarbe. Nachgebildet wird, was das Gerät tut.
  assert.equal(wetterDarstellung("weather.x", "windy-variant").color, null);
  // Unbekannter Zustand und andere Domains bleiben unangetastet.
  assert.equal(wetterDarstellung("weather.x", "gibtesnicht"), null);
  assert.equal(wetterDarstellung("sensor.x", "sunny"), null);
  assert.equal(wetterDarstellung(undefined, undefined), null);
});

// --- Wetter: Temperatur und Vorhersagespalten --------------------------------------------------

/** Eine Wetter-Entity, wie Home Assistant sie führt – mit Temperatur, aber ohne Vorhersage. */
const wetterStates = (features) => ({
  "weather.zuhause": {
    state: "sunny",
    attributes: {
      friendly_name: "Wetter",
      temperature: 26.5,
      temperature_unit: "°C",
      ...(features === undefined ? {} : { supported_features: features }),
    },
  },
});

test("Wetter zeigt die Temperatur, nicht den Zustand", () => {
  // pages.py schreibt für weather fest f'{temperature}{unit}'. Vorher stand hier „sunny“ – der
  // Zustand also, den das Gerät gar nicht als Text zeigt, sondern nur als Symbol.
  const inhalt = previewContent({ entity: "weather.zuhause" }, wetterStates());

  assert.equal(inhalt.value, "26.5°C", "ohne Leerzeichen dazwischen, wie im Backend");
  assert.equal(inhalt.vorhersageFehlt, null, "das aktuelle Wetter braucht keinen Dienstaufruf");
  // Ein eigener Wert schlägt die Ableitung weiterhin.
  assert.equal(previewContent({ entity: "weather.zuhause", value: "warm" }, wetterStates()).value, "warm");
});

test("eine Vorhersagespalte bleibt leer, bis ihre Vorhersage geladen ist", () => {
  // Die aktuelle Temperatur wäre hier schlicht falsch – die Spalte zeigt einen anderen Tag.
  const inhalt = previewContent({ entity: "weather.zuhause", type: 1 }, wetterStates(2));

  assert.equal(inhalt.value, "");
  assert.deepEqual(inhalt.vorhersageFehlt, { id: "weather.zuhause", reihe: "hourly" },
    "die Reihe kommt aus supported_features, genau wie im Backend");
  // Ohne jede Angabe bleibt es bei daily.
  assert.equal(
    previewContent({ entity: "weather.zuhause", type: 0 }, wetterStates()).vorhersageFehlt.reihe,
    "daily"
  );
  // `daily:1` nennt die Reihe ausdrücklich und schlägt supported_features.
  assert.equal(
    previewContent({ entity: "weather.zuhause", type: "daily:1" }, wetterStates(2)).vorhersageFehlt.reihe,
    "daily"
  );
});

test("mit geladener Vorhersage zeigt die Spalte den Tag, nicht das aktuelle Wetter", () => {
  const forecasts = {
    "weather.zuhause|daily": [
      { datetime: "2026-07-30T10:00:00+00:00", condition: "sunny", temperature: 34.8 },
      { datetime: "2026-07-31T10:00:00+00:00", condition: "rainy", temperature: 30.8 },
    ],
  };
  const inhalt = previewContent({ entity: "weather.zuhause", type: 1 }, wetterStates(1), null, forecasts);

  assert.equal(inhalt.value, "30.8°C");
  assert.equal(inhalt.icon, "mdi:weather-rainy", "das Wetter des Vorhersagetages");
  assert.equal(inhalt.color, "#6361ff");
  assert.equal(inhalt.vorhersageFehlt, null, "geladen – kein weiterer Dienstaufruf");
  assert.ok(inhalt.name && inhalt.name !== "Wetter", "über der Spalte steht der Wochentag");

  // Reicht die Vorhersage nicht so weit, fällt auch das Backend auf das aktuelle Wetter zurück.
  const zuWeit = previewContent({ entity: "weather.zuhause", type: 5 }, wetterStates(1), null, forecasts);
  assert.equal(zuWeit.value, "26.5°C");
  assert.equal(zuWeit.vorhersageFehlt, null, "abgefragt ist abgefragt – sonst fragte es endlos nach");
});

test("type als Text ist keine Vorhersagespalte", () => {
  // pages.py verzweigt nach dem Python-Typ: nur eine echte Ganzzahl ist ein Index, `"0"` landet
  // dort im Zweig für die aktuelle Temperatur.
  const inhalt = previewContent({ entity: "weather.zuhause", type: "0" }, wetterStates(1));

  assert.equal(inhalt.value, "26.5°C");
  assert.equal(inhalt.vorhersageFehlt, null);
  // Und bei Entities anderer Domains ändert `type` ohnehin nichts an der Anzeige.
  const sensor = previewContent(
    { entity: "sensor.x", type: 1 },
    { "sensor.x": { state: "21", attributes: { unit_of_measurement: "°C" } } }
  );
  assert.equal(sensor.value, "21 °C");
  assert.equal(sensor.vorhersageFehlt, null);
});

test("delete und leere Einträge markieren den Platz als frei", () => {
  assert.equal(previewContent({ entity: "delete" }, {}).frei, true);
  assert.equal(previewContent({ entity: "" }, {}).frei, true);
  assert.equal(previewContent(undefined, {}).frei, true);
  assert.equal(previewContent("kein objekt", {}).frei, true);
  assert.equal(previewContent({ entity: "light.k" }, {}).frei, false);
});

test("Templates werden gesammelt statt geraten", () => {
  const inhalt = previewContent(
    {
      entity: "sensor.x",
      name: "{{ states('sensor.name') }}",
      value: "{{ states('sensor.x') }} kWh",
      color: "{{ [255, 0, 0] }}",
    },
    {}
  );
  assert.deepEqual(
    inhalt.templates.map((t) => t.feld).sort(),
    ["color", "name", "value"]
  );
  // Bis das Rendering da ist, steht nichts Falsches im Platz.
  assert.equal(inhalt.value, "");
  assert.equal(inhalt.color, null);
});

test("ein unbekannter Icon-Name wird gekennzeichnet, aber nicht verworfen", () => {
  const inhalt = previewContent({ entity: "light.k", icon: "gibtesnicht-xyz" }, {});
  assert.equal(inhalt.icon, "mdi:gibtesnicht-xyz");
  assert.equal(inhalt.iconUnbekannt, true);
  assert.equal(previewContent({ entity: "light.k", icon: "lightbulb" }, {}).iconUnbekannt, false);
});

test("icon-Sonderformen sind kein Symbol und werden nicht als Name geprüft", () => {
  const inhalt = previewContent({ entity: "light.k", icon: "text:23°" }, {});
  assert.equal(inhalt.iconSonderform, true);
  assert.equal(inhalt.icon, null);
  assert.equal(inhalt.iconUnbekannt, false);
});

test("previewColor wählt bei {on, off} nach dem Zustand", () => {
  const farbe = { on: [255, 0, 0], off: [0, 0, 255] };
  assert.equal(previewColor(farbe, "on"), "#ff0000");
  assert.equal(previewColor(farbe, "off"), "#0000ff");
  assert.equal(previewColor(farbe, "closed"), "#0000ff");
  // Ohne bekannten Zustand die eingeschaltete Farbe – die hat man beim Konfigurieren im Blick.
  assert.equal(previewColor(farbe, undefined), "#ff0000");
  assert.equal(previewColor([0, 128, 255]), "#0080ff");
  // Templates ergeben hier nichts: sie müssen erst gerendert werden.
  assert.equal(previewColor("{{ x }}"), null);
  assert.equal(previewColor(undefined), null);
});

test("iconFromRendered erkennt Symbol und Text auseinander", () => {
  assert.equal(iconFromRendered("<I>thermometer</I>").icon, "thermometer");
  assert.equal(iconFromRendered("mdi:lightbulb").icon, "lightbulb");
  assert.equal(iconFromRendered("lightbulb").icon, "lightbulb");
  const text = iconFromRendered("21,5 °C");
  assert.equal(text.icon, null);
  assert.equal(text.text, "21,5 °C");
});

test("Sammelaufruf und Zerlegung passen zusammen", () => {
  const texte = ["{{ 1 }}", "{{ 2 }}", "fest"];
  const gerendert = joinTemplates(["1", "2", "fest"]);
  assert.deepEqual(splitTemplateResult(gerendert, texte.length), ["1", "2", "fest"]);
});

test("stimmt die Teilezahl nicht, wird null gemeldet statt falsch zugeordnet", () => {
  // Genau der Fall, für den es den Rückfall auf Einzelaufrufe gibt: ein Template gibt den
  // Trenner selbst aus – die Zuordnung wäre danach um eins verschoben.
  const kaputt = joinTemplates(["a", "b", "c"]);
  assert.equal(splitTemplateResult(kaputt, 2), null);
  assert.equal(splitTemplateResult("", 2), null);
});

// --- Live-Ansicht (Mitschnitt vom Gerät) -------------------------------------------------------

test("das Icon-Zeichen des Backends findet zu seinem Namen zurück", () => {
  // Über MQTT kommt nicht "lightbulb", sondern das Zeichen aus dem Nextion-Font.
  const index = icons.ICON_NAMES.indexOf("lightbulb");
  const zeichen = iconChars.ICON_CHARS[index];
  assert.equal(iconNameFromChar(zeichen), "lightbulb");
  assert.equal(iconNameFromChar(""), null);
  assert.equal(iconNameFromChar(undefined), null);
  // Ein Zeichen außerhalb des Mappings (neuere Backend-Version) ergibt keinen Namen.
  assert.equal(iconNameFromChar(freiesIconZeichen()), null);
});

test("beide Icon-Listen bleiben in Reihenfolge und Länge gekoppelt", () => {
  // Sie werden aus demselben Lauf erzeugt; driften sie auseinander, zeigt die Live-Ansicht
  // durchgehend falsche Symbole – und zwar plausibel aussehende.
  assert.equal(iconChars.ICON_CHARS.length, icons.ICON_NAMES.length);
});

test("liveContent übernimmt, was das Gerät bekommen hat – ohne etwas abzuleiten", () => {
  const index = icons.ICON_NAMES.indexOf("thermometer");
  const inhalt = liveContent({
    type: "text",
    entity: "sensor.puffer",
    iconChar: iconChars.ICON_CHARS[index],
    rgb: [16, 142, 255],
    name: "Puffer oben",
    value: "48.2 °C",
    leer: false,
  });
  assert.equal(inhalt.name, "Puffer oben");
  assert.equal(inhalt.value, "48.2 °C");
  assert.equal(inhalt.icon, "mdi:thermometer");
  assert.equal(inhalt.color, "#108eff");
  // Nichts zu schätzen, nichts nachzurendern.
  assert.equal(inhalt.iconAbgeleitet, false);
  assert.deepEqual(inhalt.templates, []);
  assert.equal(inhalt.zustandFehlt, false);
});

test("gelöschte und fehlende Einträge bleiben auch live freie Plätze", () => {
  assert.equal(liveContent({ type: "delete", leer: true }).frei, true);
  assert.equal(liveContent(undefined).frei, true);
  assert.equal(liveContent({ type: "light", leer: false }).frei, false);
});

test("ein Symbol aus einer neueren Backend-Version wird als unbekannt gekennzeichnet", () => {
  const unbekannt = freiesIconZeichen();
  const inhalt = liveContent({ type: "light", iconChar: unbekannt, name: "x", value: "" });
  assert.equal(inhalt.icon, null);
  assert.equal(inhalt.iconUnbekannt, true);
});

test("Uhr und Datum erscheinen genau einmal", () => {
  // Der Dump kennt außer tTime/tDate noch tAMPM (AM/PM-Zusatz) und tTimeAdd (frei
  // konfigurierbare Zusatzzeile). Wurden die mit derselben Uhrzeit gefüllt, stand alles doppelt
  // auf dem Bildschirm – an der echten Anlage sofort sichtbar.
  for (const typ of ["screensaver", "screensaver2"]) {
    for (const model of ["eu", "us-l", "us-p"]) {
      const slots = previewSlots({ cardType: typ, capacity: 15, filled: 3, model }).slots;
      const uhren = slots.filter((slot) => slot.kind === "clock").length;
      const daten = slots.filter((slot) => slot.kind === "date").length;
      assert.equal(uhren, 1, `${typ}/${model}: ${uhren} Uhren`);
      assert.equal(daten, 1, `${typ}/${model}: ${daten} Datumsfelder`);
    }
  }
});

test("beide Screensaver haben die zwei Status-Symbole", () => {
  // `statusIcon1`/`statusIcon2` stehen nicht in der Entity-Liste – ohne eigene Plätze fehlten sie
  // in der Vorschau, obwohl das Gerät sie zeigt.
  for (const typ of ["screensaver", "screensaver2"]) {
    for (const model of ["eu", "us-l", "us-p"]) {
      const slots = previewSlots({ cardType: typ, capacity: 15, filled: 3, model }).slots;
      const status = slots.filter((slot) => slot.kind === "status");
      assert.equal(status.length, 2, `${typ}/${model}: ${status.length} Status-Plätze`);
      assert.deepEqual(
        status.map((slot) => slot.nummer).sort(),
        [1, 2],
        `${typ}/${model}: Status-Plätze ohne saubere Nummerierung`
      );
      // Sie zählen nicht zur Entity-Liste – sonst verschöbe sich deren Reihenfolge.
      assert.equal(
        entitySlots({ slots: status }).length,
        0,
        `${typ}/${model}: Status-Platz als Listeneintrag gezählt`
      );
    }
  }
  // Karten haben keine – dort gibt es die Felder nicht.
  const karte = previewSlots({ cardType: "cardGrid", capacity: 6, filled: 6, model: "eu" }).slots;
  assert.equal(karte.filter((slot) => slot.kind === "status").length, 0);
});

test("ein Status-Symbol trägt Symbol und Text zugleich", () => {
  // Der Fall aus der echten Konfiguration: `<I>mdi:fireplace</I> ha:{{ … }} °C` wird auf dem Gerät
  // zu Flammensymbol + Messwert. Nur das Symbol zu zeigen ließe genau den Wert weg, wegen dem es
  // dort steht.
  const teile = statusIconTeile("<I>mdi:fireplace</I> 57.4 °C");
  assert.equal(teile.icon, "fireplace");
  assert.equal(teile.text, "57.4 °C");

  // Die Marker `ha:`/`text:` wirft das Backend weg (icon_mapping.get_icon_id) – sie dürfen nicht
  // als Text auf dem Display landen.
  assert.equal(statusIconTeile("ha:21.5 °C").text, "21.5 °C");
  assert.equal(statusIconTeile("text:Hallo").text, "Hallo");
  // Ein reiner Icon-Name bleibt ein reines Symbol.
  assert.deepEqual(statusIconTeile("mdi:fireplace"), { icon: "fireplace", text: "" });
});

test("live werden Symbol und Wert eines Status-Feldes getrennt", () => {
  const zeichen = iconChars.ICON_CHARS[icons.ICON_NAMES.indexOf("thermometer-water")];
  const inhalt = liveStatusContent({ iconChar: `${zeichen} 45.2 °C`, rgb: [255, 165, 0] });
  assert.equal(inhalt.icon, "mdi:thermometer-water");
  assert.equal(inhalt.iconText, "45.2 °C");
  assert.equal(inhalt.color, "#ffa500");
  assert.equal(inhalt.frei, false);

  // Nicht konfiguriert: das Backend schickt ein leeres Feldpaar, die Stelle bleibt leer.
  assert.equal(liveStatusContent({ iconChar: null, leer: true }).frei, true);
  assert.equal(liveStatusContent(undefined).frei, true);
});

test("die beiden Status-Symbole der echten Anlage", () => {
  // Wörtlich mitgeschnitten von der produktiven Instanz (2026-07-27, GET /live): so schickt das
  // Backend die Ruheanzeige-Symbole wirklich – Zeichen, Leerzeichen, Wert, Einheit in *einem* Feld.
  // Das erste Zeichen (U+FA7F) liegt über dem klassischen PUA-Ende U+F8FF; mit der alten oberen
  // Grenze galt es als Text, das Symbol fiel weg und „74 °C" stand mit dem Zeichen davor da.
  const warmwasser = liveStatusContent({
    iconChar: "\uFA7F 74 °C",
    rgb: [255, 166, 0],
    altFont: true,
  });
  assert.equal(warmwasser.icon, "mdi:thermometer-water");
  assert.equal(warmwasser.iconText, "74 °C");
  assert.equal(warmwasser.iconUnbekannt, false);

  const ofen = liveStatusContent({ iconChar: "\uEE2D 25 °C", rgb: [0, 121, 255], altFont: true });
  assert.equal(ofen.icon, "mdi:fireplace");
  assert.equal(ofen.iconText, "25 °C");
  assert.equal(ofen.color, "#0079ff");
});

test("auf dem Raster tritt bei Sensoren der Messwert an die Stelle des Symbols", () => {
  // Backend-Eigenheit (pages.py): auf cardGrid ist kein Platz für Symbol *und* Wert, also zeigt
  // das Display bei sensor-Entities ohne eigenes icon die ersten vier Zeichen des Zustands.
  const states = { "sensor.puffer": { state: "21.53", attributes: {} } };
  const raster = previewContent({ entity: "sensor.puffer" }, states, "cardGrid");
  assert.equal(raster.iconText, "21.5");
  assert.equal(raster.icon, null);

  // Auf anderen Karten bleibt es beim Symbol – dort gibt es ein eigenes Wertfeld.
  assert.equal(previewContent({ entity: "sensor.puffer" }, states, "cardEntities").iconText, null);
  // Ein selbst gesetztes Symbol gewinnt immer.
  const eigenes = previewContent({ entity: "sensor.puffer", icon: "thermometer" }, states, "cardGrid");
  assert.equal(eigenes.icon, "mdi:thermometer");
  assert.equal(eigenes.iconText, null);
});

test("endet der Ausschnitt auf einem Punkt, fällt er weg", () => {
  // Sonst stünde "100." auf dem Display – das kürzt das Backend selbst.
  assert.equal(gridSensorText("100.0"), "100");
  assert.equal(gridSensorText("21.53"), "21.5");
  assert.equal(gridSensorText("8.1"), "8.1");
  assert.equal(gridSensorText("on"), "on");
  assert.equal(gridSensorText(undefined), "");
});

test("im Icon-Feld unterscheidet die Live-Ansicht Symbol und Text", () => {
  const index = icons.ICON_NAMES.indexOf("thermometer");
  assert.equal(istIconZeichen(iconChars.ICON_CHARS[index]), true);
  // Der Messwert, den das Backend auf dem Raster statt eines Symbols schickt.
  assert.equal(istIconZeichen("21.5"), false);
  assert.equal(istIconZeichen(""), false);

  const messwert = liveContent({ iconChar: "21.5", name: "Puffer" });
  assert.equal(messwert.iconText, "21.5");
  assert.equal(messwert.icon, null);
  // Und kein falscher Alarm: das ist kein unbekanntes Symbol, sondern gewollter Text.
  assert.equal(messwert.iconUnbekannt, false);
});

// --- cardPower: die Laufbalken -----------------------------------------------------------------

test("cardPower bekommt sechs Laufbalken, einen je Außenplatz", () => {
  // Sie stehen im HMI-Dump als Slider, nicht als Textfeld – ohne sie bliebe die Fläche leer, auf
  // der am Gerät das Auffälligste der Karte passiert.
  const ergebnis = previewSlots({ cardType: "cardPower", capacity: 8, filled: 8, model: "eu" });
  const balken = ergebnis.slots.filter((slot) => slot.kind === "flow");

  assert.equal(balken.length, 6);
  assert.deepEqual(
    balken.map((b) => b.zuSlot),
    [2, 3, 4, 5, 6, 7],
    "die ersten beiden Plätze sitzen in der Mitte und haben keinen Balken"
  );
  // Abgemessen: h0 liegt bei 78,105 auf 120×12 von 480×320.
  const erster = balken[0];
  assert.ok(Math.abs(erster.x - (78 / 480) * 100) < 0.01);
  assert.ok(Math.abs(erster.w - (120 / 480) * 100) < 0.01);
  assert.equal(erster.senkrecht, false);
  assert.equal(erster.spanne, 1200);
  assert.equal(erster.ruhe, 0.5, "der Slider startet in der Mitte seines Bereichs");
  assert.equal(erster.invertiert, true, "quer dreht der Seitencode das Vorzeichen");

  // Ein Balken zeigt keine eigene Entity – die Liste der Entity-Plätze bleibt bei acht.
  assert.equal(entitySlots(ergebnis).length, 8);
});

test("hochkant stehen die Laufbalken senkrecht und ohne Vorzeichendreher", () => {
  const ergebnis = previewSlots({ cardType: "cardPower", capacity: 8, filled: 8, model: "us-p" });
  const balken = ergebnis.slots.filter((slot) => slot.kind === "flow");

  assert.equal(balken.length, 6);
  assert.equal(balken[0].senkrecht, true);
  assert.equal(balken[0].invertiert, false, "der Dreher hängt an 320 px Displayhöhe");
});

test("weniger Plätze, weniger Balken", () => {
  // Kapazität ist die einzige Quelle für die Zahl der Plätze – auch für die Balken.
  const ergebnis = previewSlots({ cardType: "cardPower", capacity: 4, filled: 4, model: "eu" });
  assert.deepEqual(
    ergebnis.slots.filter((slot) => slot.kind === "flow").map((b) => b.zuSlot),
    [2, 3]
  );
});
