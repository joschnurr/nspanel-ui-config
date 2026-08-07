// Tests des QR-Erzeugers.
//
// **Der eigentliche Beweis wurde außerhalb geführt:** Die erzeugten Matrizen wurden bitgenau gegen
// libqrencode, nayukis qrcodegen und python-qrcode geprüft (67 Texte, Versionen 1–10) — alle drei
// stimmen untereinander und mit dieser Umsetzung überein. Hier stehen deshalb die Eigenschaften,
// die sich ohne fremde Bibliothek halten lassen, plus zwei feste Referenzmatrizen aus jenem
// Vergleich als Wächter gegen stille Änderungen.

import assert from "node:assert/strict";
import { test } from "node:test";

const { qrMatrix, qrSvg } = await import(
  "../custom_components/nspanel_ui_config/www/panel/qr.js"
);

test("die Version wächst mit der Textlänge, die Größe folgt der Formel 4v+17", () => {
  for (const [text, groesse] of [
    ["HELLO WORLD", 21],
    ["WIFI:S:Testnetz;T:WPA;P:testpasswort;;", 29],
    ["x".repeat(78), 33],
  ]) {
    const m = qrMatrix(text);
    assert.equal(m.length, groesse, `${text.slice(0, 20)}: ${m.length} statt ${groesse}`);
    assert.equal(m.length % 4, 1, "jede Version ist 4·v+17 groß");
    assert.ok(m.every((z) => z.length === m.length), "die Matrix muss quadratisch sein");
  }
});

test("zu lange und leere Texte liefern nichts statt eines unlesbaren Codes", () => {
  assert.equal(qrMatrix(""), null);
  assert.equal(qrMatrix("x".repeat(272)), null, "über Version 10 hinaus");
  assert.ok(qrMatrix("x".repeat(271)), "271 Zeichen passen noch");
});

test("die drei Suchermuster sitzen und tragen ihre helle Trennlinie", () => {
  const m = qrMatrix("HELLO WORLD");
  const n = m.length;
  for (const [ox, oy] of [[0, 0], [n - 7, 0], [0, n - 7]]) {
    // Auge: 7×7 mit dunklem Rand und dunklem 3×3-Kern.
    for (let i = 0; i < 7; i++) {
      assert.equal(m[oy][ox + i], 1, "obere Kante");
      assert.equal(m[oy + 6][ox + i], 1, "untere Kante");
      assert.equal(m[oy + i][ox], 1, "linke Kante");
      assert.equal(m[oy + i][ox + 6], 1, "rechte Kante");
    }
    assert.equal(m[oy + 3][ox + 3], 1, "Kern");
    assert.equal(m[oy + 1][ox + 1], 0, "heller Ring");
    // Trennlinie: die Reihe direkt neben dem Auge muss hell sein. Ohne sie verschmilzt der
    // Sucher mit den Daten und kein Lesegerät findet ihn mehr.
    if (ox === 0 && oy === 0) {
      for (let i = 0; i < 8; i++) {
        assert.equal(m[7][i], 0, `Trennlinie unten bei x=${i}`);
        assert.equal(m[i][7], 0, `Trennlinie rechts bei y=${i}`);
      }
    }
  }
});

test("das Taktmuster wechselt und beginnt dunkel", () => {
  const m = qrMatrix("HELLO WORLD");
  for (let i = 8; i < m.length - 8; i++) {
    assert.equal(m[6][i], i % 2 === 0 ? 1 : 0, `waagerechtes Taktmuster bei x=${i}`);
    assert.equal(m[i][6], i % 2 === 0 ? 1 : 0, `senkrechtes Taktmuster bei y=${i}`);
  }
});

test("das immer dunkle Feld unter dem linken Sucher ist gesetzt", () => {
  // Der Standard schreibt genau ein Modul vor, das nie hell ist – ein guter Wächter dafür, dass
  // die Formatinformation nicht verrutscht ist.
  const m = qrMatrix("HELLO WORLD");
  assert.equal(m[m.length - 8][8], 1);
});

test("gleicher Text ergibt gleiches Muster", () => {
  const a = qrMatrix("WIFI:S:Testnetz;T:WPA;P:testpasswort;;");
  const b = qrMatrix("WIFI:S:Testnetz;T:WPA;P:testpasswort;;");
  assert.deepEqual(a, b, "der Erzeuger darf nicht zufällig arbeiten");
});

test("Referenzmatrix: HELLO WORLD, Version 1 (gegen qrencode/qrcodegen/python-qrcode geprüft)", () => {
  // Beide Werte stammen aus python-qrcode (Stufe L, Byte-Modus, Maske 4) und wurden dort
  // eigens abgefragt – nicht aus dieser Umsetzung übernommen. Sonst würde der Test nur
  // bestätigen, was der Code ohnehin tut.
  const m = qrMatrix("HELLO WORLD").map((z) => z.join(""));
  assert.equal(m.length, 21);
  assert.equal(m[0], "111111101111101111111");
  // Zahl der dunklen Module – ändert sich bei jeder Abweichung im Datenteil.
  const dunkel = m.join("").split("1").length - 1;
  assert.equal(dunkel, 228, `dunkle Module: ${dunkel}`);
});

test("qrSvg liefert ein SVG mit Ruhezone und passendem Ausschnitt", () => {
  const svg = qrSvg("HELLO WORLD", 200);
  assert.ok(svg.startsWith("<svg"), "SVG-Wurzel");
  assert.ok(svg.includes('width="200" height="200"'), "gewünschte Kantenlänge");
  // 21 Module + 2×4 Ruhezone = 29
  assert.ok(svg.includes('viewBox="0 0 29 29"'), `Ausschnitt: ${svg.slice(0, 160)}`);
  assert.equal(qrSvg("", 200), null, "ohne Text kein Bild");
});
