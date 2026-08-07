// Wo die Einträge einer Karte auf dem Display landen — die Geometrie der Vorschau.
//
// **Warum das hier steht und nicht im Schema:** `schema.py` beschreibt, was in die YAML kommt, und
// mit `CARD_CAPACITY` *wie viele* Plätze eine Karte hat. Wo diese Plätze liegen, ist reine
// Darstellung und gehört zum Frontend. Die Zahl wird deshalb bewusst **nicht** wiederholt:
// `previewSlots` bekommt die Kapazität als Parameter und verteilt genau so viele Plätze. Damit kann
// die Vorschau gar nicht in Widerspruch zum Schema geraten.
//
// **Zwei Quellen, in dieser Reihenfolge:**
//  1. `layouts.js` — aus den HMI-Dumps der Display-Firmware erzeugt (`tools/extract_layouts.py`).
//     Deckt alle Karten mit Entity-Liste ab, für alle drei Modelle, mit Symbol-, Namens- und
//     Wertfläche jedes Platzes einzeln. Dort ist die Vorschau **abgemessen**.
//  2. Die Notlösung `listenLayout` weiter unten — für Karten, die keine Entity-Liste haben
//     (`cardThermo`, `cardAlarm` …) und für Kartentypen, die diese Fassung noch nicht kennt.
//
// Maße nach außen sind **Prozent der Displayfläche**, nicht Pixel: so gilt dieselbe Beschreibung
// für das quer liegende EU-/US-L-Panel und das hochkant stehende US-P-Panel. Die Pixel bleiben
// nur dort erhalten, wo die Zeichenschicht sie braucht (Schriftgröße).

// **Dynamisch, nicht `import … from "./layouts.js"`.** Ein statischer Import löst den Pfad relativ
// zu dieser Datei auf und lässt die Query dabei fallen — der Browser fragt also `layouts.js` *ohne*
// Kennung an und nimmt seine zwischengespeicherte Fassung. Das Panel wäre dann neu, die Geometrie
// alt. Genau so fehlten die Laufbalken von `cardPower`: `preview-layouts.js` kam frisch, das
// `layouts.js` daneben stammte noch aus der Zeit davor und kannte `flow` nicht.
const { LAYOUTS } = await import(`./layouts.js${new URL(import.meta.url).search}`);

/** Displaygröße je Modell. Nur us-p steht hochkant. */
export const SCREEN = {
  eu: { w: 480, h: 320 },
  "us-l": { w: 480, h: 320 },
  "us-p": { w: 320, h: 480 },
};

const screenFor = (model) => SCREEN[model] || SCREEN.eu;

/** Steht das Display hochkant? Entscheidet über das alternative Screensaver-Layout. */
const isPortrait = (model) => screenFor(model).h > screenFor(model).w;

// --- Abgemessene Layouts ----------------------------------------------------------------------

/** Rechnet ein Pixel-Rechteck [x, y, w, h] der Displayfläche in Prozent um. */
const proz = ([x, y, w, h], breite, hoehe) => ({
  x: (x / breite) * 100,
  y: (y / hoehe) * 100,
  w: (w / breite) * 100,
  h: (h / hoehe) * 100,
});

/** Kleinstes Rechteck, das alle übergebenen enthält. */
function huelle(boxen) {
  const x = Math.min(...boxen.map((b) => b.x));
  const y = Math.min(...boxen.map((b) => b.y));
  return {
    x,
    y,
    w: Math.max(...boxen.map((b) => b.x + b.w)) - x,
    h: Math.max(...boxen.map((b) => b.y + b.h)) - y,
  };
}

/**
 * Ein Platz aus abgemessenen Bestandteilen.
 *
 * Der Platz selbst ist die Hülle seiner Teile; die Teile werden zusätzlich **relativ zu ihm**
 * angegeben, damit die Zeichenschicht nur noch Prozente setzen muss. Die Pixelmaße bleiben als
 * `px` erhalten — die Schriftgröße richtet sich nach der echten Höhe des Textfeldes.
 */
