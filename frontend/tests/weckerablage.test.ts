// Wecker und Zeitansage von Basic (RAD-15): Wecker und Ort im Speicher des Browsers, geprüft wie im Backend, die Sender
// aus den Favoriten der Senderquelle, die Bausteine der Zeitansage aus dem Repo.
import { describe, expect, it } from "vitest";
import { fluechtigerSpeicher } from "../src/lib/radio/statisch";
import type { Senderquelle } from "../src/lib/radio/quelle";
import { alleBausteine, BrowserWeckerablage, SCHLUESSEL_WECKER, StatischeZeitbausteine } from "../src/lib/telefon/weckerablage-browser";
import type { WeckerEntwurf } from "../src/lib/telefon/weckerablage";

const SENDER = { uuid: "u-1", name: "Testwelle", url: "https://welle.test/a", url_resolved: "https://welle.test/b", favicon: "" };

function entwurf(teil: Partial<WeckerEntwurf> = {}): WeckerEntwurf {
  return { aktiv: true, zeit: "06:30", tage: [5, 1, 1], quelle: "sender", sender: SENDER, podcast_id: null, lautstaerke: 60,
           anstieg_s: 60, schlummern_min: 9, weckton: "glocke", ...teil };
}

function quelle(): Senderquelle {
  const eintrag = { uuid: "u-1", name: "Testwelle" };
  return {
    abfragen: async (q: { nur_favoriten?: boolean; anzahl?: number; nach?: string | null }) => {
      if ((q.anzahl ?? 50) > 200) throw new Error("anzahl: 1 bis 200");      // wie die statische Quelle
      if (!q.nur_favoriten) return { gesamt: 0, eintraege: [], weiter: null, facetten: null };
      return q.nach ? { gesamt: 2, eintraege: [{ uuid: "u-2", name: "Zweite" }], weiter: null, facetten: null }
        : { gesamt: 2, eintraege: [eintrag], weiter: "seite-2", facetten: null };
    },
    wiedergabe: async () => ({ ...SENDER, country: "", countrycode: "", tags: "", codec: "", bitrate: 0, homepage: "" }),
  } as unknown as Senderquelle;
}

describe("Wecker im Browser", () => {
  it("legt an, ändert und löscht mit eigener Kennung, geprüft wie das Backend", async () => {
    const speicher = fluechtigerSpeicher();
    let nr = 0;
    const ablage = new BrowserWeckerablage(speicher, quelle(), () => `k-${++nr}`);
    const neu = await ablage.speichern(entwurf());
    expect(neu).toMatchObject({ id: "k-1", tage: [1, 5], weckton: "glocke", quelle: "sender" });
    await ablage.speichern(entwurf({ zeit: "05:00" }));
    expect((await ablage.liste()).map((w) => w.zeit)).toEqual(["05:00", "06:30"]);
    const geaendert = await ablage.speichern({ ...neu, zeit: "07:15", aktiv: false });
    expect(geaendert).toMatchObject({ id: "k-1", zeit: "07:15", aktiv: false });
    expect(JSON.parse(speicher.inhalt.get(SCHLUESSEL_WECKER)!)).toHaveLength(2);
    await ablage.loeschen("k-1");
    expect((await ablage.liste()).map((w) => w.id)).toEqual(["k-2"]);
    await expect(ablage.loeschen("k-1")).rejects.toThrow("nicht gefunden");
  });

  it("lehnt ab, was das Backend ablehnt", async () => {
    const ablage = new BrowserWeckerablage(fluechtigerSpeicher(), quelle());
    await expect(ablage.speichern(entwurf({ zeit: "25:00" }))).rejects.toThrow("HH:MM");
    await expect(ablage.speichern(entwurf({ tage: [0] }))).rejects.toThrow("Wochentage");
    await expect(ablage.speichern(entwurf({ sender: null }))).rejects.toThrow("Sender fehlt");
    await expect(ablage.speichern(entwurf({ quelle: "podcast" }))).rejects.toThrow("Podcast");
    await expect(ablage.speichern(entwurf({ id: "gibts-nicht" }))).rejects.toThrow("nicht gefunden");
    expect(await ablage.liste()).toEqual([]);
  });

  it("hält die Regler in ihren Grenzen", async () => {
    const w = await new BrowserWeckerablage(fluechtigerSpeicher(), quelle()).speichern(entwurf({ lautstaerke: 400, anstieg_s: -3, schlummern_min: 0 }));
    expect([w.lautstaerke, w.anstieg_s, w.schlummern_min]).toEqual([100, 0, 1]);
  });

  it("merkt den Ort, ungültige Breite und Länge fallen weg", async () => {
    const ablage = new BrowserWeckerablage(fluechtigerSpeicher(), quelle());
    expect(await ablage.ort()).toEqual({ name: "", breite: null, laenge: null });
    await ablage.ortSetzen({ name: " Probeort ", breite: 50.9, laenge: 999 });
    expect(await ablage.ort()).toEqual({ name: "Probeort", breite: 50.9, laenge: null });
    expect(ablage.faehig).toEqual({ ortssuche: false, podcast: false });
  });

  it("nimmt alle Favoriten der Senderquelle seitenweise, abspielbar", async () => {
    expect(await new BrowserWeckerablage(fluechtigerSpeicher(), quelle()).sender()).toEqual([SENDER, SENDER]);   // beide Seiten
  });

  it("übersteht einen kaputten Speicher", async () => {
    const ablage = new BrowserWeckerablage(fluechtigerSpeicher({ [SCHLUESSEL_WECKER]: "{kaputt" }), quelle());
    expect(await ablage.liste()).toEqual([]);
  });
});

describe("Bausteine der Zeitansage in Basic", () => {
  it("sind alle 84 wie im Backend und liegen unter der Basis der Seite", async () => {
    const namen = alleBausteine();
    expect(namen).toHaveLength(84);
    expect(namen.slice(0, 2)).toEqual(["es-ist", "stunde-00"]);
    expect(namen.at(-1)).toBe("minute-59");
    expect(namen).not.toContain("minute-00");
    const z = new StatischeZeitbausteine("/RadioHub/daten/zeitansage/", "katalog:sohee");
    expect(await z.stand()).toMatchObject({ stimme: "katalog:sohee", fehlend: [] });
    expect(z.adresse("katalog:sohee", "minute-42")).toBe("/RadioHub/daten/zeitansage/minute-42.mp3");
    expect(z.faehig.erzeugen).toBe(false);
  });
});

describe("Bausteine im Repo", () => {
  it("liegt zu jedem Namen eine MP3 in web/daten/zeitansage und nichts darüber hinaus", async () => {
    const { readdirSync } = await import("node:fs");
    const dateien = readdirSync(new URL("../../web/daten/zeitansage/", import.meta.url)).sort();
    expect(dateien).toEqual(alleBausteine().map((n) => `${n}.mp3`).sort());
  });
});
