// Tests der Zeichenschicht – mit einer minimalen DOM-Attrappe statt eines Browsers.
//
// **Warum das nötig wurde:** an der echten Anlage fiel auf, dass die Farbe am falschen Element
// landete (bunte Beschriftung, weißes Symbol – auf dem Gerät ist es umgekehrt). Solche Fehler
// sieht keiner der bisherigen Tests: sie prüfen Geometrie und Inhalt, nicht das Zusammensetzen.
// Die Attrappe kann genau so viel, wie die Zeichenschicht braucht – createElement, style,
// className, appendChild.

import assert from "node:assert/strict";
import { test } from "node:test";

const panelModul = await import(
  "../custom_components/nspanel_ui_config/www/panel/nspanel-ui-config-panel.js"
);
const layouts = await import(
  "../custom_components/nspanel_ui_config/www/panel/preview-layouts.js"
);

const icons = await import("../custom_components/nspanel_ui_config/www/panel/icon-names.js");
const iconChars = await import("../custom_components/nspanel_ui_config/www/panel/icon-chars.js");

const { NsPanelUiConfigPanel, previewContent, liveStatusContent } = panelModul;
const { previewSlots, entitySlots } = layouts;

/** Ein Element, das sich merken kann, was mit ihm geschah. */
function fakeElement(tag) {
  const stil = {
    setProperty(name, wert) {
      this[name] = wert;
    },
  };
  return {
    tagName: tag.toUpperCase(),
    style: stil,
    className: "",
    title: "",
    textContent: "",
    hidden: false,
    attribute: {},
    children: [],
    setAttribute(name, wert) {
      this.attribute[name] = wert;
    },
    appendChild(kind) {
      this.children.push(kind);
      return kind;
    },
    replaceWith() {},
    /** Alle Nachfahren mit dieser Klasse (die Klassen sind hier immer einteilig genug). */
    finde(klasse) {
      const treffer = [];
      const lauf = (knoten) => {
        for (const kind of knoten.children) {
          if (String(kind.className).split(" ").includes(klasse)) treffer.push(kind);
          lauf(kind);
        }
      };
      lauf(this);
      return treffer;
    },
  };
}

globalThis.document = { createElement: (tag) => fakeElement(tag) };

/** Eine Panel-Instanz ohne Browser: nur das, was die Zeichenschicht anfasst. */
function panel(schema = {}) {
  const instanz = Object.create(NsPanelUiConfigPanel.prototype);
  instanz._schema = { templateSuffixFields: ["value", "icon"], fieldHints: {}, ...schema };
  instanz._previewMode = "model";
  return instanz;
}

/** Zeichnet einen Screensaver-Platz und liefert das fertige Element. */
function zeichneScreensaverPlatz(entity, auftraege = []) {
  const ergebnis = previewSlots({
    cardType: "screensaver2",
    capacity: 15,
    filled: 15,
    model: "eu",
  });
  const slot = entitySlots(ergebnis).find((eintrag) => eintrag.parts && eintrag.parts.icon && eintrag.parts.name);
  assert.ok(slot, "kein Platz mit Symbol und Name im Layout gefunden");
  const element = fakeElement("div");
  return panel()._measuredSlot(element, slot, previewContent(entity, {}), auftraege, 1);
}

test("die Farbe liegt auf dem Symbol, nicht auf Name oder Wert", () => {
  // So macht es das Gerät: das HMI schreibt die Farbe in die Schriftfarbe der Icon-Komponente.
  const element = zeichneScreensaverPlatz({
    entity: "sensor.ofen",
    icon: "fireplace",
    name: "Ofen",
    color: [255, 165, 0],
  });

  const symbol = element.finde("icon")[0];
  assert.ok(symbol, "kein Symbol gezeichnet");
  assert.equal(symbol.style.color, "#ffa500");
  assert.equal(element.style.color, undefined, "der Platz selbst darf nicht gefärbt sein");
  for (const teil of [...element.finde("name"), ...element.finde("val")]) {
    assert.equal(teil.style.color, undefined, "Beschriftung und Wert behalten ihre feste Farbe");
  }
});

test("ein Farb-Template färbt nach dem Rendern ebenfalls das Symbol", () => {
  // Der Fall aus der echten Konfiguration: iif(...) liefert einen String wie "[0, 120, 255]".
  const auftraege = [];
  const element = zeichneScreensaverPlatz(
    {
      entity: "sensor.ofen",
      icon: "fireplace",
      name: "Ofen",
      color: "{{ iif(true, '[0, 120, 255]', '[255, 0, 0]') }}",
    },
    auftraege
  );

  const farbauftrag = auftraege.find((auftrag) => auftrag.template.includes("iif"));
  assert.ok(farbauftrag, "das Farb-Template wurde nicht zum Rendern angemeldet");
  farbauftrag.apply("[0, 120, 255]");

  const symbol = element.finde("icon")[0];
  assert.equal(symbol.style.color, "#0078ff");
  assert.equal(element.style.color, undefined);
});