function platz(teile, index, breite, hoehe, attrs = {}) {
  const boxen = Object.values(teile).map((r) => proz(r, breite, hoehe));
  if (!boxen.length) return null;
  const rahmen = huelle(boxen);
  const parts = {};
  for (const [rolle, kasten] of Object.entries(teile)) {
    const box = proz(kasten, breite, hoehe);
    parts[rolle] = {
      left: ((box.x - rahmen.x) / rahmen.w) * 100,
      top: ((box.y - rahmen.y) / rahmen.h) * 100,
      width: (box.w / rahmen.w) * 100,
      height: (box.h / rahmen.h) * 100,
      px: kasten.slice(2),
      // Font-ID, Ausrichtung und Schriftfarbe der Komponente – ohne sie stünde jede Beschriftung
      // links statt mittig und in Einheitsgröße (siehe layouts.js).
      attr: (attrs || {})[rolle] || null,
    };
  }
  return { kind: "measured", index, ...rahmen, parts };
}

/**
 * Die Laufbalken einer Karte als eigene Plätze (`cardPower`, sonst nichts).
 *
 * Sie stehen im Dump als Nextion-**Slider** und nicht als Textfeld, tauchen deshalb nicht in der
 * Slot-Tabelle auf – gezeichnet gehören sie trotzdem: dort läuft auf dem Gerät der Punkt, der den
 * Energiefluss zeigt.
 *
 * Nachgebildet wird der Seitencode, nicht eine Vorstellung davon: alle 100 ms addiert das Display
 * `speed` auf den Sliderwert und springt am Bereichsende auf die andere Seite. Daraus folgen
 * Ruhelage (`ruhe`, der Startwert im Bereich) und Umlaufzeit (`spanne` Schritte weit).
 */
function flussPlaetze(layout, breite, hoehe, capacity, model) {
  return (layout.flow || [])
    .filter((balken) => balken.index < capacity)
    .map((balken) => {
      const spanne = Math.max(1, balken.max - balken.min);
      return {
        kind: "flow",
        // Bewusst nicht `index`: das kennzeichnet einen Platz, der selbst eine Entity zeigt
        // (`entitySlots`). Der Balken zeigt keine, er gehört nur zu einer.
        zuSlot: balken.index,
        ...proz(balken.rect, breite, hoehe),
        senkrecht: balken.dir === "v",
        spanne,
        ruhe: (balken.start - balken.min) / spanne,
        // Der Seitencode dreht das Vorzeichen bei 320 px Displayhöhe (`if(p0.h==320)`), also auf
        // den beiden quer liegenden Modellen. Hier steht die Bedingung als das, was sie meint.
        invertiert: !isPortrait(model),
      };
    });
}

/** Karten: Titel und Blättertasten oben, darunter die Plätze der Entity-Liste. */
function kartenLayout(layout, capacity, model, filled = 0) {
  const [breite, hoehe] = layout.screen;
  const slots = [];
  const chrome = layout.chrome || {};
  const chromeAttrs = layout.chromeAttrs || {};
  if (chrome.title) {
    slots.push({
      kind: "title",
      ...proz(chrome.title, breite, hoehe),
      attr: chromeAttrs.title || null,
    });
  }
  for (const taste of ["prev", "next"]) {
    if (chrome[taste]) {
      slots.push({
        kind: "navbtn",
        taste,
        ...proz(chrome[taste], breite, hoehe),
        attr: chromeAttrs[taste] || null,
      });
    }
  }
  const slotAttrs = layout.slotAttrs || [];
  layout.slots.slice(0, capacity).forEach((teile, index) => {
    const eintrag = platz(teile, index, breite, hoehe, slotAttrs[index]);
    if (eintrag) slots.push(eintrag);
  });
  slots.push(...flussPlaetze(layout, breite, hoehe, capacity, model));

  // `cardQR`: der Code rückt in die Mitte, sobald die Karte keine Einträge hat — so steht es im
  // Seitencode (`if(type2 leer){ if(type1 leer){ qrcode m1 } } else { qrcode m0 }`). Die Bedingung
  // hängt an den *gefüllten* Einträgen, nicht an der Kapazität.
  if (layout.qr) {
    const rechteck = filled > 0 ? layout.qr.mitEintraegen : layout.qr.allein;
    if (rechteck) slots.push({ kind: "qr", ...proz(rechteck, breite, hoehe) });
  }
  return { screen: { w: breite, h: hoehe }, chrome: false, slots, gemessen: true, back: layout.back };
}

