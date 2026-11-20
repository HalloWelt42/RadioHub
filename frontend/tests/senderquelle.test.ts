// RAD-7: Senderquelle gegen eine nachgestellte Schnittstelle des Backends. Geprüft wird, dass die Umsetzung die Wege der
// Schnittstelle richtig anspricht (Methode, Weg, Inhalt, Sitzung), Fehler weiterreicht, und dass Liste und Regel-Ablauf
// nur über die Schnittstelle Senderquelle arbeiten (wie später die Webversion).
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BackendQuelle } from "../src/lib/radio/backend";
import { netz, Netzfehler } from "../src/lib/radio/netz";
import type { Senderquelle } from "../src/lib/radio/quelle";
import { Regelablauf } from "../src/lib/radio/regelablauf.svelte";
import { Senderliste } from "../src/lib/radio/senderliste.svelte";
import type { Abfrageergebnis, RegelVorschau, SenderEintrag, StationQuery } from "../src/lib/radio/typen";
import { sitzungVerbinden } from "../src/lib/sitzung";

function eintrag(uuid: string, teil: Partial<SenderEintrag> = {}): SenderEintrag {
  return {
    uuid, name: `Sender ${uuid}`, logo: "", homepage: "", land: "DE", land_name: "Germany", region: "", bundesland: "",
    sprachen: [], genres: [], codec: "MP3", kbps: 128, kbps_gemessen: false, qualitaet: "mittel", stimmen: 1, erreichbar: true,
    hls: false, gruppe: uuid, varianten: 1, favorit: false, ausnahme: [], verschwunden: false, kategorien: [], bewertungen: [],
    werbung: { stufe: "keine", entscheidung: null }, eigene_adresse: null, adresse: "", adresse_aufgeloest: "", ...teil,
  };
}

interface Aufruf { weg: string; methode: string; daten: unknown; kopf: Record<string, string> }

/** Nachgestelltes Backend: Antworten je "METHODE weg", jeder Aufruf wird mitgeschrieben */
function backend(antworten: Record<string, unknown | ((daten: unknown) => unknown)>) {
  const aufrufe: Aufruf[] = [];
  const abruf = async (weg: string, init: RequestInit) => {
    const methode = init.method ?? "GET";
    const daten = init.body ? JSON.parse(String(init.body)) : undefined;
    aufrufe.push({ weg, methode, daten, kopf: init.headers as Record<string, string> });
    const schluessel = `${methode} ${weg}`;
    if (!(schluessel in antworten)) return new Response(JSON.stringify({ detail: "nicht da" }), { status: 404 });
    const a = antworten[schluessel];
    const inhalt = typeof a === "function" ? (a as (d: unknown) => unknown)(daten) : a;
    if (inhalt instanceof Response) return inhalt;
    return new Response(JSON.stringify(inhalt ?? null), { status: 200, headers: { "Content-Type": "application/json" } });
  };
  return { aufrufe, quelle: new BackendQuelle({ anfrage: netz(abruf), messenNachMs: 0 }) };
}

beforeEach(() => sitzungVerbinden({ token: () => "sitzung-test", abgewiesen: () => {} }));

