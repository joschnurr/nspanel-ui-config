// Erzeugt die Brand-Bilder aus der Quelle — für die Integration *und* für das brands-Repo.
//
// **Warum es dieses Werkzeug gibt:** Home Assistant und das
// [brands-Repo](https://github.com/home-assistant/brands) stellen unterschiedliche Anforderungen,
// und von Hand trifft man sie nicht zuverlässig:
//
//   icon.png     256×256, quadratisch
//   icon@2x.png  512×512, quadratisch
//   logo.png     kürzeste Seite 128–256
//   logo@2x.png  kürzeste Seite 256–512
//
// Dazu die Regel, an der der erste Anlauf gescheitert wäre: **„The image should be trimmed, so it
// contains the minimum amount of empty space on the edges."** Die früheren Icons waren oben und
// unten transparent aufgefüllt, damit vom nicht-quadratischen Foto nichts verlorengeht — genau das
// verlangt das brands-Repo nicht. Die Icons entstehen deshalb als **mittiger quadratischer
// Ausschnitt**: beschnitten wird der seitliche Geräterahmen, nicht der Inhalt. Das Logo behält das
// volle Bild samt Schriftzug, es darf rechteckig sein.
//
// Die Größenoptimierung macht anschließend `optimize-brand-png.mjs` (Median-Cut auf eine Palette).
// Aufgerufen wird es als Kindprozess, damit dieselbe Umsetzung für beide Wege gilt.
//
// Voraussetzung: `npm install jpeg-js pngjs`
// Aufruf: node tools/make-brand-images.mjs docs/brand-source.jpg custom_components/nspanel_ui_config/brand

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import jpeg from "jpeg-js";
import { PNG } from "pngjs";

const HIER = path.dirname(fileURLToPath(import.meta.url));
const [, , quellPfad, zielOrdner] = process.argv;
if (!quellPfad || !zielOrdner) {
  console.error("Aufruf: node tools/make-brand-images.mjs <quelle.jpg> <zielordner>");
  process.exit(2);
}

// Farbtiefe der Palette. 128 ist die Grenze, ab der der dunkle Geräterahmen sichtbar bandet
// (nachgeprüft, siehe optimize-brand-png.mjs).
const MAX_FARBEN = 128;

const quelle = jpeg.decode(fs.readFileSync(quellPfad), { useTArray: true });

/** Box-Filter: jeder Zielpixel ist der Mittelwert der Quellpixel, die auf ihn fallen. */
function skaliere(bild, aus, zielBreite, zielHoehe) {
  const ziel = Buffer.alloc(zielBreite * zielHoehe * 4);
  const xFaktor = aus.w / zielBreite;
  const yFaktor = aus.h / zielHoehe;
  for (let y = 0; y < zielHoehe; y++) {
    const y0 = aus.y + Math.floor(y * yFaktor);
    const y1 = Math.max(y0 + 1, aus.y + Math.floor((y + 1) * yFaktor));
    for (let x = 0; x < zielBreite; x++) {
      const x0 = aus.x + Math.floor(x * xFaktor);
      const x1 = Math.max(x0 + 1, aus.x + Math.floor((x + 1) * xFaktor));
      let r = 0;
      let g = 0;
      let b = 0;
      let n = 0;
      for (let sy = y0; sy < y1 && sy < bild.height; sy++) {
        for (let sx = x0; sx < x1 && sx < bild.width; sx++) {
          const p = (sy * bild.width + sx) * 4;
          r += bild.data[p];
          g += bild.data[p + 1];
          b += bild.data[p + 2];
          n++;
        }
      }
      const p = (y * zielBreite + x) * 4;
      ziel[p] = Math.round(r / n);
      ziel[p + 1] = Math.round(g / n);
      ziel[p + 2] = Math.round(b / n);
      ziel[p + 3] = 255;
    }
  }
  return { width: zielBreite, height: zielHoehe, data: ziel };
}

function schreibePng(bild, pfad) {
  const png = new PNG({ width: bild.width, height: bild.height });
  bild.data.copy(png.data);
  fs.writeFileSync(pfad, PNG.sync.write(png));
}

/** Mittiger quadratischer Ausschnitt — beschnitten wird der Rahmen, nicht das Motiv. */
const kante = Math.min(quelle.width, quelle.height);
const quadrat = {
  x: Math.round((quelle.width - kante) / 2),
  y: Math.round((quelle.height - kante) / 2),
  w: kante,
  h: kante,
};
const ganz = { x: 0, y: 0, w: quelle.width, h: quelle.height };

// Logo: kürzeste Seite auf das Maximum des jeweiligen Bereichs, Seitenverhältnis bleibt.
const logoSkala = (kurz) => {
  const faktor = kurz / Math.min(quelle.width, quelle.height);
  return [Math.round(quelle.width * faktor), Math.round(quelle.height * faktor)];
};

const bilder = [
  { name: "icon.png", aus: quadrat, groesse: [256, 256] },
  { name: "icon@2x.png", aus: quadrat, groesse: [512, 512] },
  { name: "logo.png", aus: ganz, groesse: logoSkala(256) },
  { name: "logo@2x.png", aus: ganz, groesse: logoSkala(512) },
];

fs.mkdirSync(zielOrdner, { recursive: true });
for (const { name, aus, groesse } of bilder) {
  const [breite, hoehe] = groesse;
  const roh = path.join(zielOrdner, `.${name}.roh.png`);
  const ziel = path.join(zielOrdner, name);
  schreibePng(skaliere(quelle, aus, breite, hoehe), roh);
  execFileSync(
    process.execPath,
    [path.join(HIER, "optimize-brand-png.mjs"), roh, ziel, String(MAX_FARBEN)],
    { stdio: "pipe" }
  );
  fs.unlinkSync(roh);
  const kb = (fs.statSync(ziel).size / 1024).toFixed(1);
  console.log(`${name}: ${breite}×${hoehe}, ${kb} kB`);
}
