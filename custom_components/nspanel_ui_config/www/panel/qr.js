// Ein QR-Code-Erzeuger für die Vorschau von `cardQR`.
//
// **Warum selbst gebaut und nicht `ha-qr-code` benutzt:** Das Element gibt es im HA-Frontend, es
// liegt dort aber in einem nachgeladenen Bündel (`63767.…js`) und ist nur definiert, wenn eine
// HA-Ansicht es zuvor gebraucht hat. Ein Custom Panel kann sich darauf nicht verlassen — und der
// Chunk-Name ändert sich mit jeder HA-Fassung, ist also auch nicht direkt ladbar. Ein eigener
// Erzeuger ist dafür klein, prüfbar ohne Browser und unabhängig von HA-Interna.
//
// **Umfang mit Absicht begrenzt:** nur der Byte-Modus und die Versionen 1–10 (bis 271 Zeichen bei
// Fehlerkorrektur L). Auf dieser Karte steht typischerweise ein WLAN-Zugang
// (`WIFI:S:…;T:WPA;P:…;;`) mit 30–70 Zeichen; alles darüber ist am 200×200-Feld des Displays
// ohnehin nicht mehr ablesbar. Reicht der Platz nicht, meldet `qrMatrix` das mit `null`, statt
// einen unlesbaren Code zu zeichnen.
//
// Das Display zeichnet seinen Code mit dem Nextion-Befehl
// `qrcode <x>,<y>,200,65535,defaultBcoColor,-1,8,<text>` — weiß auf dem Kartenhintergrund, mit
// Fehlerkorrekturstufe 8 %, also **L**. Genau diese Stufe wird hier voreingestellt, damit die
// Vorschau denselben Code zeigt wie das Gerät (Stufe und Version bestimmen das Muster mit).

/** Anzahl der Datenbits, die eine Version mit Fehlerkorrektur L fasst (Byte-Modus, netto). */
const KAPAZITAET_L = [0, 17, 32, 53, 78, 106, 134, 154, 192, 230, 271];

/** Fehlerkorrektur-Codewörter pro Block und Blockaufteilung je Version (nur Stufe L). */
const EC_L = {
  1: { ec: 7, gruppen: [[1, 19]] },
  2: { ec: 10, gruppen: [[1, 34]] },
  3: { ec: 15, gruppen: [[1, 55]] },
  4: { ec: 20, gruppen: [[1, 80]] },
  5: { ec: 26, gruppen: [[1, 108]] },
  6: { ec: 18, gruppen: [[2, 68]] },
  7: { ec: 20, gruppen: [[2, 78]] },
  8: { ec: 24, gruppen: [[2, 97]] },
  9: { ec: 30, gruppen: [[2, 116]] },
  10: { ec: 18, gruppen: [[2, 68], [2, 69]] },
};

/** Position der Ausrichtungsmuster je Version (ab Version 2). */
const AUSRICHTUNG = {
  1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30],
  6: [6, 34], 7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50],
};

// --- Rechnen im Galois-Feld GF(256) -------------------------------------------------------------
// Die Fehlerkorrektur multipliziert Polynome über GF(256) mit dem Generator 0x11D. Mit Log- und
// Exponententabelle wird aus jeder Multiplikation eine Addition.
const EXP = new Uint8Array(512);
const LOG = new Uint8Array(256);
(() => {
  let x = 1;
  for (let i = 0; i < 255; i++) {
    EXP[i] = x;
    LOG[x] = i;
    x <<= 1;
    if (x & 0x100) x ^= 0x11d;
  }
  for (let i = 255; i < 512; i++) EXP[i] = EXP[i - 255];
})();

const mul = (a, b) => (a === 0 || b === 0 ? 0 : EXP[LOG[a] + LOG[b]]);