describe("BackendQuelle", () => {
  it("fragt die Liste mit der Sitzung über /api/radio/abfrage ab", async () => {
    const { aufrufe, quelle } = backend({ "POST /api/radio/abfrage": { gesamt: 1, eintraege: [eintrag("a")], weiter: null, facetten: null } });
    const r = await quelle.abfragen({ laender: ["DE"], nur_favoriten: true });
    expect(r.gesamt).toBe(1);
    expect(aufrufe[0]).toMatchObject({ methode: "POST", weg: "/api/radio/abfrage", daten: { laender: ["DE"], nur_favoriten: true } });
    expect(aufrufe[0].kopf["X-Kellerwolke-Sitzung"]).toBe("sitzung-test");
  });

  it("entfernt eine Regel nur bestätigt und reicht Fehler mit dem Text des Servers weiter", async () => {
    const { aufrufe, quelle } = backend({
      "DELETE /api/radio/regeln/r1?bestaetigt=true": { regel: null, bestand: {}, ausgeblendet: 0, wieder_sichtbar: 5 },
      "PATCH /api/radio/regeln/r2": new Response(JSON.stringify({ detail: "Regel unbekannt" }), { status: 404 }),
    });
    expect((await quelle.entfernen("r1")).wieder_sichtbar).toBe(5);
    await expect(quelle.schalten("r2", false)).rejects.toThrowError(new Netzfehler(404, "Regel unbekannt"));
    expect(aufrufe[1]).toMatchObject({ methode: "PATCH", daten: { an: false } });
  });

  it("sperrt und entsperrt über die Kennung, Freigaben ebenso", async () => {
    const sicht = { uuid: "a", sichtbar: false, verschwunden: false, favorit: false, freigegeben: false, gesperrt: true, gruende: [] };
    const { aufrufe, quelle } = backend({
      "POST /api/radio/sperren": sicht, "DELETE /api/radio/sperren/a": { ...sicht, sichtbar: true, gesperrt: false },
      "POST /api/radio/freigaben": sicht, "DELETE /api/radio/freigaben/a": sicht,
    });
    expect((await quelle.sperren("a")).gesperrt).toBe(true);
    expect((await quelle.entsperren("a")).sichtbar).toBe(true);
    await quelle.freigeben("a");
    await quelle.freigabeZuruecknehmen("a");
    expect(aufrufe.map((x) => `${x.methode} ${x.weg}`)).toEqual([
      "POST /api/radio/sperren", "DELETE /api/radio/sperren/a", "POST /api/radio/freigaben", "DELETE /api/radio/freigaben/a"]);
    expect(aufrufe[0].daten).toEqual({ uuid: "a" });
  });

  it("holt die Felder der Wiedergabe einmal; die eigene Adresse gilt vor der des Verzeichnisses", async () => {
    const { aufrufe, quelle } = backend({ "GET /api/stations/a": { name: "A", url: "http://a/u", url_resolved: "http://a/r", favicon: "f" } });
    const e = eintrag("a", { eigene_adresse: "https://eigen/strom" });
    const w = await quelle.wiedergabe(e);
    expect(w).toMatchObject({ uuid: "a", url: "http://a/u", url_resolved: "https://eigen/strom", bitrate: 128 });
    await quelle.wiedergabe(e);
    expect(aufrufe).toHaveLength(1);
  });

  it("ein Eintrag mit Adresse spielt ohne weitere Abfrage, die eigene Adresse vorn (Vor und Zurück über die Liste)", async () => {
    const { aufrufe, quelle } = backend({});
    const w = await quelle.wiedergabe(eintrag("b", { adresse: "http://b/u", adresse_aufgeloest: "http://b/r" }));
    expect(w).toMatchObject({ uuid: "b", url: "http://b/u", url_resolved: "http://b/r" });
    const eigen = await quelle.wiedergabe(eintrag("c", { adresse: "http://c/u", adresse_aufgeloest: "http://c/r", eigene_adresse: "https://eigen/c" }));
    expect(eigen.url_resolved).toBe("https://eigen/c");
    expect(aufrufe).toHaveLength(0);
  });

  it("Favorit an schickt die Felder der Wiedergabe, aus löscht; danach meldet sie sich", async () => {
    let gemeldet = 0;
    const aufrufe: string[] = [];
    const quelle = new BackendQuelle({
      beiFavoriten: () => gemeldet++,
      anfrage: netz(async (weg, init) => {
        aufrufe.push(`${init.method} ${weg}`);
        if (weg === "/api/stations/a") return Response.json({ url: "http://a" });
        return Response.json({ ok: true });
      }),
    });
    await quelle.favorit(eintrag("a"), true);
    await quelle.favorit(eintrag("a"), false);
    expect(aufrufe).toEqual(["GET /api/stations/a", "POST /api/favorites", "DELETE /api/favorites/a"]);
    expect(gemeldet).toBe(2);
  });

  it("Bewertungen: Sterne als Wert, Werbung nimmt den Widerspruch zurück, fehlende Marke beim Entfernen ist kein Fehler", async () => {
    const { aufrufe, quelle } = backend({ "PUT /api/station-tags/a/sterne": { ok: true }, "PUT /api/station-tags/a/werbung": { ok: true } });
    await quelle.bewerten("a", "sterne:2", true);
    await quelle.bewerten("a", "werbung", true);
    await quelle.bewerten("a", "religioes", false);
    expect(aufrufe.map((x) => `${x.methode} ${x.weg}`)).toEqual([
      "PUT /api/station-tags/a/sterne", "PUT /api/station-tags/a/werbung", "DELETE /api/station-tags/a/werbung_widerspruch?source=user",
      "DELETE /api/station-tags/a/religioes?source=user"]);
    expect(aufrufe[0].daten).toEqual({ tag_key: "sterne", tag_value: "2", source: "user" });
  });

  it("misst nach dem Abspielen und liefert den Messwert", async () => {
    const { aufrufe, quelle } = backend({
      "POST /api/stations/verify-bitrate": { queued: 1 }, "POST /api/ad-detection/check": {},
      "POST /api/stations/bitrates": { bitrates: { a: { bitrate: 192, codec: "aac" } } },
    });
    expect(await quelle.gespielt(eintrag("a"))).toEqual({ kbps: 192, codec: "AAC" });
    const pruefung = aufrufe.find((x) => x.weg === "/api/ad-detection/check");
    expect(pruefung?.daten).toEqual({ uuid: "a", name: "Sender a" });   // nur die Kennung, keine Adresse (Regel B6)
  });

  it("liest die Länder der Seitenleiste auch als Text und schreibt sie in die Einstellungen", async () => {
    const { aufrufe, quelle } = backend({ "GET /api/config": { sidebar_countries: '["DE","AT"]' }, "PUT /api/config": { ok: true } });
    expect(await quelle.laenderLeiste()).toEqual(["DE", "AT"]);
    await quelle.laenderLeisteSetzen(["FR"]);
    expect(aufrufe[1].daten).toEqual({ updates: { sidebar_countries: ["FR"] } });
  });
});

