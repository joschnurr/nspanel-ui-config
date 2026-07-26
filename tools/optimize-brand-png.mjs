// Verkleinert die Brand-Icons.
//
// **Warum:** die Bilder in `brand/` landen in jeder Installation, und das brands-Repo von Home
// Assistant achtet ausdrücklich auf Dateigröße. Direkt aus einem Foto exportiert waren sie mit
// 83 kB (256×256) und 285 kB (512×512) rund fünfzehnmal so groß wie üblich — zum Vergleich liefert
// HAs Brands-Proxy für `hue` 5,8 kB.
//
// **Der Hebel:** RGBA-Bild auf <=256 Farben quantisieren (Median-Cut) und als *indiziertes* PNG
// schreiben (colorType 3 + tRNS für die Alphawerte). pngjs kann nur Truecolor schreiben, deshalb
// bauen wir die Chunks von Hand. Ergebnis bei 128 Farben: ~83 % kleiner, ohne sichtbaren
// Unterschied. Bei 64 Farben zeigt der dunkle Rahmen des Icons Banding — 128 ist die Grenze.
//
// Vollständig transparente Pixel bekommen einen reservierten Paletteneintrag, damit sie die
// Farbwahl der sichtbaren Bildteile nicht verfälschen (bei einem Icon mit Rand sind sie die
// Mehrheit).
//
// Voraussetzung: `npm install pngjs`
// Aufruf: node tools/optimize-brand-png.mjs <quelle.png> <ziel.png> [maxFarben=256]

import fs from "node:fs";
import zlib from "node:zlib";
import { PNG } from "pngjs";

const [, , quellPfad, zielPfad, maxFarbenArg] = process.argv;
const MAX_FARBEN = Number(maxFarbenArg || 256);

// --- CRC32 (PNG-Chunks) -----------------------------------------------------------------------
const CRC_TABELLE = (() => {
  const t = new Int32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c;
  }
  return t;
})();

function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = CRC_TABELLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function chunk(typ, daten) {
  const laenge = Buffer.alloc(4);
  laenge.writeUInt32BE(daten.length);
  const typBuf = Buffer.from(typ, "ascii");
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([typBuf, daten])));
  return Buffer.concat([laenge, typBuf, daten, crc]);
}

// --- Median-Cut -------------------------------------------------------------------------------
// Vollständig transparente Pixel kommen in einen eigenen Eimer: sie sollen nicht die Farbwahl
// der sichtbaren Bildteile verfälschen, und sie sind bei einem Icon mit Rand die Mehrheit.

function sammleFarben(daten) {
  const zaehler = new Map();
  for (let i = 0; i < daten.length; i += 4) {
    const a = daten[i + 3];
    // Unsichtbares auf einen einzigen Schlüssel normieren – RGB darunter ist bedeutungslos.
    const key = a === 0 ? "T" : `${daten[i]},${daten[i + 1]},${daten[i + 2]},${a}`;
    zaehler.set(key, (zaehler.get(key) || 0) + 1);
  }
  return zaehler;
}

function medianCut(farben, maxFarben) {
  // farben: [{r,g,b,a,n}]
  let boxen = [farben];
  while (boxen.length < maxFarben) {
    // Box mit der größten Ausdehnung (gewichtet mit der Pixelzahl) teilen.
    let bestIdx = -1;
    let bestSpanne = 0;
    let bestAchse = "r";
    boxen.forEach((box, idx) => {
      if (box.length < 2) return;
      for (const achse of ["r", "g", "b", "a"]) {
        let min = 255;
        let max = 0;
        for (const f of box) {
          if (f[achse] < min) min = f[achse];
          if (f[achse] > max) max = f[achse];
        }
        const spanne = max - min;
        if (spanne > bestSpanne) {
          bestSpanne = spanne;
          bestIdx = idx;
          bestAchse = achse;
        }
      }
    });
    if (bestIdx < 0 || bestSpanne === 0) break;

    const box = boxen[bestIdx];
    box.sort((x, y) => x[bestAchse] - y[bestAchse]);
    // An der Pixel-Median-Stelle teilen, nicht in der Mitte der Liste: häufige Farben zählen mehr.
    const gesamt = box.reduce((s, f) => s + f.n, 0);
    let summe = 0;
    let teil = 1;
    for (let i = 0; i < box.length - 1; i++) {
      summe += box[i].n;
      if (summe >= gesamt / 2) {
        teil = i + 1;
        break;
      }
    }
    boxen.splice(bestIdx, 1, box.slice(0, teil), box.slice(teil));
  }

  return boxen.map((box) => {
    let r = 0;
    let g = 0;
    let b = 0;
    let a = 0;
    let n = 0;
    for (const f of box) {
      r += f.r * f.n;
      g += f.g * f.n;
      b += f.b * f.n;
      a += f.a * f.n;
      n += f.n;
    }
    return { r: Math.round(r / n), g: Math.round(g / n), b: Math.round(b / n), a: Math.round(a / n) };
  });
}