// Welche Sonderkomponente wie gezeichnet wird. Uhrzeit und Datum füllt das Backend aus eigenen
// Befehlen (`time`/`date`), nicht aus der Entity-Liste — ohne sie fehlte die halbe Ruheanzeige.
//
// `tIcon1`/`tIcon2` sind die beiden **Status-Symbole** aus `statusIcon1`/`statusIcon2`. Sie stehen
// ebenfalls nicht in der Entity-Liste: das Backend schickt sie in einer eigenen Nachricht
// (`statusUpdate`, pages.py → `update_status_icons`). `nummer` sagt der Zeichenschicht, welches
// der beiden Felder sie füllt.
//
// **Bewusst nicht dabei:** `tAMPM` (der AM/PM-Zusatz, im 24-Stunden-Format leer) und `tTimeAdd`
// (die frei konfigurierbare Zusatzzeile aus `timeAdditionalTemplate`). Beide tragen *nicht* die
// Uhrzeit — sie mit ihr zu füllen ließ die Vorschau die Uhr und das Datum doppelt zeigen.
const SPECIAL_KINDS = {
  tTime: { kind: "clock" },
  tDate: { kind: "date" },
  tIcon1: { kind: "status", nummer: 1 },
  tIcon2: { kind: "status", nummer: 2 },
};

/**
 * Screensaver: Plätze aus dem Seitencode, plus die Umschaltung auf das alternative Layout.
 *
 * **Was die 6. Entity auslöst** (im HMI nachgelesen, siehe CAPACITY_LAYOUT_NOTES): der Hauptbereich
 * trägt dann zwei Textblöcke — Eintrag 1 rückt an seine Alt-Position, Eintrag 6 darunter/daneben.
 * Quer blendet das Display zusätzlich die erste Vorhersagespalte aus und rückt die übrigen nach
 * rechts; **Eintrag 5 verliert dadurch seinen Platz**. Hochkant entfällt die Verschiebung
 * (`if(p0.w!=320)`), dort bleiben alle sechs sichtbar.
 */
function screensaverLayout(layout, capacity, filled, model) {
  const [breite, hoehe] = layout.screen;
  const slots = [];
  const specialAttrs = layout.specialAttrs || {};
  for (const [name, rechteck] of Object.entries(layout.special || {})) {
    const art = SPECIAL_KINDS[name];
    if (art) {
      slots.push({ ...art, ...proz(rechteck, breite, hoehe), attr: specialAttrs[name] || null });
    }
  }

  const alternativ = filled >= 6 && layout.alt;
  const slotAttrs = layout.slotAttrs || [];
  const altAttrs = layout.altAttrs || {};
  const zeichne = (teile, index, attrs) => {
    const eintrag = platz(teile, index, breite, hoehe, attrs || slotAttrs[index]);
    if (eintrag) slots.push(eintrag);
  };

  if (!alternativ) {
    // Standard: Eintrag 1 im Hauptbereich, 2–5 in den Vorhersagespalten. Der letzte Platz gehört
    // allein dem alternativen Layout und bleibt leer.
    layout.slots.slice(0, Math.min(capacity, layout.slots.length)).forEach((teile, index) => {
      if (layout.alt && index === layout.slots.length - 1) return;
      zeichne(teile, index);
    });
    return { screen: { w: breite, h: hoehe }, chrome: false, slots, gemessen: true, back: layout.back };
  }

  const letzter = layout.slots.length - 1;
  for (const [indexText, teile] of Object.entries(layout.alt)) {
    zeichne(teile, Number(indexText), altAttrs[indexText]);
  }
  zeichne(layout.slots[letzter], letzter);

  const spalten = layout.slots.slice(1, letzter); // die Vorhersagespalten
  spalten.forEach((teile, i) => {
    // Quer rutscht der Inhalt eine Spalte nach rechts: die Geometrie von Spalte i+1 zeigt dann
    // Eintrag i+1 statt i+2. Die letzte Spalte hat danach keinen Inhalt mehr.
    const index = isPortrait(model) ? i + 1 : i;
    if (index < 1) return;
    zeichne(teile, index);
  });
  return { screen: { w: breite, h: hoehe }, chrome: false, slots, gemessen: true, back: layout.back };
}

