// Sitzung für die Anfragen der alten Datenschicht (lib/api.js, Ton, Wellenform): die Anmeldung selbst führt die Schale
// des Appkerns (Konto der Kellerwolke, Schlüssel radiohub_sitzung im Browser). Die Schale verbindet beim Start, woher
// der Token kommt und was bei einer Abweisung geschieht (`sitzungVerbinden`); so kennt diese Schicht keine Oberfläche
// und bleibt ohne Browser prüfbar. Mit der neuen Datenschicht (Etappe 3) gehen die Anfragen direkt über den Appkern.

const KOPF = "X-Kellerwolke-Sitzung";
const KENNZEICHEN = "Kellerwolke-Sitzung";

interface Quelle {
  /** der Token dieses Geräts, leer ohne Anmeldung */
  token: () => string;
  /** der Server hat die Sitzung abgewiesen: die Schale prüft und zeigt dann die Anmeldung */
  abgewiesen: () => void;
}

let quelle: Quelle = { token: () => "", abgewiesen: () => {} };

export function sitzungVerbinden(neu: Quelle): void {
  quelle = neu;
}

/** Kopf für eigene Anfragen ans Backend; ohne Token kein leerer Kopf */
export function kopf(weitere: Record<string, string> = {}): Record<string, string> {
  const t = quelle.token();
  return t ? { ...weitere, [KOPF]: t } : { ...weitere };
}

/** Nach jeder Antwort: nur eine Abweisung mit dem Kennzeichen der Sitzung beendet sie (ein 401 ohne ist nur ein Fehler
 *  dieser Anfrage, etwa von einem anderen Dienst weitergereicht) */
export function antwortPruefen(antwort: { status: number; headers: Headers }): void {
  if (antwort.status === 401 && (antwort.headers.get("www-authenticate") ?? "").includes(KENNZEICHEN)) quelle.abgewiesen();
}
