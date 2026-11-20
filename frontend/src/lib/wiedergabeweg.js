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
 * @property {(station: { uuid: string, url?: string, url_resolved?: string }) => string} stromAdresse
 * @property {(station: { uuid: string, name: string }) => void} merken  letzten Sender merken
 */

/** @type {Wiedergabeweg} */
export const ueberBackend = {
  zeitversatz: true,
  aufnahme: true,
  folgen: true,
  stromAdresse: (station) => api.getStationStreamUrl(station.uuid),
  merken: (station) => {
    api.updateConfig({ last_station_uuid: station.uuid, last_station_name: station.name }).catch(() => {});
  },
};

const LETZTER_SENDER = 'radiohub.web.letzter_sender';   // wie die eigenen Angaben der Webversion (radiohub.web.*)

/** @type {Wiedergabeweg} */
export const direkt = {
  zeitversatz: false,
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
};
