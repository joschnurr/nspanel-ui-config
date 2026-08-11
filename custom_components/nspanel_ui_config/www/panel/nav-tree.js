// Der Aufbau der Panel-Navigation als Baum — und die Umbauten, die der Editor daran vornimmt.
//
// **Warum ein Baum:** In der flachen Liste aus `cards` und `hiddenCards` ist nicht zu sehen, wie
// man am Gerät von einer Karte zur nächsten kommt. Genau daran scheiterte eine echte Konfiguration:
// zwei Karten hatten ihre Blättertasten mit festen Zielen überschrieben (`navItem1`/`navItem2`),
// die Kette endete dort, und drei dahinterliegende Karten waren unerreichbar — in der Liste sahen
// sie völlig normal aus.
//
// Die Verbindungen stehen im Modell verstreut:
//   * `cards` sind über die Blättertasten miteinander verbunden (Reihenfolge = Kette),
//   * ein Eintrag `navigate.<key>` auf einer Karte springt zu einer anderen,
//   * `navItem1`/`navItem2` ersetzen die Blättertasten durch feste Ziele,
//   * `screensaver.defaultCard` sagt, wo das Panel nach dem Aufwachen landet.
//
// Dieses Modul ist bewusst frei von DOM und Home Assistant: die Zuordnung ist die Logik, an der ein
// Fehler weh tut, und die soll ohne Browser prüfbar sein.

/** Ein `navigate.<ziel>` aus einem Entity-Wert – oder `null`. */
export function navigationsZiel(wert) {
  if (typeof wert !== "string") return null;
  const text = wert.trim();
  return text.startsWith("navigate.") ? text.slice("navigate.".length) : null;
}

/**
 * Alle Sprungziele, die eine Karte enthält (Einträge und überschriebene Blättertasten).
 *
 * `eintragIndex` ist die Stelle in `entities` – daran hängt das Umsortieren der Menüpunkte: wer im
 * Baum ein Untermenü verschiebt, meint die Reihenfolge *auf der Menükarte*, nicht die Reihenfolge
 * der versteckten Karten (die ist am Gerät gar nicht sichtbar).
 */
export function zieleEiner(card) {
  if (!card || typeof card !== "object") return [];
  const ziele = [];
  (card.entities || []).forEach((eintrag, eintragIndex) => {
    const ziel = navigationsZiel(eintrag && eintrag.entity);
    if (ziel) ziele.push({ ziel, quelle: "entity", eintragIndex });
  });
  for (const feld of ["navItem1", "navItem2"]) {
    const wert = card[feld];
    const ziel = navigationsZiel(wert && typeof wert === "object" ? wert.entity : wert);
    if (ziel) ziele.push({ ziel, quelle: feld, eintragIndex: null });
  }
  return ziele;
}

/** Karte zu einem `key` bzw. `uuid.<id>` finden. */
function findeKarte(alle, ziel) {
  if (!ziel) return null;
  return (
    alle.find((eintrag) => eintrag.card && eintrag.card.key === ziel) ||
    // uuid-Ziele vergibt das Backend selbst; im Modell stehen sie nicht, deshalb bleiben sie leer.
    null
  );
}

/**
 * Baut den Navigationsbaum des Modells.
 *
 * Wurzeln sind die sichtbaren Karten (sie hängen über die Blättertasten zusammen). Darunter hängen
 * die Karten, auf die sie per `navigate.<key>` zeigen. Eine Karte erscheint **einmal** im Baum, beim
 * ersten Erreichen; weitere Verweise darauf werden als `mehrfach` vermerkt, statt den Baum
 * unendlich tief zu machen (Karten dürfen sich gegenseitig verlinken).
 *
 * Rückgabe: `{ wurzeln, verwaist, unbekannt }` — `verwaist` sind versteckte Karten, die **niemand**
 * verlinkt: am Gerät sind sie nicht erreichbar. Genau die soll der Editor sichtbar machen.
 */
export function baueBaum(model) {
  const sichtbar = (model && model.cards) || [];
  const versteckt = (model && model.hiddenCards) || [];
  const alle = [
    ...sichtbar.map((card, index) => ({ card, kind: "cards", index })),
    ...versteckt.map((card, index) => ({ card, kind: "hiddenCards", index })),
  ];

  const gesehen = new Set();
  const unbekannt = [];

  const knoten = (eintrag, tiefe, ueber, eltern) => {
    const schluessel = `${eintrag.kind}:${eintrag.index}`;
    const mehrfach = gesehen.has(schluessel);
    gesehen.add(schluessel);
    const kinder = [];
    if (!mehrfach) {
      for (const { ziel, quelle, eintragIndex } of zieleEiner(eintrag.card)) {
        const treffer = findeKarte(alle, ziel);
        if (!treffer) {
          unbekannt.push({ von: eintrag.card && eintrag.card.key, ziel, quelle });
          continue;
        }
        kinder.push(
          knoten(treffer, tiefe + 1, quelle, {
            kind: eintrag.kind,
            index: eintrag.index,
            eintragIndex,
          })
        );
      }
    }
    return { ...eintrag, tiefe, ueber, mehrfach, kinder, eltern: eltern || null };
  };

  const wurzeln = sichtbar.map((card, index) =>
    knoten({ card, kind: "cards", index }, 0, "kette", null)
  );
  const verwaist = versteckt
    .map((card, index) => ({ card, kind: "hiddenCards", index }))
    .filter((eintrag) => !gesehen.has(`hiddenCards:${eintrag.index}`))
    .map((eintrag) => ({
      ...eintrag,
      tiefe: 0,
      ueber: null,
      mehrfach: false,
      kinder: [],
      eltern: null,
    }));

  return { wurzeln, verwaist, unbekannt };
}

