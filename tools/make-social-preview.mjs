// Erzeugt das Social-Preview-Bild des Repos (1280×640) aus der Brand-Quelle.
//
// **Warum als Werkzeug und nicht von Hand:** GitHub zeigt dieses Bild in jeder Vorschau eines
// Links auf das Repo, verlangt aber genau 1280×640 (2:1) und höchstens 1 MB. Die Quelle
// (`docs/brand-source.jpg`, 945×797) hat ein ganz anderes Seitenverhältnis; von Hand skaliert
// landet man schnell bei verzerrtem Bild oder einer 3-MB-Datei. Mit diesem Skript ist das Ergebnis
// reproduzierbar — und nach einer neuen Quelle in einem Aufruf wieder da.
//
// Das Motiv wird **nicht beschnitten**, sondern proportional eingepasst und auf schwarzem Grund
// zentriert: der Rahmen der Quelle ist ohnehin fast schwarz, der Übergang fällt deshalb nicht auf.
// Beschneiden würde den Schriftzug am unteren Rand kosten.
//
// Voraussetzung: `npm install jpeg-js`
// Aufruf: node tools/make-social-preview.mjs docs/brand-source.jpg docs/social-preview.jpg

import fs from "node:fs";
import jpeg from "jpeg-js";

const [, , quellPfad, zielPfad] = process.argv;
if (!quellPfad || !zielPfad) {
  console.error("Aufruf: node tools/make-social-preview.mjs <quelle.jpg> <ziel.jpg>");
  process.exit(2);
}

const BREITE = 1280;
const HOEHE = 640;
const RAND = 24; // damit das Motiv oben/unten nicht an der Kante klebt
const HINTERGRUND = [10, 11, 13]; // dasselbe Fast-Schwarz wie der Rahmen der Quelle

const quelle = jpeg.decode(fs.readFileSync(quellPfad), { useTArray: true });

/**
 * Skaliert mit einem Box-Filter: jeder Zielpixel ist der Mittelwert der Quellpixel, die auf ihn
 * fallen. Beim Verkleinern ist das dem naiven „nächster Nachbar" deutlich überlegen – dort flimmern
 * feine Strukturen wie die Ziffern auf dem Display.
 */
function skaliere(bild, zielBreite, zielHoehe) {
  const ziel = Buffer.alloc(zielBreite * zielHoehe * 4);
  const xFaktor = bild.width / zielBreite;
  const yFaktor = bild.height / zielHoehe;
  for (let y = 0; y < zielHoehe; y++) {
    const y0 = Math.floor(y * yFaktor);
    const y1 = Math.max(y0 + 1, Math.floor((y + 1) * yFaktor));
    for (let x = 0; x < zielBreite; x++) {
      const x0 = Math.floor(x * xFaktor);
      const x1 = Math.max(x0 + 1, Math.floor((x + 1) * xFaktor));
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

const skalierung = Math.min(BREITE / quelle.width, (HOEHE - 2 * RAND) / quelle.height);
const motivBreite = Math.round(quelle.width * skalierung);
const motivHoehe = Math.round(quelle.height * skalierung);
const motiv = skaliere(quelle, motivBreite, motivHoehe);

const leinwand = Buffer.alloc(BREITE * HOEHE * 4);
for (let i = 0; i < BREITE * HOEHE; i++) {
  leinwand[i * 4] = HINTERGRUND[0];
  leinwand[i * 4 + 1] = HINTERGRUND[1];
  leinwand[i * 4 + 2] = HINTERGRUND[2];
  leinwand[i * 4 + 3] = 255;
}

const offsetX = Math.round((BREITE - motivBreite) / 2);
const offsetY = Math.round((HOEHE - motivHoehe) / 2);
for (let y = 0; y < motivHoehe; y++) {
  for (let x = 0; x < motivBreite; x++) {
    const von = (y * motivBreite + x) * 4;
    const nach = ((y + offsetY) * BREITE + (x + offsetX)) * 4;
    leinwand[nach] = motiv.data[von];
    leinwand[nach + 1] = motiv.data[von + 1];
    leinwand[nach + 2] = motiv.data[von + 2];
    leinwand[nach + 3] = 255;
  }
}

// JPEG statt PNG: ein Foto mit Verläufen wird als PNG ein Vielfaches groß, ohne dass man den
// Unterschied sähe. Qualität 88 liegt sichtbar über dem, was GitHub daraus wieder skaliert.
const kodiert = jpeg.encode({ data: leinwand, width: BREITE, height: HOEHE }, 88);
fs.writeFileSync(zielPfad, kodiert.data);

const kb = (kodiert.data.length / 1024).toFixed(1);
console.log(
  `${zielPfad}: ${BREITE}×${HOEHE}, Motiv ${motivBreite}×${motivHoehe} zentriert, ${kb} kB`
);
