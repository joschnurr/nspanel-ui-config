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
const {
  widgetFor,
  setField,
  cardLabel,
  esc,
  isPlain,
  generateStatus,
  iconKind,
  iconIsKnown,
  filterIconNames,
  colorShape,
  isRgb,
  rgbToHex,
  hexToRgb,
  parseRgbText,
} = module;

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

test("generateStatus meldet einen fehlgeschlagenen Reload als Fehler, nicht als Erfolg", () => {
  const [text, tone] = generateStatus({
    path: "/nspanel-shared/nspanel_config.yaml",
    reload: { mode: "restart_container", ok: false, detail: "Container 'appdaemon' nicht gefunden" },
  });
  assert.equal(tone, "error");
  assert.match(text, /nicht neu geladen/);
  // Der Pfad muss trotzdem dastehen – die Datei ist geschrieben.
  assert.match(text, /nspanel_config\.yaml/);
});

test("generateStatus nennt bei aktivem Reload, was passiert ist", () => {
  const [text, tone] = generateStatus({
    path: "/x.yaml",
    reload: { mode: "touch_module", ok: true, detail: "/apps/nspanel.py angetickt" },
  });
  assert.equal(tone, "ok");
  assert.match(text, /angetickt/);
});

test("generateStatus bleibt knapp, wenn kein Reload konfiguriert ist", () => {
  for (const reload of [{ mode: "none", ok: true, detail: "Kein Reload konfiguriert" }, {}, undefined]) {
    const [text, tone] = generateStatus({ path: "/x.yaml", reload });
    assert.equal(tone, "ok");
    assert.equal(text, "YAML geschrieben nach /x.yaml");
  }
});

// --- Icon-Picker ------------------------------------------------------------------------------

test("iconKind erkennt die Sonderformen des Backends", () => {
  assert.equal(iconKind("mdi:lightbulb"), "name");
  assert.equal(iconKind("lightbulb"), "name");
  // Diese vier dürfen nicht als Icon-Name bewertet werden.
  assert.equal(iconKind("text:23°"), "special");
  assert.equal(iconKind('ha:{{ states("sensor.x") }}'), "special");
  assert.equal(iconKind("<I>mdi:fireplace</I> ha:{{ states('sensor.y') }} °C"), "special");
  assert.equal(iconKind("{{ 'mdi:x' }}"), "special");
  assert.equal(iconKind(""), "empty");
  assert.equal(iconKind(undefined), "empty");
});

test("iconIsKnown prüft gegen die Mapping-Liste des Backends, mit und ohne mdi:", () => {
  assert.equal(iconIsKnown("mdi:lightbulb"), true);
  assert.equal(iconIsKnown("lightbulb"), true);
  assert.equal(iconIsKnown("mdi:thermometer-water"), true);
  // Ein echtes MDI-Icon, das das Backend-Mapping nicht enthält, muss auffallen.
  assert.equal(iconIsKnown("mdi:gibt-es-nicht-xyz"), false);
  assert.equal(iconIsKnown(""), false);
  assert.equal(iconIsKnown(42), false);
});

test("filterIconNames stellt Präfix-Treffer vor Teiltreffer", () => {
  const treffer = filterIconNames("lightbulb", 10);
  assert.ok(treffer.length > 0);
  assert.equal(treffer[0], "lightbulb");
  assert.ok(treffer.every((name) => name.includes("lightbulb")));

  // "mdi:" darf man mittippen.
  assert.deepEqual(filterIconNames("mdi:lightbulb", 3), filterIconNames("lightbulb", 3));
  // Groß/klein ist egal, und das Limit gilt.
  assert.equal(filterIconNames("LIGHT", 5).length, 5);
  assert.equal(filterIconNames("", 7).length, 7);
  assert.deepEqual(filterIconNames("gibtesnichtxyz"), []);
});

// --- Farbwähler -------------------------------------------------------------------------------

test("colorShape unterscheidet die drei vom Backend akzeptierten Formen", () => {
  assert.equal(colorShape([255, 165, 0]), "rgb");
  assert.equal(colorShape({ on: [255, 255, 0], off: [0, 0, 0] }), "onoff");
  assert.equal(colorShape({ on: [1, 2, 3] }), "onoff");
  assert.equal(colorShape("{{ iif(is_state('x','on'), '[0,255,0]', '[255,0,0]') }}"), "template");
  assert.equal(colorShape(undefined), "unset");
  assert.equal(colorShape(""), "unset");
  // Alles Unbekannte bleibt im JSON-Editor, statt verbogen zu werden.
  assert.equal(colorShape([255, 165]), "other");
  assert.equal(colorShape([300, 0, 0]), "other");
  assert.equal(colorShape({ on: "rot" }), "other");
  assert.equal(colorShape({ tag: [1, 2, 3] }), "other");
});

test("widgetFor schickt Farben in den Farbwähler, nicht in den JSON-Editor", () => {
  assert.equal(widgetFor("color", [255, 165, 0]), "color");
  assert.equal(widgetFor("color", { on: [1, 2, 3], off: [0, 0, 0] }), "color");
  assert.equal(widgetFor("color", undefined), "color");
  // Templates gehören ins Textfeld, Unverstandenes ins JSON.
  assert.equal(widgetFor("color", "{{ x }}"), "string");
  assert.equal(widgetFor("color", [1, 2]), "json");
});

test("Hex und RGB rechnen verlustfrei hin und zurück", () => {
  assert.equal(rgbToHex([255, 165, 0]), "#ffa500");
  assert.equal(rgbToHex([0, 0, 0]), "#000000");
  assert.deepEqual(hexToRgb("#ffa500"), [255, 165, 0]);
  assert.deepEqual(hexToRgb("ffa500"), [255, 165, 0]);
  for (const rgb of [[0, 0, 0], [255, 255, 255], [12, 34, 56], [140, 140, 140]]) {
    assert.deepEqual(hexToRgb(rgbToHex(rgb)), rgb);
  }
  // Ohne Wert nimmt der Wähler den Grauwert, den auch das Backend als Fallback nutzt.
  assert.equal(rgbToHex(undefined), "#8c8c8c");
  assert.equal(hexToRgb("#xyz"), null);
});

test("parseRgbText nimmt die üblichen Schreibweisen und lehnt Unsinn ab", () => {
  assert.deepEqual(parseRgbText("255, 165, 0"), [255, 165, 0]);
  assert.deepEqual(parseRgbText("255,165,0"), [255, 165, 0]);
  assert.deepEqual(parseRgbText("[255, 165, 0]"), [255, 165, 0]);
  // Abgelehnt heißt: der alte Wert bleibt stehen.
  assert.equal(parseRgbText("255, 165"), null);
  assert.equal(parseRgbText("255, 165, 300"), null);
  assert.equal(parseRgbText("rot"), null);
  assert.equal(parseRgbText(""), null);
});

test("isRgb akzeptiert nur echte 0–255-Tripel", () => {
  assert.equal(isRgb([0, 0, 0]), true);
  assert.equal(isRgb([255, 255, 255]), true);
  assert.equal(isRgb(["255", 0, 0]), false);
  assert.equal(isRgb([0, 0, 0, 0]), false);
  assert.equal(isRgb([-1, 0, 0]), false);
});

test("isPlain trennt Objekte/Listen von Skalaren", () => {
  assert.equal(isPlain({}), true);
  assert.equal(isPlain([]), true);
  assert.equal(isPlain(null), false);
  assert.equal(isPlain("x"), false);
  assert.equal(isPlain(0), false);
});