/** Den Baum als flache Liste – so, wie die Seitenleiste ihn Zeile für Zeile zeichnet. */
export function alsListe(baum) {
  const zeilen = [];
  const lauf = (knoten) => {
    zeilen.push(knoten);
    for (const kind of knoten.kinder) lauf(kind);
  };
  for (const wurzel of baum.wurzeln) lauf(wurzel);
  return zeilen;
}

/**
 * Verschiebt eine Karte – das, was Ziehen und Fallenlassen im Editor auslöst.
 *
 * `nach` ist die Zielliste (`cards`/`hiddenCards`), `vor` die Position davor. Das Modell wird
 * **in place** geändert, damit der Editor mit derselben Objektreferenz weiterarbeitet.
 *
 * Rückgabe: die neue Position, oder `null`, wenn nichts zu tun war.
 */
export function verschiebeKarte(model, vonKind, vonIndex, nachKind, nachIndex) {
  const quelle = model[vonKind];
  const ziel = model[nachKind] || (model[nachKind] = []);
  if (!Array.isArray(quelle) || vonIndex < 0 || vonIndex >= quelle.length) return null;

  const [karte] = quelle.splice(vonIndex, 1);
  // Innerhalb derselben Liste verschiebt sich alles hinter der Entnahmestelle um eins nach vorn.
  let einfuegen = nachIndex;
  if (vonKind === nachKind && vonIndex < nachIndex) einfuegen -= 1;
  einfuegen = Math.max(0, Math.min(einfuegen, ziel.length));
  ziel.splice(einfuegen, 0, karte);

  // **Die Liste entscheidet, nicht ein Key an der Karte.** Das Backend baut seine Karten in
  // `config.py` als `Card(card, hidden=True)` – die Eigenschaft ergibt sich allein daraus, dass die
  // Karte unter `hiddenCards:` steht; ein `hidden:` in der Konfiguration liest es nirgends.
  //
  // Früher wurde hier eins gesetzt. Es stand dann im gespeicherten Modell, kam aber nie in der
  // erzeugten YAML an (`hidden` ist kein bekanntes Kartenfeld, also wirft `denormalize_card` es
  // weg) und verschwand beim nächsten Rundlauf über den YAML-Dialog wieder. Ein solcher Rest wird
  // hier deshalb entfernt, statt ihn weiterzuschleppen.
  delete karte.hidden;

  return { kind: nachKind, index: einfuegen };
}

/**
 * Vergibt einer Karte einen eindeutigen `key`, falls sie keinen brauchbaren hat.
 *
 * Ohne `key` ist eine Karte nicht verlinkbar (`navigate.<key>` braucht einen Namen). Der Vorschlag
 * kommt aus dem Titel — klein, Umlaute aufgelöst, alles Unlesbare wird `-`. Kollidiert er mit einem
 * vorhandenen `key`, hängt eine Zahl dran: lieber `heizung-2` als ein stiller Doppelverweis, bei dem
 * das Backend nur die erste Karte findet.
 */
export function vergebeKey(model, card) {
  if (card.key && card.key !== "unknown") return card.key;
  const basis =
    String(card.title || card.type || "karte")
      .toLowerCase()
      .replace(/ä/g, "ae")
      .replace(/ö/g, "oe")
      .replace(/ü/g, "ue")
      .replace(/ß/g, "ss")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "karte";
  const vergeben = new Set(
    [...(model.cards || []), ...(model.hiddenCards || [])].map((k) => k && k.key).filter(Boolean)
  );
  let key = basis;
  for (let n = 2; vergeben.has(key); n += 1) key = `${basis}-${n}`;
  card.key = key;
  return key;
}

/**
 * Löst den Verweis, über den eine Baumzeile an ihrer Elternkarte hängt.
 *
 * `ueber` sagt, wo der Verweis steht: als Menüeintrag (`entity`, dann zeigt `eintragIndex` auf die
 * Stelle) oder als überschriebene Blättertaste (`navItem1`/`navItem2`). Der `eintragIndex` wird
 * gegen den `key` geprüft, bevor gelöscht wird — zwischen Zeichnen und Ziehen kann sich die Liste
 * geändert haben, und ein Löschen an der falschen Stelle risse einen fremden Menüpunkt heraus.
 */