// --- Karten mit festem Aufbau ------------------------------------------------------------------

/**
 * `cardThermo`: eine Entity, aber fest aufgeteilte Fläche statt Liste.
 *
 * Gezeichnet wird **eines von zwei Bedienbildern**, weil das Gerät genau eines zeigt
 * (`vis`-Befehle im Seitencode, siehe `fixed_card_thermo` im Extraktor):
 *   * ein Sollwert  → große Zahl mittig, große Plus/Minus-Tasten
 *   * zwei Sollwerte → zwei Zahlen nebeneinander, je ein kleines Tastenpaar
 * Welches gilt, weiß nur die aufrufende Seite (es hängt an den Attributen der Entity), deshalb
 * kommt `zielwerte` von außen und wird hier nicht geraten.
 *
 * Die acht Betriebsartentasten sind **immer alle** im Layout, aber nur so viele werden gezeichnet,
 * wie die Entity Betriebsarten hat — der Rest bleibt am Gerät unsichtbar (`vis btN,0`).
 */
function thermoLayout(layout, model, zielwerte, betriebsarten) {
  const [breite, hoehe] = layout.screen;
  const fest = layout.fixed || {};
  const attrs = layout.fixedAttrs || {};
  const slots = [];

  const nimm = (rolle, kind, extra = {}) => {
    if (!fest[rolle]) return;
    slots.push({
      kind,
      rolle,
      ...proz(fest[rolle], breite, hoehe),
      px: fest[rolle].slice(2),
      attr: attrs[rolle] || null,
      ...extra,
    });
  };

  const chrome = layout.chrome || {};
  const chromeAttrs = layout.chromeAttrs || {};
  if (chrome.title) {
    slots.push({ kind: "title", ...proz(chrome.title, breite, hoehe), attr: chromeAttrs.title || null });
  }
  for (const taste of ["prev", "next"]) {
    if (chrome[taste]) {
      slots.push({
        kind: "navbtn",
        taste,
        ...proz(chrome[taste], breite, hoehe),
        attr: chromeAttrs[taste] || null,
      });
    }
  }

  // Linke Spalte: zwei feste Beschriftungen mit je einem Wert darunter.
  nimm("curTempLbl", "thermo-label");
  nimm("curTemp", "thermo-wert", { feld: "current" });
  nimm("stateLbl", "thermo-label");
  nimm("state", "thermo-wert", { feld: "state" });

  if (zielwerte >= 2) {
    nimm("destHigh", "thermo-ziel", { feld: "high" });
    nimm("destHighUnit", "thermo-einheit");
    nimm("destLow", "thermo-ziel", { feld: "low" });
    nimm("destLowUnit", "thermo-einheit");
    nimm("upHigh", "thermo-taste", { zeichen: "+" });
    nimm("downHigh", "thermo-taste", { zeichen: "−" });
    nimm("upLow", "thermo-taste", { zeichen: "+" });
    nimm("downLow", "thermo-taste", { zeichen: "−" });
  } else {
    nimm("dest", "thermo-ziel", { feld: "target" });
    nimm("destUnit", "thermo-einheit");
    nimm("up", "thermo-taste", { zeichen: "+" });
    nimm("down", "thermo-taste", { zeichen: "−" });
  }
  nimm("detail", "thermo-taste", { zeichen: "…" });

  const modeAttrs = layout.modeAttrs || {};
  const anzahl = Math.max(0, Math.min(betriebsarten, (layout.modes || []).length));
  (layout.modes || []).slice(0, anzahl).forEach((rect, index) => {
    slots.push({
      kind: "thermo-modus",
      modus: index,
      ...proz(rect, breite, hoehe),
      px: rect.slice(2),
      attr: modeAttrs[String(index)] || null,
    });
  });

  return { screen: { w: breite, h: hoehe }, chrome: false, slots, gemessen: true, back: layout.back };
}