/** Senderquelle zum Nachstellen: nur, was der Test braucht */
function quelleMit(teil: Partial<Senderquelle>): Senderquelle {
  return teil as Senderquelle;
}

describe("Senderliste", () => {
  it("lädt die erste Seite mit Gesamtzahl und Facetten, dann weiter über den Zeiger, ohne Doppel", async () => {
    const abfragen = vi.fn(async (q: StationQuery): Promise<Abfrageergebnis> => q.nach
      ? { gesamt: null, eintraege: [eintrag("b"), eintrag("c")], weiter: null, facetten: null }
      : { gesamt: 3, eintraege: [eintrag("a"), eintrag("b")], weiter: "z1",
          facetten: { laender: [], genres: [], qualitaet: [], codecs: [], bewertungen: [], kategorien: [] } });
    const liste = new Senderliste(quelleMit({ abfragen }), 2);
    await liste.laden({ laender: ["DE"] });
    expect(liste.gesamt).toBe(3);
    await liste.mehr();
    expect(liste.eintraege.map((e) => e.uuid)).toEqual(["a", "b", "c"]);
    expect(abfragen.mock.calls[1][0]).toMatchObject({ laender: ["DE"], nach: "z1", anzahl: 2, mit_facetten: false });
    expect(liste.facetten).not.toBeNull();
    await liste.mehr();   // kein Zeiger mehr: nichts
    expect(abfragen).toHaveBeenCalledTimes(2);
  });

  it("eine verspätete ältere Antwort ändert nichts", async () => {
    const antworten: ((r: Abfrageergebnis) => void)[] = [];
    const abfragen = (_q: StationQuery) => new Promise<Abfrageergebnis>((fertig) => antworten.push(fertig));
    const liste = new Senderliste(quelleMit({ abfragen }));
    const erste = liste.laden({ suche: "a" });
    const zweite = liste.laden({ suche: "ab" });
    antworten[1]({ gesamt: 1, eintraege: [eintrag("neu")], weiter: null, facetten: null });
    await zweite;
    antworten[0]({ gesamt: 9, eintraege: [eintrag("alt")], weiter: null, facetten: null });
    await erste;
    expect(liste.eintraege.map((e) => e.uuid)).toEqual(["neu"]);
    expect(liste.gesamt).toBe(1);
  });

  it("Ausblenden nimmt den Sender heraus, Rückgängig setzt ihn an seine Stelle", async () => {
    const liste = new Senderliste(quelleMit({
      abfragen: async () => ({ gesamt: 3, eintraege: [eintrag("a"), eintrag("b"), eintrag("c")], weiter: null, facetten: null }),
    }));
    await liste.laden({});
    const b = liste.eintraege[1];
    const stelle = liste.entfernen("b");
    expect(liste.gesamt).toBe(2);
    liste.einfuegen(b, stelle);
    expect(liste.eintraege.map((e) => e.uuid)).toEqual(["a", "b", "c"]);
    expect(liste.gesamt).toBe(3);
  });
});

