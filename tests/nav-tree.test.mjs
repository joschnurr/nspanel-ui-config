// Tests des Navigationsbaums – die Logik hinter der Baumansicht und dem Ziehen von Karten.
//
// Der Anlass ist eine echte Konfiguration: zwei Karten hatten ihre Blättertasten mit festen Zielen
// überschrieben, dadurch endete die Kette dort, und drei dahinterliegende Karten waren am Gerät
// unerreichbar. In der flachen Liste des Editors sahen sie völlig normal aus. Genau solche Fälle
// muss der Baum zeigen.

import assert from "node:assert/strict";
import { test } from "node:test";

const {
  navigationsZiel,
  zieleEiner,
  baueBaum,
  alsListe,
  verschiebeKarte,
  verschiebeEintrag,
} = await import("../custom_components/nspanel_ui_config/www/panel/nav-tree.js");

const karte = (key, eintraege = [], rest = {}) => ({
  type: "cardGrid",
  key,
  title: key,
  entities: eintraege.map((e) => (typeof e === "string" ? { entity: e } : e)),
  ...rest,
});

test("Sprungziele werden erkannt, alles andere nicht", () => {
  assert.equal(navigationsZiel("navigate.heizung"), "heizung");
  assert.equal(navigationsZiel("  navigate.uuid.abc  "), "uuid.abc");
  assert.equal(navigationsZiel("light.kueche"), null);
  assert.equal(navigationsZiel(undefined), null);
});

test("eine Karte gibt ihre Ziele aus Einträgen und Blättertasten preis", () => {
  const menue = karte("menu", ["navigate.heizung", "light.k", "navigate.licht"], {
    navItem1: { entity: "navigate.garage" },
    navItem2: "navigate.muell",
  });
  assert.deepEqual(
    zieleEiner(menue).map((z) => [z.ziel, z.quelle]),
    [
      ["heizung", "entity"],
      ["licht", "entity"],
      ["garage", "navItem1"],
      ["muell", "navItem2"],
    ]
  );
});

test("aus Menü und Unterseiten entsteht ein Baum", () => {
  const model = {
    cards: [karte("menu", ["navigate.energie", "navigate.licht"])],
    hiddenCards: [karte("energie"), karte("licht")],
  };
  const baum = baueBaum(model);
  assert.equal(baum.wurzeln.length, 1);
  assert.deepEqual(
    baum.wurzeln[0].kinder.map((k) => k.card.key),
    ["energie", "licht"]
  );
  assert.equal(baum.wurzeln[0].kinder[0].tiefe, 1);
  assert.deepEqual(baum.verwaist, []);
});

test("versteckte Karten, die niemand verlinkt, werden als verwaist gemeldet", () => {
  // Der eigentliche Zweck der Ansicht: am Gerät sind sie nicht erreichbar, in der Liste sehen sie
  // aus wie jede andere Karte.
  const model = {
    cards: [karte("menu", ["navigate.energie"])],
    hiddenCards: [karte("energie"), karte("vergessen")],
  };
  const baum = baueBaum(model);
  assert.deepEqual(baum.verwaist.map((k) => k.card.key), ["vergessen"]);
});

test("ein Ziel, das es nicht gibt, wird gemeldet statt verschluckt", () => {
  const model = { cards: [karte("menu", ["navigate.gibtesnicht"])], hiddenCards: [] };
  const baum = baueBaum(model);
  assert.deepEqual(baum.unbekannt, [{ von: "menu", ziel: "gibtesnicht", quelle: "entity" }]);
  assert.deepEqual(baum.wurzeln[0].kinder, []);
});

test("gegenseitige Verweise führen nicht in eine Endlosschleife", () => {
  const model = {
    cards: [karte("a", ["navigate.b"])],
    hiddenCards: [karte("b", ["navigate.a"])],
  };
  const baum = baueBaum(model);
  const b = baum.wurzeln[0].kinder[0];
  assert.equal(b.card.key, "b");
  // Der Rückverweis auf a wird als „schon gesehen" markiert und nicht weiter verfolgt.
  assert.equal(b.kinder[0].card.key, "a");
  assert.equal(b.kinder[0].mehrfach, true);
  assert.deepEqual(b.kinder[0].kinder, []);
});

