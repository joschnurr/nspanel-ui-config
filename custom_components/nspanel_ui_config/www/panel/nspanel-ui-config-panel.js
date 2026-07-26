// NSPanel UI Config – visueller Editor als HA-Custom-Panel.
//
// Warum ein Custom-Element und kein iFrame: nur so setzt Home Assistant das `hass`-Objekt auf das
// Panel. Damit stehen der Auth-Token für die Integrations-API (`hass.callApi`) und die Entity-Liste
// (`hass.states`) zur Verfügung – ein iFrame bekommt beides nicht.
//
// Kein Build-Schritt, keine externen Abhängigkeiten: das Modul wird direkt so ausgeliefert.
//
// Leitprinzip des Editors (wie bei Importer/Generator): **verlustfrei vor vollständig.**
//   - Das Modell wird als JSON geladen, in-place bearbeitet und unverändert zurückgeschickt.
//     Alles, was der Editor nicht kennt, fasst er nicht an.
//   - Trägt ein Feld ein Dict/eine Liste, schaltet es unabhängig vom Schema-Hinweis auf den
//     JSON-Modus – lieber roh editieren als einen Wert auf ein zu einfaches Widget abschneiden.
//   - Ein geleertes Feld *löscht* den Key, statt "" zu speichern. So bleibt in der erzeugten YAML
//     nur stehen, was auch wirklich gesetzt wurde.

// **Die Nebenmodule werden dynamisch geladen – mit derselben Version im Query wie dieses Modul.**
// Home Assistant hängt an die Panel-URL `?v=<Manifest-Version>`; die Nebenmodule bekämen bei einem
// statischen `import` gar keinen Parameter und blieben nach einem Update im Browser-Cache liegen.
// Dann lädt der Browser das neue Panel und die alte Geometrie dazu – ein Fehler, der wie ein nicht
// installiertes Update aussieht. `import.meta.url` trägt den Parameter, also reichen wir ihn weiter.
// Außerhalb des Browsers (tests/preview.test.mjs) ist er leer, dort ändert sich nichts.
const MODUL_VERSION = new URL(import.meta.url).search;

// Die Namensliste des Backend-Icon-Mappings (erzeugt von tools/extract_icon_names.py).
const { ICON_NAMES } = await import(`./icon-names.js${MODUL_VERSION}`);
// Zu jedem Namen das Zeichen, mit dem das Backend dieses Icon überträgt. Gebraucht für die
// Live-Vorschau: über MQTT kommt nur das Zeichen an, <ha-icon> will den Namen.
const { ICON_CHARS } = await import(`./icon-chars.js${MODUL_VERSION}`);
// Wo die Plätze einer Karte auf dem Display sitzen. Wie *viele* es sind, kommt weiterhin aus dem
// Schema (cardCapacity) und wird an previewSlots übergeben – siehe preview-layouts.js.
const { previewSlots } = await import(`./preview-layouts.js${MODUL_VERSION}`);

const ELEMENT_NAME = "nspanel-ui-config-panel";

const STYLES = `
  :host {
    display: block;
    height: 100%;
    background: var(--primary-background-color, #fafafa);
    color: var(--primary-text-color, #212121);
    font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
    --ns-border: var(--divider-color, #e0e0e0);
  }
  .app { display: flex; flex-direction: column; height: 100%; box-sizing: border-box; }

  header {
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    padding: 10px 16px;
    background: var(--app-header-background-color, var(--primary-color, #03a9f4));
    color: var(--app-header-text-color, #fff);
    box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0,0,0,.2));
  }
  header h1 { font-size: 18px; font-weight: 400; margin: 0; flex: 1; }
  header .dirty { font-size: 13px; opacity: .9; }

  button {
    font: inherit; font-size: 14px; cursor: pointer;
    border: 1px solid transparent; border-radius: 4px; padding: 6px 12px;
    background: rgba(255,255,255,.15); color: inherit;
  }
  button:hover:not(:disabled) { background: rgba(255,255,255,.28); }
  button:disabled { opacity: .5; cursor: default; }
  .body button {
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color, #212121);
    border-color: var(--ns-border);
  }
  .body button:hover:not(:disabled) { background: var(--secondary-background-color, #e5e5e5); }
  .body button.primary { background: var(--primary-color, #03a9f4); color: #fff; border-color: transparent; }
  .body button.danger:hover:not(:disabled) { background: var(--error-color, #db4437); color: #fff; }
  button.icon { padding: 2px 7px; line-height: 1.4; }

  .body { display: flex; flex: 1; min-height: 0; }

  nav {
    width: 290px; flex: none; overflow-y: auto; padding: 12px;
    border-right: 1px solid var(--ns-border);
    background: var(--card-background-color, #fff);
    box-sizing: border-box;
  }
  nav h2 {
    font-size: 12px; text-transform: uppercase; letter-spacing: .06em;
    color: var(--secondary-text-color, #727272);
    margin: 16px 0 6px;
  }
  nav h2:first-child { margin-top: 0; }

  .item {
    display: flex; align-items: center; gap: 4px;
    padding: 6px 8px; border-radius: 4px; cursor: pointer;
    border: 1px solid transparent;
  }
  .item:hover { background: var(--secondary-background-color, #f0f0f0); }
  .item.active { background: var(--primary-color, #03a9f4); color: #fff; }
  .item.active button { color: #fff; }
  .item .label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }
  .item .sub { font-size: 11px; opacity: .7; }
  .item .tools { display: none; gap: 2px; }
  .item:hover .tools, .item.active .tools { display: flex; }
  .item .tools button { background: none; border: none; padding: 1px 5px; font-size: 13px; }

  .add-row { display: flex; gap: 4px; margin-top: 6px; }
  .add-row select { flex: 1; min-width: 0; }

  main { flex: 1; overflow-y: auto; padding: 16px 20px; }
  main h2 { font-size: 20px; font-weight: 400; margin: 0 0 4px; }
  main .hint { color: var(--secondary-text-color, #727272); font-size: 13px; margin: 0 0 16px; }

  fieldset {
    border: 1px solid var(--ns-border); border-radius: 6px;
    margin: 0 0 16px; padding: 12px 14px;
    background: var(--card-background-color, #fff);
  }
  legend { font-size: 13px; font-weight: 500; padding: 0 6px; color: var(--secondary-text-color, #727272); }

  .field { margin-bottom: 12px; }
  .field > label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 3px; }
  .field .desc { font-size: 12px; color: var(--secondary-text-color, #727272); margin-bottom: 3px; }
  .field .row { display: flex; align-items: center; gap: 6px; }
  .field .err { font-size: 12px; color: var(--error-color, #db4437); margin-top: 3px; }
  /* Zulässige Werte: bewusst schwächer als die Beschreibung – erst *was* das Feld tut, dann *womit*. */
  .field .vals {
    font-size: 11.5px; color: var(--secondary-text-color, #727272); opacity: .85;
    margin-bottom: 4px; line-height: 1.45;
  }
  .field .vals b { font-weight: 500; opacity: .8; }

  /* Kapazitätsanzeige an der Entity-Liste. */
  legend .cap { font-weight: 400; }
  legend .cap.over { color: var(--error-color, #db4437); font-weight: 500; }
  .caphint {
    font-size: 12px; color: var(--secondary-text-color, #727272);
    margin: -4px 0 10px; line-height: 1.45;
  }
  .caphint.over { color: var(--error-color, #db4437); }
  /* Einträge jenseits der Anzeigekapazität: sichtbar, aber erkennbar wirkungslos. */
  details.entity.over { border-color: var(--error-color, #db4437); }
  details.entity.over > summary .title { opacity: .6; }
  details.entity > summary .badge {
    font-size: 10.5px; padding: 1px 6px; border-radius: 9px; flex: none;
    background: var(--error-color, #db4437); color: #fff; font-weight: 500;
  }
  .typenote {
    font-size: 12.5px; color: var(--secondary-text-color, #727272);
    margin: 0 0 14px; line-height: 1.5;
  }

  /* Sicherungen */
  .backups { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
  .backup-row {
    display: flex; align-items: center; gap: 10px;
    padding: 7px 10px; border: 1px solid var(--ns-border); border-radius: 6px;
  }
  .backup-row .backup-when { flex: 1; font-size: 14px; }
  .backup-row .backup-size { font-size: 12px; color: var(--secondary-text-color, #727272); }
  .backup-row .tag {
    font-size: 10.5px; padding: 1px 6px; border-radius: 9px; margin-left: 6px;
    background: var(--primary-color, #03a9f4); color: #fff;
  }

  input[type="text"], input[type="number"], select, textarea {
    font: inherit; font-size: 14px; width: 100%; box-sizing: border-box;
    padding: 6px 8px; border-radius: 4px;
    border: 1px solid var(--ns-border);
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color, #212121);
  }
  input:focus, select:focus, textarea:focus { outline: 2px solid var(--primary-color, #03a9f4); outline-offset: -1px; }
  input.invalid, textarea.invalid { border-color: var(--error-color, #db4437); }
  textarea { font-family: var(--code-font-family, monospace); font-size: 13px; resize: vertical; min-height: 62px; }
  /* Farbwähler: der Hex-Wähler bleibt klein, das Zahlenfeld daneben trägt die Wahrheit. */
  .colorbox { display: flex; flex-direction: column; gap: 6px; width: 100%; }
  .colorrow { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .colorrow input[type="color"] {
    inline-size: 42px; block-size: 30px; padding: 0; flex: none;
    border: 1px solid var(--divider-color, #e0e0e0); border-radius: 4px; background: none; cursor: pointer;
  }
  .colorrow .rgbtext { max-width: 140px; }
  .colorrow .colorlabel {
    font-family: var(--code-font-family, monospace); font-size: 12px; min-width: 24px;
    color: var(--secondary-text-color, #727272);
  }
  .colorrow .err { flex-basis: 100%; }
  /* Template-Editor: der Umschalter sitzt rechts im Label, die Vorschau direkt unter dem Feld. */
  .body button.linkbtn {
    float: right; background: none; border: none; padding: 0; font-size: 12px;
    color: var(--primary-color, #03a9f4); text-decoration: underline; cursor: pointer;
  }
  .body button.linkbtn:hover { background: none; }
  .tplbox { display: flex; flex-direction: column; gap: 5px; width: 100%; }
  textarea.tpl { min-height: 74px; }
  .tplpreview {
    display: flex; align-items: center; gap: 6px; min-height: 18px; font-size: 12px;
    font-family: var(--code-font-family, monospace); color: var(--secondary-text-color, #727272);
    word-break: break-word;
  }
  .tplswatch {
    inline-size: 14px; block-size: 14px; flex: none; border-radius: 3px;
    border: 1px solid var(--divider-color, #e0e0e0);
  }

  details.entity { border: 1px solid var(--ns-border); border-radius: 6px; margin-bottom: 8px; }
  details.entity > summary {
    display: flex; align-items: center; gap: 8px;
    padding: 7px 10px; cursor: pointer; font-size: 14px; list-style: none;
  }
  details.entity > summary::-webkit-details-marker { display: none; }
  details.entity > summary .caret { opacity: .6; font-size: 11px; width: 10px; }
  details[open].entity > summary .caret { transform: rotate(90deg); }
  details.entity > summary .title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  details.entity > summary .title small { color: var(--secondary-text-color, #727272); }
  details.entity > .inner { padding: 4px 12px 10px; border-top: 1px solid var(--ns-border); }

  footer {
    border-top: 1px solid var(--ns-border); padding: 8px 16px;
    background: var(--card-background-color, #fff); font-size: 13px;
    max-height: 27vh; overflow-y: auto;
  }
  footer .status { color: var(--secondary-text-color, #727272); }
  footer .status.error { color: var(--error-color, #db4437); }
  footer .status.ok { color: var(--success-color, #43a047); }
  footer ul { margin: 6px 0 0; padding-left: 18px; }
  footer li.error { color: var(--error-color, #db4437); }
  footer li.warning { color: var(--warning-color, #ffa600); }
  footer code { font-family: var(--code-font-family, monospace); opacity: .8; }

  /* Vorschau: Nachbau der Displayfläche, 1:1 in Pixeln (480×320, us-p hochkant). Bewusst keine
     Skalierung – so entspricht ein Pixel hier einem Pixel auf dem Gerät. */
  details.preview { border: 1px solid var(--ns-border); border-radius: 6px; margin: 0 0 16px;
    background: var(--card-background-color, #fff); }
  details.preview > summary {
    padding: 8px 12px; cursor: pointer; font-size: 13px; font-weight: 500;
    color: var(--secondary-text-color, #727272); list-style: none;
  }
  details.preview > summary::-webkit-details-marker { display: none; }
  details.preview > summary .caret { display: inline-block; width: 12px; opacity: .6; font-size: 11px; }
  details[open].preview > summary .caret { transform: rotate(90deg); }
  .modeswitch { display: flex; gap: 6px; padding: 0 12px 8px; }
  .body button.modebtn { font-size: 12.5px; padding: 4px 10px; border-radius: 12px; }
  .body button.modebtn.aktiv {
    background: var(--primary-color, #03a9f4); color: #fff; border-color: transparent;
  }
  .showrow { display: flex; align-items: center; gap: 10px; padding: 0 12px 8px; flex-wrap: wrap; }
  .showrow .hinweis { font-size: 12px; color: var(--secondary-text-color, #727272); }
  .screenwrap { padding: 0 12px 12px; overflow-x: auto; }
  .screenwrap .note { font-size: 12px; color: var(--secondary-text-color, #727272); margin: 0 0 8px; line-height: 1.45; }
  .screen {
    position: relative; background: #000; color: #fff; overflow: hidden;
    border: 4px solid #23262b; border-radius: 8px;
    font-family: Roboto, Arial, sans-serif;
  }
  .screen .slot {
    position: absolute; box-sizing: border-box; overflow: hidden;
    display: flex; align-items: center; gap: 6px; padding: 0 4px;
  }
  /* Freie Plätze sichtbar machen: die Karte hat sie, die Konfiguration füllt sie (noch) nicht. */
  .screen .slot.frei { border: 1px dashed #3a3f47; border-radius: 4px; }
  /* Standardfarbe des Symbols; eine konfigurierte Farbe wird inline gesetzt und gewinnt. */
  .screen .slot .icon { flex: none; --mdc-icon-size: 26px; color: #f5f5f5; }
  .screen .slot .name { flex: 1; font-size: 15px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .screen .slot .val { flex: none; font-size: 15px; color: #d7d9dd; max-width: 45%;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .screen .slot.tile { flex-direction: column; justify-content: center; gap: 2px; }
  .screen .slot.tile .icon { --mdc-icon-size: 30px; }
  .screen .slot.tile .name { flex: none; font-size: 12px; max-width: 100%; text-align: center; }
  .screen .slot.tile .val { font-size: 12px; max-width: 100%; }
  .screen .slot.icon-only { justify-content: center; }
  .screen .slot.main { flex-direction: column; justify-content: center; }
  .screen .slot.main .icon { --mdc-icon-size: 68px; }
  .screen .slot.main .val { font-size: 22px; max-width: 100%; }
  .screen .slot.forecast { flex-direction: column; justify-content: flex-start; gap: 1px; }
  .screen .slot.forecast .name { flex: none; font-size: 12px; max-width: 100%; }
  .screen .slot.forecast .icon { --mdc-icon-size: 34px; }
  .screen .slot.forecast .val { font-size: 13px; max-width: 100%; }
  .screen .slot.center { justify-content: center; }
  .screen .clock { display: flex; align-items: flex-end; justify-content: flex-end; font-size: 44px; }
  .screen .date { display: flex; align-items: flex-start; justify-content: flex-end; font-size: 15px; color: #d7d9dd; }
  .screen .title {
    display: flex; align-items: center; justify-content: center;
    font-size: 15px; color: #fff; border-bottom: 1px solid #23262b;
  }
  .screen .nav {
    display: flex; align-items: center; justify-content: space-between; padding: 0 14px;
    border-top: 1px solid #23262b; color: #7f8590; font-size: 17px;
  }
  /* Flächen, die das Backend selbst gestaltet – die Vorschau zeigt nur, dass sie da sind. */
  .screen .platzhalter {
    display: flex; align-items: center; justify-content: center; text-align: center;
    border: 1px dashed #3a3f47; border-radius: 6px; color: #7f8590; font-size: 13px;
    padding: 4px 8px; line-height: 1.35;
  }
  .screen .slot.tpl { opacity: .75; }
  .screen .slot .warn { color: #ffb300; flex: none; font-size: 12px; }
  /* Abgemessene Plätze: jeder Bestandteil sitzt an seiner eigenen Stelle, kein Flex-Fluss. */
  .screen .slot.measured { display: block; padding: 0; }
  .screen .slot.measured .name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .screen .slot.measured .val { max-width: none; color: #d7d9dd; }
  .screen .title.measured { border: none; }
  .screen .navbtn {
    display: flex; align-items: center; justify-content: center;
    color: #7f8590; font-size: 20px;
  }

  .overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,.45);
    display: flex; align-items: center; justify-content: center; z-index: 10;
  }
  .dialog {
    background: var(--card-background-color, #fff); border-radius: 8px;
    padding: 18px 20px; width: min(680px, 92vw); max-height: 86vh; overflow-y: auto;
    box-shadow: 0 8px 32px rgba(0,0,0,.3);
  }
  .dialog h3 { margin: 0 0 4px; font-weight: 400; }
  .dialog .actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px; }
  .empty { color: var(--secondary-text-color, #727272); font-style: italic; font-size: 14px; }
`;