test("ohne Symbolfläche färbt der Platz selbst", () => {
  // cardPower hält die ersten beiden Einträge in der Mitte – dort gibt es kein eigenes Symbol.
  const ergebnis = previewSlots({ cardType: "cardPower", capacity: 8, filled: 8, model: "eu" });
  const ohneIcon = entitySlots(ergebnis).find((slot) => slot.parts && !slot.parts.icon);
  assert.ok(ohneIcon, "cardPower sollte einen Platz ohne Symbolfläche haben");

  const element = panel()._measuredSlot(
    fakeElement("div"),
    ohneIcon,
    previewContent({ entity: "sensor.x", name: "Netz", color: [255, 0, 0] }, {}),
    [],
    1
  );
  assert.equal(element.style.color, "#ff0000");
});

test("Name und Wert stehen an ihren abgemessenen Plätzen", () => {
  const element = zeichneScreensaverPlatz({
    entity: "sensor.x",
    icon: "thermometer",
    name: "Ofen",
    value: "24.9 °C",
  });
  const [name] = element.finde("name");
  const [wert] = element.finde("val");
  assert.equal(name.textContent, "Ofen");
  assert.equal(wert.textContent, "24.9 °C");
  // Relativ zum Platz positioniert, nicht im Fluss.
  assert.equal(name.style.position, "absolute");
  assert.equal(wert.style.position, "absolute");
});

test("ein freier Platz bleibt leer", () => {
  const element = zeichneScreensaverPlatz({ entity: "delete" });
  assert.equal(element.children.length, 0);
  assert.match(element.className, /frei/);
});

/** Zeichnet eines der beiden Status-Felder der Ruheanzeige. */
function zeichneStatus(inhalt, auftraege = [], nummer = 1) {
  const ergebnis = previewSlots({
    cardType: "screensaver2",
    capacity: 15,
    filled: 15,
    model: "eu",
  });
  const slot = ergebnis.slots.find((platz) => platz.kind === "status" && platz.nummer === nummer);
  assert.ok(slot, `kein Status-Platz ${nummer} im Layout`);
  return panel()._statusSlot(fakeElement("div"), slot, inhalt, auftraege, 1);
}

test("ein Status-Symbol zeigt Symbol und Wert, sobald das Template gerendert ist", () => {
  // Genau die Form aus der echten apps.yaml: Symbol, dahinter der Messwert samt Einheit.
  const auftraege = [];
  const element = zeichneStatus(
    previewContent(
      {
        entity: "sensor.puffer_oben",
        icon: '<I>mdi:thermometer-water</I> ha:{{ states("sensor.puffer_oben") }} °C',
      },
      {}
    ),
    auftraege
  );

  const [symbol] = element.finde("icon");
  const [wert] = element.finde("val");
  // Vor dem Rendern steht dort noch nichts – erst die Antwort füllt beides.
  assert.equal(symbol.hidden, true);
  assert.equal(wert.textContent, "");

  const auftrag = auftraege.find((eintrag) => eintrag.template.includes("states"));
  assert.ok(auftrag, "das Icon-Template wurde nicht zum Rendern angemeldet");
  // Das Backend rendert nur bis zum letzten `}`; die Einheit hängt der Editor wieder an.
  auftrag.apply("<I>mdi:thermometer-water</I> 45.2");

  assert.equal(symbol.hidden, false);
  assert.equal(symbol.attribute.icon, "mdi:thermometer-water");
  assert.equal(wert.textContent, "45.2 °C");
});

test("die Farbe eines Status-Feldes liegt auf Symbol und Wert", () => {
  // Anders als bei einem Eintrag: das HMI trägt beides in *einer* Komponente, deren Schriftfarbe
  // gesetzt wird – färbte man nur das Symbol, bliebe der Messwert weiß.
  const element = zeichneStatus(
    previewContent({ entity: "sensor.ofen", icon: "fireplace", color: [255, 165, 0] }, {})
  );
  assert.equal(element.style.color, "#ffa500");
  assert.equal(element.finde("icon")[0].attribute.icon, "mdi:fireplace");
});

test("ein Status-Symbol ohne Jinja steht sofort da", () => {
  // Ohne Template gibt es nichts zu rendern – der Rohtext ist bereits das Ergebnis. Vorher wäre
  // der Platz dauerhaft leer geblieben.
  const element = zeichneStatus(
    previewContent({ entity: "sensor.ofen", icon: "<I>mdi:fireplace</I> heiß" }, {})
  );
  assert.equal(element.finde("icon")[0].attribute.icon, "mdi:fireplace");
  assert.equal(element.finde("val")[0].textContent, "heiß");
});

test("ein nicht gesetztes Status-Symbol bleibt leer", () => {
  const element = zeichneStatus(previewContent(undefined, {}), [], 2);
  assert.equal(element.children.length, 0);
  assert.match(element.className, /frei/);
  assert.match(element.title, /statusIcon2/);
});

test("live steht im Status-Feld das Zeichen des Geräts samt Wert", () => {
  const zeichen = iconChars.ICON_CHARS[icons.ICON_NAMES.indexOf("fireplace")];
  const element = zeichneStatus(
    liveStatusContent({ iconChar: `${zeichen} 57.4 °C`, rgb: [255, 165, 0] })
  );
  assert.equal(element.finde("icon")[0].attribute.icon, "mdi:fireplace");
  assert.equal(element.finde("val")[0].textContent, "57.4 °C");
  assert.equal(element.style.color, "#ffa500");
});
