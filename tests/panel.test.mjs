// Tests der reinen Hilfsfunktionen des Panels – ohne DOM, mit dem Test-Runner von Node (>= 18):
//   node --test tests/
//
// Geprüft wird die Logik, an der Datenverlust hängen würde: die Widget-Wahl (ein Dict darf nie in
// einem Textfeld landen) und die Regel „leeres Feld löscht den Key“.

import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
import { test } from "node:test";

const module = await import(
  "../custom_components/nspanel_ui_config/www/panel/nspanel-ui-config-panel.js"
);
const {
  backupLabel,
  capacityInfo,
  formatSize,
  widgetFor,
  setField,
  entityObjectFields,
  navTargets,
  navSuggestions,
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
  isTemplate,
  splitTemplateSuffix,
  parseTemplateColor,
  templateFieldMode,
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

test("entity_object bekommt seinen eigenen Editor, kein Textfeld", () => {
  // Der Fall, der den Editor einmal „[object Object]“ zeigen ließ: ein Dict ohne eigenen Zweig
  // fällt bis zum Textfeld durch. Auch der *nicht gesetzte* Wert muss dort landen, sonst gäbe es
  // keine Stelle, an der man das Feld anlegen kann.
  assert.equal(widgetFor("entity_object", { entity: "light.a" }), "entity_object");
  assert.equal(widgetFor("entity_object", undefined), "entity_object");
  // Steht dort etwas anderes als ein Dict, bleibt der JSON-Editor – der Wert soll nicht verstümmelt
  // werden, nur weil das Schema ein Objekt erwartet.
  assert.equal(widgetFor("entity_object", "light.a"), "json");
});

test("entityObjectFields hängt die Zusatzkeys an die Entity-Felder", () => {
  const schema = {
    entityFields: ["entity", "name", "icon"],
    entityLikeExtraFields: { statusIcon1: ["altFont"], statusIcon2: ["altFont"] },
  };
  assert.deepEqual(entityObjectFields(schema, "statusIcon1"), ["entity", "name", "icon", "altFont"]);
  // navItem kennt kein altFont – dort darf das Feld auch nicht auftauchen.
  assert.deepEqual(entityObjectFields(schema, "navItem1"), ["entity", "name", "icon"]);
  // Ein Schema ohne die Angabe (ältere Integration im Browser-Cache) darf nicht abstürzen.
  assert.deepEqual(entityObjectFields({}, "statusIcon1"), []);
});

test("navTargets sammelt die Sprungziele aus sichtbaren und versteckten Karten", () => {
  const model = {
    cards: [
      { type: "cardEntities", title: "Wohnzimmer", key: "wohnzimmer" },
      { type: "cardGrid", title: "Küche" }, // ohne key – kein Ziel, das Backend fände sie nicht
      "kaputt",
    ],
    hiddenCards: [{ type: "cardGrid", title: "Heizung", key: "heizung" }],
  };
  assert.deepEqual(navTargets(model), [
    { value: "navigate.wohnzimmer", label: "Wohnzimmer" },
    { value: "navigate.heizung", label: "Heizung · versteckt" },
  ]);
});

test("navTargets nennt einen doppelten Key nur einmal", () => {
  // Das Backend findet zu einem Key nur die erste Karte – die zweite wäre ein totes Ziel.
  const model = {
    cards: [
      { type: "cardGrid", title: "Erste", key: "bad" },
      { type: "cardGrid", title: "Zweite", key: "bad" },
    ],
  };
  assert.deepEqual(navTargets(model), [{ value: "navigate.bad", label: "Erste" }]);
  // Ohne Modell bleibt die Liste leer, statt zu werfen.
  assert.deepEqual(navTargets(undefined), []);
  assert.deepEqual(navTargets({}), []);
});

test("navTargets fällt auf den Kartentyp zurück, wenn der Titel fehlt", () => {
  const model = { cards: [{ type: "cardQR", key: "gast" }] };
  assert.deepEqual(navTargets(model), [{ value: "navigate.gast", label: "cardQR" }]);
});

test("navSuggestions zeigt die Ziele sofort und Entities erst beim Tippen", () => {
  const ziele = [
    { value: "navigate.wohnzimmer", label: "Wohnzimmer" },
    { value: "navigate.bad", label: "Bad · versteckt" },
  ];
  const ids = ["light.bad_lights", "switch.pool", "light.wohnzimmer_decke"];

  // Leeres Feld: alle Ziele, keine Entities – sonst stünde die halbe Installation im DOM.
  assert.deepEqual(navSuggestions(ziele, ids, ""), ziele);
  assert.deepEqual(navSuggestions(ziele, ids, "n"), ziele);

  // Ab zwei Zeichen kommen passende Entities dazu, gefiltert wie die Ziele.
  const treffer = navSuggestions(ziele, ids, "bad");
  assert.deepEqual(treffer, [
    { value: "navigate.bad", label: "Bad · versteckt" },
    { value: "light.bad_lights", label: "" },
  ]);

  // Auch der Titel trägt die Suche, nicht nur der navigate-Wert.
  assert.deepEqual(navSuggestions(ziele, [], "wohnz")[0].value, "navigate.wohnzimmer");
});

test("navSuggestions deckelt die Entity-Vorschläge", () => {
  const ids = Array.from({ length: 200 }, (_, i) => `light.lampe_${String(i).padStart(3, "0")}`);
  const treffer = navSuggestions([], ids, "lampe");
  assert.equal(treffer.length, 50);
  assert.equal(treffer[0].value, "light.lampe_000");
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

// --- Template-Editor --------------------------------------------------------------------------

test("isTemplate erkennt Jinja in beiden Klammerformen", () => {
  assert.equal(isTemplate("{{ states('sensor.x') }}"), true);
  assert.equal(isTemplate("{% if true %}a{% endif %}"), true);
  assert.equal(isTemplate("mdi:lightbulb"), false);
  assert.equal(isTemplate(""), false);
  assert.equal(isTemplate([255, 0, 0]), false);
  assert.equal(isTemplate(undefined), false);
});

test("splitTemplateSuffix schneidet am letzten } – wie das Backend", () => {
  // Der reale Fall: Template plus Einheit.
  assert.deepEqual(splitTemplateSuffix('{{ states("sensor.puffer_oben") }} °C'), [
    '{{ states("sensor.puffer_oben") }}',
    " °C",
  ]);
  // Mehrere Klammern: geschnitten wird am *letzten*, nicht am ersten.
  assert.deepEqual(splitTemplateSuffix("{{ a }}{{ b }} kWh"), ["{{ a }}{{ b }}", " kWh"]);
  // Ohne } gibt es keinen Suffix.
  assert.deepEqual(splitTemplateSuffix("nur Text"), ["nur Text", ""]);
  assert.deepEqual(splitTemplateSuffix(""), ["", ""]);
});

test("parseTemplateColor liest RGB aus einem Rendering-Ergebnis", () => {
  // So liefern die Templates in echten Konfigurationen ihre Farben.
  assert.deepEqual(parseTemplateColor("[0, 120, 255]"), [0, 120, 255]);
  assert.deepEqual(parseTemplateColor("255,165,0"), [255, 165, 0]);
  assert.equal(parseTemplateColor("ha-dark"), null);
  assert.equal(parseTemplateColor(""), null);
});

test("templateFieldMode startet im Template-Modus, wenn der Wert Jinja enthält", () => {
  assert.equal(templateFieldMode("{{ x }}"), "template");
  assert.equal(templateFieldMode("mdi:lightbulb"), "value");
  assert.equal(templateFieldMode([255, 0, 0]), "value");
  assert.equal(templateFieldMode(undefined), "value");
  // Die Wahl des Nutzers schlägt die Erkennung – in beide Richtungen.
  assert.equal(templateFieldMode("mdi:lightbulb", "template"), "template");
  assert.equal(templateFieldMode("{{ x }}", "value"), "value");
  assert.equal(templateFieldMode("{{ x }}", undefined), "template");
});

test("isPlain trennt Objekte/Listen von Skalaren", () => {
  assert.equal(isPlain({}), true);
  assert.equal(isPlain([]), true);
  assert.equal(isPlain(null), false);
  assert.equal(isPlain("x"), false);
  assert.equal(isPlain(0), false);
});

// --- Anzeigekapazität ------------------------------------------------------------------------
//
// Die Zahlen kommen aus schema.py; hier wird nur geprüft, dass das Panel sie richtig auswählt.
// Falsch gewählt hieße: eine Warnung, die es nicht geben darf, oder eine fehlende, die den
// Nutzer stillschweigend Einträge verlieren lässt.

const SCHEMA_STUB = {
  cardCapacity: {
    cardEntities: { eu: 4, "us-l": 4, "us-p": 6 },
    cardGrid: { eu: 6, "us-l": 6, "us-p": 6 },
    cardGrid2: { eu: 8, "us-l": 8, "us-p": 9 },
  },
  cardsWithoutEntityList: ["cardThermo", "cardAlarm", "cardChart", "cardUnlock"],
  gridAutoSwitchAt: 6,
};

test("capacityInfo richtet sich nach dem Panel-Modell", () => {
  assert.equal(capacityInfo(SCHEMA_STUB, "cardEntities", 5, "eu").limit, 4);
  assert.equal(capacityInfo(SCHEMA_STUB, "cardEntities", 5, "eu").over, 1);
  // Dieselbe Karte auf us-p: passt, also keine Übersteigung.
  assert.equal(capacityInfo(SCHEMA_STUB, "cardEntities", 5, "us-p").limit, 6);
  assert.equal(capacityInfo(SCHEMA_STUB, "cardEntities", 5, "us-p").over, 0);
});

test("capacityInfo fällt bei unbekanntem Modell auf eu zurück", () => {
  assert.equal(capacityInfo(SCHEMA_STUB, "cardEntities", 0, undefined).limit, 4);
  assert.equal(capacityInfo(SCHEMA_STUB, "cardEntities", 0, "quatsch").limit, 4);
});

test("capacityInfo bildet den automatischen Wechsel auf cardGrid2 nach", () => {
  // Bis 6 bleibt es ein Grid …
  const sechs = capacityInfo(SCHEMA_STUB, "cardGrid", 6, "eu");
  assert.equal(sechs.shownType, "cardGrid");
  assert.equal(sechs.over, 0);
  // … ab 7 stellt das Backend selbst um, es geht also nichts verloren.
  const sieben = capacityInfo(SCHEMA_STUB, "cardGrid", 7, "eu");
  assert.equal(sieben.shownType, "cardGrid2");
  assert.equal(sieben.switched, true);
  assert.equal(sieben.over, 0);
  // Erst jenseits von cardGrid2 fehlen wirklich Einträge.
  assert.equal(capacityInfo(SCHEMA_STUB, "cardGrid", 9, "eu").over, 1);
});

test("capacityInfo behauptet nichts über Karten ohne Entity-Liste", () => {
  const info = capacityInfo(SCHEMA_STUB, "cardThermo", 3, "eu");
  assert.equal(info.limit, null);
  assert.equal(info.noList, true);
  // Unbekannter Typ: ebenfalls keine Aussage, aber auch nicht als "ohne Liste" ausgeben.
  const fremd = capacityInfo(SCHEMA_STUB, "cardNeuAusUpstream", 3, "eu");
  assert.equal(fremd.limit, null);
  assert.equal(fremd.noList, false);
});

// --- Sicherungen -----------------------------------------------------------------------------

test("generateStatus nennt die angelegte Sicherung", () => {
  const [text, tone] = generateStatus({
    path: "/nspanel-shared/nspanel_config.yaml",
    changed: true,
    backup: { name: "nspanel_config.yaml.2026-07-26_11-30-00-123.bak" },
    reload: { mode: "none", ok: true },
  });
  assert.equal(tone, "ok");
  assert.ok(text.includes("nspanel_config.yaml.2026-07-26_11-30-00-123.bak"), text);
});

test("generateStatus unterscheidet 'nichts geändert' vom Schreiben", () => {
  // Sonst wartet man auf eine Wirkung, die gar nicht eintreten kann.
  const [text, tone] = generateStatus({
    path: "/x/nspanel_config.yaml",
    changed: false,
    backup: null,
    reload: { mode: "none", ok: true },
  });
  assert.equal(tone, "ok");
  assert.ok(/bereits aktuell/.test(text), text);
});

test("generateStatus bleibt bei fehlgeschlagenem Reload ein Fehler", () => {
  const [text, tone] = generateStatus({
    path: "/x/nspanel_config.yaml",
    changed: true,
    backup: { name: "b.bak" },
    reload: { mode: "touch_module", ok: false, detail: "Datei fehlt" },
  });
  assert.equal(tone, "error");
  assert.ok(text.includes("Datei fehlt"), text);
});

test("backupLabel macht aus dem Dateinamen eine lesbare Zeitangabe", () => {
  assert.equal(
    backupLabel({ timestamp: "2026-07-26_11-30-00-123", name: "x.bak" }),
    "26.07.2026, 11:30:00"
  );
  // Unlesbarer Stempel: lieber der Dateiname als eine erfundene Zeit.
  assert.equal(backupLabel({ timestamp: "", name: "komisch.bak" }), "komisch.bak");
});

test("formatSize bleibt kurz", () => {
  assert.equal(formatSize(512), "512 B");
  assert.equal(formatSize(2048), "2.0 kB");
  assert.equal(formatSize(undefined), "");
});

test("das Panel kennt die Fassung, die der Browser geladen hat", () => {
  // Sie steht in der Kopfzeile, weil ES-Module pro Seitenaufruf nur einmal geladen werden: nach
  // einem Update läuft in einer offenen Oberfläche weiter die alte Fassung. Ohne diese Anzeige
  // sucht man den Fehler im Code statt im Browser-Cache.
  const quelle = readFileSync(
    new URL("../custom_components/nspanel_ui_config/www/panel/nspanel-ui-config-panel.js", import.meta.url),
    "utf-8"
  );
  assert.match(quelle, /const PANEL_VERSION = new URLSearchParams\(MODUL_VERSION\)\.get\("v"\)/);
  assert.match(quelle, /class="version"/);
});
