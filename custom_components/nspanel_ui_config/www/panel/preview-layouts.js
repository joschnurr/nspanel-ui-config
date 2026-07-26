// Wo die Einträge einer Karte auf dem Display landen — die Geometrie der Vorschau.
//
// **Warum das hier steht und nicht im Schema:** `schema.py` beschreibt, was in die YAML kommt, und
// mit `CARD_CAPACITY` *wie viele* Plätze eine Karte hat. Wo diese Plätze liegen, ist reine
// Darstellung und gehört zum Frontend. Die Zahl wird deshalb bewusst **nicht** wiederholt:
// `previewSlots` bekommt die Kapazität als Parameter und verteilt genau so viele Plätze. Damit kann
// die Vorschau gar nicht in Widerspruch zum Schema geraten.
//
// **Stufe 1 – schematisch.** Die Plätze stimmen in Anzahl, Reihenfolge und grober Lage; Größen sind
// nachempfunden, nicht aus den HMI-Dumps übernommen. Für die Fragen „passt das, wirkt die Farbe,
// stimmt die Reihenfolge?" reicht das. Stufe 2 (layout-treu, aus `HMI/n2t-out-visual/*.txt` erzeugt)
// bleibt offen — siehe docs/vorschau-machbarkeit.md.
//
// Alle Maße sind **Prozent der Displayfläche**, nicht Pixel: so gilt dieselbe Definition für das
// quer liegende EU-/US-L-Panel und das hochkant stehende US-P-Panel.

/** Displaygröße je Modell. Nur us-p steht hochkant. */
export const SCREEN = {
  eu: { w: 480, h: 320 },
  "us-l": { w: 480, h: 320 },
  "us-p": { w: 320, h: 480 },
};

/** Kopfzeile (Kartentitel) und Fußzeile (Navigationstasten) rahmen jede Karte ein. */
const CHROME_TOP = 11;
const CHROME_BOTTOM = 11;

const screenFor = (model) => SCREEN[model] || SCREEN.eu;

/** Steht das Display hochkant? Entscheidet über die Spaltenzahl der Raster. */
const isPortrait = (model) => screenFor(model).h > screenFor(model).w;

const rect = (kind, x, y, w, h, extra = {}) => ({ kind, x, y, w, h, ...extra });

/** Ein Platz, der eine Entity aus der Liste anzeigt. `index` ist die Position in `entities`. */
const entitySlot = (kind, index, x, y, w, h, extra = {}) =>
  rect(kind, x, y, w, h, { index, ...extra });

// --- Anordnungen ------------------------------------------------------------------------------

/** Untereinander, eine Zeile je Eintrag (cardEntities). */
function rowsLayout(count, kind = "row") {
  const top = CHROME_TOP + 1;
  const hoehe = (100 - top - CHROME_BOTTOM - 1) / Math.max(1, count);
  const slots = [];
  for (let i = 0; i < count; i++) {
    slots.push(entitySlot(kind, i, 3, top + i * hoehe, 94, hoehe - 1.5));
  }
  return slots;
}

/**
 * Kachelraster (cardGrid/cardGrid2). Die Spaltenzahl richtet sich nach der Ausrichtung des
 * Displays: quer 3 bzw. 4 Spalten, hochkant eine weniger — genau die Aufteilung, die
 * `CAPACITY_LAYOUT_NOTES` im Schema beschreibt (3×2, 4×2, us-p 3×3).
 */
function gridLayout(count, model, dicht) {
  const cols = isPortrait(model) ? (dicht ? 3 : 2) : dicht ? 4 : 3;
  const rows = Math.max(1, Math.ceil(count / cols));
  const top = CHROME_TOP + 1;
  const flaeche = 100 - top - CHROME_BOTTOM - 1;
  const zellH = flaeche / rows;
  const zellW = 100 / cols;
  const slots = [];
  for (let i = 0; i < count; i++) {
    const spalte = i % cols;
    const zeile = Math.floor(i / cols);
    slots.push(
      entitySlot("tile", i, spalte * zellW + 1.5, top + zeile * zellH, zellW - 3, zellH - 2)
    );
  }
  return slots;
}

/** QR-Code links, daneben die zwei Textzeilen. */
function qrLayout(count) {
  const slots = [rect("qr", 5, CHROME_TOP + 4, 42, 100 - CHROME_TOP - CHROME_BOTTOM - 8)];
  const top = CHROME_TOP + 8;
  for (let i = 0; i < count; i++) {
    slots.push(entitySlot("row", i, 50, top + i * 22, 47, 18));
  }
  return slots;
}

