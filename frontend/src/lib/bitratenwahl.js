/**
 * Wahl der Bitrate des Zeitversatzes (RAD-92), an einer Stelle für Engine, Anfrage und Kanzel; gemerkt im Browser
 * (radiohub_bitrate_override, wie bisher). "original": der Ton des Senders geht unverändert in den Puffer (Vorgabe);
 * "voll": umgewandelt in der Bitrate des Senders; eine Zahl: umgewandelt in diese Bitrate (kbit/s).
 * Ein Gerät, das den Ton des Senders nicht abspielen kann, stellt auf "voll" (playerEngine).
 * @typedef {"original" | "voll" | number} Bitratenwahl
 */

const SCHLUESSEL = 'radiohub_bitrate_override';
/** wer von einer neuen Wahl erfahren will (die Drehwahl der Kanzel, wenn die Engine selbst umstellt) */
const hoerer = new Set();

/** @param {(wahl: Bitratenwahl) => void} f @returns {() => void} */
export function beiBitratenwahl(f) {
  hoerer.add(f);
  return () => hoerer.delete(f);
}

/** @returns {Bitratenwahl} */
export function bitratenwahlLesen() {
  try {
    const wert = JSON.parse(localStorage.getItem(SCHLUESSEL) || 'null');
    if (wert === 'voll' || (typeof wert === 'number' && wert > 0)) return wert;
  } catch {
    /* ohne Speicher im Browser gilt die Vorgabe */
  }
  return 'original';
}

/** @param {Bitratenwahl} wahl */
export function bitratenwahlSetzen(wahl) {
  try {
    if (wahl === 'original') localStorage.removeItem(SCHLUESSEL);
    else localStorage.setItem(SCHLUESSEL, JSON.stringify(wahl));
  } catch {
    /* nur für diese Seite */
  }
  for (const f of hoerer) f(wahl);
}

/** Felder der Startanfrage des Puffers (/api/hls/start) */
export function bitratenwahlAnfrage(wahl = bitratenwahlLesen()) {
  return { original: wahl === 'original', override_bitrate: typeof wahl === 'number' ? wahl : 0 };
}
