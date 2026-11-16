// Anmeldung am RadioHub mit dem Konto der Kellerwolke (RAD-6), nach dem Muster der Schale des Appkerns: der Token liegt
// im Gerät (localStorage, Schlüssel radiohub_sitzung wie in der Schale, so bleibt ein Gerät auch mit der neuen
// Oberfläche aus Teil 2c angemeldet) und geht im Kopf X-Kellerwolke-Sitzung mit jeder Anfrage. Ton, Bilder und
// Ereignisströme holt der Browser ohne eigenen Kopf; für sie richtet der Lesezugang einen Keks unter /api ein, der
// beim Start und danach alle zwölf Stunden erneuert wird (die Weckeransicht am Nachttisch lädt tagelang nicht neu).
//
// Weist der Server eine Anfrage mit dem Kennzeichen WWW-Authenticate: Kellerwolke-Sitzung ab, ist die Sitzung vorbei:
// die Oberfläche zeigt wieder die Anmeldung. Ein 401 ohne dieses Kennzeichen ist nur ein Fehler dieser Anfrage.
// Ein Telefon (Web-App vom Startbildschirm) koppelt man mit einem Code aus der Kellerwolke; der Geräteschlüssel gilt,
// bis man das Gerät dort trennt.

const SCHLUESSEL = 'radiohub_sitzung';
const KOPF = 'X-Kellerwolke-Sitzung';
const KENNZEICHEN = 'Kellerwolke-Sitzung';
const ZUGANG_ERNEUERN_MS = 12 * 3600 * 1000;
export const CODE_LAENGE = 8;

export const sitzung = $state({ geladen: false, app: null, angemeldet: false, konto: null, fehler: '' });

let erneuern = null;

export function token() {
  try {
    return localStorage.getItem(SCHLUESSEL) ?? '';
  } catch {
    return '';
  }
}

function setzeToken(wert) {
  try {
    if (wert) localStorage.setItem(SCHLUESSEL, wert);
    else localStorage.removeItem(SCHLUESSEL);
  } catch {
    // ohne Speicher gilt die Anmeldung nur bis zum Neuladen
  }
}

// Kopf für eigene Anfragen ans Backend
export function kopf(weitere = {}) {
  const t = token();
  return t ? { ...weitere, [KOPF]: t } : { ...weitere };
}

// Nach jeder Antwort des Backends: hat es die Sitzung abgewiesen, ist sie vorbei
export function antwortPruefen(antwort) {
  if (antwort.status === 401 && antwort.headers.get('www-authenticate') === KENNZEICHEN && sitzung.angemeldet) vorbei();
}

function vorbei() {
  sitzung.angemeldet = false;
  sitzung.konto = null;
  if (erneuern) clearInterval(erneuern);
  erneuern = null;
}

async function frage(pfad, optionen = {}) {
  const antwort = await fetch(`/api/v1${pfad}`, {
    ...optionen,
    headers: kopf({ 'Content-Type': 'application/json', ...(optionen.headers ?? {}) }),
  });
  if (!antwort.ok) {
    let meldung = `Fehler ${antwort.status}`;
    try {
      const daten = await antwort.json();
      if (typeof daten.detail === 'string') meldung = daten.detail;
    } catch {
      // ohne lesbare Antwort bleibt die Nummer
    }
    throw new Error(meldung);
  }
  return antwort.status === 204 ? null : antwort.json();
}

async function lesezugang() {
  try {
    await frage('/anmeldung/zugang', { method: 'POST' });
  } catch {
    // ohne Lesezugang fehlen nur Ton und Bilder; der nächste Versuch kommt mit dem Takt
  }
}

async function adresseMelden() {
  try {
    await frage('/adresse', { method: 'POST', body: JSON.stringify({ adresse: location.origin }) });
  } catch {
    // ohne Adresse fehlt nur das Öffnen aus der Kellerwolke
  }
}

async function angemeldet(konto) {
  await lesezugang();
  void adresseMelden();
  if (erneuern) clearInterval(erneuern);
  erneuern = setInterval(lesezugang, ZUGANG_ERNEUERN_MS);
  sitzung.konto = konto;
  sitzung.angemeldet = true;
}

// Beim Start: Angaben der App, dann ob der gespeicherte Token noch gilt
export async function starten() {
  sitzung.fehler = '';
  try {
    sitzung.app = await frage('/app');
    if (!sitzung.app.einrichtung_noetig) {
      const stand = await frage('/anmeldung');
      if (stand.angemeldet) await angemeldet(stand.konto);
      else if (sitzung.app.anmeldung !== 'ohne') setzeToken('');
    }
  } catch (f) {
    sitzung.fehler = `RadioHub antwortet nicht: ${f.message}`;
  } finally {
    sitzung.geladen = true;
  }
}

export async function anmelden(kennung, passwort) {
  const daten = await frage('/anmeldung', { method: 'POST', body: JSON.stringify({ kennung, passwort }) });
  setzeToken(daten.token);
  await angemeldet(daten.konto);
}

export async function koppeln(code, name, art) {
  const daten = await frage('/anmeldung/koppeln', { method: 'POST', body: JSON.stringify({ code, name, art }) });
  setzeToken(daten.token);
  await angemeldet(daten.konto);
}

// Erste Einrichtung (nur solange keine Kellerwolke eingetragen ist); von anderswo als dem Rechner mit dem Code
export async function einrichten(kellerwolke_adresse, kellerwolke_schluessel, einrichtungscode = '') {
  sitzung.app = await frage('/einrichtung', {
    method: 'POST', body: JSON.stringify({ kellerwolke_adresse, kellerwolke_schluessel, einrichtungscode }),
  });
}

export async function abmelden() {
  try {
    await frage('/anmeldung/abmelden', { method: 'POST' });
  } catch {
    // lokal ist man danach in jedem Fall abgemeldet
  }
  setzeToken('');
  vorbei();
}

// Ein anderer Tab derselben App hat sich an- oder abgemeldet
globalThis.addEventListener?.('storage', (e) => {
  if (e.key !== SCHLUESSEL) return;
  if (e.newValue && !sitzung.angemeldet) void starten();
  else if (!e.newValue && sitzung.angemeldet) vorbei();
});

// --- Koppeln ------------------------------------------------------------------------------------------------------

export function codeNormal(text) {
  return text.replace(/[^0-9a-z]/gi, '').toUpperCase().slice(0, CODE_LAENGE);
}

// Kam die Seite über einen Koppel-Link (#koppeln=CODE), den Code einmal herausnehmen und aus der Adresse entfernen
export function codeAusLinkNehmen() {
  const marke = location.hash.slice(1);
  if (!marke.startsWith('koppeln=')) return '';
  history.replaceState(null, '', location.pathname + location.search);
  return codeNormal(marke.slice('koppeln='.length));
}

// Vom Startbildschirm gestartet oder im Browser; auf dem iPhone haben beide getrennte Speicher
export function geraeteArt() {
  const eigen = matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  return eigen ? 'webapp' : 'browser';
}

export function namensvorschlag() {
  const ua = navigator.userAgent;
  if (/iPad|Tablet/i.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1)) return 'Tablet';
  if (/iPhone|Mobile/i.test(ua)) return 'Telefon';
  if (/Android/i.test(ua)) return 'Tablet';
  return 'Rechner';
}