/** Medienseite: Titelblock, Lautstärke, unten die Symbolreihe aus der Entity-Liste. */
function mediaLayout(count) {
  const slots = [
    rect("flat-title", 4, CHROME_TOP + 2, 92, 20, { index: "flat" }),
    rect("slider", 4, CHROME_TOP + 26, 92, 10),
    rect("transport", 4, CHROME_TOP + 40, 92, 14),
  ];
  const breite = 100 / Math.max(1, count);
  for (let i = 0; i < count; i++) {
    slots.push(entitySlot("icon", i, i * breite + 1, 100 - CHROME_BOTTOM - 16, breite - 2, 14));
  }
  return slots;
}

/**
 * Energiefluss: die ersten beiden Einträge stehen in der Mitte, die übrigen außen herum —
 * links von oben nach unten, dann rechts (t0…t5 im HMI).
 */
function powerLayout(count) {
  const slots = [];
  const mitte = [
    { x: 33, y: 34, w: 34, h: 13 },
    { x: 33, y: 50, w: 34, h: 13 },
  ];
  const aussen = [];
  const top = CHROME_TOP + 3;
  const hoehe = (100 - top - CHROME_BOTTOM - 3) / 3;
  for (let seite = 0; seite < 2; seite++) {
    for (let zeile = 0; zeile < 3; zeile++) {
      aussen.push({ x: seite === 0 ? 2 : 71, y: top + zeile * hoehe, w: 27, h: hoehe - 2 });
    }
  }
  for (let i = 0; i < count; i++) {
    const platz = i < 2 ? mitte[i] : aussen[i - 2];
    if (!platz) break;
    slots.push(entitySlot(i < 2 ? "center" : "tile", i, platz.x, platz.y, platz.w, platz.h));
  }
  return slots;
}

/**
 * Klassische Ruheanzeige: große Uhr oben, darunter Datum, unten das Hauptwetter und vier
 * Vorhersagespalten.
 *
 * **Hier stehen ausnahmsweise abgemessene Werte**, keine geschätzten: die Prozentangaben stammen
 * aus den HMI-Dumps (`HMI/n2t-out-visual/screensaver.txt` bzw. `HMI/US/portrait/…`), umgerechnet
 * auf die jeweilige Displaygröße. Beim Screensaver lohnt sich das, weil seine Aufteilung am
 * wenigsten zu erraten ist — von „Uhr oben, Wetter unten" hätte ein Nachbau kaum etwas getroffen.
 *
 * **Das alternative Layout ist mehr als eine Umsortierung.** Eine sechste Entity setzt
 * `tMainTextAlt2` und schaltet um; was dann passiert, hängt an der Ausrichtung:
 *
 * - **quer (eu, us-l):** der Hauptbereich wird in zwei Zeilen geteilt (Entity 1 oben, Entity 6
 *   unten), die erste Vorhersagespalte wird ausgeblendet und die übrigen rücken nach rechts
 *   (`tForecast4 = tForecast3` …). Angezeigt werden dadurch die Entities 2–4 — **die fünfte Entity
 *   verschwindet**, obwohl sie konfiguriert und gesendet ist.
 * - **hochkant (us-p):** die beiden Textblöcke stehen nebeneinander, die Verschiebung entfällt
 *   (sie steckt im HMI hinter `if(p0.w!=320)`). Dort bleiben alle vier Vorhersagespalten stehen.
 */
function screensaverLayout(count, filled, model) {
  const hochkant = isPortrait(model);
  const alt = filled >= 6;
  const slots = [];

  if (hochkant) {
    slots.push(rect("clock", 0, 0, 100, 27));
    slots.push(rect("date", 2, 28, 96, 8));
    if (alt) {
      slots.push(entitySlot("main", 0, 0, 54, 50, 22));
      slots.push(entitySlot("main", 5, 50, 54, 50, 22));
    } else {
      slots.push(entitySlot("main", 0, 33, 54, 34, 22));
    }
    for (let i = 0; i < 4; i++) {
      const index = i + 1;
      if (index >= count) break;
      slots.push(entitySlot("forecast", index, 1.6 + i * 25.2, 78, 22, 20));
    }
    return slots;
  }

  slots.push(rect("clock", 7.7, 7.8, 78.3, 35));
  slots.push(rect("date", 0, 51.6, 93.8, 10));
  if (alt) {
    slots.push(entitySlot("main", 0, 2.3, 67.2, 40.4, 14.1));
    slots.push(entitySlot("main", 5, 2.3, 82.8, 40.4, 14.1));
  } else {
    slots.push(entitySlot("main", 0, 1.5, 65, 23, 34));
  }
  // Spalte 1 entfällt im alternativen Layout, die Inhalte rücken eine Spalte nach rechts.
  for (let i = alt ? 1 : 0; i < 4; i++) {
    const index = alt ? i : i + 1;
    if (index >= count || index < 1) continue;
    slots.push(entitySlot("forecast", index, 26 + i * 17.1, 67.5, 15, 32));
  }
  return slots;
}

