// Weg der Wiedergabe (RAD-4): woher der Strom eines Senders kommt und was dazugehört. Die Engine kennt nur diese
// Schnittstelle; die volle App spielt über das Backend (Durchleiter, Zeitversatz, Aufnahme, letzter Sender in der
// Konfiguration), die Webversion direkt im Browser (nur https-Ströme, ohne Zeitversatz und Aufnahme, letzter Sender im
// Browser). Die Kanzel zeigt nur, was der Weg kann.
import { api } from './api.js';

/**
 * @typedef {object} Wiedergabeweg
 * @property {boolean} zeitversatz  Zeitversatz über den Puffer im Backend (Original oder Zeitversatz, Spulen, Bitrate)
 * @property {boolean} aufnahme     Aufnahme eines Senders
 * @property {boolean} folgen       Folgen und Aufnahmen abspielen (Position, Spulen, Reihenfolge)
 * @property {boolean} uebergabe    Übergabe zwischen Geräten (Vermittler im Backend, RAD-18)
 * @property {(station: { uuid: string, url?: string, url_resolved?: string }) => string} stromAdresse
 * @property {(station: { uuid: string, name: string }) => void} merken  letzten Sender merken
 * @property {Folgenweg | null} folge  woher Folgen kommen und wohin Stelle und gehört gehen (nur mit `folgen`)
 */

/**
 * Folgen eines Podcasts (RAD-102): die volle App über das Backend (gespeichert, Durchleiter, Puffer), die Webversion
 * direkt vom Server der Folge mit Stelle und gehört im Browser (ziel/web/podcasts.ts).
 * @typedef {object} Folgenweg
 * @property {boolean} puffern  nicht gespeicherte Folgen über den Puffer des Backends spielen (HLS)
 * @property {(folge: object) => string} adresse  Adresse der Datei zum Abspielen
 * @property {(folge: object) => string | null} bild  Bild der Folge (Sperrbildschirm), null ohne
 * @property {(id: number, sekunden: number) => void} stelleMerken
 * @property {(id: number) => void} gehoert  zu Ende gehört (Stelle zurück auf den Anfang)
 */

/** @type {Wiedergabeweg} */
export const ueberBackend = {
  zeitversatz: true,
  uebergabe: true,
  aufnahme: true,
  folgen: true,
  stromAdresse: (station) => api.getStationStreamUrl(station.uuid),
  merken: (station) => {
    api.updateConfig({ last_station_uuid: station.uuid, last_station_name: station.name }).catch(() => {});
  },
  folge: {
    puffern: true,
    adresse: (folge) => (folge.fassung || folge.is_downloaded ? api.getEpisodePlayUrl(folge.id, folge.fassung) : api.getEpisodeStreamUrl(folge.id)),
    bild: (folge) => (folge.image_url || folge.podcast_image_url || folge.podcast?.image_url ? api.getEpisodeImageUrl(folge.id) : null),
    stelleMerken: (id, sekunden) => { api.updateEpisodePosition(id, sekunden).catch(() => {}); },
    gehoert: (id) => {
      api.markEpisodePlayed(id).catch(() => {});
      api.updateEpisodePosition(id, 0).catch(() => {});
    },
  },
};

const LETZTER_SENDER = 'radiohub.web.letzter_sender';   // wie die eigenen Angaben der Webversion (radiohub.web.*)

/** @type {Wiedergabeweg} */
export const direkt = {
  zeitversatz: false,
  uebergabe: false,
  aufnahme: false,
  folgen: false,
  stromAdresse: (station) => station.url_resolved || station.url || '',
  merken: (station) => {
    try {
      localStorage.setItem(LETZTER_SENDER, JSON.stringify({ uuid: station.uuid, name: station.name }));
    } catch {
      /* ohne Speicher im Browser bleibt nur der Sender dieser Sitzung */
    }
  },
  // Folgen setzt das Bauziel dazu (ziel/web/wurzel.ts), sobald es eine Podcastquelle hat
  folge: null,
};
