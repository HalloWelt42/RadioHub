// Abos sichern und übernehmen (RAD-102, Wahl A): als OPML-Datei, dem üblichen Austauschformat der Podcast-Apps. Eine
// Stelle für Rechner und Telefon, PRO und Basic: sichern schreibt die Abos der Aboliste in eine Datei, übernehmen liest
// eine Datei und abonniert nacheinander, was fehlt. Der Stand des Übernehmens ist sichtbar (lange Vorgänge zeigen, was
// läuft); was sich nicht abonnieren ließ, zählt mit Grund.
import { t } from "../i18n.js";
import type { Aboliste } from "./abos.svelte";
import { feedsAus, opmlAus } from "./opml";

export const DATEINAME = "radiohub-abos.opml";

export interface Uebernahme {
  /** Feeds in der Datei */
  gesamt: number;
  /** davon schon abonniert */
  schonDa: number;
  neu: number;
  /** nicht abonnierbar, mit dem Grund der Quelle */
  fehler: { feed: string; grund: string }[];
}

export class Aboaustausch {
  /** läuft gerade: wie weit (für die Anzeige), sonst null */
  stand = $state<{ fertig: number; von: number } | null>(null);

  constructor(private readonly aboliste: Aboliste, private readonly parser: () => DOMParser = () => new DOMParser()) {}

  /** die Abos als Text einer OPML-Datei */
  text(): string {
    return opmlAus(this.aboliste.abos);
  }

  /** die Datei auf dem Gerät speichern (Herunterladen im Browser) */
  sichern(): void {
    const url = URL.createObjectURL(new Blob([this.text()], { type: "text/x-opml" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: DATEINAME });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10_000);
  }

  /** eine OPML-Datei lesen und abonnieren, was fehlt; nacheinander, damit Quelle und Feed-Server nicht überlaufen */
  async uebernehmen(inhalt: string): Promise<Uebernahme> {
    const feeds = feedsAus(inhalt, this.parser());
    const offen = feeds.filter((f) => !this.aboliste.abonniert(f));
    const ergebnis: Uebernahme = { gesamt: feeds.length, schonDa: feeds.length - offen.length, neu: 0, fehler: [] };
    this.stand = { fertig: 0, von: offen.length };
    try {
      for (const feed of offen) {
        try {
          await this.aboliste.abonnieren(feed);
          ergebnis.neu += 1;
        } catch (f) {
          ergebnis.fehler.push({ feed, grund: (f as Error).message });
        }
        this.stand = { fertig: this.stand.fertig + 1, von: offen.length };
      }
    } finally {
      this.stand = null;
    }
    return ergebnis;
  }
}

/** eine Datei wählen lassen (OPML oder XML) und ihren Text liefern; null ohne Wahl. Muss aus einem Klick heraus kommen. */
export function dateiWaehlen(): Promise<string | null> {
  return new Promise((fertig) => {
    const feld = Object.assign(document.createElement("input"), { type: "file", accept: ".opml,.xml,text/xml,text/x-opml,application/xml" });
    feld.addEventListener("change", () => {
      const datei = feld.files?.[0];
      if (!datei) return fertig(null);
      datei.text().then(fertig, () => fertig(null));
    });
    feld.addEventListener("cancel", () => fertig(null));
    feld.click();
  });
}

/** Text der Meldung nach dem Übernehmen */
export function uebernahmeText(e: Uebernahme): string {
  if (!e.gesamt) return t("podcastAnsicht.austausch.keineFeeds");
  const teile = [t("podcastAnsicht.austausch.neu", { n: e.neu })];
  if (e.schonDa) teile.push(t("podcastAnsicht.austausch.schonDa", { n: e.schonDa }));
  if (e.fehler.length) teile.push(t("podcastAnsicht.austausch.fehler", { n: e.fehler.length }));
  return teile.join(", ");
}
