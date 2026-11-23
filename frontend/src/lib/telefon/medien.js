/**
 * Wiedergabe am Sperrbildschirm (Media Session): Titel, Sender oder Abo, Bild, Wiedergabe und Pause; bei Folgen
 * Spulen, beim Radio voriger und nächster Favorit, bei Aufnahmen Spulen und voriger
 * und nächster Titel (RAD-134).
 */
import { folgenBild } from '../playerEngine.js';
import { senderquelle } from '$ziel/quelle';

/** App-Symbol als Ersatz am Sperrbildschirm, unter dem Pfad der Seite (Basic liegt unter /RadioHub/, RAD-90) */
const APPBILD = `${import.meta.env.BASE_URL}icon-512.png`;

const da = () => typeof navigator !== 'undefined' && 'mediaSession' in navigator;

function bild(src) {
  return src ? [{ src: new URL(src, location.href).href, sizes: '512x512' }] : [];
}

/** Beschreibung der laufenden Wiedergabe aus dem Zustand der App. `bild` ist das eigene Bild der Quelle (Logo des Senders
 *  über die Senderquelle, in Basic keins; Bild der Folge) oder null, `artwork` dasselbe für den Sperrbildschirm, ohne
 *  eigenes Bild das App-Symbol. */
export function beschreibung(appState) {
  const ep = appState.currentEpisode;
  if (ep) {
    const eigenes = folgenBild(ep);
    return { title: ep.title || '', artist: ep.podcast?.title || ep.podcast_title || '', album: 'RadioHub',
             bild: eigenes, artwork: bild(eigenes ?? APPBILD), folge: true, spulbar: true, reihe: false };
  }
  const a = appState.currentRecording;
  if (a) {
    const logo = a.station_uuid ? senderquelle.logoAdresse(a.station_uuid, '') : null;
    return { title: a.name || a.station_name || '', artist: a.name === a.station_name ? '' : a.station_name || '', album: 'RadioHub',
             bild: logo, artwork: bild(logo ?? APPBILD), folge: false, spulbar: true, reihe: true };
  }
  const s = appState.currentStation;
  if (s) {
    const logo = senderquelle.logoAdresse(s.uuid, s.favicon || '');
    return { title: appState.streamTitle || s.name || '', artist: appState.streamTitle ? s.name : '', album: 'RadioHub',
             bild: logo, artwork: bild(logo ?? APPBILD), folge: false, spulbar: false, reihe: true };
  }
  return null;
}

/** Metadaten und Zustand setzen; `aktionen` = { abspielen, pause, zurueck(s), vor(s), springen(t), voriger, naechster } */
export function aktualisieren(appState, aktionen) {
  if (!da()) return;
  const b = beschreibung(appState);
  const ms = navigator.mediaSession;
  ms.metadata = b ? new MediaMetadata({ title: b.title, artist: b.artist, album: b.album, artwork: b.artwork }) : null;
  ms.playbackState = !b ? 'none' : (appState.isPlaying && !appState.isPaused ? 'playing' : 'paused');
  const setzen = (name, fn) => { try { ms.setActionHandler(name, fn); } catch { /* nicht unterstützt */ } };
  setzen('play', aktionen.abspielen);
  setzen('pause', aktionen.pause);
  setzen('seekbackward', b?.spulbar && !b.reihe ? (d) => aktionen.zurueck(d?.seekOffset || 15) : null);
  setzen('seekforward', b?.spulbar && !b.reihe ? (d) => aktionen.vor(d?.seekOffset || 30) : null);
  setzen('seekto', b?.spulbar ? (d) => aktionen.springen(d.seekTime) : null);
  setzen('previoustrack', b?.reihe ? aktionen.voriger : null);
  setzen('nexttrack', b?.reihe ? aktionen.naechster : null);
}

/** Position für die Leiste am Sperrbildschirm (nur bei Folgen mit bekannter Dauer). */
export function position(dauer, zeit, rate = 1) {
  if (!da() || !navigator.mediaSession.setPositionState) return;
  try {
    if (dauer > 0 && Number.isFinite(dauer)) {
      navigator.mediaSession.setPositionState({ duration: dauer, position: Math.min(zeit, dauer), playbackRate: rate });
    }
  } catch { /* ungültige Werte während des Ladens */ }
}