/**
 * Generatorpolynom für `grad` Fehlerkorrektur-Codewörter, also das Produkt (x−α⁰)(x−α¹)…
 *
 * Index 0 hält den höchsten Grad. Das Verschieben um eine Stelle ist deshalb die Multiplikation
 * mit x, und der mit α^i skalierte Summand gehört eine Stelle weiter nach hinten. Vertauscht man
 * die beiden Zeilen, kommt das gespiegelte Polynom heraus — die Division läuft dann sauber durch,
 * liefert aber lauter falsche Prüfwörter, was am Muster nirgends auffällt.
 */
function generator(grad) {
  let poly = [1];
  for (let i = 0; i < grad; i++) {
    const neu = new Array(poly.length + 1).fill(0);
    for (let j = 0; j < poly.length; j++) {
      neu[j] ^= poly[j];
      neu[j + 1] ^= mul(poly[j], EXP[i]);
    }
    poly = neu;
  }
  return poly;
}

/** Die Fehlerkorrektur-Codewörter eines Datenblocks (Polynomdivision, Rest). */
function fehlerkorrektur(daten, anzahl) {
  const gen = generator(anzahl);
  const rest = new Array(anzahl).fill(0);
  for (const wert of daten) {
    const faktor = wert ^ rest[0];
    rest.shift();
    rest.push(0);
    if (faktor !== 0) {
      for (let i = 0; i < anzahl; i++) rest[i] ^= mul(gen[i + 1], faktor);
    }
  }
  return rest;
}

// --- Kodierung ----------------------------------------------------------------------------------

/** Text als UTF-8-Bytes — der Byte-Modus überträgt genau diese. */
function bytes(text) {
  return Array.from(new TextEncoder().encode(String(text)));
}

/** Kleinste Version, in die `laenge` Bytes passen. `null`, wenn es keine gibt. */
function versionFuer(laenge) {
  for (let v = 1; v <= 10; v++) if (laenge <= KAPAZITAET_L[v]) return v;
  return null;
}

/** Datenbits: Modusanzeige, Länge, Nutzdaten, Abschluss, Füllmuster. */
function datenbits(daten, version) {
  const { gruppen } = EC_L[version];
  const gesamtWoerter = gruppen.reduce((summe, [anzahl, groesse]) => summe + anzahl * groesse, 0);
  const bits = [];
  const schreibe = (wert, breite) => {
    for (let i = breite - 1; i >= 0; i--) bits.push((wert >> i) & 1);
  };

  schreibe(0b0100, 4); // Byte-Modus
  schreibe(daten.length, version <= 9 ? 8 : 16); // Längenfeld
  for (const b of daten) schreibe(b, 8);

  // Abschluss, dann auf ganze Bytes auffüllen.
  for (let i = 0; i < 4 && bits.length < gesamtWoerter * 8; i++) bits.push(0);
  while (bits.length % 8 !== 0) bits.push(0);

  // Rest mit dem vorgeschriebenen Wechselmuster 0xEC/0x11 füllen.
  const woerter = [];
  for (let i = 0; i < bits.length; i += 8) {
    woerter.push(bits.slice(i, i + 8).reduce((wert, bit) => (wert << 1) | bit, 0));
  }
  for (let i = 0; woerter.length < gesamtWoerter; i++) woerter.push(i % 2 === 0 ? 0xec : 0x11);
  return woerter;
}

/** Daten- und Fehlerkorrekturwörter blockweise verschränken (so schreibt es der Standard vor). */
function verschraenken(woerter, version) {
  const { ec, gruppen } = EC_L[version];
  const bloecke = [];
  let pos = 0;
  for (const [anzahl, groesse] of gruppen) {
    for (let i = 0; i < anzahl; i++) {
      bloecke.push(woerter.slice(pos, pos + groesse));
      pos += groesse;
    }
  }
  const ecBloecke = bloecke.map((b) => fehlerkorrektur(b, ec));

  const ergebnis = [];
  const maxLaenge = Math.max(...bloecke.map((b) => b.length));
  for (let i = 0; i < maxLaenge; i++) {
    for (const block of bloecke) if (i < block.length) ergebnis.push(block[i]);
  }
  for (let i = 0; i < ec; i++) {
    for (const block of ecBloecke) ergebnis.push(block[i]);
  }
  return ergebnis;
}