describe("Regel-Ablauf", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  const vorschau = (n: number, gleiche: string | null = null): RegelVorschau =>
    ({ titel: "t", betroffen: n, neu_ausgeblendet: n, favoriten: 0, favoriten_namen: [], beispiele: [], gleiche_regel: gleiche });

  it("zeigt die Vorschau erst nach der Pause, nur zum letzten Entwurf", async () => {
    const holen = vi.fn(async (e: { art: string; mindeststimmen?: number }) => vorschau(e.mindeststimmen ?? 0));
    const ablauf = new Regelablauf(quelleMit({ vorschau: holen as Senderquelle["vorschau"] }), 250);
    ablauf.setzen({ art: "stimmen", mindeststimmen: 1 });
    ablauf.setzen({ art: "stimmen", mindeststimmen: 10 });
    expect(ablauf.bereit).toBe(false);
    await vi.advanceTimersByTimeAsync(300);
    expect(holen).toHaveBeenCalledTimes(1);
    expect(ablauf.vorschau?.betroffen).toBe(10);
    expect(ablauf.bereit).toBe(true);
  });

  it("legt erst nach der Vorschau an, Rückgängig entfernt die neue Regel", async () => {
    const regel = { id: "neu1" } as never;
    const anlegen = vi.fn(async () => ({ regel, bestand: {} as never, ausgeblendet: 10, wieder_sichtbar: 0 }));
    const entfernen = vi.fn(async () => ({ regel: null, bestand: {} as never, ausgeblendet: 0, wieder_sichtbar: 10 }));
    const ablauf = new Regelablauf(quelleMit({ vorschau: async () => vorschau(10), anlegen, entfernen }), 0);
    await expect(ablauf.anlegen()).rejects.toThrow();
    ablauf.setzen({ art: "werbung", stufe: "hoch" });
    await vi.advanceTimersByTimeAsync(1);
    const a = await ablauf.anlegen();
    expect(a.ausgeblendet).toBe(10);
    expect(ablauf.entwurf).toBeNull();
    expect((await ablauf.rueckgaengig())?.wieder_sichtbar).toBe(10);
    expect(entfernen).toHaveBeenCalledWith("neu1");
  });

  it("eine Regel, die es schon gibt, lässt sich nicht noch einmal anlegen", async () => {
    const ablauf = new Regelablauf(quelleMit({ vorschau: async () => vorschau(3, "r7") }), 0);
    ablauf.setzen({ art: "tag", tags: ["tv"] });
    await vi.advanceTimersByTimeAsync(1);
    expect(ablauf.vorschau?.gleiche_regel).toBe("r7");
    expect(ablauf.bereit).toBe(false);
  });
});
