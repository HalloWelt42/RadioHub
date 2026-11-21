// Aufnahmen und Schnitt (RAD-17): Abbildung der Rohdaten, Adresse hin und zurück, Liste seitenweise ohne verspätete
// Antworten, Arbeitsplatz des Schnitts (Marker, Stücke, Behalten, Ausschnitt) und der Fortschrittsstrom.
import { describe, expect, it } from "vitest";
import { aufnahmeAus, titelAus } from "../src/lib/aufnahmen/backend";
import { Aufnahmeliste, ausAdresse, leer, zuAdresse } from "../src/lib/aufnahmen/zustand.svelte";
import type { Aufnahmequelle } from "../src/lib/aufnahmen/quelle";
import type { Aufnahme } from "../src/lib/aufnahmen/typen";
import { Arbeitsplatz } from "../src/lib/schnitt/arbeitsplatz.svelte";
import { strom, type Schnittinfo } from "../src/lib/schnitt/quelle";

describe("Rohdaten", () => {
  it("Sitzung und Stück", () => {
    const a = aufnahmeAus({ id: "rec_1", station_name: "Jazzkeller", start_time: "2026-11-21T20:14:03", duration: 1537.2, file_size: 50_000_000,
      codec: "aac", bitrate: 256, rec_type: "hls-rec", folder_id: 3, segment_count: 7, status: "stalled", quality_json: '{"gaps": 2}' });
    expect(a).toMatchObject({ id: "rec_1", codec: "AAC", art: "puffer", ordnerId: 3, titelzahl: 7, status: "abgebrochen", luecken: 2 });
    expect(titelAus({ id: 9, segment_index: 1, title: "Blaue Stunde", start_ms: 42000, duration_ms: 412000, file_size: 1, file_path: "A/b.mp3" }))
      .toEqual({ id: 9, nr: 2, titel: "Blaue Stunde", start: 42, dauer: 412, groesse: 1, pfad: "A/b.mp3" });
  });
});

describe("Adresse", () => {
  it("hin und zurück, frühere Adressen fallen auf die Liste", () => {
    const faelle = [
      { ...leer() },
      { ...leer(), aufnahme: "rec_1", ordner: "3", suche: "Jazz" },
      { ...leer(), aufnahme: "rec_1", schnitt: true },
      { ...leer(), sort: "sender" as const, absteigend: false },
      { ...leer(), sort: "dauer" as const, absteigend: false },
      { ...leer(), quelle: "wolke" as const, pfad: "Interviews/2025" },
      { ...leer(), quelle: "wolke" as const, schnitt: true, pfad: "Interviews/Gespräch 1.mp3" },
    ];
    for (const a of faelle) {
      const adresse = zuAdresse(a);
      const [pfad, abfrage = ""] = adresse.split("?");
      expect(ausAdresse(pfad, abfrage)).toEqual(a);
    }
    expect(zuAdresse({ ...leer(), sort: "sender", absteigend: false })).toBe("/aufnahmen?sort=sender");
    expect(ausAdresse("/aufnahmen/cutter", "")).toEqual(leer());
    expect(ausAdresse("/aufnahmen/search/Jazz", "").suche).toBe("Jazz");
  });
});

function quelle(alle: Aufnahme[], verzoegert: Record<string, Promise<void>> = {}): Aufnahmequelle {
  return {
    async aufnahmen(a, ab, anzahl) {
      await verzoegert[a.suche];
      const treffer = alle.filter((x) => x.sender.includes(a.suche));
      return { aufnahmen: treffer.slice(ab, ab + anzahl), gesamt: treffer.length };
    },
  } as Aufnahmequelle;
}

describe("Liste", () => {
  const alle = Array.from({ length: 5 }, (_, i) => aufnahmeAus({ id: `s${i}`, station_name: i < 3 ? "Nord" : "Süd" }));
  it("seitenweise und nachladen", async () => {
    const l = new Aufnahmeliste(quelle(alle), 2);
    await l.laden({ suche: "", ordner: "", sort: "datum", absteigend: true });
    expect([l.aufnahmen.length, l.gesamt, l.mehr]).toEqual([2, 5, true]);
    await l.nachladen();
    await l.nachladen();
    expect([l.aufnahmen.map((a) => a.id), l.mehr]).toEqual([["s0", "s1", "s2", "s3", "s4"], false]);
    l.entfernen("s1");
    expect([l.aufnahmen.length, l.gesamt]).toEqual([4, 4]);
  });
  it("eine verspätete Antwort ändert nichts", async () => {
    let los!: () => void;
    const spaet = new Promise<void>((r) => (los = r));
    const l = new Aufnahmeliste(quelle(alle, { Nord: spaet }), 10);
    const erste = l.laden({ suche: "Nord", ordner: "", sort: "datum", absteigend: true });
    await l.laden({ suche: "Süd", ordner: "", sort: "datum", absteigend: true });
    los();
    await erste;
    expect(l.aufnahmen.map((a) => a.sender)).toEqual(["Süd", "Süd"]);
  });
});

const info = (stuecke: Schnittinfo["stuecke"], dauer = 100): Schnittinfo => ({
  art: "sitzung", kennung: "s", titel: "T", zeit: null, format: "MP3", bitrate: 128, dauer, stuecke, titelwechsel: [], ziel: "", schritte: [], werbestellen: [],
});