// --- Matrix -------------------------------------------------------------------------------------

/** Legt Sucher-, Takt- und Ausrichtungsmuster; `reserviert` merkt die festen Felder. */
function grundmuster(groesse, version) {
  const feld = Array.from({ length: groesse }, () => new Array(groesse).fill(0));
  const reserviert = Array.from({ length: groesse }, () => new Array(groesse).fill(false));
  const setze = (x, y, wert) => {
    feld[y][x] = wert;
    reserviert[y][x] = true;
  };

  // Drei Suchermuster mit Trennlinie. Die Schleife greift absichtlich eine Stelle über das 7×7-Auge
  // hinaus, damit die helle Trennlinie gleich mitgeschrieben und reserviert wird. Sie gehört aber
  // nicht mehr zum Auge — ohne `innen` würde `y === 0` auch die Trennfelder bei x = −1 und x = 7
  // schwärzen und aus jedem Sucher ein 9 Felder breites Klotzmuster machen.
  for (const [ox, oy] of [[0, 0], [groesse - 7, 0], [0, groesse - 7]]) {
    for (let y = -1; y <= 7; y++) {
      for (let x = -1; x <= 7; x++) {
        const px = ox + x;
        const py = oy + y;
        if (px < 0 || py < 0 || px >= groesse || py >= groesse) continue;
        const innen = x >= 0 && x <= 6 && y >= 0 && y <= 6;
        const rand = x === 0 || x === 6 || y === 0 || y === 6;
        const kern = x >= 2 && x <= 4 && y >= 2 && y <= 4;
        setze(px, py, innen && (rand || kern) ? 1 : 0);
      }
    }
  }

  // Taktmuster.
  for (let i = 8; i < groesse - 8; i++) {
    setze(i, 6, i % 2 === 0 ? 1 : 0);
    setze(6, i, i % 2 === 0 ? 1 : 0);
  }

  // Ausrichtungsmuster (nicht über die Sucher legen).
  const stellen = AUSRICHTUNG[version];
  for (const cy of stellen) {
    for (const cx of stellen) {
      if ((cx === 6 && cy === 6) || (cx === 6 && cy === groesse - 7) || (cx === groesse - 7 && cy === 6)) {
        continue;
      }
      for (let y = -2; y <= 2; y++) {
        for (let x = -2; x <= 2; x++) {
          const rand = Math.abs(x) === 2 || Math.abs(y) === 2 || (x === 0 && y === 0);
          setze(cx + x, cy + y, rand ? 1 : 0);
        }
      }
    }
  }

  // Ab Version 7 trägt der Code seine Versionsnummer zweimal als 6+12-Bit-Block neben dem rechten
  // oberen und dem linken unteren Sucher. Fehlt sie, sind nicht nur 36 Felder falsch belegt —
  // sie wären auch nicht reserviert, und die Datenspur schöbe sich um 36 Bit gegen den Standard.
  if (version >= 7) {
    let rest = version;
    for (let i = 0; i < 12; i++) rest = (rest << 1) ^ ((rest >> 11) * 0x1f25);
    const vbits = (version << 12) | rest;
    for (let i = 0; i < 18; i++) {
      const wert = (vbits >> i) & 1;
      const laengs = groesse - 11 + (i % 3);
      const quer = Math.floor(i / 3);
      setze(laengs, quer, wert);
      setze(quer, laengs, wert);
    }
  }

  // Felder der Formatinformation reservieren, dazu das immer gesetzte Dunkelfeld.
  for (let i = 0; i < 9; i++) {
    if (!reserviert[8][i]) setze(i, 8, 0);
    if (!reserviert[i][8]) setze(8, i, 0);
  }
  for (let i = 0; i < 8; i++) {
    if (!reserviert[8][groesse - 1 - i]) setze(groesse - 1 - i, 8, 0);
    if (!reserviert[groesse - 1 - i][8]) setze(8, groesse - 1 - i, 0);
  }
  setze(8, groesse - 8, 1);
  return { feld, reserviert };
}

