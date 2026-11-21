// Bedienung der Radio-Liste (RAD-41): eine Variante, gespielt aus der aufgeklappten Zeile eines anderen Senders, steht
// für diese Zeile (Fokus und Vor/Zurück), nicht für ihre eigene, die weit weg in der Liste stehen kann.
import { describe, expect, it, vi } from "vitest";

const gespielt: string[] = [];
vi.mock("../src/lib/store.svelte.js", () => ({
  appState: { currentStation: null },
  actions: { playStation: async (w: { uuid: string }) => { gespielt.push(w.uuid); }, showToast: () => {} },
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
