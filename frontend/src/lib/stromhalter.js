/**
 * Stromhalter (RAD-84): hält einen direkten Live-Strom mit eigenem Vorrat am Laufen.
 *
 * Gemessen (22.11.2026): der Browser hält bei einem Live-Strom im Tonelement nur etwa 2 Sekunden Vorrat und lädt auch
 * beim Warten nicht mehr nach; kurze Lücken auf dem Weg (Mobilfunk, WLAN, Sender) werden so hörbar. Der Stromhalter
 * lädt den Strom deshalb selbst (fetch) und füttert das Tonelement über eine MediaSource:
 *  - Vorlauf: gespielt wird erst, wenn `vorlaufS` Sekunden geladen sind (höchstens `startHoechstensS` warten);
 *  - läuft der Vorrat leer, wartet er still, bis wieder `vorlaufS` Sekunden da sind, statt im Sekundentakt zu stottern;
 *  - reißt die Verbindung ab oder kommt `haengtNachS` Sekunden nichts, verbindet er neu und hängt nahtlos an
 *    (SourceBuffer im Modus "sequence"), während der Vorrat weiterspielt.
 * Geht das nicht (Sender ohne CORS, Format ohne MediaSource-Unterstützung, alter Browser), spielt das Tonelement den
 * Strom wie bisher direkt, und der Stromhalter verbindet bei Abriss neu.
 * Aufgeben meldet er über `beiAufgabe`; Zustände (Vorrat, Neuverbinden) über `beiZustand`.
 */

/** Stellgrößen an einem Ort */
export const STROMHALTER = Object.freeze({
  vorlaufS: 6,            // Vorrat vor dem Start und nach einem Leerlauf
  startHoechstensS: 4,    // so lange wartet der Start höchstens auf den Vorlauf (mit mindestens 1 s Vorrat)
  behaltenS: 30,          // so viel Gespieltes bleibt im Puffer, Älteres wird freigegeben
  haengtNachS: 12,        // ohne neue Daten so lange: Verbindung gilt als abgerissen
  pausenMs: [1000, 2000, 4000, 8000, 15000, 30000], // Wartezeiten der Neuverbindungen; danach gibt er auf
});

/** Inhaltstyp des Stroms auf einen Typ der MediaSource abbilden; null, wenn unbekannt */
export function mediaTyp(inhaltstyp) {
  const t = (inhaltstyp || '').split(';')[0].trim().toLowerCase();
  if (t === 'audio/mpeg' || t === 'audio/mp3' || t === 'audio/mpeg3') return 'audio/mpeg';
  if (t === 'audio/aac' || t === 'audio/aacp' || t === 'audio/x-aac' || t === 'audio/x-aacp') return 'audio/aac';
  return null;
}

function mediaSourceKlasse() {
  return globalThis.ManagedMediaSource || globalThis.MediaSource || null;
}

const warte = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Den Strom `adresse` im Tonelement `ton` spielen und halten.
 * @param {HTMLAudioElement} ton
 * @param {string} adresse
 * @param {{ darfSpielen?: () => boolean, beiAufgabe?: (grund: string) => void, beiZustand?: (z: { weg: 'eigen' | 'direkt', vorratS: number, neuVerbinden: number }) => void }} [rueckrufe]
 * @returns {{ beenden: () => void, weg: () => 'eigen' | 'direkt' | 'start' }}
 */