/**
 * `cardAlarm` — und damit zugleich `cardUnlock`.
 *
 * **Beide teilen sich eine Display-Seite:** Das Backend schreibt `cardUnlock` in `page_type()` auf
 * `cardAlarm` um, bevor der Kartentyp ans Panel geht. Die Geometrie ist deshalb dieselbe; die
 * Entsperrkarte benutzt davon nur Zifferntastatur und PIN-Feld.
 *
 * Die Namen der zwölf Tastaturplätze führen in die Irre: `b0`…`b8` sind die Ziffern 1–9, `b10`
 * die Null, `b11` löscht — und `b9` ist **keine Ziffer**, sondern die Zusatztaste unten links.
 * Deshalb trägt dieser Platz hier eine eigene Rolle.
 */
function alarmLayout(layout, model, tasten, tastatur) {
  const [breite, hoehe] = layout.screen;
  const fest = layout.fixed || {};
  const attrs = layout.fixedAttrs || {};
  const slots = [];

  const nimm = (rolle, kind, extra = {}) => {
    if (!fest[rolle]) return;
    slots.push({
      kind,
      rolle,
      ...proz(fest[rolle], breite, hoehe),
      px: fest[rolle].slice(2),
      attr: attrs[rolle] || null,
      ...extra,
    });
  };

  const chrome = layout.chrome || {};
  const chromeAttrs = layout.chromeAttrs || {};
  if (chrome.title) {
    slots.push({ kind: "title", ...proz(chrome.title, breite, hoehe), attr: chromeAttrs.title || null });
  }
  for (const taste of ["prev", "next"]) {
    if (chrome[taste]) {
      slots.push({
        kind: "navbtn",
        taste,
        ...proz(chrome[taste], breite, hoehe),
        attr: chromeAttrs[taste] || null,
      });
    }
  }

  nimm("state", "alarm-zustand");
  if (tastatur) {
    nimm("code", "alarm-code");
    // Die Beschriftung steht nicht im Dump (das Display setzt sie selbst), also hier.
    const ZIFFERN = ["1", "2", "3", "4", "5", "6", "7", "8", "9"];
    for (let i = 0; i < 12; i++) {
      const rolle = `key${i}`;
      if (!fest[rolle]) continue;
      if (i === 9) {
        nimm(rolle, "alarm-extra");
      } else {
        nimm(rolle, "alarm-taste", { zeichen: i === 10 ? "0" : i === 11 ? "✕" : ZIFFERN[i] });
      }
    }
  } else {
    // Ohne Tastatur bleibt die Zusatztaste trotzdem stehen – sie gehört nicht zum PIN-Block.
    nimm("key9", "alarm-extra");
  }

  const anzahl = Math.max(0, Math.min(tasten, (layout.modes || []).length));
  (layout.modes || []).slice(0, anzahl).forEach((rect, index) => {
    slots.push({
      kind: "alarm-aktion",
      aktion: index,
      ...proz(rect, breite, hoehe),
      px: rect.slice(2),
      attr: (layout.modeAttrs || {})[String(index)] || null,
    });
  });

  return { screen: { w: breite, h: hoehe }, chrome: false, slots, gemessen: true, back: layout.back };
}