/** Schreibt die Datenbits im Zickzack von rechts unten nach oben. */
function daten_einfuellen(feld, reserviert, woerter) {
  const groesse = feld.length;
  let bit = 0;
  const gesamt = woerter.length * 8;
  const naechstes = () => {
    if (bit >= gesamt) return 0;
    const wert = (woerter[bit >> 3] >> (7 - (bit & 7))) & 1;
    bit++;
    return wert;
  };

  let aufwaerts = true;
  for (let rechts = groesse - 1; rechts >= 1; rechts -= 2) {
    if (rechts === 6) rechts--; // die Taktspalte wird übersprungen
    for (let schritt = 0; schritt < groesse; schritt++) {
      const y = aufwaerts ? groesse - 1 - schritt : schritt;
      for (const x of [rechts, rechts - 1]) {
        if (!reserviert[y][x]) feld[y][x] = naechstes();
      }
    }
    aufwaerts = !aufwaerts;
  }
}

/** Die acht Maskenmuster des Standards. */
const MASKEN = [
  (x, y) => (x + y) % 2 === 0,
  (x, y) => y % 2 === 0,
  (x) => x % 3 === 0,
  (x, y) => (x + y) % 3 === 0,
  (x, y) => (Math.floor(y / 2) + Math.floor(x / 3)) % 2 === 0,
  (x, y) => ((x * y) % 2) + ((x * y) % 3) === 0,
  (x, y) => (((x * y) % 2) + ((x * y) % 3)) % 2 === 0,
  (x, y) => (((x + y) % 2) + ((x * y) % 3)) % 2 === 0,
];

/** Bewertung eines Musters nach den vier Regeln des Standards — kleiner ist besser. */
function strafe(feld) {
  const n = feld.length;
  let summe = 0;

  // Regel 1: Läufe gleicher Farbe ab fünf Feldern.
  for (let i = 0; i < n; i++) {
    for (const zeile of [feld[i], feld.map((r) => r[i])]) {
      let lauf = 1;
      for (let j = 1; j < n; j++) {
        if (zeile[j] === zeile[j - 1]) {
          lauf++;
          if (lauf === 5) summe += 3;
          else if (lauf > 5) summe++;
        } else lauf = 1;
      }
    }
  }

  // Regel 2: gleichfarbige 2×2-Blöcke.
  for (let y = 0; y < n - 1; y++) {
    for (let x = 0; x < n - 1; x++) {
      const w = feld[y][x];
      if (w === feld[y][x + 1] && w === feld[y + 1][x] && w === feld[y + 1][x + 1]) summe += 3;
    }
  }

  // Regel 3: das sucherähnliche Muster 1:1:3:1:1, wenn davor oder danach vier helle Felder liegen.
  // Der Bereich außerhalb des Symbols zählt dabei mit als hell — dort liegt die vorgeschriebene
  // Ruhezone. Sucht man stattdessen ein starres Elferfenster ganz innerhalb der Matrix, bleiben
  // ausgerechnet die drei echten Suchermuster ungezählt (18 Fundstellen je Code, waagerecht wie
  // senkrecht), und die Maskenwahl kippt regelmäßig auf die falsche Maske.
  const suchermuster = [1, 0, 1, 1, 1, 0, 1];
  const hell = (zeile, von, bis) => {
    for (let k = Math.max(von, 0); k < Math.min(bis, n); k++) if (zeile[k]) return false;
    return true;
  };
  for (let i = 0; i < n; i++) {
    for (const zeile of [feld[i], feld.map((r) => r[i])]) {
      for (let j = 0; j + 7 <= n; j++) {
        if (!suchermuster.every((w, k) => w === zeile[j + k])) continue;
        if (hell(zeile, j - 4, j) || hell(zeile, j + 7, j + 11)) summe += 40;
      }
    }
  }

  // Regel 4: Abweichung vom halb-halb-Verhältnis.
  const dunkel = feld.flat().reduce((a, b) => a + b, 0);
  const anteil = (dunkel * 100) / (n * n);
  summe += Math.floor(Math.abs(anteil - 50) / 5) * 10;
  return summe;
}