describe("Arbeitsplatz", () => {
  it("bisherige Stücke werden Marker und Namen; behalten, verwerfen, benennen", () => {
    const p = new Arbeitsplatz();
    p.uebernehmen(info([{ von: 0, bis: 40, name: "Ansage" }, { von: 40, bis: 100, name: "Lied" }]));
    expect(p.marker).toEqual([40]);
    expect(p.stuecke.map((s) => [s.name, s.behalten])).toEqual([["Ansage", true], ["Lied", true]]);
    p.markerSetzen(70.04);
    p.markerSetzen(70);                     // derselbe Marker
    p.markerSetzen(0);                      // nicht am Rand
    expect(p.marker).toEqual([40, 70]);
    expect(p.stuecke.map((s) => s.name)).toEqual(["Ansage", "Lied", "Lied"]);
    p.umschalten(p.stuecke[0]);
    p.benennen(p.stuecke[2], "Schluss");
    expect(p.wahl()).toEqual([
      { von: 0, bis: 40, name: "Ansage", behalten: false }, { von: 40, bis: 70, name: "Lied", behalten: true },
      { von: 70, bis: 100, name: "Schluss", behalten: true }]);
    expect(p.behalten).toBe(2);
    p.markerVerschieben(0, 30);
    expect(p.marker).toEqual([30, 70]);
    p.ausTitelwechseln([{ start: 0, titel: "A" }, { start: 55, titel: "B" }]);
    expect([p.marker, p.stuecke.map((s) => s.name)]).toEqual([[55], ["A", "B"]]);
    p.leeren();
    expect(p.stuecke.length).toBe(1);
  });
  it("Werbestellen der Aufnahme werden Stücke der Art Werbung, fallen beim Schneiden weg, Irrtum ausschaltbar", () => {
    const p = new Arbeitsplatz();
    p.uebernehmen(info([{ von: 0, bis: 82.38, name: "Michael Jackson" }, { von: 82.38, bis: 148, name: "OLDIE ANTENNE" }], 148));
    p.markerSetzen(90);                     // liegt mitten in der Werbung: fällt weg
    p.werbestellenUebernehmen([{ von: 82.38, bis: 102.5, text: "adac.de" }, { von: 102.5, bis: 121, text: "vodafone.de" }],
                              (w) => `Werbung: ${w.text}`);
    expect(p.marker).toEqual([82.4, 102.5, 121]);
    expect(p.stuecke.map((s) => [s.name, s.werbung, s.behalten])).toEqual([
      ["Michael Jackson", false, true], ["Werbung: adac.de", true, false], ["Werbung: vodafone.de", true, false], ["OLDIE ANTENNE", false, true]]);
    expect(p.wahl().filter((s) => s.behalten).map((s) => [s.von, s.bis])).toEqual([[0, 82.4], [121, 148]]);
    p.umschalten(p.stuecke[2]);             // keine Werbung: ein gewöhnliches Stück, behalten
    expect([p.stuecke[2].werbung, p.stuecke[2].behalten, p.behalten]).toEqual([false, true, 3]);
    p.leeren();
    expect(p.stuecke.map((s) => s.werbung)).toEqual([false]);
  });
  it("Ausschnitt: zoomen um die Mitte, Grenzen, mitlaufen bei 70 Prozent", () => {
    const p = new Arbeitsplatz();
    p.uebernehmen(info([{ von: 0, bis: 100, name: "x" }], 100));
    p.zoomen(0.5);
    expect([p.von, p.bis]).toEqual([25, 75]);
    p.zoomen(0.01);
    expect(p.bis - p.von).toBe(5);
    p.zoomen(1000);
    expect([p.von, p.bis]).toEqual([0, 100]);
    p.zoomen(0.2, 95);
    expect([p.von, p.bis]).toEqual([80, 100]);
    p.alles();
    p.zoomen(0.1, 10);
    p.zeigen(9);
    expect([p.von, p.bis]).toEqual([5, 15]);
    p.zeigen(13);
    expect(p.von).toBeCloseTo(6, 5);
  });
});

describe("Fortschrittsstrom", () => {
  const antwort = (text: string, status = 200) => new Response(text, { status, headers: { "content-type": "text/event-stream" } });
  it("meldet, liefert die Zahl, wirft mit der Meldung des Servers", async () => {
    const gemeldet: string[] = [];
    const n = await strom(antwort('data: {"type":"start"}\n\ndata: {"type":"progress","step":1,"total":2,"message":"Schneiden"}\n\ndata: {"type":"done","count":3}\n\n'),
      (f) => gemeldet.push(`${f.schritt}/${f.gesamt} ${f.text}`));
    expect([n, gemeldet]).toEqual([3, ["1/2 Schneiden"]]);
    await expect(strom(antwort('data: {"type":"error","message":"Die Aufnahme läuft noch"}\n\n'), () => {})).rejects.toThrow("Die Aufnahme läuft noch");
    await expect(strom(new Response(JSON.stringify({ detail: "Kein Stück" }), { status: 422 }), () => {})).rejects.toThrow("Kein Stück");
  });
});