// --- Helfer ----------------------------------------------------------------------------------

const esc = (value) =>
  String(value).replace(/[&<>"']/g, (ch) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch])
  );

const isPlain = (value) => value !== null && typeof value === "object";

/** Setzt einen Wert – oder entfernt den Key, wenn der Wert "nicht gesetzt" bedeutet. */
function setField(target, key, value) {
  if (value === undefined) delete target[key];
  else target[key] = value;
}

/**
 * Wählt das Eingabe-Widget: der Schema-Hinweis gilt nur, solange der tatsächliche Wert dazu passt.
 * Ein Dict/eine Liste landet immer im JSON-Editor, ein Template in einem number-Feld im Textfeld –
 * so kann die Vereinfachung im Schema nie einen echten Wert zerstören.
 */
/**
 * Wie viele Entities das Display für diese Karte tatsächlich anzeigt.
 *
 * Spiegelt `schema.capacity_for` / `schema.effective_card_type`: die Zahlen kommen aus dem Schema,
 * hier steht nur die Auswahl. `limit === null` heißt „keine Aussage möglich“ – dann behauptet der
 * Editor nichts.
 */
function capacityInfo(schema, cardType, entityCount, panelModel) {
  const table = (schema && schema.cardCapacity) || {};
  const switchAt = schema && typeof schema.gridAutoSwitchAt === "number" ? schema.gridAutoSwitchAt : 6;
  // Einziger Fall, in dem das Backend den Typ selbst wechselt (pages.py).
  const shownType = cardType === "cardGrid" && entityCount > switchAt ? "cardGrid2" : cardType;
  const byModel = table[shownType];
  if (!byModel) {
    const noList = ((schema && schema.cardsWithoutEntityList) || []).includes(cardType);
    return { limit: null, shownType, over: 0, noList };
  }
  const model = byModel[panelModel] === undefined ? "eu" : panelModel;
  const limit = byModel[model];
  return {
    limit,
    shownType,
    model,
    over: Math.max(0, entityCount - limit),
    switched: shownType !== cardType,
    noList: false,
  };
}

function widgetFor(hint, value) {
  // Farben sind der Sonderfall: [r,g,b] und {on,off} sind Objekte, gehören aber gerade *nicht* in
  // den JSON-Editor – für genau diese zwei Formen gibt es den Farbwähler.
  if (hint === "color") {
    const shape = colorShape(value);
    if (shape === "rgb" || shape === "onoff" || shape === "unset") return "color";
    if (shape === "template") return "string";
    return "json";
  }
  if (isPlain(value)) return hint === "entity_object" ? "entity_object" : "json";
  if (value === undefined || value === null || value === "") return hint || "string";
  if (hint === "number" && typeof value !== "number" && isNaN(Number(value))) return "string";
  if (hint === "boolean" && typeof value !== "boolean") return "string";
  if (hint === "entity_object") return "json";
  return hint || "string";
}

/** Beschriftung einer Karte in der Seitenleiste. */
function cardLabel(card) {
  if (!isPlain(card)) return "(ungültige Karte)";
  return card.title || card.key || card.type || "(ohne Titel)";
}

// --- Icons ------------------------------------------------------------------------------------

const ICON_NAME_SET = new Set(ICON_NAMES);

/**
 * Was für ein Icon-Wert ist das?
 *
 * `special` sind die Sonderformen des Backends, die *kein* Icon-Name sind und deshalb nicht gegen
 * die Mapping-Liste geprüft werden dürfen: `text:` (roher Text), `ha:` (Template), `<I>…</I>`
 * (Icon innerhalb eines Templates) und Jinja allgemein.
 */
function iconKind(value) {
  if (typeof value !== "string" || value.trim() === "") return "empty";
  const text = value.trim();
  if (text.includes("text:") || text.includes("ha:") || text.includes("<I>") || text.includes("{{")) {
    return "special";
  }
  return "name";
}

/** Kennt das Backend diesen Namen? Das `mdi:`-Präfix strippt es selbst. */
function iconIsKnown(value) {
  if (typeof value !== "string") return false;
  return ICON_NAME_SET.has(value.trim().replace(/^mdi:/, ""));
}

/** Vorschläge zur Eingabe: erst Namen, die so anfangen, dann alle, die den Text enthalten. */
function filterIconNames(query, limit = 40) {
  const text = String(query || "").trim().toLowerCase().replace(/^mdi:/, "");
  if (!text) return ICON_NAMES.slice(0, limit);
  const beginnt = [];
  const enthaelt = [];
  for (const name of ICON_NAMES) {
    if (name.startsWith(text)) beginnt.push(name);
    else if (name.includes(text)) enthaelt.push(name);
    if (beginnt.length >= limit) break;
  }
  return beginnt.concat(enthaelt).slice(0, limit);
}

// --- Farben -----------------------------------------------------------------------------------

const RGB_FALLBACK = [140, 140, 140]; // derselbe Grauwert, den rgb_dec565 im Backend nimmt

/** Ist das eine [r,g,b]-Liste, wie das Backend sie erwartet? */
function isRgb(value) {
  return (
    Array.isArray(value) &&
    value.length === 3 &&
    value.every((part) => typeof part === "number" && part >= 0 && part <= 255)
  );
}

/**
 * Welche der drei Formen, die das Backend akzeptiert, liegt hier vor?
 *
 * `rgb` = [r,g,b], `onoff` = {on, off} je als RGB, `template` = Jinja-String (rgb_dec565 rendert
 * Strings erst), `unset` = nichts gesetzt. Alles andere ist `other` und bleibt im JSON-Editor —
 * lieber roh anzeigen als einen Wert verbiegen, den wir nicht verstehen.
 */
function colorShape(value) {
  if (value === undefined || value === null || value === "") return "unset";
  if (isRgb(value)) return "rgb";
  if (typeof value === "string") return "template";
  if (isPlain(value) && !Array.isArray(value)) {
    const keys = Object.keys(value);
    if (keys.length > 0 && keys.every((key) => key === "on" || key === "off")) {
      if (keys.every((key) => isRgb(value[key]))) return "onoff";
    }
  }
  return "other";
}

const clamp255 = (part) => Math.max(0, Math.min(255, Math.round(Number(part) || 0)));

function rgbToHex(rgb) {
  const [r, g, b] = isRgb(rgb) ? rgb : RGB_FALLBACK;
  return `#${[r, g, b].map((part) => clamp255(part).toString(16).padStart(2, "0")).join("")}`;
}

function hexToRgb(hex) {
  const match = /^#?([0-9a-f]{6})$/i.exec(String(hex || "").trim());
  if (!match) return null;
  const int = parseInt(match[1], 16);
  return [(int >> 16) & 255, (int >> 8) & 255, int & 255];
}

/** "255, 165, 0" → [255,165,0]; alles Unbrauchbare wird zu null (Wert bleibt dann stehen). */
function parseRgbText(text) {
  const parts = String(text || "")
    .replace(/[[\]]/g, "")
    .split(",")
    .map((part) => part.trim())
    .filter((part) => part !== "");
  if (parts.length !== 3 || parts.some((part) => !/^\d+$/.test(part))) return null;
  const rgb = parts.map(Number);
  return rgb.every((part) => part <= 255) ? rgb : null;
}

// --- Templates --------------------------------------------------------------------------------

/** Steckt Jinja drin? Reicht als Erkennung: das Backend selbst prüft nicht genauer. */
function isTemplate(value) {
  return typeof value === "string" && (value.includes("{{") || value.includes("{%"));
}

/**
 * Zerlegt einen Wert so, wie das Backend es bei ``value``/``icon`` tut: gerendert wird nur bis zum
 * **letzten** ``}``, der Rest wird wörtlich angehängt (``rpartition('}')`` in pages.py). Genau so
 * entstehen Suffixe wie ``…°C`` — die Vorschau muss das nachbilden, sonst zeigt sie etwas anderes
 * als später das Panel.
 */
function splitTemplateSuffix(text) {
  const source = String(text ?? "");
  const cut = source.lastIndexOf("}");
  if (cut === -1) return [source, ""];
  return [source.slice(0, cut + 1), source.slice(cut + 1)];
}

/** Ergibt das Rendering eine RGB-Liste? Templates für Farben liefern Strings wie "[0, 120, 255]". */
function parseTemplateColor(text) {
  return parseRgbText(text);
}

/**
 * Startmodus eines template-fähigen Feldes: Template, sobald der Wert nach Jinja aussieht.
 * `override` ist die bewusste Wahl des Nutzers und schlägt die Erkennung.
 */
function templateFieldMode(value, override) {
  if (override === "template" || override === "value") return override;
  return isTemplate(value) ? "template" : "value";
}

// --- Vorschau ---------------------------------------------------------------------------------

/**
 * Was für ein Eintrag steht im `entity`-Feld?
 *
 * Neben echten entity_ids kennt das Backend Sonderformen, die nie einen Zustand haben: `iText.`
 * (fester Text), `navigate.` (Sprung auf eine andere Karte), `service.` (Dienstaufruf) und `delete`
 * (Platz bewusst frei lassen). Die Vorschau darf für sie weder einen Zustand suchen noch einen
 * fehlenden melden.
 */
function entityKind(id) {
  const text = typeof id === "string" ? id.trim() : "";
  if (!text) return "empty";
  if (text === "delete") return "delete";
  if (text.startsWith("iText.")) return "text";
  if (text.startsWith("navigate.")) return "navigate";
  if (text.startsWith("service.")) return "service";
  return "state";
}

/**
 * Farbe eines Eintrags als CSS-Wert – oder `null`, wenn sie erst gerendert werden muss.
 *
 * `{on, off}` wählt nach dem *aktuellen* Zustand aus; ist keiner bekannt, gilt `on`, weil das die
 * Farbe ist, die man beim Konfigurieren im Blick hat.
 */
function previewColor(value, state) {
  const shape = colorShape(value);
  if (shape === "rgb") return rgbToHex(value);
  if (shape === "onoff") {
    const an = String(state) !== "off" && String(state) !== "closed";
    const gewaehlt = an ? value.on || value.off : value.off || value.on;
    return isRgb(gewaehlt) ? rgbToHex(gewaehlt) : null;
  }
  return null;
}

/**
 * Alles, was für einen Platz der Vorschau ohne Template-Rendering feststeht.
 *
 * `templates` sammelt die Felder, die noch durch HAs Template-Engine müssen – das Panel rendert sie
 * gebündelt nach und trägt das Ergebnis ein. So ist die Vorschau sofort da und wird dann genauer,
 * statt auf einen API-Aufruf zu warten.
 *
 * Zwei Stellen, an denen die Vorschau bewusst *nicht* rät:
 *  - Ohne konfiguriertes `icon` leitet das Backend das Symbol aus Domain und Zustand ab
 *    (`icon_mapping.py`). Nachgebaut wird das nicht; ersatzweise steht hier das Symbol, das Home
 *    Assistant selbst für die Entity führt, gekennzeichnet als `iconAbgeleitet`.
 *  - Ohne `value` steht der Zustand aus Home Assistant da. Das Backend formatiert ihn teils anders
 *    (Einheiten, Übersetzungen) – deshalb ist auch das nur eine Näherung.
 */
function previewContent(entity, states = {}) {
  if (!isPlain(entity)) {
    return { frei: true, kind: "empty", name: "", value: "", icon: "", templates: [] };
  }
  const id = typeof entity.entity === "string" ? entity.entity.trim() : "";
  const kind = entityKind(id);
  const zustand = kind === "state" ? states[id] : undefined;
  const attrs = (zustand && zustand.attributes) || {};
  const templates = [];

  const fest = (feld, wert) => {
    if (typeof wert === "string" && isTemplate(wert)) {
      templates.push({ feld, text: wert });
      return null;
    }
    return wert === undefined || wert === null || wert === "" ? null : String(wert);
  };

  let name = fest("name", entity.name);
  if (name === null && !templates.some((t) => t.feld === "name")) {
    if (kind === "text") name = "";
    else if (kind === "state") name = attrs.friendly_name || id;
    else name = id;
  }

  let value = fest("value", entity.value);
  if (value === null && !templates.some((t) => t.feld === "value")) {
    if (kind === "text") value = id.slice("iText.".length);
    else if (zustand) {
      value = attrs.unit_of_measurement
        ? `${zustand.state} ${attrs.unit_of_measurement}`
        : zustand.state;
    } else value = "";
  }

  let icon = null;
  let iconAbgeleitet = false;
  let iconSonderform = false;
  if (typeof entity.icon === "string" && entity.icon.trim() !== "") {
    if (iconKind(entity.icon) === "special") {
      // `text:`/`ha:`/`<I>` sind kein Icon-Name. Steckt Jinja drin, rendert das Panel es nach.
      iconSonderform = true;
      if (isTemplate(entity.icon)) templates.push({ feld: "icon", text: entity.icon });
    } else {
      icon = `mdi:${entity.icon.trim().replace(/^mdi:/, "")}`;
    }
  } else if (attrs.icon) {
    icon = attrs.icon;
    iconAbgeleitet = true;
  }

  let color = previewColor(entity.color, zustand && zustand.state);
  if (color === null && colorShape(entity.color) === "template") {
    templates.push({ feld: "color", text: entity.color });
  }

  return {
    frei: kind === "empty" || kind === "delete",
    kind,
    id,
    name: name === null ? "" : name,
    value: value === null ? "" : value,
    icon,
    iconAbgeleitet,
    iconSonderform,
    iconUnbekannt: icon !== null && !iconAbgeleitet && !iconIsKnown(icon),
    color,
    // Fehlt eine echte entity_id in Home Assistant, ist das fast immer ein Tippfehler.
    zustandFehlt: kind === "state" && !zustand,
    templates,
  };
}

/**
 * Der Icon-Name zu einem Zeichen aus dem Nextion-Font – der Rückweg des Backend-Mappings.
 *
 * Über MQTT kommt das Symbol als Zeichen an (`icon_mapping.py` bildet Name → Zeichen ab).
 * `icon-chars.js` steht in derselben Reihenfolge wie `icon-names.js`, der Index verbindet beide.
 */
function iconNameFromChar(zeichen) {
  if (typeof zeichen !== "string" || zeichen === "") return null;
  const index = ICON_CHARS.indexOf(zeichen[0]);
  return index === -1 ? null : ICON_NAMES[index];
}

/**
 * Ein Eintrag, wie ihn das Gerät gerade anzeigt, in der Form, die die Zeichenschicht erwartet.
 *
 * Hier ist **nichts abgeleitet**: Symbol, Farbe, Name und Wert stehen so in der Nachricht, die ans
 * Display ging. Deshalb entfallen alle Kennzeichen der Modell-Vorschau (`iconAbgeleitet`,
 * `templates`, `zustandFehlt`) – es gibt nichts zu schätzen und nichts nachzurendern.
 */
function liveContent(eintrag) {
  if (!isPlain(eintrag)) {
    return { frei: true, kind: "empty", name: "", value: "", icon: null, templates: [] };
  }
  const name = iconNameFromChar(eintrag.iconChar);
  return {
    frei: Boolean(eintrag.leer),
    kind: eintrag.type || "state",
    id: eintrag.entity || "",
    name: eintrag.name || "",
    value: eintrag.value || "",
    icon: name ? `mdi:${name}` : null,
    iconAbgeleitet: false,
    iconSonderform: false,
    // Ein Zeichen, das nicht im mitgelieferten Mapping steht, kommt aus einer neueren
    // Backend-Version. Das Display zeigt es trotzdem – nur wir kennen den Namen nicht.
    iconUnbekannt: Boolean(eintrag.iconChar) && !name,
    color: Array.isArray(eintrag.rgb) ? rgbToHex(eintrag.rgb) : null,
    zustandFehlt: false,
    templates: [],
  };
}

/**
 * Bündelt mehrere Templates in einen einzigen Aufruf von `/api/template`.
 *
 * Eine Karte kann leicht zwei Dutzend Templates tragen (Name, Wert, Icon und Farbe je Eintrag) –
 * einzeln gerendert wären das ebenso viele Anfragen bei jeder Änderung. Getrennt wird mit dem
 * ASCII-Steuerzeichen *Record Separator*, das in gerendertem Text praktisch nie vorkommt.
 *
 * Der Aufrufer muss den Fall abfangen, dass die Teilezahl nicht stimmt: ein Template, das den
 * Trenner selbst ausgibt, würde die Zuordnung verschieben. Dann ist Einzelrendern richtig.
 */
const TEMPLATE_SEPARATOR = "\u001e";

/**
 * Was ist aus einem gerenderten `icon`-Template geworden – ein Symbol oder Text?
 *
 * Das Backend erlaubt in Icon-Feldern `<I>name</I>`, um mitten im Text ein Symbol zu setzen; steht
 * am Ende ein reiner Icon-Name, ist es ebenfalls ein Symbol. Alles andere ist schlicht Text.
 */
function iconFromRendered(text) {
  const roh = String(text ?? "").trim();
  const treffer = /<I>([^<]+)<\/I>/i.exec(roh);
  if (treffer) return { icon: treffer[1].trim().replace(/^mdi:/, ""), text: roh };
  const name = roh.replace(/^mdi:/, "");
  if (name && iconIsKnown(name)) return { icon: name, text: roh };
  return { icon: null, text: roh };
}

function joinTemplates(texts) {
  return texts.join(TEMPLATE_SEPARATOR);
}

function splitTemplateResult(rendered, count) {
  const parts = String(rendered ?? "").split(TEMPLATE_SEPARATOR);
  if (parts.length !== count) return null;
  return parts.map((part) => part.trim());
}

/**
 * Statuszeile nach dem Generieren: `[Text, Ton]`.
 *
 * Ein fehlgeschlagener Reload ist keine gescheiterte Ausgabe – die YAML steht schon auf der Platte.
 * Der Unterschied muss aber sichtbar sein, sonst hält man das Panel für übernommen, während das
 * NSPanel noch die alte Konfiguration zeigt.
 */
function generateStatus(result) {
  const path = result?.path;
  const reload = result?.reload || {};
  // `changed: false` heißt, die Datei hatte schon genau diesen Inhalt – dann wurde bewusst weder
  // geschrieben noch gesichert. Das muss man sehen, sonst wartet man auf eine Wirkung, die ausbleibt.
  const geschrieben =
    result?.changed === false
      ? `Keine Änderung – ${path} war bereits aktuell`
      : `YAML geschrieben nach ${path}`;
  const gesichert = result?.backup?.name ? ` (vorheriger Stand gesichert als ${result.backup.name})` : "";

  if (reload.ok === false) {
    return [
      `${geschrieben}${gesichert}, aber AppDaemon nicht neu geladen: ${reload.detail}`,
      "error",
    ];
  }
  const stillerModus = !reload.mode || reload.mode === "none" || reload.mode === "skipped";
  if (stillerModus) return [`${geschrieben}${gesichert}`, "ok"];
  return [`${geschrieben}${gesichert} – ${reload.detail}`, "ok"];
}

/** Zeitstempel einer Sicherung (aus dem Dateinamen) als lesbare lokale Angabe. */
function backupLabel(entry) {
  const stamp = entry?.timestamp || "";
  const match = stamp.match(/^(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})/);
  if (!match) return entry?.name || "";
  const [, jahr, monat, tag, stunde, minute, sekunde] = match;
  return `${tag}.${monat}.${jahr}, ${stunde}:${minute}:${sekunde}`;
}

