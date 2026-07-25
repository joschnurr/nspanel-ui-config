// NSPanel UI Config – Panel (v0.1 Platzhalter).
//
// Das Panel wird derzeit als iFrame ausgeliefert. iFrame-Panels erhalten den HA-Auth-Token nicht
// automatisch, daher kann die authentifizierte Integrations-API von hier noch nicht direkt
// aufgerufen werden. Der geplante Ausbau stellt auf ein panel_custom-Element um, das das
// `hass`-Objekt (inkl. Verbindung/Token) erhält und darüber Modell laden/speichern kann.
//
// Für jetzt: freundlicher Status statt eines fehlschlagenden Requests.

(function () {
  "use strict";

  const statusEl = document.getElementById("status");
  if (!statusEl) return;

  // Optimistischer, aber tokenloser Probe-Request. 401 ist im iFrame-Kontext erwartbar und wird
  // als "Integration läuft, Editor-Anbindung folgt" interpretiert – nicht als Fehler.
  fetch("/api/nspanel_ui_config/config", { headers: { Accept: "application/json" } })
    .then((res) => {
      if (res.ok) {
        statusEl.textContent = "Verbunden. Modell geladen – der visuelle Editor folgt in Kürze.";
      } else if (res.status === 401) {
        statusEl.textContent =
          "Integration aktiv. Die Editor-Anbindung (authentifiziert) wird als nächstes umgesetzt.";
      } else {
        statusEl.textContent = "Integration erreichbar (HTTP " + res.status + ").";
      }
    })
    .catch(() => {
      statusEl.textContent =
        "API noch nicht erreichbar – ist die Integration eingerichtet? (Einstellungen → Geräte & Dienste)";
    });
})();
