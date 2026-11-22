// Ausgaben des RadioHub (Nutzer 20.11.2026): PRO ist die volle Version mit Frontend und Backend, Basic die Webversion
// mit Radio und Podcasts im Browser (RAD-102). Die Basic verweist auf den Quellcode der PRO.
export type Ausgabe = "pro" | "basic";

/** Quellcode der PRO (volle Version mit Frontend und Backend) */
export const PRO_QUELLCODE = "https://github.com/HalloWelt42/RadioHub";

/** Spendenseite und Adressen zum Bedanken (Einstellungen > Allgemein > Bedanken, RAD-11) */
export const SPENDENSEITE = "https://ko-fi.com/HalloWelt42";
export interface Spendenadresse { kuerzel: string; symbol: string; adresse: string; bild: string }
export const SPENDENADRESSEN: readonly Spendenadresse[] = [
  { kuerzel: "BTC", symbol: "fa-brands fa-bitcoin", adresse: "bc1qnd599khdkv3v3npmj9ufxzf6h4fzanny2acwqr", bild: "images/btc-qr.svg" },
  { kuerzel: "DOGE", symbol: "fa-solid fa-dog", adresse: "DL7tuiYCqm3xQjMDXChdxeQxqUGMACn1ZV", bild: "images/doge-qr.svg" },
  { kuerzel: "ETH", symbol: "fa-brands fa-ethereum", adresse: "0x8A28fc47bFFFA03C8f685fa0836E2dBe1CA14F27", bild: "images/eth-qr.svg" },
];