/** Dateigröße kurz und lesbar. */
function formatSize(bytes) {
  if (typeof bytes !== "number" || bytes < 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} kB`;
}

// --- Panel -----------------------------------------------------------------------------------

// Im Browser ist das schlicht HTMLElement. Der Fallback existiert nur, damit sich das Modul auch
// in Node importieren lässt (tests/panel.test.mjs) – dort wird die Klasse nie instanziiert.
const PanelBase = typeof HTMLElement !== "undefined" ? HTMLElement : class {};

class NsPanelUiConfigPanel extends PanelBase {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._model = null;
    this._schema = null;
    this._findings = [];
    this._selection = { kind: "global", index: 0 };
    this._dirty = false;
    this._status = { text: "", tone: "" };
    this._booted = false;
    // Pro Feld die bewusste Wahl "Template" oder "fester Wert". WeakMap, damit gelöschte Karten und
    // Entities nichts festhalten; der Modus ist reine Ansichtssache und wird nie mitgespeichert.
    this._templateModes = new WeakMap();
    // Vorschau: aufgeklappt bleibt über Kartenwechsel hinweg erhalten, die Marke schützt vor
    // Template-Antworten, die zu einer längst ersetzten Zeichnung gehören.
    this._previewOpen = true;
    this._previewToken = 0;
    this._previewTimer = null;
    // "model" = aus der bearbeiteten Konfiguration, "live" = was das Gerät gerade anzeigt.
    this._previewMode = "model";
    this._livePollTimer = null;
    this._liveTitle = "";
  }

  // HA setzt `hass` bei *jedem* State-Update. Hier darf deshalb nichts neu gerendert werden –
  // sonst verliert jedes Eingabefeld bei der nächsten Zustandsänderung im Haus den Fokus.
  set hass(value) {
    this._hass = value;
    if (!this._booted && this.isConnected) this._boot();
  }
  get hass() {
    return this._hass;
  }

  connectedCallback() {
    if (!this.shadowRoot.firstChild) this._renderShell();
    if (!this._booted && this._hass) this._boot();
  }

  async _boot() {
    this._booted = true;
    try {
      const [schema, config] = await Promise.all([
        this._hass.callApi("GET", "nspanel_ui_config/schema"),
        this._hass.callApi("GET", "nspanel_ui_config/config"),
      ]);
      this._schema = schema;
      this._model = config.model;
      this._findings = config.findings || [];
      this._setStatus(
        config.stored
          ? "Gespeicherte Konfiguration geladen."
          : "Noch nichts gespeichert – leeres Gerüst. Bestehende apps.yaml über „Importieren“ übernehmen.",
        config.stored ? "" : "warn"
      );
    } catch (err) {
      this._setStatus(`Laden fehlgeschlagen: ${this._errText(err)}`, "error");
    }
    this._renderAll();
  }

  _errText(err) {
    if (!err) return "unbekannter Fehler";
    if (typeof err === "string") return err;
    if (err.body && err.body.message) return err.body.message;
    return err.message || JSON.stringify(err);
  }

  // --- Grundgerüst ---------------------------------------------------------------------------

  _renderShell() {
    this.shadowRoot.innerHTML = `
      <style>${STYLES}</style>
      <div class="app">
        <header>
          <h1>NSPanel UI Konfiguration</h1>
          <span class="dirty" id="dirty"></span>
          <button id="btn-import">Importieren…</button>
          <button id="btn-backups">Sicherungen…</button>
          <button id="btn-save">Speichern</button>
          <button id="btn-generate">YAML erzeugen</button>
        </header>
        <div class="body">
          <nav id="nav"></nav>
          <main id="main"></main>
        </div>
        <footer>
          <div class="status" id="status"></div>
          <div id="findings"></div>
        </footer>
      </div>
      <div id="dialog-host"></div>
      <datalist id="entity-list"></datalist>
    `;
    this._$("btn-import").addEventListener("click", () => this._openImportDialog());
    this._$("btn-backups").addEventListener("click", () => this._openBackupDialog());
    this._$("btn-save").addEventListener("click", () => this._save());
    this._$("btn-generate").addEventListener("click", () => this._generate());
  }

  _$(id) {
    return this.shadowRoot.getElementById(id);
  }

  _renderAll() {
    this._renderEntityDatalist();
    this._renderNav();
    this._renderDetail();
    this._renderStatus();
  }

  _renderEntityDatalist() {
    const list = this._$("entity-list");
    if (!list || !this._hass || list.childElementCount) return;
    const states = this._hass.states || {};
    list.innerHTML = Object.keys(states)
      .sort()
      .map((id) => {
        const name = (states[id].attributes && states[id].attributes.friendly_name) || "";
        return `<option value="${esc(id)}">${esc(name)}</option>`;
      })
      .join("");
  }

  _setStatus(text, tone = "") {
    this._status = { text, tone };
    if (this.shadowRoot.firstChild) this._renderStatus();
  }

  _renderStatus() {
    const el = this._$("status");
    if (!el) return;
    el.className = `status ${this._status.tone === "error" ? "error" : this._status.tone === "ok" ? "ok" : ""}`;
    el.textContent = this._status.text;
    this._$("dirty").textContent = this._dirty ? "• ungespeicherte Änderungen" : "";

    const findings = this._findings || [];
    this._$("findings").innerHTML = findings.length
      ? `<ul>${findings
          .map(
            (f) =>
              `<li class="${esc(f.level)}"><code>${esc(f.path)}</code> – ${esc(f.message)}</li>`
          )
          .join("")}</ul>`
      : "";
  }

  _markDirty() {
    this._dirty = true;
    this._findings = [];
    this._renderStatus();
    // Das Formular bleibt stehen (Fokus!), die Vorschau zieht nach.
    this._schedulePreview();
  }

  // --- Seitenleiste --------------------------------------------------------------------------

  _renderNav() {
    const nav = this._$("nav");
    if (!this._model || !this._schema) {
      nav.innerHTML = "";
      return;
    }
    const sel = this._selection;
    const active = (kind, index) =>
      sel.kind === kind && (index === undefined || sel.index === index) ? " active" : "";

    const cardItems = (kind, cards) =>
      (cards || [])
        .map(
          (card, index) => `
          <div class="item${active(kind, index)}" data-kind="${kind}" data-index="${index}">
            <span class="label">${esc(cardLabel(card))}
              <span class="sub">${esc(isPlain(card) ? card.type || "?" : "?")}</span>
            </span>
            <span class="tools">
              <button class="icon" data-act="up" title="Nach oben">▲</button>
              <button class="icon" data-act="down" title="Nach unten">▼</button>
              <button class="icon" data-act="dup" title="Duplizieren">⧉</button>
              <button class="icon" data-act="del" title="Löschen">✕</button>
            </span>
          </div>`
        )
        .join("") || `<div class="empty" style="padding:4px 8px">keine</div>`;

    const typeOptions = [...this._schema.cardTypes]
      .map((type) => `<option value="${esc(type)}">${esc(type)}</option>`)
      .join("");

    nav.innerHTML = `
      <h2>Allgemein</h2>
      <div class="item${active("global")}" data-kind="global"><span class="label">Globale Einstellungen</span></div>
      <div class="item${active("screensaver")}" data-kind="screensaver"><span class="label">Screensaver</span></div>

      <h2>Karten</h2>
      ${cardItems("cards", this._model.cards)}
      <div class="add-row">
        <select id="add-type">${typeOptions}</select>
        <button data-add="cards" title="Karte hinzufügen">+</button>
      </div>

      <h2>Versteckte Karten</h2>
      ${cardItems("hiddenCards", this._model.hiddenCards)}
      <div class="add-row">
        <button data-add="hiddenCards" style="flex:1">+ versteckte Karte</button>
      </div>
    `;

    nav.querySelectorAll(".item").forEach((item) => {
      item.addEventListener("click", (event) => {
        const toolButton = event.target.closest("button[data-act]");
        const kind = item.dataset.kind;
        const index = item.dataset.index === undefined ? undefined : Number(item.dataset.index);
        if (toolButton) {
          event.stopPropagation();
          this._cardAction(toolButton.dataset.act, kind, index);
          return;
        }
        this._selection = { kind, index: index || 0 };
        this._renderNav();
        this._renderDetail();
      });
    });

    nav.querySelectorAll("button[data-add]").forEach((button) => {
      button.addEventListener("click", () => this._addCard(button.dataset.add));
    });
  }

  _addCard(kind) {
    const type = this._$("add-type") ? this._$("add-type").value : "cardEntities";
    const card = { type, entities: [], extra: {} };
    if (!Array.isArray(this._model[kind])) this._model[kind] = [];
    this._model[kind].push(card);
    this._selection = { kind, index: this._model[kind].length - 1 };
    this._markDirty();
    this._renderNav();
    this._renderDetail();
  }

  _cardAction(action, kind, index) {
    const list = this._model[kind];
    if (!Array.isArray(list) || index === undefined) return;
    if (action === "del") {
      if (!confirm(`Karte „${cardLabel(list[index])}“ löschen?`)) return;
      list.splice(index, 1);
      if (this._selection.kind === kind && this._selection.index >= list.length) {
        this._selection = { kind, index: Math.max(0, list.length - 1) };
      }
    } else if (action === "dup") {
      list.splice(index + 1, 0, JSON.parse(JSON.stringify(list[index])));
      this._selection = { kind, index: index + 1 };
    } else {
      const target = action === "up" ? index - 1 : index + 1;
      if (target < 0 || target >= list.length) return;
      [list[index], list[target]] = [list[target], list[index]];
      this._selection = { kind, index: target };
    }
    this._markDirty();
    this._renderNav();
    this._renderDetail();
  }

  // --- Detailbereich -------------------------------------------------------------------------

  /** Das gerade ausgewählte Objekt (globale Settings, Screensaver oder eine Karte). */
  _selected() {
    const { kind, index } = this._selection;
    if (kind === "global") return this._model.global || (this._model.global = {});
    if (kind === "screensaver") return this._model.screensaver;
    const list = this._model[kind];
    return Array.isArray(list) ? list[index] : undefined;
  }

  _renderDetail() {
    const main = this._$("main");
    if (!this._model || !this._schema) {
      main.innerHTML = `<p class="hint">Wird geladen…</p>`;
      return;
    }
    const { kind } = this._selection;
    if (kind === "global") return this._renderGlobal(main);
    if (kind === "screensaver") return this._renderScreensaver(main);
    return this._renderCard(main);
  }

  _renderGlobal(main) {
    const settings = this._model.global || {};
    // Bekannte Felder in Schema-Reihenfolge, danach alles, was sonst noch im Block steht.
    const known = this._schema.globalFieldOrder;
    const rest = Object.keys(settings).filter((key) => !known.includes(key));

    main.innerHTML = `
      <h2>Globale Einstellungen</h2>
      <p class="hint">Gelten für das gesamte Panel. Leere Felder werden nicht in die YAML geschrieben –
        das Backend nutzt dann seinen Standardwert (in Klammern).</p>
      ${this._previewBlockHtml()}
      <fieldset><legend>Panel</legend><div id="global-known"></div></fieldset>
      ${rest.length ? `<fieldset><legend>Weitere Felder aus der Quelldatei</legend><div id="global-rest"></div></fieldset>` : ""}
    `;

    // Auch hier eine Vorschau, und zwar aus zwei Gründen: dies ist die Startseite des Editors –
    // ohne sie fände man die Vorschau erst, wenn man links etwas auswählt –, und `model`
    // (eu/us-l/us-p) ändert unmittelbar Größe und Aufteilung des Displays.
    this._bindPreview(main);

    const host = main.querySelector("#global-known");
    known.forEach((name) => host.appendChild(this._field(settings, name, { showDefault: true })));
    if (rest.length) {
      const restHost = main.querySelector("#global-rest");
      rest.forEach((name) => restHost.appendChild(this._field(settings, name)));
    }
  }

  _renderScreensaver(main) {
    if (!this._model.screensaver) {
      main.innerHTML = `
        <h2>Screensaver</h2>
        <p class="hint">Für dieses Panel ist kein Screensaver konfiguriert.</p>
        <button class="primary" id="add-screensaver">Screensaver anlegen</button>`;
      main.querySelector("#add-screensaver").addEventListener("click", () => {
        this._model.screensaver = { type: "screensaver2", entities: [], extra: {} };
        this._markDirty();
        this._renderDetail();
      });
      return;
    }
    this._renderCardLike(main, this._model.screensaver, "Screensaver", {
      hint: "Die Anzeige im Ruhezustand.",
      typeOptions: this._schema.screensaverTypes,
      removable: true,
      onRemove: () => {
        if (!confirm("Screensaver-Konfiguration entfernen?")) return;
        this._model.screensaver = null;
        this._markDirty();
        this._renderDetail();
      },
    });
  }

  _renderCard(main) {
    const card = this._selected();
    if (!card) {
      main.innerHTML = `<h2>Karte</h2><p class="hint">Keine Karte ausgewählt.</p>`;
      return;
    }
    if (!isPlain(card)) {
      main.innerHTML = `<h2>Ungültige Karte</h2>
        <p class="hint">Dieser Eintrag ist kein Objekt und wird unverändert durchgereicht:</p>
        <pre><code>${esc(JSON.stringify(card, null, 2))}</code></pre>`;
      return;
    }
    const position = this._selection.index + 1;
    const total = (this._model[this._selection.kind] || []).length;
    this._renderCardLike(main, card, `${cardLabel(card)}`, {
      hint: `${this._selection.kind === "cards" ? "Karte" : "Versteckte Karte"} ${position} von ${total}`,
      typeOptions: this._schema.cardTypes,
    });
  }

  /**
   * Gemeinsames Formular für Karte und Screensaver: erst die typabhängigen Felder, dann – je nach
   * Kartentyp – die flache Entity und/oder die Entity-Liste, zuletzt das `extra`-Dict.
   */
  _renderCardLike(main, card, title, options) {
    const type = card.type;
    const schema = this._schema;
    const isFlat = schema.flatEntityCardTypes.includes(type);
    const isSingle = schema.singleEntityCardTypes.includes(type);
    const showEntityList = !isSingle || Array.isArray(card.entities);

    const cardFields = [
      ...schema.cardCommonFields,
      ...(schema.cardTypeFields[type] || []),
    ].filter((name, index, all) => all.indexOf(name) === index);

    const capacity = this._capacity(card);
    const typeNote = (schema.cardTypeNotes || {})[type];

    main.innerHTML = `
      <h2>${esc(title)}</h2>
      <p class="hint">${esc(options.hint || "")}</p>
      ${typeNote ? `<p class="typenote">${esc(typeNote)}</p>` : ""}
      ${this._previewBlockHtml()}
      <fieldset><legend>Karte</legend><div id="card-fields"></div>
        ${options.removable ? `<button class="danger" id="remove-card">Entfernen</button>` : ""}
      </fieldset>
      ${isFlat ? `<fieldset><legend>Entity der Karte</legend><div id="flat-entity"></div></fieldset>` : ""}
      ${showEntityList ? `<fieldset><legend>Entity-Liste${capacity.legend}</legend>
        ${capacity.note ? `<p class="caphint${capacity.over ? " over" : ""}">${capacity.note}</p>` : ""}
        <div id="entity-list-host"></div>
        <button class="primary" id="add-entity">+ Entity</button></fieldset>` : ""}
      <div id="extra-host"></div>
    `;

    this._bindPreview(main);

    const fieldHost = main.querySelector("#card-fields");
    cardFields.forEach((name) => {
      const opts = { cardType: type };
      if (name === "type") {
        opts.options = options.typeOptions;
        opts.onChange = () => this._retypeCard();
      }
      fieldHost.appendChild(this._field(card, name, opts));
    });

    if (options.removable) {
      main.querySelector("#remove-card").addEventListener("click", options.onRemove);
    }

    if (isFlat) {
      const flatHost = main.querySelector("#flat-entity");
      schema.entityFields.forEach((name) =>
        flatHost.appendChild(this._field(card, name, { cardType: type }))
      );
    }

    if (showEntityList) {
      this._renderEntityList(main.querySelector("#entity-list-host"), card);
      main.querySelector("#add-entity").addEventListener("click", () => {
        if (!Array.isArray(card.entities)) card.entities = [];
        card.entities.push({ entity: "", extra: {} });
        this._markDirty();
        this._renderDetail();
      });
    }

    main.querySelector("#extra-host").appendChild(this._extraEditor(card));
  }

  /**
   * Kapazitätsanzeige für die Entity-Liste einer Karte: Legendenzusatz, Erläuterung und wie viele
   * Einträge über dem Limit liegen. Ein zu langer Block ist sonst nicht zu bemerken – die YAML
   * bleibt gültig, das Backend schweigt, und auf dem Panel fehlen die Einträge einfach.
   */
  _capacity(card) {
    const entities = Array.isArray(card.entities) ? card.entities : [];
    const info = capacityInfo(
      this._schema,
      card.type,
      entities.length,
      (this._model.global || {}).model
    );
    if (info.limit === null) {
      if (!info.noList) return { limit: null, over: 0, legend: "", note: "" };
      return {
        limit: null,
        over: 0,
        legend: "",
        note: `${esc(card.type)} wertet keine Entity-Liste aus – maßgeblich ist die Entity der Karte.`,
      };
    }

    const layout = (this._schema.capacityLayoutNotes || {})[info.shownType];
    const modelNote = info.model ? ` auf Modell <code>${esc(info.model)}</code>` : "";
    const switched = info.switched
      ? ` Weil mehr als ${this._schema.gridAutoSwitchAt} Entities konfiguriert sind, stellt das
         Backend die Karte selbst auf <code>cardGrid2</code> um.`
      : "";
    const overNote = info.over
      ? ` <b>Die letzten ${info.over} erscheinen nicht auf dem Display</b> – sie bleiben in der
         Konfiguration erhalten, werden aber nirgends angezeigt.`
      : "";

    return {
      limit: info.limit,
      over: info.over,
      legend: ` <span class="cap${info.over ? " over" : ""}">– ${entities.length} von ${
        info.limit
      } Plätzen</span>`,
      note: `${esc(info.shownType)} zeigt${modelNote} ${info.limit} Einträge.${switched}${
        layout ? ` ${esc(layout)}` : ""
      }${overNote}`,
    };
  }

  // --- Vorschau ------------------------------------------------------------------------------

  /** Der aufklappbare Vorschau-Block – identisch auf jeder Seite des Editors. */
  _previewBlockHtml() {
    return `
      <details class="preview" id="preview"${this._previewOpen ? " open" : ""}>
        <summary><span class="caret">▶</span> Vorschau – wie das Display die Einträge anordnet</summary>
        <div class="modeswitch">
          <button class="modebtn${this._previewMode === "live" ? "" : " aktiv"}" data-mode="model">aus der Konfiguration</button>
          <button class="modebtn${this._previewMode === "live" ? " aktiv" : ""}" data-mode="live">vom Gerät (live)</button>
        </div>
        <div class="screenwrap" id="preview-host"></div>
      </details>`;
  }

  /** Hängt die Bedienung an den Vorschau-Block und zeichnet ihn, wenn er offen ist. */
  _bindPreview(main) {
    const vorschau = main.querySelector("#preview");
    if (!vorschau) return;
    vorschau.addEventListener("toggle", () => {
      this._previewOpen = vorschau.open;
      if (vorschau.open) this._renderPreview();
      else this._stopLivePolling();
    });
    main.querySelectorAll(".modebtn").forEach((button) => {
      button.addEventListener("click", () => {
        this._previewMode = button.dataset.mode;
        main.querySelectorAll(".modebtn").forEach((b) => b.classList.toggle("aktiv", b === button));
        this._renderPreview();
      });
    });
    if (this._previewOpen) this._renderPreview();
  }

  /**
   * Welche Karte die Vorschau zeigt.
   *
   * Auf den globalen Einstellungen gibt es keine ausgewählte Karte – dort steht stellvertretend der
   * Screensaver, sonst die erste Karte. `stellvertretend` sagt der Beschriftung, dass die gezeigte
   * Karte nicht die bearbeitete ist.
   */
  _previewCard() {
    if (this._selection.kind !== "global") return { card: this._selected() };
    const screensaver = this._model.screensaver;
    if (isPlain(screensaver)) return { card: screensaver, stellvertretend: "Screensaver" };
    const erste = (this._model.cards || []).find((eintrag) => isPlain(eintrag));
    if (erste) return { card: erste, stellvertretend: `Karte „${cardLabel(erste)}“` };
    return { card: null };
  }

  /**
   * Zeichnet die Displayfläche der ausgewählten Karte neu.
   *
   * Bewusst getrennt vom Formular: Feldänderungen bauen das Formular *nicht* neu auf (sonst
   * verlöre das Eingabefeld den Fokus), die Vorschau aber schon – sie hängt deshalb an
   * `_markDirty` und nicht an `_renderDetail`.
   */
  _renderPreview() {
    const host = this._$("preview-host");
    if (!host || !this._model || !this._schema) return;
    if (this._previewMode === "live") return this._renderLivePreview(host);
    this._stopLivePolling();
    const { card, stellvertretend } = this._previewCard();
    if (!isPlain(card)) {
      host.innerHTML = `<p class="note">Noch keine Karte, die sich zeigen ließe – zuerst eine
        anlegen oder eine bestehende <code>apps.yaml</code> importieren.</p>`;
      return;
    }

    const model = (this._model.global || {}).model || "eu";
    const entities = Array.isArray(card.entities) ? card.entities : [];
    const info = capacityInfo(this._schema, card.type, entities.length, model);
    const layout = previewSlots({
      cardType: info.shownType,
      capacity: info.limit === null ? 0 : info.limit,
      filled: entities.length,
      model,
    });

    // Jede Neuzeichnung bekommt eine Marke: Antworten auf Template-Anfragen einer *älteren*
    // Vorschau dürfen die neue nicht überschreiben.
    const marke = (this._previewToken = (this._previewToken || 0) + 1);
    const auftraege = [];
    const states = (this._hass && this._hass.states) || {};

    const screen = document.createElement("div");
    screen.className = "screen";
    screen.style.width = `${layout.screen.w}px`;
    screen.style.height = `${layout.screen.h}px`;

    if (layout.chrome) {
      screen.appendChild(
        this._chromeSlot("title", 0, 0, 100, 11, card.title === undefined ? "" : String(card.title))
      );
      const nav = this._chromeSlot("nav", 0, 89, 100, 11, "");
      nav.innerHTML = `<span>◀</span><span>⌂</span><span>▶</span>`;
      screen.appendChild(nav);
    }

    // Die Zeichenschicht bekommt den Inhalt als Funktion – dieselbe Fläche zeigt so wahlweise das
    // Modell oder das, was das Gerät gerade anzeigt (siehe _renderLivePreview).
    const inhaltFuer = (slot) =>
      previewContent(slot.index === "flat" ? card : entities[slot.index], states);
    layout.slots.forEach((slot) => {
      const element = this._slotElement(slot, card, inhaltFuer, auftraege, marke);
      if (element) screen.appendChild(element);
    });

    host.innerHTML = "";
    const hinweis = document.createElement("p");
    hinweis.className = "note";
    // Welche Einträge das Layout gar nicht erst zeichnet (der Screensaver verdrängt im
    // alternativen Layout einen) – das wäre sonst nirgends zu sehen.
    const belegt = new Set(
      layout.slots.map((slot) => slot.index).filter((index) => typeof index === "number")
    );
    const verdeckt = [];
    for (let i = 0; i < Math.min(entities.length, info.limit === null ? 0 : info.limit); i++) {
      if (!belegt.has(i)) verdeckt.push(i + 1);
    }
    hinweis.innerHTML = this._previewNote(info, model, entities.length, verdeckt, stellvertretend);
    host.appendChild(hinweis);
    host.appendChild(screen);

    if (auftraege.length) this._resolvePreviewTemplates(auftraege, marke);
  }

  /** Der Titel, der auf der Displayfläche steht – im Live-Modus der des Geräts. */
  _previewTitle(card) {
    if (this._previewMode === "live") return this._liveTitle || "";
    return isPlain(card) && card.title !== undefined ? String(card.title) : "";
  }

  /**
   * Die Vorschau aus dem Mitschnitt des Geräts.
   *
   * **Was hier anders ist als in der Modell-Vorschau:** nichts wird abgeleitet. Symbol, Farbe, Name
   * und Wert stehen genau so in der Nachricht, die ans Display ging – auch die Symbole, die das
   * Backend selbst aus Domain und Zustand wählt, und die Formatierung der Werte. Dafür zeigt sie
   * **die Karte, die das Panel gerade anzeigt**, nicht die, die man gerade bearbeitet.
   */
  async _renderLivePreview(host) {
    // Gezielt nach der Karte fragen, die gerade bearbeitet wird – das Panel selbst steht meist im
    // Ruhezustand und sendet dann nur den Screensaver.
    const { card: gesucht } = this._previewCard();
    const frage = new URLSearchParams();
    if (isPlain(gesucht)) {
      if (gesucht.title) frage.set("card", String(gesucht.title));
      if (gesucht.type) frage.set("type", String(gesucht.type));
    }
    const pfad = `nspanel_ui_config/live${frage.toString() ? `?${frage}` : ""}`;

    let antwort;
    try {
      antwort = await this._hass.callApi("GET", pfad);
    } catch (err) {
      this._stopLivePolling();
      host.innerHTML = `<p class="note">Live-Ansicht nicht abrufbar: ${esc(this._errText(err))}</p>`;
      return;
    }
    this._startLivePolling();

    const nachricht = antwort && antwort.message;
    if (!nachricht) {
      const grund = (antwort && antwort.reason) || "Noch nichts empfangen.";
      const topic = antwort && antwort.topic;
      host.innerHTML = `<p class="note">${esc(grund)}${
        topic ? `<br>Topic: <code>${esc(topic)}</code>` : ""
      }</p>`;
      return;
    }

    const model = (this._model.global || {}).model || "eu";
    const eintraege = nachricht.entities || [];
    const info = capacityInfo(this._schema, nachricht.cardType, eintraege.length, model);
    const layout = previewSlots({
      cardType: info.shownType,
      capacity: info.limit === null ? eintraege.length : info.limit,
      filled: eintraege.length,
      model,
    });

    this._liveTitle = nachricht.title || "";
    const marke = (this._previewToken = (this._previewToken || 0) + 1);

    const screen = document.createElement("div");
    screen.className = "screen";
    screen.style.width = `${layout.screen.w}px`;
    screen.style.height = `${layout.screen.h}px`;

    if (layout.chrome) {
      screen.appendChild(this._chromeSlot("title", 0, 0, 100, 11, this._liveTitle));
      const nav = this._chromeSlot("nav", 0, 89, 100, 11, "");
      nav.innerHTML = `<span>◀</span><span>⌂</span><span>▶</span>`;
      screen.appendChild(nav);
    }

    // Kein Template-Rendering nötig: was hier ankommt, ist bereits gerendert.
    const inhaltFuer = (slot) => liveContent(eintraege[slot.index]);
    layout.slots.forEach((slot) => {
      const element = this._slotElement(slot, {}, inhaltFuer, [], marke);
      if (element) screen.appendChild(element);
    });

    host.innerHTML = "";
    host.appendChild(this._liveNote(antwort, nachricht, eintraege.length));
    const aufruf = this._showButton(gesucht, antwort);
    if (aufruf) host.appendChild(aufruf);
    host.appendChild(screen);
  }

  /**
   * Knopf, der das Panel auf die bearbeitete Karte bittet.
   *
   * **Das Gerät wechselt dabei sichtbar die Anzeige** – deshalb steht das auch dran, und deshalb
   * passiert es nur auf Klick. Das Backend findet eine Karte über ihren `key`; hat sie keinen,
   * lässt sie sich nicht gezielt aufrufen, und der Knopf sagt genau das.
   */
  _showButton(karte, antwort) {
    if (!isPlain(karte) || String(karte.type || "").startsWith("screensaver")) return null;
    const zeile = document.createElement("div");
    zeile.className = "showrow";

    const key = typeof karte.key === "string" ? karte.key.trim() : "";
    if (!key) {
      zeile.innerHTML =
        `<span class="hinweis">Zum gezielten Aufrufen braucht diese Karte ein Feld ` +
        `<code>key</code> – dann kann das Backend sie über <code>navigate.&lt;key&gt;</code> finden.</span>`;
      return zeile;
    }

    const knopf = document.createElement("button");
    knopf.textContent = "Karte am Gerät aufrufen";
    knopf.title = "Das Panel wechselt sichtbar auf diese Karte – geschaltet wird nichts.";
    const meldung = document.createElement("span");
    meldung.className = "hinweis";
    if (!antwort.matched) meldung.textContent = "danach steht sie hier";

    knopf.addEventListener("click", async () => {
      knopf.disabled = true;
      meldung.textContent = "wird aufgerufen…";
      try {
        await this._hass.callApi("POST", "nspanel_ui_config/show", { key });
        meldung.textContent = "aufgerufen – die Ansicht folgt in wenigen Sekunden";
      } catch (err) {
        meldung.textContent = `Fehlgeschlagen: ${this._errText(err)}`;
      } finally {
        knopf.disabled = false;
      }
    });

    zeile.appendChild(knopf);
    zeile.appendChild(meldung);
    return zeile;
  }

  /** Erklärt, woher das Bild kommt – und worauf dabei zu achten ist. */
  _liveNote(antwort, nachricht, anzahl) {
    const hinweis = document.createElement("p");
    hinweis.className = "note";
    const alter = antwort.ageSeconds;
    const wann =
      alter === null || alter === undefined
        ? ""
        : alter < 60
        ? `vor ${Math.round(alter)} s`
        : alter < 5400
        ? `vor ${Math.round(alter / 60)} min`
        : `vor ${Math.round(alter / 3600)} h`;

    const teile = [];
    if (antwort.matched) {
      // Der Normalfall, für den die Ansicht gedacht ist: der letzte echte Stand *dieser* Karte.
      teile.push(
        `<b>Diese Karte, wie sie zuletzt auf dem Gerät stand</b>${wann ? ` (${wann})` : ""}: ` +
          `${anzahl} ${anzahl === 1 ? "Eintrag" : "Einträge"}.`
      );
    } else {
      // Die bearbeitete Karte war noch nie dran – das Panel steht meist im Ruhezustand.
      teile.push(
        `<b>Diese Karte wurde noch nicht am Gerät angezeigt.</b> Am Panel einmal dorthin ` +
          `blättern, dann steht sie hier – auch später noch, wenn das Panel wieder ruht. ` +
          `Gezeigt wird solange <code>${esc(nachricht.cardType || "?")}</code>` +
          `${nachricht.title ? ` („${esc(nachricht.title)}")` : ""}${wann ? `, ${wann}` : ""}.`
      );
    }
    if (!nachricht.strukturiert) {
      teile.push(
        "Diese Karte baut das Backend aus eigenen Feldern statt aus Einträgen – die Fläche bleibt " +
          "deshalb leer."
      );
    }
    const bekannt = (antwort.known || []).filter((eintrag) => eintrag.cardType);
    if (bekannt.length > 1) {
      teile.push(
        `Bisher mitgeschnitten: ${bekannt
          .map((eintrag) => esc(eintrag.title || eintrag.cardType))
          .join(", ")}.`
      );
    }
    teile.push(
      "Hier ist nichts geschätzt: Symbole, Farben und Werte kommen so, wie sie ans Display gingen."
    );
    hinweis.innerHTML = teile.join(" ");
    return hinweis;
  }

  /** Holt den Live-Stand regelmäßig nach, solange die Ansicht offen ist. */
  _startLivePolling() {
    if (this._livePollTimer) return;
    this._livePollTimer = setInterval(() => {
      if (this._previewMode !== "live" || !this._previewOpen) {
        this._stopLivePolling();
        return;
      }
      const host = this._$("preview-host");
      if (host) this._renderLivePreview(host);
    }, 3000);
  }

  _stopLivePolling() {
    if (!this._livePollTimer) return;
    clearInterval(this._livePollTimer);
    this._livePollTimer = null;
  }

  /** Erklärt, was die Vorschau zeigt – und was sie nicht leisten kann. */
  _previewNote(info, model, entityCount, verdeckt = [], stellvertretend = null) {
    const teile = [
      stellvertretend
        ? `Stellvertretend: ${esc(stellvertretend)} – Modell <code>${esc(model)}</code>`
        : `Modell <code>${esc(model)}</code>, ${esc(info.shownType)}`,
    ];
    if (info.switched) teile.push("vom Backend automatisch umgestellt");
    const kopf = teile.join(" – ");
    const ueber =
      info.over > 0
        ? ` <b>Die letzten ${info.over} von ${entityCount} Einträgen haben keinen Platz</b> und fehlen hier wie auf dem Gerät.`
        : "";
    // Kein Kapazitätsproblem, sondern ein Layout: der Eintrag liegt im Rahmen, das Display zeigt
    // ihn trotzdem nicht (Screensaver, alternatives Layout).
    const gedraengt = verdeckt.length
      ? ` <b>Eintrag ${verdeckt.join(", ")} hat in diesem Layout keinen Platz</b> – er zählt zur ` +
        `Kapazität, wird vom Display aber nicht gezeigt.`
      : "";
    return (
      `${kopf}. Schematisch: Plätze, Reihenfolge, Farben und Werte stimmen, Größen und Schriftart ` +
      `sind nachempfunden. Symbole ohne eigene Angabe leitet das Backend aus der Entity ab – ` +
      `ersatzweise steht hier das Symbol aus Home Assistant (blasser dargestellt).${ueber}${gedraengt}`
    );
  }

  _chromeSlot(kind, x, y, w, h, text) {
    const element = document.createElement("div");
    element.className = kind;
    Object.assign(element.style, {
      position: "absolute",
      left: `${x}%`,
      top: `${y}%`,
      width: `${w}%`,
      height: `${h}%`,
      boxSizing: "border-box",
    });
    if (text) element.textContent = text;
    return element;
  }

  /**
   * Ein Platz der Vorschau – entweder ein Eintrag oder eine Fläche, die das Backend selbst füllt.
   *
   * `inhaltFuer(slot)` liefert den Inhalt: aus dem bearbeiteten Modell (`previewContent`) oder aus
   * dem Mitschnitt des Geräts (`liveContent`). Beide liefern dieselbe Form, deshalb kommt die
   * Zeichenschicht mit einer einzigen Fassung aus.
   */
  _slotElement(slot, card, inhaltFuer, auftraege, marke) {
    const element = document.createElement("div");
    Object.assign(element.style, {
      position: "absolute",
      left: `${slot.x}%`,
      top: `${slot.y}%`,
      width: `${slot.w}%`,
      height: `${slot.h}%`,
      boxSizing: "border-box",
    });

    // Flächen ohne Entity: QR-Code, Regler, Tastatur … – nachgebaut wird nur ihre Lage.
    const platzhalter = {
      qr: "QR-Code",
      slider: "Lautstärke",
      transport: "⏮  ⏯  ⏭",
      "flat-main": {
        thermo: "Thermostat-Bedienung",
        keypad: "Zifferntastatur",
        chart: "Diagramm",
      },
    }[slot.kind];
    if (platzhalter !== undefined) {
      element.className = "platzhalter";
      element.textContent =
        typeof platzhalter === "string" ? platzhalter : platzhalter[slot.widget] || "";
      if (slot.kind === "flat-main") {
        // Auf diesen Karten trägt die Karte selbst die Entity – ihr Name gehört sichtbar dazu.
        const inhalt = inhaltFuer(slot);
        element.textContent = `${element.textContent}${inhalt.name ? `\n${inhalt.name}` : ""}`;
        element.style.whiteSpace = "pre-line";
      }
      return element;
    }

    if (slot.kind === "title" || slot.kind === "navbtn") {
      // Rahmen aus dem abgemessenen Layout: Kartentitel und die beiden Blättertasten.
      element.className = slot.kind === "title" ? "title measured" : "navbtn";
      element.textContent =
        slot.kind === "title"
          ? this._previewTitle(card)
          : slot.taste === "prev"
          ? "◀"
          : "▶";
      return element;
    }

    if (slot.kind === "clock" || slot.kind === "date") {
      element.className = slot.kind;
      // Näherung: die echte Formatierung macht das Backend nach timeFormat/dateFormat (strftime).
      const jetzt = new Date();
      element.textContent =
        slot.kind === "clock"
          ? jetzt.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })
          : jetzt.toLocaleDateString(undefined, {
              weekday: "long",
              day: "numeric",
              month: "long",
            });
      return element;
    }

    const inhalt = inhaltFuer(slot);

    if (slot.parts) return this._measuredSlot(element, slot, inhalt, auftraege, marke);

    const art = { icon: "icon-only", value: "row", "flat-title": "row" }[slot.kind] || slot.kind;
    element.className = `slot ${art}${inhalt.frei ? " frei" : ""}`;
    if (inhalt.frei) {
      // Freier Platz: `delete` ist Absicht, „nichts konfiguriert" nur noch nicht gefüllt.
      element.title =
        inhalt.kind === "delete" ? "entity: delete – Platz bleibt frei" : "Platz nicht belegt";
      return element;
    }

    const zeigtName = art !== "icon-only" && art !== "center" && art !== "main";
    const zeigtWert = art !== "icon-only";

    // Das Symbol trägt die Farbe (siehe _faerbe) – es wird deshalb hier festgehalten.
    const symbol = art !== "center" ? this._slotIcon(inhalt, auftraege, marke) : null;
    if (symbol) element.appendChild(symbol);
    if (zeigtName) {
      const name = document.createElement("span");
      name.className = "name";
      name.textContent = inhalt.name;
      this._registerTemplate(inhalt, "name", auftraege, marke, (text) => {
        name.textContent = text;
      });
      element.appendChild(name);
    }
    if (zeigtWert) {
      const wert = document.createElement("span");
      wert.className = "val";
      wert.textContent = inhalt.value;
      this._registerTemplate(inhalt, "value", auftraege, marke, (text) => {
        wert.textContent = text;
      });
      element.appendChild(wert);
    }
    this._faerbe(symbol || element, inhalt, auftraege, marke);
    if (inhalt.zustandFehlt) {
      element.title = `${inhalt.id} gibt es in Home Assistant nicht`;
      const warnung = document.createElement("span");
      warnung.className = "warn";
      warnung.textContent = "⚠";
      element.appendChild(warnung);
    }
    return element;
  }

  /**
   * Ein Platz, dessen Geometrie aus den HMI-Dumps stammt (`layouts.js`).
   *
   * Anders als bei den nachempfundenen Anordnungen sitzt hier **jeder Bestandteil an seiner
   * eigenen Stelle** – Symbol, Name und Bedienfläche stehen im Dump als getrennte Komponenten.
   * Die Schriftgröße richtet sich nach der echten Höhe des Textfeldes, gedeckelt auf einen Wert,
   * der im Browser noch lesbar bleibt.
   */
  _measuredSlot(element, slot, inhalt, auftraege, marke) {
    element.className = `slot measured${inhalt.frei ? " frei" : ""}`;
    if (inhalt.frei) {
      element.title =
        inhalt.kind === "delete" ? "entity: delete – Platz bleibt frei" : "Platz nicht belegt";
      return element;
    }

    const setze = (kind, teil) => {
      kind.style.position = "absolute";
      kind.style.left = `${teil.left}%`;
      kind.style.top = `${teil.top}%`;
      kind.style.width = `${teil.width}%`;
      kind.style.height = `${teil.height}%`;
      kind.style.boxSizing = "border-box";
    };

    const { icon, name, value } = slot.parts;
    let symbol = null;
    if (icon) {
      symbol = this._slotIcon(inhalt, auftraege, marke);
      setze(symbol, icon);
      // Symbolflächen sind im HMI meist deutlich größer als das Symbol selbst.
      symbol.style.setProperty("--mdc-icon-size", `${Math.round(Math.min(icon.px[0], icon.px[1]) * 0.8)}px`);
      symbol.style.display = "flex";
      symbol.style.alignItems = "center";
      symbol.style.justifyContent = "center";
      element.appendChild(symbol);
    }
    if (name) {
      const text = document.createElement("span");
      text.className = "name";
      text.textContent = inhalt.name;
      setze(text, name);
      text.style.fontSize = `${Math.min(Math.round(name.px[1] * 0.62), 20)}px`;
      text.style.display = "flex";
      text.style.alignItems = "center";
      this._registerTemplate(inhalt, "name", auftraege, marke, (gerendert) => {
        text.textContent = gerendert;
      });
      element.appendChild(text);
    }
    if (value) {
      const wert = document.createElement("span");
      wert.className = "val";
      wert.textContent = inhalt.value;
      setze(wert, value);
      wert.style.fontSize = `${Math.min(Math.round(value.px[1] * 0.55), 18)}px`;
      wert.style.display = "flex";
      wert.style.alignItems = "center";
      wert.style.justifyContent = "center";
      this._registerTemplate(inhalt, "value", auftraege, marke, (gerendert) => {
        wert.textContent = gerendert;
      });
      element.appendChild(wert);
    } else if (!name && inhalt.value) {
      // Karten wie cardMedia haben nur eine Symbolfläche – der Wert bekommt dann keinen Platz.
      element.title = `${inhalt.name}${inhalt.value ? `: ${inhalt.value}` : ""}`;
    }

    this._faerbe(symbol || element, inhalt, auftraege, marke);
    if (inhalt.zustandFehlt) element.title = `${inhalt.id} gibt es in Home Assistant nicht`;
    return element;
  }

  /**
   * Legt die konfigurierte Farbe auf das **Symbol**, nicht auf den ganzen Platz.
   *
   * So macht es das Gerät: das HMI schreibt die übertragene Farbe in die Schriftfarbe der
   * Icon-Komponente (`covx tTmp.txt,tF1Icon.pco`), während Name und Wert ihre feste Farbe behalten.
   * Färbte man den ganzen Platz, würden Name und Wert bunt und das Symbol bliebe weiß – genau
   * verkehrt herum. Fehlt ein Symbol (etwa auf der Mitte von cardPower), färbt der Platz selbst.
   */
  _faerbe(ziel, inhalt, auftraege, marke) {
    // Neben `color` auch `--icon-primary-color`: `ha-icon` füllt sein SVG mit
    // `var(--icon-primary-color, currentcolor)`. Ist die Variable von einem Theme gesetzt, gewinnt
    // sie gegen die geerbte Farbe – dann bliebe das Symbol trotz gesetzter Farbe unverändert.
    const setzen = (farbe) => {
      ziel.style.color = farbe;
      ziel.style.setProperty("--icon-primary-color", farbe);
    };
    if (inhalt.color) setzen(inhalt.color);
    this._registerTemplate(inhalt, "color", auftraege, marke, (text) => {
      const rgb = parseTemplateColor(text);
      if (rgb) setzen(rgbToHex(rgb));
    });
  }

  /** Das Symbol eines Platzes – inklusive der Sonderformen, die gar kein Symbol sind. */
  _slotIcon(inhalt, auftraege, marke) {
    if (inhalt.iconSonderform) {
      // `text:`/`ha:`/`<I>…</I>`: hier steht Text, kein Symbol. Was dabei herauskommt, zeigt das
      // Template-Rendering – bis dahin bleibt der Platz leer.
      const span = document.createElement("span");
      span.className = "val";
      span.style.flex = "none";
      this._registerTemplate(inhalt, "icon", auftraege, marke, (text) => {
        const gelesen = iconFromRendered(text);
        if (gelesen.icon) {
          const symbol = document.createElement("ha-icon");
          symbol.className = "icon";
          symbol.setAttribute("icon", `mdi:${gelesen.icon}`);
          span.replaceWith(symbol);
        } else span.textContent = gelesen.text;
      });
      return span;
    }
    const symbol = document.createElement("ha-icon");
    symbol.className = `icon${inhalt.iconAbgeleitet ? " abgeleitet" : ""}`;
    symbol.setAttribute("icon", inhalt.icon || "mdi:checkbox-blank-circle-outline");
    if (!inhalt.icon) {
      symbol.style.opacity = ".35";
      symbol.title = "Kein Symbol gesetzt – das Backend leitet es aus der Entity ab";
    } else if (inhalt.iconAbgeleitet) {
      symbol.style.opacity = ".6";
      symbol.title = `Aus Home Assistant übernommen (${inhalt.icon}) – das Backend wählt eigenständig`;
    } else if (inhalt.iconUnbekannt) {
      symbol.title = `${inhalt.icon} steht nicht im Mapping des Backends – dort erschiene alert-circle-outline`;
    }
    return symbol;
  }

  /** Merkt ein noch zu renderndes Template für den nächsten Sammelaufruf vor. */
  _registerTemplate(inhalt, feld, auftraege, marke, apply) {
    const eintrag = (inhalt.templates || []).find((t) => t.feld === feld);
    if (!eintrag) return;
    // Bei value und icon rendert das Backend nur bis zum letzten `}` – der Rest bleibt wörtlich.
    const suffixFeld = (this._schema.templateSuffixFields || []).includes(feld);
    const [template, suffix] = suffixFeld ? splitTemplateSuffix(eintrag.text) : [eintrag.text, ""];
    auftraege.push({
      template,
      marke,
      apply: (text) => apply(text === null ? eintrag.text : `${text}${suffix}`),
    });
  }

  /**
   * Rendert alle Templates der Vorschau – in einem Aufruf, mit Einzelaufrufen als Rückfallebene.
   *
   * Eine volle Karte trägt schnell zwei Dutzend Templates; einzeln gerendert wären das ebenso viele
   * Anfragen bei jeder Änderung. Stimmt die Teilezahl nicht (ein Template gibt den Trenner selbst
   * aus) oder scheitert der Sammelaufruf an einem einzigen kaputten Template, wird einzeln
   * gerendert: dann bleiben die übrigen Plätze richtig.
   */
  async _resolvePreviewTemplates(auftraege, marke) {
    if (!this._hass) return;
    const texte = auftraege.map((auftrag) => auftrag.template);
    let ergebnisse = null;
    try {
      const gerendert = await this._hass.callApi("POST", "template", {
        template: joinTemplates(texte),
      });
      ergebnisse = splitTemplateResult(gerendert, texte.length);
    } catch (err) {
      ergebnisse = null;
    }
    if (!ergebnisse) {
      ergebnisse = await Promise.all(
        texte.map(async (text) => {
          try {
            return String(await this._hass.callApi("POST", "template", { template: text })).trim();
          } catch (err) {
            return null; // Fehlerhaftes Template: der Platz zeigt weiter den Rohtext.
          }
        })
      );
    }
    if (marke !== this._previewToken) return; // Die Vorschau wurde inzwischen neu gebaut.
    auftraege.forEach((auftrag, index) => auftrag.apply(ergebnisse[index]));
  }

  /** Zeichnet die Vorschau entprellt neu – ein Tastendruck soll keine Anfragewelle auslösen. */
  _schedulePreview() {
    clearTimeout(this._previewTimer);
    this._previewTimer = setTimeout(() => this._renderPreview(), 400);
  }

  /** Nach einem Typwechsel ändern sich die anzuzeigenden Felder – Formular komplett neu bauen. */
  _retypeCard() {
    this._renderNav();
    this._renderDetail();
  }

  _renderEntityList(host, card) {
    const entities = Array.isArray(card.entities) ? card.entities : [];
    if (!entities.length) {
      host.innerHTML = `<p class="empty">Noch keine Entities.</p>`;
      return;
    }
    const limit = this._capacity(card).limit;
    host.innerHTML = "";
    entities.forEach((entity, index) => {
      const details = document.createElement("details");
      // Über der Kapazität: der Eintrag bleibt bedienbar, wird aber als wirkungslos gekennzeichnet.
      const beyond = limit !== null && index >= limit;
      details.className = beyond ? "entity over" : "entity";
      const label = isPlain(entity) ? entity.entity || "(ohne entity)" : String(entity);
      const name = isPlain(entity) && entity.name ? ` – ${entity.name}` : "";
      details.innerHTML = `
        <summary>
          <span class="caret">▶</span>
          <span class="title">${esc(index + 1)}. ${esc(label)}<small>${esc(name)}</small></span>
          ${beyond ? `<span class="badge" title="Über der Anzeigekapazität dieser Karte">nicht sichtbar</span>` : ""}
          <button class="icon" data-act="up" title="Nach oben">▲</button>
          <button class="icon" data-act="down" title="Nach unten">▼</button>
          <button class="icon" data-act="dup" title="Duplizieren">⧉</button>
          <button class="icon danger" data-act="del" title="Löschen">✕</button>
        </summary>
        <div class="inner"></div>`;

      details.querySelectorAll("summary button").forEach((button) => {
        button.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          this._entityAction(button.dataset.act, entities, index);
        });
      });

      const inner = details.querySelector(".inner");
      if (isPlain(entity)) {
        this._schema.entityFields.forEach((fieldName) =>
          inner.appendChild(this._field(entity, fieldName, { cardType: card.type }))
        );
        inner.appendChild(this._extraEditor(entity));
      } else {
        inner.innerHTML = `<p class="empty">Kein Objekt – wird unverändert übernommen.</p>`;
      }
      host.appendChild(details);
    });
  }

  _entityAction(action, entities, index) {
    if (action === "del") {
      entities.splice(index, 1);
    } else if (action === "dup") {
      entities.splice(index + 1, 0, JSON.parse(JSON.stringify(entities[index])));
    } else {
      const target = action === "up" ? index - 1 : index + 1;
      if (target < 0 || target >= entities.length) return;
      [entities[index], entities[target]] = [entities[target], entities[index]];
    }
    this._markDirty();
    this._renderDetail();
  }

  // --- Felder --------------------------------------------------------------------------------

  /** Beschreibung eines Feldes – kartentyp-spezifische Fassung schlägt die allgemeine. */
  _fieldDescription(name, cardType) {
    const perCard = (this._schema.cardFieldDescriptions || {})[cardType];
    if (perCard && perCard[name]) return perCard[name];
    return this._schema.fieldDescriptions[name];
  }

  /**
   * Baut ein Eingabefeld für `target[name]`. Schreibt bei `change` direkt ins Modell zurück –
   * nicht bei jedem Tastendruck, damit das Formular während der Eingabe nicht neu aufgebaut wird.
   */
  _field(target, name, options = {}) {
    const value = target[name];
    const hint = options.forceWidget || this._schema.fieldHints[name] || "string";
    const widget = options.forceWidget || widgetFor(hint, value);
    // Kartentyp-spezifische Beschreibung geht vor: `entity` heißt auf cardThermo etwas anderes
    // als auf dem Screensaver.
    const description = this._fieldDescription(name, options.cardType);
    const valueHint = (this._schema.fieldValueHints || {})[name];
    const fallback = options.showDefault ? this._schema.globalDefaults[name] : undefined;

    const wrapper = document.createElement("div");
    wrapper.className = "field";
    const caption = options.label || name;
    const labelText =
      fallback === undefined || fallback === null
        ? esc(caption)
        : `${esc(caption)} <span class="desc" style="display:inline">(Standard: ${esc(
            typeof fallback === "object" ? JSON.stringify(fallback) : fallback
          )})</span>`;
    wrapper.innerHTML = `<label>${labelText}</label>${
      description ? `<div class="desc">${esc(description)}</div>` : ""
    }${
      valueHint ? `<div class="vals"><b>Mögliche Werte:</b> ${esc(valueHint)}</div>` : ""
    }<div class="row"></div><div class="err" hidden></div>`;

    const row = wrapper.querySelector(".row");
    const errorEl = wrapper.querySelector(".err");
    const commit = (newValue) => {
      setField(target, name, newValue);
      this._markDirty();
      if (options.onChange) options.onChange();
      else if (name === "title" || name === "key" || name === "name" || name === "entity") {
        // Beschriftungen in Seitenleiste bzw. Entity-Kopfzeile mitziehen.
        this._renderNav();
        if (name === "name" || name === "entity") this._refreshEntitySummaries();
      }
    };

    if (widget === "json") {
      const area = document.createElement("textarea");
      const lines = isPlain(value) ? JSON.stringify(value, null, 2).split("\n").length : 3;
      area.rows = Math.max(3, Math.min(12, lines));
      area.value = value === undefined ? "" : JSON.stringify(value, null, 2);
      area.addEventListener("change", () => {
        const text = area.value.trim();
        if (!text) {
          area.classList.remove("invalid");
          errorEl.hidden = true;
          commit(undefined);
          return;
        }
        try {
          const parsed = JSON.parse(text);
          area.classList.remove("invalid");
          errorEl.hidden = true;
          commit(parsed);
        } catch (err) {
          // Ungültiges JSON wird bewusst *nicht* übernommen – sonst ginge der alte Wert verloren.
          area.classList.add("invalid");
          errorEl.hidden = false;
          errorEl.textContent = `Kein gültiges JSON: ${err.message} (Wert unverändert)`;
        }
      });
      row.appendChild(area);
      return wrapper;
    }

    // Template-fähige Felder bekommen einen Umschalter. Der `extra`-Bereich und erzwungene Widgets
    // bleiben außen vor – dort steht rohes JSON, kein einzelner Wert.
    const templateCapable =
      !options.forceWidget && (this._schema.templateFields || []).includes(name);
    if (templateCapable) {
      const mode = templateFieldMode(value, this._templateOverride(target, name));
      const umschalter = document.createElement("button");
      umschalter.type = "button";
      umschalter.className = "linkbtn";
      umschalter.textContent = mode === "template" ? "als festen Wert bearbeiten" : "als Template bearbeiten";
      umschalter.addEventListener("click", () => {
        this._setTemplateOverride(target, name, mode === "template" ? "value" : "template");
        // Nur dieses Feld neu bauen: ein kompletter Neuaufbau würde offene Entity-Blöcke zuklappen.
        wrapper.replaceWith(this._field(target, name, options));
      });
      wrapper.querySelector("label").appendChild(umschalter);

      if (mode === "template") {
        row.appendChild(this._templateEditor(name, value, commit, errorEl));
        return wrapper;
      }
    }

    if (widget === "color") {
      row.appendChild(this._colorEditor(value, commit));
      return wrapper;
    }

    if (widget === "boolean") {
      const select = document.createElement("select");
      select.innerHTML = `
        <option value="">– nicht gesetzt –</option>
        <option value="true">ja</option>
        <option value="false">nein</option>`;
      select.value = value === undefined ? "" : String(Boolean(value));
      select.addEventListener("change", () =>
        commit(select.value === "" ? undefined : select.value === "true")
      );
      row.appendChild(select);
      return wrapper;
    }

    const input = document.createElement("input");
    input.type = widget === "number" ? "number" : "text";
    input.value = value === undefined || value === null ? "" : String(value);

    if (widget === "entity") {
      input.setAttribute("list", "entity-list");
      input.placeholder = "z. B. light.wohnzimmer";
    } else if (widget === "select" || options.options) {
      // Immer neu befüllen: `type` etwa hat je nach Kontext andere Auswahl (Karte vs. Screensaver),
      // eine einmal erzeugte Liste würde sonst die falschen Werte behalten.
      const listId = `opts-${name}`;
      let list = this.shadowRoot.getElementById(listId);
      if (!list) {
        list = document.createElement("datalist");
        list.id = listId;
        this.shadowRoot.appendChild(list);
      }
      const choices = options.options || this._schema.fieldOptions[name] || [];
      list.innerHTML = choices.map((choice) => `<option value="${esc(choice)}"></option>`).join("");
      input.setAttribute("list", listId);
    }

    input.addEventListener("change", () => {
      const text = input.value.trim();
      if (!text) return commit(undefined);
      if (widget === "number") {
        const parsed = Number(text);
        return commit(isNaN(parsed) ? text : parsed);
      }
      commit(text);
    });
    row.appendChild(input);

    if (widget === "icon") {
      // `ha-icon` ist im HA-Frontend global registriert und funktioniert auch im Shadow DOM.
      const preview = document.createElement("ha-icon");
      preview.style.flex = "none";
      input.placeholder = "z. B. mdi:lightbulb";

      // Vorschlagsliste je Feld, damit parallel offene Icon-Felder sich nicht gegenseitig
      // überschreiben. Gefüllt wird sie erst beim Tippen – 6896 <option>-Elemente wären sonst
      // sinnlos im DOM.
      const listId = `icons-${Math.random().toString(36).slice(2)}`;
      const list = document.createElement("datalist");
      list.id = listId;
      this.shadowRoot.appendChild(list);
      input.setAttribute("list", listId);

      const fillSuggestions = () => {
        list.innerHTML = filterIconNames(input.value)
          .map((name) => `<option value="mdi:${esc(name)}"></option>`)
          .join("");
      };
      const refresh = () => {
        const text = input.value.trim();
        const kind = iconKind(text);
        preview.icon = kind === "name" ? text : "";
        // Sonderformen (text:, ha:, <I>…</I>, Jinja) sind keine Icon-Namen – nicht bewerten.
        if (kind === "name" && !iconIsKnown(text)) {
          errorEl.hidden = false;
          errorEl.textContent =
            `Das Backend kennt "${text}" nicht – es rendert dann alert-circle-outline. ` +
            `Der Wert bleibt trotzdem gespeichert.`;
        } else {
          errorEl.hidden = true;
          if (kind === "special") {
            preview.removeAttribute("icon");
          }
        }
      };

      input.addEventListener("input", fillSuggestions);
      input.addEventListener("change", refresh);
      refresh();
      row.appendChild(preview);
    }
    return wrapper;
  }

  /** Vom Nutzer gewählter Modus eines template-fähigen Feldes (überschreibt die Erkennung). */
  _templateOverride(target, name) {
    return this._templateModes.get(target)?.get(name);
  }

  _setTemplateOverride(target, name, mode) {
    if (!this._templateModes.has(target)) this._templateModes.set(target, new Map());
    this._templateModes.get(target).set(name, mode);
  }

  /**
   * Template-Editor mit Live-Vorschau.
   *
   * Die Vorschau geht über HAs eigene Template-API (`POST /api/template`) — dieselbe Engine, die
   * später auch das Backend benutzt (`ha_api.render_template`). Damit sieht man hier echte Werte und
   * echte Jinja-Fehlermeldungen, statt eine Nachbildung.
   */
  _templateEditor(name, value, commit, errorEl) {
    const host = document.createElement("div");
    host.className = "tplbox";

    const suffixField = (this._schema.templateSuffixFields || []).includes(name);
    const area = document.createElement("textarea");
    area.className = "tpl";
    area.rows = 4;
    area.placeholder = "{{ states('sensor.puffer_oben') }} °C";
    // Nicht-Strings (etwa eine RGB-Liste) als Text anbieten, aber nichts davon speichern, solange
    // der Nutzer nichts ändert – der bestehende Wert bleibt bis dahin unangetastet.
    area.value = value === undefined || value === null ? "" : typeof value === "string" ? value : JSON.stringify(value);

    const preview = document.createElement("div");
    preview.className = "tplpreview";
    const swatch = document.createElement("span");
    swatch.className = "tplswatch";
    swatch.hidden = true;
    const previewText = document.createElement("span");
    previewText.className = "tplresult";
    preview.appendChild(swatch);
    preview.appendChild(previewText);

    if (suffixField) {
      const hinweis = document.createElement("div");
      hinweis.className = "desc";
      hinweis.textContent =
        "Das Backend rendert nur bis zum letzten } und hängt den Rest wörtlich an – so entstehen " +
        "Einheiten wie „ °C“. Die Vorschau macht es genauso.";
      host.appendChild(hinweis);
    }

    let timer = null;
    const render = async () => {
      const text = area.value;
      if (!text.trim()) {
        previewText.textContent = "";
        swatch.hidden = true;
        errorEl.hidden = true;
        return;
      }
      const [template, suffix] = suffixField ? splitTemplateSuffix(text) : [text, ""];
      if (!isTemplate(template)) {
        // Kein Jinja drin: dann ist das Ergebnis der Text selbst, kein API-Aufruf nötig.
        this._showTemplateResult(previewText, swatch, errorEl, name, `${template}${suffix}`);
        return;
      }
      previewText.textContent = "…";
      try {
        const rendered = await this._hass.callApi("POST", "template", { template });
        this._showTemplateResult(previewText, swatch, errorEl, name, `${rendered}${suffix}`);
      } catch (err) {
        swatch.hidden = true;
        previewText.textContent = "";
        errorEl.hidden = false;
        errorEl.textContent = `Template-Fehler: ${this._errText(err)}`;
      }
    };

    area.addEventListener("input", () => {
      // Entprellt: bei jedem Tastendruck zu rendern wäre ein API-Aufruf pro Zeichen.
      clearTimeout(timer);
      timer = setTimeout(render, 700);
    });
    area.addEventListener("change", () => {
      clearTimeout(timer);
      const text = area.value;
      commit(text.trim() ? text : undefined);
      render();
    });

    host.appendChild(area);
    host.appendChild(preview);
    render();
    return host;
  }

  /** Zeigt ein Rendering an – bei Farbfeldern zusätzlich als Farbfleck, wenn es RGB ergibt. */
  _showTemplateResult(previewText, swatch, errorEl, name, result) {
    errorEl.hidden = true;
    const text = String(result ?? "");
    previewText.textContent = `→ ${text.length > 300 ? `${text.slice(0, 300)}…` : text}`;
    const rgb = this._schema.fieldHints[name] === "color" ? parseTemplateColor(text) : null;
    if (rgb) {
      swatch.hidden = false;
      swatch.style.background = rgbToHex(rgb);
      swatch.title = rgb.join(", ");
    } else {
      swatch.hidden = true;
    }
  }

  /**
   * Farbwähler für die zwei Formen, die das Backend versteht: eine Farbe ([r,g,b]) oder eine je
   * Zustand ({on, off}). Der Hex-Wähler ist die Bequemlichkeit, das Zahlenfeld daneben bleibt die
   * Wahrheit – NSPanel-Konfigurationen werden oft aus Beispielen als "255, 165, 0" kopiert.
   */
  _colorEditor(value, commit) {
    const host = document.createElement("div");
    host.className = "colorbox";
    const shape = colorShape(value);
    let current = shape === "onoff" ? { ...value } : value;

    const zeile = (rgb, label, onChange) => {
      const wrap = document.createElement("div");
      wrap.className = "colorrow";
      const gesetzt = isRgb(rgb);

      const picker = document.createElement("input");
      picker.type = "color";
      picker.value = rgbToHex(rgb);
      picker.title = label ? `Farbe für "${label}"` : "Farbe wählen";

      const text = document.createElement("input");
      text.type = "text";
      text.className = "rgbtext";
      text.placeholder = "r, g, b";
      text.value = gesetzt ? rgb.join(", ") : "";

      const fehler = document.createElement("div");
      fehler.className = "err";
      fehler.hidden = true;

      const uebernehmen = (rgbNeu, quelle) => {
        picker.value = rgbToHex(rgbNeu);
        if (quelle !== "text") text.value = rgbNeu.join(", ");
        fehler.hidden = true;
        text.classList.remove("invalid");
        onChange(rgbNeu);
      };

      picker.addEventListener("change", () => uebernehmen(hexToRgb(picker.value), "picker"));
      text.addEventListener("change", () => {
        const roh = text.value.trim();
        if (!roh) {
          // Leeres Zahlenfeld heißt "keine Farbe" – konsistent zur Regel im restlichen Editor.
          fehler.hidden = true;
          text.classList.remove("invalid");
          onChange(undefined);
          return;
        }
        const parsed = parseRgbText(roh);
        if (!parsed) {
          // Nicht übernehmen, sonst wäre der alte Wert weg.
          text.classList.add("invalid");
          fehler.hidden = false;
          fehler.textContent = "Erwartet drei Zahlen 0–255, z. B. 255, 165, 0 (Wert unverändert)";
          return;
        }
        uebernehmen(parsed, "text");
      });

      if (label) {
        const tag = document.createElement("span");
        tag.className = "colorlabel";
        tag.textContent = label;
        wrap.appendChild(tag);
      }
      wrap.appendChild(picker);
      wrap.appendChild(text);
      wrap.appendChild(fehler);
      return wrap;
    };

    if (shape === "onoff") {
      ["on", "off"].forEach((state) => {
        host.appendChild(
          zeile(current[state], state, (rgbNeu) => {
            if (rgbNeu === undefined) delete current[state];
            else current[state] = rgbNeu;
            commit(Object.keys(current).length ? current : undefined);
          })
        );
      });
      const hinweis = document.createElement("div");
      hinweis.className = "desc";
      hinweis.textContent = "Je Zustand eine Farbe (on/off) – wie im Backend.";
      host.appendChild(hinweis);
      return host;
    }

    host.appendChild(zeile(isRgb(current) ? current : undefined, "", (rgbNeu) => commit(rgbNeu)));
    return host;
  }

  /** Aktualisiert nur die Kopfzeilen der Entity-Blöcke – ohne die offenen Formulare neu zu bauen. */
  _refreshEntitySummaries() {
    const card = this._selected();
    if (!isPlain(card) || !Array.isArray(card.entities)) return;
    this.shadowRoot.querySelectorAll("details.entity .title").forEach((titleEl, index) => {
      const entity = card.entities[index];
      if (!isPlain(entity)) return;
      titleEl.innerHTML = `${index + 1}. ${esc(entity.entity || "(ohne entity)")}<small>${
        entity.name ? esc(` – ${entity.name}`) : ""
      }</small>`;
    });
  }

  /**
   * Editor für das `extra`-Dict einer Ebene. Sichtbar zu machen, was der Editor *nicht* versteht,
   * ist hier Absicht: der Nutzer soll sehen, dass diese Keys erhalten bleiben.
   */
  _extraEditor(target) {
    const extra = target.extra;
    const count = isPlain(extra) ? Object.keys(extra).length : 0;
    const details = document.createElement("details");
    details.innerHTML = `
      <summary style="cursor:pointer;font-size:13px;color:var(--secondary-text-color,#727272);margin:6px 0">
        Weitere Felder (${count}) – unverändert übernommen
      </summary>`;
    const host = document.createElement("div");
    host.style.paddingTop = "8px";
    details.appendChild(host);
    host.appendChild(
      this._field(target, "extra", {
        // Immer als JSON: hier steht per Definition alles, wofür es kein benanntes Feld gibt.
        forceWidget: "json",
        label: "Unbekannte Keys (JSON)",
        onChange: () => {
          details.querySelector("summary").textContent = `Weitere Felder (${
            isPlain(target.extra) ? Object.keys(target.extra).length : 0
          }) – unverändert übernommen`;
        },
      })
    );
    return details;
  }

  // --- Aktionen ------------------------------------------------------------------------------

  async _save() {
    if (!this._model) return;
    this._setStatus("Speichere…");
    try {
      const result = await this._hass.callApi("POST", "nspanel_ui_config/config", this._model);
      this._findings = result.findings || [];
      this._dirty = false;
      this._setStatus("Gespeichert.", "ok");
    } catch (err) {
      this._setStatus(`Speichern fehlgeschlagen: ${this._errText(err)}`, "error");
    }
    this._renderStatus();
    return !this._dirty;
  }

  async _generate() {
    // `generate` arbeitet serverseitig auf dem *gespeicherten* Modell – ungespeicherte Änderungen
    // würden sonst stillschweigend fehlen. Deshalb vorher speichern.
    if (this._dirty && !(await this._save())) return;
    this._setStatus("Erzeuge YAML…");
    try {
      const result = await this._hass.callApi("POST", "nspanel_ui_config/generate", {});
      this._findings = result.findings || [];
      this._setStatus(...generateStatus(result));
    } catch (err) {
      this._setStatus(`Erzeugen fehlgeschlagen: ${this._errText(err)}`, "error");
    }
    this._renderStatus();
  }

  /**
   * Sicherungen ansehen und zurückspielen.
   *
   * Wichtig für das Verständnis: die Sicherungen gehören zur *Datei*, nicht zum Modell im Editor.
   * Nach dem Zurückspielen steht auf der Platte etwas anderes als im Editor — darauf weist der
   * Dialog hin, statt beides stillschweigend auseinanderlaufen zu lassen.
   */
  async _openBackupDialog() {
    const host = this._$("dialog-host");
    host.innerHTML = `
      <div class="overlay">
        <div class="dialog body">
          <h3>Sicherungen der erzeugten YAML</h3>
          <p class="hint">Vor jedem Überschreiben wird der bisherige Stand hier abgelegt. Beim
            Zurückspielen wird der aktuelle Stand seinerseits gesichert – rückgängig machen bleibt
            also möglich.</p>
          <div id="backup-body"><p class="hint">Wird geladen…</p></div>
          <div class="actions">
            <button id="backup-close">Schließen</button>
          </div>
        </div>
      </div>`;

    const close = () => (host.innerHTML = "");
    host.querySelector("#backup-close").addEventListener("click", close);
    host.querySelector(".overlay").addEventListener("click", (event) => {
      if (event.target.classList.contains("overlay")) close();
    });
    await this._renderBackupList();
  }

  async _renderBackupList() {
    const body = this.shadowRoot.getElementById("backup-body");
    if (!body) return;
    let data;
    try {
      data = await this._hass.callApi("GET", "nspanel_ui_config/backups");
    } catch (err) {
      body.innerHTML = `<p class="status error">Sicherungen nicht lesbar: ${esc(
        this._errText(err)
      )}</p>`;
      return;
    }

    const entries = data.backups || [];
    const kopf = `<p class="hint">Ausgabedatei: <code>${esc(data.path || "–")}</code>${
      data.keep ? ` · aufbewahrt werden ${data.keep}` : " · Sicherungen sind abgeschaltet"
    }</p>`;

    if (!entries.length) {
      body.innerHTML = `${kopf}<p class="empty">Noch keine Sicherungen – sie entstehen, sobald
        eine vorhandene Ausgabedatei überschrieben wird.</p>`;
      return;
    }

    body.innerHTML = `${kopf}<div class="backups">${entries
      .map(
        (entry, index) => `
        <div class="backup-row">
          <span class="backup-when">${esc(backupLabel(entry))}${
          index === 0 ? ' <span class="tag">neueste</span>' : ""
        }</span>
          <span class="backup-size">${esc(formatSize(entry.size))}</span>
          <button data-name="${esc(entry.name)}">Zurückspielen</button>
        </div>`
      )
      .join("")}</div>`;

    body.querySelectorAll("button[data-name]").forEach((button) => {
      button.addEventListener("click", () => this._restoreBackup(button.dataset.name));
    });
  }

  async _restoreBackup(name) {
    if (
      !confirm(
        `Sicherung "${name}" zurückspielen?\n\n` +
          "Die erzeugte YAML wird damit auf diesen Stand zurückgesetzt. Der aktuelle Stand wird " +
          "vorher selbst gesichert.\n\nDas Modell im Editor bleibt unverändert – wer es angleichen " +
          "will, importiert die Datei anschließend."
      )
    ) {
      return;
    }
    this._setStatus("Spiele Sicherung zurück…");
    try {
      const result = await this._hass.callApi("POST", "nspanel_ui_config/backups/restore", { name });
      const ersetzt = result.backup_of_previous?.name;
      this._setStatus(
        `Sicherung ${name} zurückgespielt nach ${result.path}` +
          (ersetzt ? ` (bisheriger Stand als ${ersetzt} gesichert)` : "") +
          ". AppDaemon wurde dabei nicht neu geladen.",
        "ok"
      );
      await this._renderBackupList();
    } catch (err) {
      this._setStatus(`Zurückspielen fehlgeschlagen: ${this._errText(err)}`, "error");
    }
    this._renderStatus();
  }

  _openImportDialog() {
    const host = this._$("dialog-host");
    host.innerHTML = `
      <div class="overlay">
        <div class="dialog body">
          <h3>Bestehende Konfiguration importieren</h3>
          <p class="hint">Liest den <code>config:</code>-Block einer AppDaemon-<code>apps.yaml</code>
            (oder einer bereits ausgelagerten Include-Datei) ein. Der Import ersetzt das aktuell
            geöffnete Modell, speichert aber noch nichts.</p>
          <div class="field">
            <label>Pfad auf dem HA-Server</label>
            <div class="desc">Muss in <code>allowlist_external_dirs</code> freigegeben sein.
              Leer lassen, um den beim Einrichten hinterlegten Pfad zu verwenden.</div>
            <div class="row"><input type="text" id="imp-path" placeholder="/config/appdaemon/apps/apps.yaml"></div>
          </div>
          <div class="field">
            <label>…oder YAML direkt einfügen</label>
            <div class="row"><textarea id="imp-text" rows="8" placeholder="nspanel-1:\n  module: ...\n  config:\n    ..."></textarea></div>
          </div>
          <div class="field" id="imp-app-field" hidden>
            <label>App auswählen</label>
            <div class="desc">Die Datei enthält mehrere Apps mit config-Block.</div>
            <div class="row"><select id="imp-app"></select></div>
          </div>
          <div class="status" id="imp-status"></div>
          <div class="actions">
            <button id="imp-cancel">Abbrechen</button>
            <button class="primary" id="imp-run">Einlesen</button>
          </div>
        </div>
      </div>`;

    const close = () => (host.innerHTML = "");
    host.querySelector("#imp-cancel").addEventListener("click", close);
    host.querySelector(".overlay").addEventListener("click", (event) => {
      if (event.target.classList.contains("overlay")) close();
    });
    host.querySelector("#imp-run").addEventListener("click", async () => {
      const statusEl = host.querySelector("#imp-status");
      const text = host.querySelector("#imp-text").value.trim();
      const path = host.querySelector("#imp-path").value.trim();
      const appSelect = host.querySelector("#imp-app");
      const appField = host.querySelector("#imp-app-field");

      const payload = {};
      if (text) payload.text = text;
      else if (path) payload.path = path;
      if (!appField.hidden && appSelect.value) payload.app_name = appSelect.value;

      statusEl.textContent = "Lese…";
      statusEl.className = "status";
      try {
        const result = await this._hass.callApi("POST", "nspanel_ui_config/import", payload);
        // Mehrere Apps und noch keine ausgewählt: erst auswählen lassen, dann erneut einlesen.
        if ((result.apps || []).length > 1 && !payload.app_name) {
          appSelect.innerHTML = result.apps
            .map((app) => `<option value="${esc(app)}">${esc(app)}</option>`)
            .join("");
          appField.hidden = false;
          statusEl.textContent = `${result.apps.length} Apps gefunden – bitte auswählen und erneut einlesen.`;
          return;
        }
        this._model = result.model;
        this._findings = result.findings || [];
        this._selection = { kind: "global", index: 0 };
        this._dirty = true;
        close();
        this._renderAll();
        const cardCount = (this._model.cards || []).length;
        this._setStatus(
          `Importiert: ${cardCount} Karte(n). Noch nicht gespeichert – „Speichern“ übernimmt den Stand.`,
          "ok"
        );
      } catch (err) {
        statusEl.textContent = `Import fehlgeschlagen: ${this._errText(err)}`;
        statusEl.className = "status error";
      }
    });
  }
}

// Das Modul wird mit Cache-Busting-Query geladen; ein zweites define() würde sonst werfen.
// Die Abfrage auf `customElements` erlaubt es zugleich, das Modul außerhalb des Browsers zu
// importieren – siehe tests/panel.test.mjs, das die reinen Hilfsfunktionen prüft.
if (typeof customElements !== "undefined" && !customElements.get(ELEMENT_NAME)) {
  customElements.define(ELEMENT_NAME, NsPanelUiConfigPanel);
}

export {
  NsPanelUiConfigPanel,
  backupLabel,
  capacityInfo,
  formatSize,
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
  isTemplate,
  splitTemplateSuffix,
  parseTemplateColor,
  templateFieldMode,
  entityKind,
  previewColor,
  previewContent,
  iconFromRendered,
  iconNameFromChar,
  liveContent,
  joinTemplates,
  splitTemplateResult,
};
