// Tests der reinen Hilfsfunktionen des Panels – ohne DOM, mit dem Test-Runner von Node (>= 18):
//   node --test tests/
//
// Geprüft wird die Logik, an der Datenverlust hängen würde: die Widget-Wahl (ein Dict darf nie in
// einem Textfeld landen) und die Regel „leeres Feld löscht den Key“.

import assert from "node:assert/strict";
import { test } from "node:test";

const module = await import(
  "../custom_components/nspanel_ui_config/www/panel/nspanel-ui-config-panel.js"
);
const { widgetFor, setField, cardLabel, esc, isPlain } = module;

test("Modul lässt sich ohne Browser importieren", () => {
  assert.equal(typeof module.NsPanelUiConfigPanel, "function");
});

test("widgetFor folgt dem Schema-Hinweis bei passenden Werten", () => {
  assert.equal(widgetFor("string", "Wohnzimmer"), "string");
  assert.equal(widgetFor("number", 20), "number");
  assert.equal(widgetFor("boolean", true), "boolean");
  assert.equal(widgetFor("entity", "light.kueche"), "entity");
  assert.equal(widgetFor("icon", "mdi:lightbulb"), "icon");
});

test("Dicts und Listen landen immer im JSON-Editor", () => {
  // Der wichtigste Fall: icon kann {on, off} sein, obwohl das Schema "icon" sagt.
  assert.equal(widgetFor("icon", { on: "mdi:lightbulb-on", off: "mdi:lightbulb" }), "json");
  assert.equal(widgetFor("number", [1, 2, 3]), "json");
  assert.equal(widgetFor("string", { a: 1 }), "json");
  assert.equal(widgetFor("boolean", { zeitplan: [] }), "json");
});

test("unpassende Skalare fallen auf ein Textfeld zurück, statt den Wert zu verstümmeln", () => {
  // sleepTimeout als Template statt Zahl – ein number-Feld würde den Text verwerfen.
  assert.equal(widgetFor("number", "{{ states('input_number.x') }}"), "string");
  assert.equal(widgetFor("boolean", "irgendwas"), "string");
  // Numerische Strings darf das Zahlenfeld übernehmen.
  assert.equal(widgetFor("number", "42"), "number");
});

test("leere und fehlende Werte behalten den Schema-Hinweis", () => {
  assert.equal(widgetFor("number", undefined), "number");
  assert.equal(widgetFor("entity", ""), "entity");
  assert.equal(widgetFor("json", null), "json");
  assert.equal(widgetFor(undefined, undefined), "string");
});

test("entity_object nutzt den JSON-Editor", () => {
  assert.equal(widgetFor("entity_object", { entity: "light.a" }), "entity_object");
  assert.equal(widgetFor("entity_object", "light.a"), "json");
});

test("setField löscht den Key bei undefined statt leere Werte zu speichern", () => {
  const target = { title: "Küche", key: "kueche" };
  setField(target, "title", "Bad");
  assert.deepEqual(target, { title: "Bad", key: "kueche" });

  setField(target, "key", undefined);
  assert.deepEqual(target, { title: "Bad" });
  assert.ok(!("key" in target), "Key muss entfernt sein, nicht auf undefined stehen");

  // Falsy-Werte, die trotzdem gesetzt sein sollen, überleben.
  setField(target, "sleepTimeout", 0);
  setField(target, "quiet", false);
  assert.equal(target.sleepTimeout, 0);
  assert.equal(target.quiet, false);
});

test("cardLabel bevorzugt Titel, dann key, dann Typ", () => {
  assert.equal(cardLabel({ type: "cardGrid", key: "k", title: "Wohnzimmer" }), "Wohnzimmer");
  assert.equal(cardLabel({ type: "cardGrid", key: "k" }), "k");
  assert.equal(cardLabel({ type: "cardGrid" }), "cardGrid");
  assert.equal(cardLabel({}), "(ohne Titel)");
  assert.equal(cardLabel("kaputt"), "(ungültige Karte)");
});

test("esc entschärft HTML in Nutzerwerten", () => {
  assert.equal(esc(`<img src=x onerror="alert(1)">`), "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;");
  assert.equal(esc("A & B"), "A &amp; B");
});

test("isPlain trennt Objekte/Listen von Skalaren", () => {
  assert.equal(isPlain({}), true);
  assert.equal(isPlain([]), true);
  assert.equal(isPlain(null), false);
  assert.equal(isPlain("x"), false);
  assert.equal(isPlain(0), false);
});
