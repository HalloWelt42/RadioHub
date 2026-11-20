// Bauziel Webversion (RAD-15): Wecker und Ort im Speicher des Browsers, die Sender aus den Favoriten, die Zeitansage
// aus den Bausteinen im Repo (web/daten/zeitansage, beim Bau unter daten/zeitansage der Seite). Die Seite ist
// öffentlich, die Bausteine spricht deshalb eine Katalogstimme der Vertonung (LIESMICH dort).
import { browserSpeicher } from "../../lib/radio/statisch";
import { BrowserWeckerablage, StatischeZeitbausteine } from "../../lib/telefon/weckerablage-browser";
import type { Weckerablage, Zeitbausteine } from "../../lib/telefon/weckerablage";
import { senderquelle } from "./quelle";

const STIMME = "katalog:sohee";

// erst beim Lesen und Schreiben auf localStorage zugreifen (private Fenster), wie bei der Senderquelle
const ablage = { getItem: (k: string) => localStorage.getItem(k), setItem: (k: string, w: string) => localStorage.setItem(k, w) };

export const weckerablage: Weckerablage = new BrowserWeckerablage(browserSpeicher(ablage), senderquelle);
export const zeitbausteine: Zeitbausteine = new StatischeZeitbausteine(`${import.meta.env.BASE_URL}daten/zeitansage/`, STIMME);