// --- Hauptlauf --------------------------------------------------------------------------------

const png = PNG.sync.read(fs.readFileSync(quellPfad));
const { width, height, data } = png;

const zaehler = sammleFarben(data);
const hatTransparenz = zaehler.has("T");
const sichtbare = [];
for (const [key, n] of zaehler) {
  if (key === "T") continue;
  const [r, g, b, a] = key.split(",").map(Number);
  sichtbare.push({ r, g, b, a, n });
}

// Ein Platz bleibt für "vollständig transparent" reserviert.
const budget = hatTransparenz ? MAX_FARBEN - 1 : MAX_FARBEN;
const palette = sichtbare.length <= budget
  ? sichtbare.map(({ r, g, b, a }) => ({ r, g, b, a }))
  : medianCut(sichtbare, budget);

if (hatTransparenz) palette.unshift({ r: 0, g: 0, b: 0, a: 0 });

// --- Pixel auf Paletten-Indizes abbilden ------------------------------------------------------
const cache = new Map();
function naechsterIndex(r, g, b, a) {
  if (a === 0) return 0; // reservierter Transparenz-Eintrag (nur wenn hatTransparenz)
  const key = (r << 24) | (g << 16) | (b << 8) | a;
  const treffer = cache.get(key);
  if (treffer !== undefined) return treffer;
  let best = 0;
  let bestAbstand = Infinity;
  for (let i = 0; i < palette.length; i++) {
    const p = palette[i];
    // Alpha stärker gewichten: ein Farbfehler fällt weniger auf als ein Transparenzfehler.
    const dr = p.r - r;
    const dg = p.g - g;
    const db = p.b - b;
    const da = (p.a - a) * 2;
    const abstand = dr * dr + dg * dg + db * db + da * da;
    if (abstand < bestAbstand) {
      bestAbstand = abstand;
      best = i;
    }
  }
  cache.set(key, best);
  return best;
}

// Scanlines mit Filter-Byte 0 (None) – bei indizierten Bildern bringt Filtern kaum etwas.
const roh = Buffer.alloc(height * (width + 1));
let pos = 0;
for (let y = 0; y < height; y++) {
  roh[pos++] = 0;
  for (let x = 0; x < width; x++) {
    const i = (y * width + x) * 4;
    roh[pos++] = naechsterIndex(data[i], data[i + 1], data[i + 2], data[i + 3]);
  }
}

// --- Chunks bauen -----------------------------------------------------------------------------
const ihdr = Buffer.alloc(13);
ihdr.writeUInt32BE(width, 0);
ihdr.writeUInt32BE(height, 4);
ihdr[8] = 8; // bit depth
ihdr[9] = 3; // color type: indiziert
ihdr[10] = 0;
ihdr[11] = 0;
ihdr[12] = 0;

const plte = Buffer.alloc(palette.length * 3);
palette.forEach((p, i) => {
  plte[i * 3] = p.r;
  plte[i * 3 + 1] = p.g;
  plte[i * 3 + 2] = p.b;
});

// tRNS darf kürzer als die Palette sein – alles dahinter gilt als undurchsichtig. Wir kürzen
// bis zum letzten Eintrag mit a < 255, das spart Bytes.
let letzterTransparenter = -1;
palette.forEach((p, i) => {
  if (p.a < 255) letzterTransparenter = i;
});
const trns =
  letzterTransparenter >= 0
    ? Buffer.from(palette.slice(0, letzterTransparenter + 1).map((p) => p.a))
    : null;

const idat = zlib.deflateSync(roh, { level: 9, memLevel: 9, strategy: zlib.constants.Z_DEFAULT_STRATEGY });

const teile = [
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
  chunk("IHDR", ihdr),
  chunk("PLTE", plte),
];
if (trns) teile.push(chunk("tRNS", trns));
teile.push(chunk("IDAT", idat), chunk("IEND", Buffer.alloc(0)));

const ausgabe = Buffer.concat(teile);
fs.writeFileSync(zielPfad, ausgabe);

const vorher = fs.statSync(quellPfad).size;
console.log(
  `${quellPfad.split("/").pop()}: ${(vorher / 1024).toFixed(0)} kB -> ` +
    `${(ausgabe.length / 1024).toFixed(1)} kB  (${palette.length} Farben, ` +
    `${(100 - (ausgabe.length / vorher) * 100).toFixed(0)} % kleiner)`
);