/**
 * Alternative Ruheanzeige (Backend ≥ 4.0): Hauptbereich, eine Zeile mit Symbol und Wert,
 * Kacheln mit Symbol/Name/Wert und ganz unten reine Symbole — 1 + 3 + 6 + 5.
 */
function screensaver2Layout(count) {
  const gruppen = [
    { kind: "main", n: 1, y: 3, h: 26, x: 3, w: 45 },
    { kind: "value", n: 3, y: 3, h: 8.5, x: 52, w: 45 },
    { kind: "tile", n: 6, y: 33, h: 28 },
    { kind: "icon", n: 5, y: 64, h: 16 },
  ];
  const slots = [];
  let index = 0;
  for (const gruppe of gruppen) {
    for (let i = 0; i < gruppe.n; i++) {
      if (index >= count) return slots;
      if (gruppe.x !== undefined) {
        slots.push(
          entitySlot(gruppe.kind, index, gruppe.x, gruppe.y + i * gruppe.h, gruppe.w, gruppe.h - 1)
        );
      } else {
        const breite = 100 / gruppe.n;
        slots.push(
          entitySlot(gruppe.kind, index, i * breite + 1, gruppe.y, breite - 2, gruppe.h)
        );
      }
      index++;
    }
  }
  return slots;
}

/** Karten mit genau einer Entity: die Fläche gehört der Bedienoberfläche des Backends. */
function singleEntityLayout(kind) {
  return [
    rect("flat-main", 6, CHROME_TOP + 3, 88, 100 - CHROME_TOP - CHROME_BOTTOM - 8, {
      index: "flat",
      widget: kind,
    }),
  ];
}

// --- Einstieg ---------------------------------------------------------------------------------

/** Kartentypen, deren Fläche das Backend allein gestaltet (keine Entity-Liste). */
const SINGLE_WIDGETS = {
  cardThermo: "thermo",
  cardAlarm: "keypad",
  cardUnlock: "keypad",
  cardChart: "chart",
};

/**
 * Die Plätze einer Karte, in Anzeigereihenfolge.
 *
 * - `capacity`: wie viele Entities das Display zeigt — kommt aus `schema.cardCapacity`, nie von hier.
 * - `filled`: wie viele Entities konfiguriert sind. Nur der Screensaver wertet das aus (siehe oben);
 *   für alle anderen bleibt die Plätzezahl gleich, leere Plätze zeigt die Vorschau als frei.
 * - `cardType` ist der **wirksame** Typ: cardGrid mit mehr als sechs Einträgen ist längst cardGrid2.
 *   Diese Umrechnung macht `capacityInfo` im Panel, nicht diese Datei.
 *
 * Rückgabe: `{ screen, slots, chrome }`. `chrome: false` heißt Vollbild ohne Titel- und Navileiste —
 * so zeigt das Panel den Screensaver.
 */
export function previewSlots({ cardType, capacity, filled = 0, model = "eu" } = {}) {
  const screen = screenFor(model);
  const anzahl = Math.max(0, Number(capacity) || 0);

  if (cardType === "screensaver") {
    return { screen, chrome: false, slots: screensaverLayout(anzahl, filled, model) };
  }
  if (cardType === "screensaver2") {
    return { screen, chrome: false, slots: screensaver2Layout(anzahl) };
  }

  const widget = SINGLE_WIDGETS[cardType];
  if (widget) return { screen, chrome: true, slots: singleEntityLayout(widget) };

  let slots;
  if (cardType === "cardGrid") slots = gridLayout(anzahl, model, false);
  else if (cardType === "cardGrid2") slots = gridLayout(anzahl, model, true);
  else if (cardType === "cardQR") slots = qrLayout(anzahl);
  else if (cardType === "cardMedia") slots = mediaLayout(anzahl);
  else if (cardType === "cardPower") slots = powerLayout(anzahl);
  else slots = rowsLayout(anzahl);

  return { screen, chrome: true, slots };
}

/** Nur die Plätze, die eine Entity aus der Liste zeigen (in Listenreihenfolge). */
export function entitySlots(result) {
  return (result.slots || []).filter((slot) => typeof slot.index === "number");
}
