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

// Die Namensliste des Backend-Icon-Mappings (erzeugt von tools/extract_icon_names.py). Sie steckt in
// einem eigenen Modul, damit dieses hier lesbar bleibt – 6896 Namen sind ~110 kB.
import { ICON_NAMES } from "./icon-names.js";

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
  if (reload.ok === false) {
    return [
      `YAML geschrieben nach ${path}, aber AppDaemon nicht neu geladen: ${reload.detail}`,
      "error",
    ];
  }
  const stillerModus = !reload.mode || reload.mode === "none" || reload.mode === "skipped";
  if (stillerModus) return [`YAML geschrieben nach ${path}`, "ok"];
  return [`YAML geschrieben nach ${path} – ${reload.detail}`, "ok"];
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
      <fieldset><legend>Panel</legend><div id="global-known"></div></fieldset>
      ${rest.length ? `<fieldset><legend>Weitere Felder aus der Quelldatei</legend><div id="global-rest"></div></fieldset>` : ""}
    `;

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
      hint: "Die Anzeige im Ruhezustand. `entities` sind hier die Status-/Wetterzeilen.",
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

    main.innerHTML = `
      <h2>${esc(title)}</h2>
      <p class="hint">${esc(options.hint || "")}</p>
      <fieldset><legend>Karte</legend><div id="card-fields"></div>
        ${options.removable ? `<button class="danger" id="remove-card">Entfernen</button>` : ""}
      </fieldset>
      ${isFlat ? `<fieldset><legend>Entity der Karte</legend><div id="flat-entity"></div></fieldset>` : ""}
      ${showEntityList ? `<fieldset><legend>Entity-Liste</legend><div id="entity-list-host"></div>
        <button class="primary" id="add-entity">+ Entity</button></fieldset>` : ""}
      <div id="extra-host"></div>
    `;

    const fieldHost = main.querySelector("#card-fields");
    cardFields.forEach((name) => {
      const opts = name === "type" ? { options: options.typeOptions, onChange: () => this._retypeCard() } : {};
      fieldHost.appendChild(this._field(card, name, opts));
    });

    if (options.removable) {
      main.querySelector("#remove-card").addEventListener("click", options.onRemove);
    }

    if (isFlat) {
      const flatHost = main.querySelector("#flat-entity");
      schema.entityFields.forEach((name) => flatHost.appendChild(this._field(card, name)));
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
    host.innerHTML = "";
    entities.forEach((entity, index) => {
      const details = document.createElement("details");
      details.className = "entity";
      const label = isPlain(entity) ? entity.entity || "(ohne entity)" : String(entity);
      const name = isPlain(entity) && entity.name ? ` – ${entity.name}` : "";
      details.innerHTML = `
        <summary>
          <span class="caret">▶</span>
          <span class="title">${esc(index + 1)}. ${esc(label)}<small>${esc(name)}</small></span>
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
          inner.appendChild(this._field(entity, fieldName))
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

  /**
   * Baut ein Eingabefeld für `target[name]`. Schreibt bei `change` direkt ins Modell zurück –
   * nicht bei jedem Tastendruck, damit das Formular während der Eingabe nicht neu aufgebaut wird.
   */
  _field(target, name, options = {}) {
    const value = target[name];
    const hint = options.forceWidget || this._schema.fieldHints[name] || "string";
    const widget = options.forceWidget || widgetFor(hint, value);
    const description = this._schema.fieldDescriptions[name];
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
};