/** Formatinformation (Stufe L + Maske) mit BCH-Fehlerschutz an ihre beiden Plätze schreiben. */
function formatinfo(feld, maske) {
  const n = feld.length;
  let wert = (0b01 << 3) | maske; // 01 = Stufe L
  let rest = wert << 10;
  for (let i = 4; i >= 0; i--) {
    if (rest & (1 << (i + 10))) rest ^= 0b10100110111 << i;
  }
  const bits = ((wert << 10) | rest) ^ 0b101010000010010;

  // Beide Kopien laufen um den Sucher herum, aber gegenläufig: die erste beginnt senkrecht in
  // Spalte 8 und biegt in Zeile 8 nach links ab, die zweite beginnt waagerecht am rechten Rand und
  // läuft senkrecht am unteren aus. Verwechselt man dabei Zeile und Spalte, entsteht die
  // gespiegelte Anordnung — die Datenfelder bleiben unberührt, der Code wird trotzdem unlesbar,
  // weil jedes Lesegerät zuerst hier nach Stufe und Maske sucht.
  for (let i = 0; i <= 5; i++) feld[i][8] = (bits >> i) & 1;
  feld[7][8] = (bits >> 6) & 1;
  feld[8][8] = (bits >> 7) & 1;
  feld[8][7] = (bits >> 8) & 1;
  for (let i = 9; i < 15; i++) feld[8][14 - i] = (bits >> i) & 1;

  for (let i = 0; i <= 7; i++) feld[8][n - 1 - i] = (bits >> i) & 1;
  for (let i = 8; i < 15; i++) feld[n - 15 + i][8] = (bits >> i) & 1;
}

/**
 * Der QR-Code zu `text` als quadratisches Feld aus 0/1 — oder `null`, wenn er nicht hineinpasst.
 *
 * Gewählt wird die kleinste Version, die den Text fasst, und danach die Maske mit der geringsten
 * Strafpunktzahl. Beides schreibt der Standard so vor; damit entsteht dasselbe Muster, das auch
 * jeder andere Erzeuger liefert — und das Display zeigt.
 */
export function qrMatrix(text) {
  const daten = bytes(text);
  const version = versionFuer(daten.length);
  if (!version || !daten.length) return null;

  const woerter = verschraenken(datenbits(daten, version), version);
  const groesse = version * 4 + 17;

  let bestes = null;
  let besteStrafe = Infinity;
  for (let maske = 0; maske < 8; maske++) {
    const { feld, reserviert } = grundmuster(groesse, version);
    daten_einfuellen(feld, reserviert, woerter);
    for (let y = 0; y < groesse; y++) {
      for (let x = 0; x < groesse; x++) {
        if (!reserviert[y][x] && MASKEN[maske](x, y)) feld[y][x] ^= 1;
      }
    }
    formatinfo(feld, maske);
    const punkte = strafe(feld);
    if (punkte < besteStrafe) {
      besteStrafe = punkte;
      bestes = feld;
    }
  }
  return bestes;
}

/** Der QR-Code als SVG-Zeichenkette, passend in ein Quadrat der Kantenlänge `kante`. */
export function qrSvg(text, kante = 200, farbe = "#ffffff", grund = "transparent") {
  const feld = qrMatrix(text);
  if (!feld) return null;
  const n = feld.length;
  // Der Standard verlangt vier Module Rand; das Display hält ihn ebenfalls ein.
  const rand = 4;
  const gesamt = n + rand * 2;
  const teile = [];
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      if (feld[y][x]) teile.push(`M${x + rand} ${y + rand}h1v1h-1z`);
    }
  }
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" width="${kante}" height="${kante}" ` +
    `viewBox="0 0 ${gesamt} ${gesamt}" shape-rendering="crispEdges">` +
    `<rect width="${gesamt}" height="${gesamt}" fill="${grund}"/>` +
    `<path d="${teile.join("")}" fill="${farbe}"/></svg>`
  );
}