export function stromHalten(ton, adresse, rueckrufe = {}) {
  let beendet = false;
  let weg = /** @type {'eigen' | 'direkt' | 'start'} */ ('start');
  let abbruch = new AbortController();
  let objektAdresse = null;
  const aufraeumen = [];

  const vorrat = () => {
    const b = ton.buffered;
    for (let i = 0; i < b.length; i++) if (b.end(i) > ton.currentTime && b.start(i) <= ton.currentTime + 0.5) return b.end(i) - ton.currentTime;
    return 0;
  };
  const melden = (neuVerbinden = 0) => rueckrufe.beiZustand?.({ weg: weg === 'eigen' ? 'eigen' : 'direkt', vorratS: vorrat(), neuVerbinden });
  // nie gegen den Willen des Hörers: hat er angehalten, startet der Stromhalter nicht wieder
  const spielen = () => { if (rueckrufe.darfSpielen?.() !== false) ton.play().catch(() => {}); };
  const hoeren = (ziel, name, f) => { ziel.addEventListener(name, f); aufraeumen.push(() => ziel.removeEventListener(name, f)); };

  async function eigenerWeg() {
    const MS = mediaSourceKlasse();
    let antwort;
    try {
      antwort = await fetch(adresse, { signal: abbruch.signal, cache: 'no-store' });
    } catch {
      return false;                                  // ohne CORS oder nicht erreichbar: direkt versuchen
    }
    const typ = mediaTyp(antwort.headers.get('content-type'));
    if (!antwort.ok || !antwort.body || !typ || !MS.isTypeSupported(typ)) {
      abbruch.abort();
      abbruch = new AbortController();
      return false;
    }
    if (beendet) return true;
    weg = 'eigen';
    const quelle = new MS();
    objektAdresse = URL.createObjectURL(quelle);
    if (globalThis.ManagedMediaSource && MS === globalThis.ManagedMediaSource) ton.disableRemotePlayback = true;
    ton.src = objektAdresse;
    await new Promise((r) => quelle.addEventListener('sourceopen', r, { once: true }));
    if (beendet) return true;
    const puffer = quelle.addSourceBuffer(typ);
    puffer.mode = 'sequence';
    void fuettern(quelle, puffer, antwort);
    return true;
  }

  async function fuettern(quelle, puffer, ersteAntwort) {
    const warteschlange = [];
    let gestartet = false, fuellt = false, startZeit = Date.now(), letzteDaten = Date.now();
    const anhaengen = () => {
      if (beendet || puffer.updating || quelle.readyState !== 'open') return;
      // Gespieltes freigeben, damit der Speicher nicht vollläuft
      if (puffer.buffered.length && ton.currentTime - puffer.buffered.start(0) > STROMHALTER.behaltenS * 2) {
        puffer.remove(0, ton.currentTime - STROMHALTER.behaltenS);
        return;
      }
      const stueck = warteschlange.shift();
      if (!stueck) return;
      try {
        puffer.appendBuffer(stueck);
      } catch (e) {
        if (e?.name === 'QuotaExceededError') { warteschlange.unshift(stueck); puffer.remove(0, Math.max(0, ton.currentTime - 5)); }
        else throw e;
      }
    };
    const pruefen = () => {
      const v = vorrat();
      if (!gestartet) {
        const lange = (Date.now() - startZeit) / 1000 >= STROMHALTER.startHoechstensS;
        if (v >= STROMHALTER.vorlaufS || (lange && v >= 1)) { gestartet = true; spielen(); }
      } else if (fuellt && v >= STROMHALTER.vorlaufS) {
        fuellt = false;
        spielen();
      }
      melden();
    };
    hoeren(puffer, 'updateend', () => { anhaengen(); pruefen(); });
    // leergelaufen: still auffüllen statt im Sekundentakt zu stottern
    hoeren(ton, 'waiting', () => {
      if (!gestartet || beendet || ton.paused) return;
      fuellt = true;
      ton.pause();
    });

    let versuch = 0;
    /** liest eine Verbindung, bis sie endet, abreißt oder `haengtNachS` lang nichts kommt */
    const lesen = async (antwort) => {
      const leser = antwort.body.getReader();
      letzteDaten = Date.now();
      const waechter = setInterval(() => {
        if (Date.now() - letzteDaten > STROMHALTER.haengtNachS * 1000) abbruch.abort();
      }, 1000);
      try {
        for (;;) {
          const { done, value } = await leser.read();
          if (done) return;
          letzteDaten = Date.now();
          versuch = 0;
          warteschlange.push(value);
          anhaengen();
        }
      } catch {
        /* abgerissen oder hängend abgebrochen */
      } finally {
        clearInterval(waechter);
      }
    };

    let antwort = ersteAntwort;
    while (!beendet) {
      if (antwort) await lesen(antwort);
      if (beendet) return;
      // neu verbinden, der Vorrat spielt derweil weiter
      const pause = STROMHALTER.pausenMs[versuch];
      if (pause === undefined) { aufgeben('Verbindung zum Sender verloren'); return; }
      versuch++;
      melden(versuch);
      await warte(pause);
      if (beendet) return;
      abbruch = new AbortController();
      antwort = await fetch(adresse, { signal: abbruch.signal, cache: 'no-store' })
        .then((a) => (a.ok && a.body ? a : null))
        .catch(() => null);
    }
  }

  /** Ohne eigenen Puffer: das Tonelement lädt selbst, bei Abriss verbindet der Stromhalter neu */
  function direkterWeg() {
    weg = 'direkt';
    let versuch = 0;
    let haengt = null;
    const verbinden = () => {
      if (beendet) return;
      ton.src = adresse;
      ton.load();
      spielen();
    };
    const abriss = async () => {
      if (beendet) return;
      const pause = STROMHALTER.pausenMs[versuch];
      if (pause === undefined) { aufgeben('Verbindung zum Sender verloren'); return; }
      versuch++;
      melden(versuch);
      await warte(pause);
      verbinden();
    };
    hoeren(ton, 'playing', () => { clearTimeout(haengt); versuch = 0; melden(); });
    // hängt das Tonelement ohne Fehlermeldung, gilt die Verbindung nach `haengtNachS` als abgerissen
    hoeren(ton, 'waiting', () => { clearTimeout(haengt); haengt = setTimeout(() => void abriss(), STROMHALTER.haengtNachS * 1000); });
    aufraeumen.push(() => clearTimeout(haengt));
    hoeren(ton, 'ended', abriss);
    hoeren(ton, 'error', () => { if (ton.error?.code === 2) void abriss(); });
    verbinden();
  }

  function aufgeben(grund) {
    if (beendet) return;
    rueckrufe.beiAufgabe?.(grund);
  }

  // ohne MediaSource und fetch sofort direkt, sonst erst den eigenen Puffer versuchen
  if (!mediaSourceKlasse() || !globalThis.fetch || !globalThis.ReadableStream) direkterWeg();
  else void (async () => {
    if (!(await eigenerWeg()) && !beendet) direkterWeg();
  })();

  return {
    weg: () => weg,
    beenden() {
      beendet = true;
      abbruch.abort();
      for (const f of aufraeumen.splice(0)) f();
      if (objektAdresse) {
        // erst vom Tonelement lösen (load bricht ein laufendes Laden ab), dann die Adresse freigeben (RAD-81)
        if (ton.src === objektAdresse) { ton.removeAttribute('src'); ton.load(); }
        URL.revokeObjectURL(objektAdresse);
        objektAdresse = null;
      }
    },
  };
}