export function loeseVerweis(elternCard, ueber, kindKey, eintragIndex) {
  if (!elternCard || typeof elternCard !== "object") return false;
  if (ueber === "navItem1" || ueber === "navItem2") {
    const wert = elternCard[ueber];
    const ziel = navigationsZiel(wert && typeof wert === "object" ? wert.entity : wert);
    if (ziel !== kindKey) return false;
    delete elternCard[ueber];
    return true;
  }
  const liste = elternCard.entities || [];
  let index =
    eintragIndex != null && navigationsZiel(liste[eintragIndex] && liste[eintragIndex].entity) === kindKey
      ? eintragIndex
      : liste.findIndex((e) => navigationsZiel(e && e.entity) === kindKey);
  if (index < 0) return false;
  liste.splice(index, 1);
  return true;
}

/**
 * Hängt eine Karte als Unterseite unter eine Zielkarte — das „mitten auf die Zeile"-Ziehen.
 *
 * Macht in einem Zug, was bisher drei Handgriffe waren: `key` sicherstellen, den bisherigen
 * Menü-Verweis der gezogenen Zeile lösen (nur diesen einen — absichtliche Mehrfach-Verweise von
 * anderen Karten bleiben stehen), `navigate.<key>` auf der Zielkarte anlegen (Name aus dem Titel
 * vorbelegt) und die Karte selbst zu den Unterseiten stellen, falls sie in der Blätterkette stand.
 *
 * `optionen.maxEintraege` ist die Anzeigekapazität der Zielkarte (aus dem Schema, `null` = keine
 * Aussage): ein Eintrag über der Kapazität käme in der YAML an, bliebe am Gerät aber unsichtbar —
 * genau die stillen Fehler, vor denen der Editor sonst überall warnt.
 *
 * Rückgabe `{ ok: true, key }` oder `{ ok: false, grund }`; das Modell wird nur im Erfolgsfall
 * angefasst (alle Prüfungen stehen vor der ersten Änderung).
 */
export function haengeUnter(model, quelle, ziel, optionen = {}) {
  const karte = (model[quelle.kind] || [])[quelle.index];
  const zielKarte = (model[ziel.kind] || [])[ziel.index];
  if (!karte || !zielKarte) return { ok: false, grund: "Karte nicht gefunden" };
  if (karte === zielKarte) return { ok: false, grund: "Eine Karte kann nicht unter sich selbst hängen" };

  const liste = zielKarte.entities || (zielKarte.entities = []);
  const key = karte.key && karte.key !== "unknown" ? karte.key : null;
  if (key && liste.some((e) => navigationsZiel(e && e.entity) === key))
    return { ok: false, grund: "Die Zielkarte verlinkt diese Karte schon" };
  if (optionen.maxEintraege != null && liste.length >= optionen.maxEintraege)
    return {
      ok: false,
      grund: `Die Zielkarte ist voll (${liste.length}/${optionen.maxEintraege} Plätze) — der neue Eintrag wäre am Gerät unsichtbar`,
    };

  // Ab hier wird geändert. Elternkarte VOR dem Listenumbau auflösen — ihr Index gilt noch.
  const echterKey = vergebeKey(model, karte);
  if (optionen.eltern) {
    const elternKarte = (model[optionen.eltern.kind] || [])[optionen.eltern.index];
    loeseVerweis(elternKarte, optionen.ueber || "entity", echterKey, optionen.eltern.eintragIndex);
  }

  // Unterseiten stehen unter `hiddenCards` — eine verlinkte Karte hat in der Blätterkette nichts
  // mehr verloren (sie käme sonst doppelt: einmal geblättert, einmal gesprungen).
  if (quelle.kind === "cards") {
    const index = (model.cards || []).indexOf(karte);
    if (index >= 0) {
      model.cards.splice(index, 1);
      (model.hiddenCards || (model.hiddenCards = [])).push(karte);
      delete karte.hidden; // wie in verschiebeKarte: die Liste entscheidet, nicht das Feld.
    }
  }

  const eintrag = { entity: `navigate.${echterKey}`, extra: {} };
  if (karte.title) eintrag.name = karte.title;
  liste.push(eintrag);
  return { ok: true, key: echterKey };
}

/** Verschiebt einen Eintrag innerhalb einer Karte (die Reihenfolge der Menüpunkte). */
export function verschiebeEintrag(card, vonIndex, nachIndex) {
  const liste = card && card.entities;
  if (!Array.isArray(liste) || vonIndex < 0 || vonIndex >= liste.length) return null;
  const [eintrag] = liste.splice(vonIndex, 1);
  let einfuegen = nachIndex;
  if (vonIndex < nachIndex) einfuegen -= 1;
  einfuegen = Math.max(0, Math.min(einfuegen, liste.length));
  liste.splice(einfuegen, 0, eintrag);
  return einfuegen;
}
