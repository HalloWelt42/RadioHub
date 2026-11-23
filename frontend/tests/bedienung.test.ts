// Bedienung der Radio-Liste (RAD-41): eine Variante, gespielt aus der aufgeklappten Zeile eines anderen Senders, steht
// für diese Zeile (Fokus und Vor/Zurück), nicht für ihre eigene, die weit weg in der Liste stehen kann.
import { describe, expect, it, vi } from "vitest";

const gespielt: string[] = [];
vi.mock("../src/lib/store.svelte.js", () => ({
  appState: { currentStation: null },
  actions: { playStationFromList: async (w: { uuid: string }) => { gespielt.push(w.uuid); }, showToast: () => {} },
}));
import { Radiobedienung } from "../src/lib/radio/bedienung.svelte";
import type { Senderquelle } from "../src/lib/radio/quelle";
import type { SenderEintrag } from "../src/lib/radio/typen";

const quelle = { faehig: { messen: false }, wiedergabe: async (e: SenderEintrag) => ({ uuid: e.uuid, url: "https://ton.test" }) } as unknown as Senderquelle;
const sender = (uuid: string) => ({ uuid }) as SenderEintrag;

describe("Zeile des laufenden Senders", () => {
  it("Variante aus einer Zeile gehört zu dieser Zeile", async () => {
    const b = new Radiobedienung(quelle);
    await b.spielen(sender("bfm"), sender("rmc-fr"));
    expect(gespielt.at(-1)).toBe("bfm");
    expect(b.zeileFuer("bfm")).toBe("rmc-fr");
  });
  it("ein Sender aus seiner eigenen Zeile und jeder spätere Wechsel stehen für sich", async () => {
    const b = new Radiobedienung(quelle);
    await b.spielen(sender("bfm"), sender("rmc-fr"));
    await b.spielen(sender("walm"));
    expect(b.zeileFuer("walm")).toBe("walm");
    expect(b.zeileFuer("bfm")).toBe("bfm");
    await b.spielen(sender("rmc-fr"), sender("rmc-fr"));
    expect(b.zeileFuer("rmc-fr")).toBe("rmc-fr");
    expect(b.zeileFuer(null)).toBeNull();
  });
});

describe("Nachbar des laufenden Senders (RAD-124)", () => {
  /** Verzeichnis mit n Sendern s0, s1, ... in Seiten zu 50 */
  function verzeichnis(n: number) {
    let alle = Array.from({ length: n }, (_, i) => ({ uuid: `s${i}`, name: `s${i}`, ausnahme: [], genres: [] }) as unknown as SenderEintrag);
    const nummer = (e: SenderEintrag) => Number(e.uuid.slice(1));
    // der Zeiger ist wie in beiden Quellen ein Schlüssel (der letzte der Seite), keine Nummer: Ausgeblendete verschieben nichts
    const abfragen = vi.fn(async (q: { anzahl: number; nach: string | null }) => {
      const rest = q.nach === null ? alle : alle.filter((e) => nummer(e) > Number(q.nach));
      const eintraege = rest.slice(0, q.anzahl);
      return { eintraege, gesamt: n, facetten: null, weiter: rest.length > q.anzahl ? String(nummer(eintraege.at(-1)!)) : null };
    });
    const sperren = async (uuid: string) => { alle = alle.filter((e) => e.uuid !== uuid); return { sichtbar: false, gruende: [] }; };
    return { ...quelle, abfragen, sperren } as unknown as Senderquelle & { abfragen: typeof abfragen };
  }
  async function bereit(n: number, laeuft: string, seiten = 1) {
    const q = verzeichnis(n);
    const b = new Radiobedienung(q);
    await b.laden({});
    for (let i = 1; i < seiten; i++) await b.liste.mehr();
    b.nachbarnVorbereiten(laeuft);
    return { b, q };
  }
  const name = async (p: Promise<{ uuid: string } | null>) => (await p)?.uuid ?? null;

  it("mitten in der Liste", async () => {
    const { b } = await bereit(120, "s4");
    expect([await name(b.nachbar("s4", 1)), await name(b.nachbar("s4", -1))]).toEqual(["s5", "s3"]);
  });
  it("am Ende der geladenen Seite geht es weiter, nicht von vorn", async () => {
    const { b } = await bereit(120, "s10");
    expect(await name(b.nachbar("s49", 1))).toBe("s50");
  });
  it("rundum erst am wirklichen Ende", async () => {
    const { b } = await bereit(60, "s59", 2);
    expect([await name(b.nachbar("s59", 1)), await name(b.nachbar("s0", -1))]).toEqual(["s0", "s59"]);
  });
  it("nach einem Wechsel des Bereichs beginnt die Liste wieder bei der ersten Seite: die Stelle gilt weiter", async () => {
    const { b } = await bereit(200, "s120", 3);
    await b.laden({});
    expect(b.liste.eintraege).toHaveLength(50);
    expect(await name(b.nachbar("s120", 1))).toBe("s121");
  });
  it("ausgeblendet: der nächste rückt an seine Stelle, auch der letzte der Seite und während des Nachladens", async () => {
    const { b } = await bereit(120, "s4");
    await b.ausblenden(b.liste.eintraege[4]);
    expect([await name(b.nachbar("s4", 1)), await name(b.nachbar("s4", -1))]).toEqual(["s5", "s3"]);
    const { b: c } = await bereit(120, "s30");
    c.nachbarnVorbereiten("s49");
    const ziel = c.nachbar("s49", 1);
    await c.ausblenden(c.liste.eintraege.find((e) => e.uuid === "s49")!);
    expect(await name(ziel)).toBe("s50");
  });
  it("alle der Reihe nach ausblenden führt durch das ganze Verzeichnis", async () => {
    const { b } = await bereit(130, "s0");
    let jetzt = "s0";
    for (let i = 1; i < 130; i++) {
      const e = b.eintragVon(jetzt)!;
      const [ziel] = await Promise.all([b.nachbar(jetzt, 1), b.ausblenden(e)]);
      expect(ziel?.uuid).toBe(`s${i}`);
      jetzt = ziel!.uuid;
      b.nachbarnVorbereiten(jetzt);
    }
  });
  it("eine Variante zählt als ihre Zeile", async () => {
    const { b } = await bereit(120, "s7");
    await b.spielen(sender("variante"), b.liste.eintraege[7]);
    expect(await name(b.nachbar("variante", 1))).toBe("s8");
  });
  it("unbekannter Sender: Vor beginnt beim ersten, Zurück bleibt", async () => {
    const { b } = await bereit(120, "s0");
    expect([await name(b.nachbar("fremd", 1)), await name(b.nachbar("fremd", -1))]).toEqual(["s0", null]);
  });
});
