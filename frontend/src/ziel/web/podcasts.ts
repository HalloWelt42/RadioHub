// Bauziel Webversion (RAD-102): Podcasts ganz im Browser. Gesucht wird direkt in den Verzeichnissen, die Feeds liest der
// Browser selbst, Abos und Stellen liegen im Speicher des Browsers; ohne Werbeerkennung. Der Folgenweg sagt der
// Wiedergabe, woher eine Folge kommt und wohin Stelle und gehört gehen.
import { t } from "../../lib/i18n.js";
import { BrowserPodcastquelle } from "../../lib/podcasts/browser/browser-quelle";
import { OhneWerbequelle, type Werbequelle } from "../../lib/podcasts/werbung";
import type { Podcastquelle } from "../../lib/podcasts/quelle";
import { browserSpeicher } from "../../lib/radio/statisch";

/** dieselben Verzeichnisse wie die volle App (Vorgaben in backend/app/einstellungen.py) */
const VERZEICHNIS = { weltweit: "https://itunes.apple.com/search", deutsch: "https://api.fyyd.de/0.2/search/podcast" };

// erst beim Lesen und Schreiben auf localStorage zugreifen (private Fenster), wie bei der Senderquelle
const ablage = { getItem: (k: string) => localStorage.getItem(k), setItem: (k: string, w: string) => localStorage.setItem(k, w) };

const quelle = new BrowserPodcastquelle({ speicher: browserSpeicher(ablage), verzeichnis: VERZEICHNIS,
                                          hinweis: (p) => t(`podcastAnsicht.feed_${p.art}`, { detail: p.detail }) });

export const podcastquelle: Podcastquelle = quelle;
export const werbequelle: Werbequelle = new OhneWerbequelle();

/** Folgen der Webversion direkt von ihrem Server, Stelle und gehört in den Speicher des Browsers (Folgenweg in lib/wiedergabeweg.js) */
export const folgenweg = {
  puffern: false,
  adresse: (folge: { remote_audio_url?: string }) => folge.remote_audio_url ?? "",
  bild: (folge: { image_url?: string; podcast?: { image_url?: string } }) => folge.image_url || folge.podcast?.image_url || null,
  stelleMerken: (id: number, sekunden: number) => void quelle.stelleMerken(id, sekunden).catch(() => {}),
  gehoert: (id: number) => void quelle.gehoert(id, true).catch(() => {}),
};
