# Entwicklung

Alles, was an dieser Integration *gebaut* wird — die Schnittstelle, aus der das Panel seine Daten
zieht, die mitgelieferten Bilder und die Werkzeuge, die beides erzeugen. Zum Einrichten und Bedienen
braucht man nichts davon; dafür sind [einrichtung.md](einrichtung.md) und
[funktionen.md](funktionen.md) da.

## HTTP-API

Alle Endpunkte sind authentifiziert und **nur für Administratoren**.

| Methode | Pfad | Zweck |
| --- | --- | --- |
| `GET` | `/api/nspanel_ui_config/schema` | Feld-/Kartentyp-Schema, aus dem das Panel seine Formulare baut |
| `GET` | `/api/nspanel_ui_config/config` | aktuelles Modell + Validierungsbefunde |
| `POST` | `/api/nspanel_ui_config/config` | Modell speichern |
| `POST` | `/api/nspanel_ui_config/import` | `apps.yaml` einlesen (`{"text": …}` oder `{"path": …}`, optional `app_name`, `save`) |
| `POST` | `/api/nspanel_ui_config/yaml` | YAML zum übergebenen Stand (`{"model": …}`, ohne Body der gespeicherte) — **nur zum Ansehen**, schreibt nichts |
| `POST` | `/api/nspanel_ui_config/generate` | YAML erzeugen, schreiben und AppDaemon neu laden (`{"reload": false}` überspringt den Reload) |
| `GET` | `/api/nspanel_ui_config/backups` | vorhandene Sicherungen der Ausgabedatei |
| `POST` | `/api/nspanel_ui_config/backups/restore` | eine Sicherung zurückspielen (`{"name": …}`) |

Beim Import über `path` muss das Verzeichnis in Home Assistants `allowlist_external_dirs` stehen
(der Pfad kommt aus dem Request). Der *Ausgabe*pfad stammt dagegen aus den Integrations-Optionen und
wird von einem Administrator gesetzt. Beim Zurückspielen werden Pfadanteile im `name` abgewiesen.

## Brand-Assets

`custom_components/nspanel_ui_config/brand/` enthält die Bilder, die Home Assistant und HACS für die
Integration anzeigen: `icon.png` (256×256), `icon@2x.png` (512×512), `logo.png` (304×256) und
`logo@2x.png` (607×512). Erzeugt werden sie aus `docs/brand-source.jpg`:

```bash
npm install jpeg-js pngjs
node tools/make-brand-images.mjs docs/brand-source.jpg custom_components/nspanel_ui_config/brand
```

**Die Icons sind mittig quadratisch beschnitten, nicht aufgefüllt.** Das brands-Repo verlangt
ausdrücklich getrimmte Bilder („minimum amount of empty space on the edges"); eine frühere Fassung
mit transparenten Rändern oben und unten wäre dort abgelehnt worden. Beschnitten wird nur der
seitliche Geräterahmen — Display, Stift und Schriftzug bleiben vollständig. Das Logo behält das
ganze Bild, es darf rechteckig sein. `tests/test_manifests.py` prüft die Maße mit, weil sie sonst
erst im PR auffallen.

**Zwei Wege, die man nicht verwechseln darf** — beide nachgemessen:

| Wo | Woher das Bild kommt | Zeigt es unser Icon? |
| --- | --- | --- |
| Home Assistant (*Geräte & Dienste*) | liest `brand/` direkt aus der Integration und serviert es unter `/api/brands/integration/<domain>/<bild>` – mit Vorrang vor dem CDN (ab HA 2026.3) | **ja** |
| HACS-Übersicht | Brands-CDN, feste URL auf `brands.home-assistant.io` (Stand HACS 2.0.5) | **nein**, generischer Platzhalter |

**Ein Eintrag im [brands-Repo](https://github.com/home-assistant/brands) hilft dagegen nicht mehr –
er ist gar nicht mehr möglich.** Seit Home Assistant 2026.3 liefern Custom-Integrationen ihre Bilder
selbst, und das Repo nimmt dafür keine Beiträge mehr an; ein PR wird vom Bot automatisch geschlossen
([Ankündigung](https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api), hier am
2026-07-26 mit PR #10853 ausprobiert und genau so beschieden).

Dass die HACS-Übersicht trotzdem den Platzhalter zeigt, liegt allein daran, dass HACS seine
Bild-URLs noch fest gegen das CDN baut, statt den lokalen Proxy zu nutzen. Das ist dort bekannt
(u. a. hacs/frontend#937, hacs/integration#5179) und kommt mit einer künftigen HACS-Version – von
dieser Integration aus lässt sich daran nichts ändern.

**Warten ist dabei die einzige Option, und es kann dauern.** Nachgeprüft am 2026-07-29: Die neueste
HACS-Fassung ist weiterhin **2.0.5 vom 28.01.2025** — seit anderthalb Jahren kein Release. Die
HACS-Doku nennt inzwischen zwar das `brand/`-Verzeichnis im Repository als bevorzugten Weg, aber
was zählt, ist die Fassung, die tatsächlich installiert ist. Ein Update, das den Platzhalter
ersetzt, steht also nicht kurz bevor.

**Am Repo liegt es nicht:** Die vier Bilder sind vorhanden, haben die geforderten Maße (von
`tests/test_manifests.py` geprüft), und Home Assistant selbst zeigt sie unter *Geräte & Dienste*
korrekt an. Es gibt hier nichts zu reparieren.

Fehlt eine Dark-Variante (`dark_icon.png`), fällt HA auf die helle zurück – Dark-Assets sind nicht
nötig.

**Dateigröße zählt.** Das brands-Repo achtet ausdrücklich darauf, und die Bilder landen in jeder
Installation. Direkt aus einem Foto exportiert waren unsere mit 83 kB (256×256) und 285 kB (512×512)
rund fünfzehnmal so groß wie üblich. `tools/optimize-brand-png.mjs` quantisiert sie auf eine Palette
und schreibt ein indiziertes PNG:

```bash
npm install pngjs
node tools/optimize-brand-png.mjs quelle.png ziel.png 128
```

Das drückt sie um ~83 % (14,1 / 47,5 / 38,8 kB) **ohne sichtbaren Unterschied**. Bei 64 Farben
zeigt der dunkle Rahmen des Icons Banding – 128 ist die Grenze.

### Social Preview

`docs/social-preview.jpg` (1280×640, ~105 kB) ist das Bild, das GitHub in jeder Linkvorschau des
Repos zeigt. Erzeugt aus derselben Quelle:

```bash
npm install jpeg-js
node tools/make-social-preview.mjs docs/brand-source.jpg docs/social-preview.jpg
```

Das Motiv wird proportional eingepasst und auf Fast-Schwarz zentriert, **nicht beschnitten** – ein
2:1-Ausschnitt würde den Schriftzug am unteren Rand kosten.

**Hochladen lässt es sich nur von Hand:** *Settings → General → Social preview* im Web-UI von
GitHub. Es gibt dafür keinen API-Endpunkt, die Datei im Repo genügt also nicht.
