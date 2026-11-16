/**
 * Wiedergabe am Sperrbildschirm (Media Session): Titel, Sender oder Abo, Bild, Wiedergabe und Pause; bei Folgen
 * Spulen, beim Radio voriger und nächster Favorit.
 */
import { api } from '../api.js';

const da = () => typeof navigator !== 'undefined' && 'mediaSession' in navigator;

function bild(src) {
  return src ? [{ src: new URL(src, location.href).href, sizes: '512x512' }] : [];
}

/** Beschreibung der laufenden Wiedergabe aus dem Zustand der App. */
export function beschreibung(appState) {
  const ep = appState.currentEpisode;
  if (ep) {
    return { title: ep.title || '', artist: ep.podcast?.title || ep.podcast_title || '', album: 'RadioHub',
             artwork: bild(ep.image_url || ep.podcast_image_url || ep.podcast?.image_url ? api.getEpisodeImageUrl(ep.id) : null),
             folge: true };
  }
  const s = appState.currentStation;
  if (s) {
    return { title: appState.streamTitle || s.name || '', artist: appState.streamTitle ? s.name : '', album: 'RadioHub',
             artwork: bild(s.favicon ? `/api/favicon/${s.uuid}` : '/icon-512.png'), folge: false };
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
  setzen('seekbackward', b?.folge ? (d) => aktionen.zurueck(d?.seekOffset || 15) : null);
  setzen('seekforward', b?.folge ? (d) => aktionen.vor(d?.seekOffset || 30) : null);
  setzen('seekto', b?.folge ? (d) => aktionen.springen(d.seekTime) : null);
  setzen('previoustrack', b && !b.folge ? aktionen.voriger : null);
  setzen('nexttrack', b && !b.folge ? aktionen.naechster : null);
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