test("die flache Liste zeichnet den Baum in Anzeigereihenfolge", () => {
  const model = {
    cards: [karte("menu", ["navigate.energie"]), karte("test")],
    hiddenCards: [karte("energie", ["navigate.detail"]), karte("detail")],
  };
  assert.deepEqual(
    alsListe(baueBaum(model)).map((k) => [k.card.key, k.tiefe]),
    [["menu", 0], ["energie", 1], ["detail", 2], ["test", 0]]
  );
});

// --- Umbauten durch Ziehen und Fallenlassen ----------------------------------------------------

test("eine Karte in die versteckten zu ziehen setzt kein hidden an der Karte", () => {
  // Die Zugehörigkeit zur Liste ist die ganze Information. Das Backend baut daraus selbst
  // `Card(card, hidden=True)` (config.py); einen `hidden:`-Key liest es nirgends – und in die
  // erzeugte YAML käme er auch nicht, weil er kein bekanntes Kartenfeld ist.
  const model = { cards: [karte("a"), karte("b")], hiddenCards: [] };
  const ziel = verschiebeKarte(model, "cards", 1, "hiddenCards", 0);
  assert.deepEqual(ziel, { kind: "hiddenCards", index: 0 });
  assert.equal(model.cards.length, 1);
  assert.equal(model.hiddenCards[0].key, "b");
  assert.equal("hidden" in model.hiddenCards[0], false);
});

test("ein Altbestand von hidden wird beim Verschieben entfernt", () => {
  // Ältere Fassungen haben den Key gesetzt. Er stand dann im gespeicherten Modell, ohne je in der
  // Datei anzukommen – wer eine solche Karte anfasst, wird ihn hier los.
  const model = {
    cards: [karte("a")],
    hiddenCards: [karte("b", [], { hidden: true }), karte("c", [], { hidden: true })],
  };
  verschiebeKarte(model, "hiddenCards", 0, "cards", 0);
  assert.equal(model.cards[0].key, "b");
  assert.equal("hidden" in model.cards[0], false);

  // Auch beim Zug in die andere Richtung, nicht nur zurück in die sichtbaren.
  verschiebeKarte(model, "hiddenCards", 0, "hiddenCards", 0);
  assert.equal("hidden" in model.hiddenCards[0], false);
});

test("innerhalb einer Liste stimmt die Position nach dem Herausnehmen", () => {
  // Der klassische Fehler beim Umsortieren: nach dem Entnehmen rutscht alles dahinter um eins vor.
  const model = { cards: [karte("a"), karte("b"), karte("c")], hiddenCards: [] };
  verschiebeKarte(model, "cards", 0, "cards", 2);
  assert.deepEqual(model.cards.map((k) => k.key), ["b", "a", "c"]);
  verschiebeKarte(model, "cards", 2, "cards", 0);
  assert.deepEqual(model.cards.map((k) => k.key), ["c", "b", "a"]);
});

test("unmögliche Züge ändern nichts", () => {
  const model = { cards: [karte("a")], hiddenCards: [] };
  assert.equal(verschiebeKarte(model, "cards", 5, "hiddenCards", 0), null);
  assert.equal(verschiebeKarte(model, "hiddenCards", 0, "cards", 0), null);
  assert.deepEqual(model.cards.map((k) => k.key), ["a"]);
});

test("Menüpunkte lassen sich innerhalb einer Karte umsortieren", () => {
  const menue = karte("menu", ["navigate.a", "navigate.b", "navigate.c"]);
  verschiebeEintrag(menue, 2, 0);
  assert.deepEqual(menue.entities.map((e) => e.entity), ["navigate.c", "navigate.a", "navigate.b"]);
  verschiebeEintrag(menue, 0, 3);
  assert.deepEqual(menue.entities.map((e) => e.entity), ["navigate.a", "navigate.b", "navigate.c"]);
});