// --- Notlösung für Karten ohne abgemessenes Layout ---------------------------------------------

/** Kopfzeile und Fußzeile, wenn nichts Abgemessenes vorliegt. */
const CHROME_TOP = 11;
const CHROME_BOTTOM = 11;

/** Eine Zeile je Eintrag — bewusst schlicht: das hier ist nur der Rückfall. */
function listenLayout(count) {
  const top = CHROME_TOP + 1;
  const hoehe = (100 - top - CHROME_BOTTOM - 1) / Math.max(1, count);
  const slots = [];
  for (let i = 0; i < count; i++) {
    slots.push({ kind: "row", index: i, x: 3, y: top + i * hoehe, w: 94, h: hoehe - 1.5 });
  }
  return slots;
}

/** Karten mit genau einer Entity: die Fläche gehört der Bedienoberfläche des Backends. */
const SINGLE_WIDGETS = {
  cardThermo: "thermo",
  cardAlarm: "keypad",
  cardUnlock: "keypad",
  cardChart: "chart",
};

// --- Einstieg ---------------------------------------------------------------------------------

/**
 * Die Plätze einer Karte, in Anzeigereihenfolge.
 *
 * - `capacity`: wie viele Entities das Display zeigt — kommt aus `schema.cardCapacity`, nie von hier.
 * - `filled`: wie viele Entities konfiguriert sind. Nur der Screensaver wertet das aus (siehe oben);
 *   sonst bleibt die Zahl der Plätze gleich, leere zeigt die Vorschau als frei.
 * - `cardType` ist der **wirksame** Typ: cardGrid mit mehr als sechs Einträgen ist längst cardGrid2.
 *   Diese Umrechnung macht `capacityInfo` im Panel, nicht diese Datei.
 *
 * Rückgabe: `{ screen, slots, chrome, gemessen }`. `chrome: true` heißt, dass die Zeichenschicht
 * Titel- und Navigationsleiste selbst ergänzt — das ist nur beim Rückfall nötig, im abgemessenen
 * Fall stehen sie als eigene Plätze in der Liste.
 */
export function previewSlots({
  cardType,
  capacity,
  filled = 0,
  model = "eu",
  zielwerte = 1,
  betriebsarten = 8,
  aktionen = 4,
  tastatur = true,
} = {}) {
  const screen = screenFor(model);
  const anzahl = Math.max(0, Number(capacity) || 0);

  // `cardUnlock` wird am Gerät als `cardAlarm` gezeichnet (das Backend schreibt den Typ um),
  // hat also keine eigene Geometrie.
  const seite = cardType === "cardUnlock" ? "cardAlarm" : cardType;
  const gemessen = LAYOUTS[seite] && LAYOUTS[seite][model];
  if (gemessen) {
    if (seite === "cardAlarm") {
      // Die Entsperrkarte zeigt nur PIN-Feld und Tastatur, keine Aktionstasten.
      const nurCode = cardType === "cardUnlock";
      return alarmLayout(gemessen, model, nurCode ? 0 : aktionen, nurCode ? true : tastatur);
    }
    if (gemessen.fixed) return thermoLayout(gemessen, model, zielwerte, betriebsarten);
    return gemessen.special
      ? screensaverLayout(gemessen, anzahl, filled, model)
      : kartenLayout(gemessen, anzahl, model, filled);
  }

  const widget = SINGLE_WIDGETS[cardType];
  if (widget) {
    return {
      screen,
      chrome: true,
      slots: [
        {
          kind: "flat-main",
          index: "flat",
          widget,
          x: 6,
          y: CHROME_TOP + 3,
          w: 88,
          h: 100 - CHROME_TOP - CHROME_BOTTOM - 8,
        },
      ],
    };
  }

  return { screen, chrome: true, slots: listenLayout(anzahl) };
}

/** Nur die Plätze, die eine Entity aus der Liste zeigen (in Listenreihenfolge). */
export function entitySlots(result) {
  return (result.slots || []).filter((slot) => typeof slot.index === "number");
}
