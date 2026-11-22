// Podcastschicht (RAD-17): Quelle gegen ein nachgestelltes Backend, Folgenliste seitenweise, eine Aboliste.
import { describe, expect, it } from "vitest";
import { Aboliste } from "../src/lib/podcasts/abos.svelte";
import { BackendPodcastquelle, type Anfrager } from "../src/lib/podcasts/backend";
import { Folgenliste } from "../src/lib/podcasts/folgenliste.svelte";

const ABO = { id: 3, title: "Probefunk", author: "Haus", description: "<p>x</p>", feed_url: "https://feed.test/a", auto_download: 1,
              last_updated: "2026-11-20T08:00:00", episode_count: 12, downloaded_count: 2, unplayed_count: 5, today_unplayed: 1,
              week_unplayed: 3, total_duration: 3600 };
const folge = (id: number, extra = {}) => ({ id, podcast_id: 3, title: `Folge ${id}`, description: "", duration: 600,
  published_at: "2026-11-19", resume_position: 30, is_played: 0, is_downloaded: id === 1 ? 1 : 0, local_path: id === 1 ? "Podcasts/Probefunk/Folge 1.mp3" : null,
  file_size: 1000, image_url: null, ...extra });

function backend(antworten: Record<string, unknown> = {}) {
  const aufrufe: { pfad: string; optionen?: RequestInit }[] = [];
  const api: Anfrager = {
    baseUrl: "",
    async fetch(pfad, optionen) {
      aufrufe.push({ pfad, optionen });
      const treffer = Object.keys(antworten).find((k) => pfad.startsWith(k));
      return treffer ? (typeof antworten[treffer] === "function" ? (antworten[treffer] as (p: string) => unknown)(pfad) : antworten[treffer]) : {};
    },
  };
  return { quelle: new BackendPodcastquelle(api), aufrufe };
}

describe("Podcastquelle gegen das Backend", () => {
  it("bildet Abos und Folgen auf das Datenmodell ab, Bilder über die eigene App", async () => {
    const { quelle } = backend({ "/api/podcasts/subscriptions": { subscriptions: [ABO] },
      "/api/podcasts/3/episodes": { episodes: [folge(1), folge(2, { image_url: "https://fremd.test/b.jpg" })], total: 2 } });
    const [abo] = await quelle.abos();
    expect(abo).toMatchObject({ id: 3, titel: "Probefunk", autoLaden: true, ungehoert: 5, heuteUngehoert: 1, bild: "/api/podcasts/3/image",
      angeheftet: false, sortierung: "", gespeichert: 2 });
    const s = await quelle.folgen({ abos: [3] });
    expect(s.folgen[0]).toMatchObject({ id: 1, aboId: 3, gespeichert: true, ablagePfad: "Podcasts/Probefunk/Folge 1.mp3", gehoert: false, stelle: 30, bild: "/api/podcasts/3/image" });
    expect(s.folgen[1].bild).toBe("/api/podcasts/episodes/2/image");                 // nie direkt der fremde Server
    expect(s.folgen[1].ablagePfad).toBe("");
    expect(quelle.dateiAdresse(2)).toBe("/api/podcasts/episodes/2/datei");           // Herunterladen aufs Gerät
    expect(quelle.faehig).toMatchObject({ speichern: true, herunterladen: true });
    expect(s.weiter).toBeNull();
  });

  it("übersetzt Filter, Sortierung und Seiten in die Parameter des Backends", async () => {
    const { quelle, aufrufe } = backend({ "/api/podcasts/episodes/all": { episodes: [folge(1), folge(2)], total: 5 } });
    const s = await quelle.folgen({ abos: [3, 4], filter: "gespeichert", sortierung: "dauer", absteigend: false, anzahl: 2, nach: "2" });
    const q = new URLSearchParams(aufrufe[0].pfad.split("?")[1]);
    expect(Object.fromEntries(q)).toEqual({ limit: "2", offset: "2", filter_status: "downloaded", sort_by: "duration", sort_order: "asc", podcast_ids: "3,4" });
    expect(s.weiter).toBe("4");
  });

  it("schreibt Gehört, Stelle, Speichern, Anheften und Sortierung an die richtigen Stellen", async () => {
    const { quelle, aufrufe } = backend();
    await quelle.gehoert(7, true);
    await quelle.gehoert(7, false);
    await quelle.stelleMerken(7, 61.6);
    await quelle.speichern(7, true);
    await quelle.speichern(7, false);
    await quelle.anheften(3, true);
    await quelle.sortierungSetzen(3, "alt");
    expect(aufrufe.map((a) => `${a.optionen?.method} ${a.pfad}`)).toEqual([
      "PUT /api/podcasts/episodes/7/played", "PUT /api/podcasts/episodes/7/unplayed", "PUT /api/podcasts/episodes/7/position",
      "POST /api/podcasts/episodes/7/download", "DELETE /api/podcasts/episodes/7/download", "PUT /api/podcasts/3/anheften",
      "PUT /api/podcasts/3/sortierung"]);
    expect(JSON.parse(aufrufe[2].optionen!.body as string)).toEqual({ position_seconds: 62 });
  });

  it("gibt dem Spieler die Folge in seinem Format", async () => {
    const { quelle } = backend({ "/api/podcasts/subscriptions": { subscriptions: [ABO] },
      "/api/podcasts/episodes/all": { episodes: [folge(1)], total: 1 } });
    const [f] = (await quelle.folgen({})).folgen;
    const w = await quelle.wiedergabe(f);
    expect(w.folge).toMatchObject({ id: 1, title: "Folge 1" });
    expect(w.abo).toMatchObject({ id: 3, title: "Probefunk" });
  });
});

describe("Folgenliste", () => {
  it("lädt seitenweise, ohne Doppel, und eine neue Abfrage gewinnt gegen eine verspätete", async () => {
    let seiten = 0;
    const { quelle } = backend({ "/api/podcasts/episodes/all": (pfad: string) => {
      seiten += 1;
      const stelle = Number(new URLSearchParams(pfad.split("?")[1]).get("offset"));
      return stelle === 0 ? { episodes: [folge(1), folge(2)], total: 3 } : { episodes: [folge(2), folge(3)], total: 3 };
    } });
    const liste = new Folgenliste(quelle, 2);
    await liste.laden({ filter: "alle" });
    expect(liste.folgen.map((f) => f.id)).toEqual([1, 2]);
    await liste.mehr();
    expect(liste.folgen.map((f) => f.id)).toEqual([1, 2, 3]);
    expect(seiten).toBe(2);
    liste.aendern(2, { gehoert: true });
    expect(liste.folgen[1].gehoert).toBe(true);
  });

  it("eine Folge außerhalb der geladenen Seiten kommt vorn dazu (Direktlink, laufende Folge), eine unbekannte nicht", async () => {
    const { quelle } = backend({
      "/api/podcasts/episodes/all": { episodes: [folge(1), folge(2)], total: 9 },
      "/api/podcasts/episodes/7": folge(7, { werbung_anzahl: 1, werbung_dauer: 30 }),
      "/api/podcasts/episodes/8": () => { throw new Error("Episode nicht gefunden"); },
    });
    const liste = new Folgenliste(quelle);
    await liste.laden({ filter: "alle" });
    expect(await liste.sicherstellen(2)).toBe(true);
    expect(await liste.sicherstellen(7)).toBe(true);
    expect(liste.folgen.map((f) => f.id)).toEqual([7, 1, 2]);
    expect(liste.folgen[0].werbung).toEqual({ anzahl: 1, dauer: 30 });
    expect(await liste.sicherstellen(8)).toBe(false);
    expect(liste.folgen.length).toBe(3);
  });

  it("zeigt beim Wechsel der Abos bis zur Antwort nicht die alte Liste, sondern lädt (RAD-107)", async () => {
    let freigeben: (() => void) | null = null;
    const { quelle } = backend({
      "/api/podcasts/episodes/all": { episodes: [folge(1)], total: 1 },
      "/api/podcasts/5/episodes": () => new Promise((fertig) => { freigeben = () => fertig({ episodes: [folge(5)], total: 1 }); }),
    });
    const liste = new Folgenliste(quelle);
    await liste.laden({ filter: "alle" });
    expect([liste.geladen, liste.folgen.map((f) => f.id)]).toEqual([true, [1]]);
    const laeuft = liste.laden({ abos: [5], filter: "alle" });
    expect([liste.geladen, liste.folgen.length]).toEqual([false, 0]);
    await new Promise((r) => setTimeout(r, 0));
    freigeben!();
    await laeuft;
    expect([liste.geladen, liste.folgen.map((f) => f.id)]).toEqual([true, [5]]);
    // gleiche Wahl, nur ein anderer Filter: die Liste bleibt stehen, bis die Antwort da ist
    void liste.laden({ abos: [5], filter: "ungehoert" });
    expect(liste.geladen).toBe(true);
  });

  it("sucht mit Suchtext im Volltext, mit Abo-Wahl, Filter und Sortierung wie die Liste (RAD-44)", async () => {
    const { quelle, aufrufe } = backend({ "/api/podcasts/episodes/all": { episodes: [folge(9)], total: 1 } });
    const liste = new Folgenliste(quelle);
    await liste.laden({ abos: [3], filter: "gespeichert", sortierung: "titel", absteigend: false }, " Wetter ");
    const adresse = new URLSearchParams(aufrufe[0].pfad.split("?")[1]);
    expect(aufrufe[0].pfad.startsWith("/api/podcasts/episodes/all?")).toBe(true);
    expect([adresse.get("q"), adresse.get("podcast_ids"), adresse.get("filter_status"), adresse.get("sort_by"), adresse.get("sort_order")])
      .toEqual(["Wetter", "3", "downloaded", "title", "asc"]);
    expect(liste.folgen.map((f) => f.id)).toEqual([9]);
  });
});

describe("Aboliste", () => {
  it("eine Liste: abonnieren, ordnen (bei Fehler zurück), abbestellen", async () => {
    let ordnenScheitert = false;
    const { quelle } = backend({
      "/api/podcasts/subscriptions": { subscriptions: [ABO, { ...ABO, id: 4, title: "Zwei", feed_url: "https://feed.test/b" }] },
      "/api/podcasts/subscribe": { podcast: { ...ABO, id: 5, title: "Neu", feed_url: "https://feed.test/c" } },
      "/api/podcasts/order": () => { if (ordnenScheitert) throw new Error("weg"); return {}; },
    });
    const liste = new Aboliste(quelle);
    await liste.laden();
    expect(liste.abonniert("https://feed.test/b")).toBe(true);
    await liste.abonnieren("https://feed.test/c");
    expect(liste.abos.map((a) => a.id)).toEqual([3, 4, 5]);
    await liste.ordnen([5, 3, 4]);
    expect(liste.abos.map((a) => a.id)).toEqual([5, 3, 4]);
    ordnenScheitert = true;
    await expect(liste.ordnen([4, 5, 3])).rejects.toThrow("weg");
    expect(liste.abos.map((a) => a.id)).toEqual([5, 3, 4]);
    await liste.abbestellen(3);
    expect(liste.abos.map((a) => a.id)).toEqual([5, 4]);
  });
});

describe("Adresse der Podcast-Ansicht", async () => {
  const { ausAdresse, zuAdresse, zuAbfrage, leer } = await import("../src/lib/podcasts/ansicht.svelte");

  it("liest und schreibt Abo, Folge, Wahl, Suche, Sortierung und Verzeichnis, auch die Adressen des Telefons", () => {
    expect(ausAdresse("/podcasts", "")).toEqual(leer());
    expect(ausAdresse("/podcasts/3/17", "")).toMatchObject({ abos: [3], offen: 17 });
    expect(ausAdresse("/podcasts", "abo=3,4,3&wahl=gespeichert&suche=Wetter&sort=laenge&verzeichnis=1"))
      .toMatchObject({ abos: [3, 4], wahl: "gespeichert", suche: "Wetter", sortierung: "laenge", verzeichnis: true });
    expect(ausAdresse("/podcasts", "wahl=boese&sort=boese")).toMatchObject({ wahl: "alle", sortierung: "neu" });
    expect(ausAdresse("/podcasts/search/Wetter%20heute", "")).toMatchObject({ suche: "Wetter heute", abos: [] });
    for (const a of [leer(), { ...leer(), abos: [3] }, { ...leer(), abos: [3], offen: 17 }, { ...leer(), abos: [3, 4], wahl: "ungehoert" as const, suche: "x" }]) {
      const adresse = zuAdresse(a);
      const [pfad, abfrage = ""] = adresse.split("?");
      expect(ausAdresse(pfad, abfrage)).toEqual(a);
    }
    expect(zuAdresse({ ...leer(), offen: 9 }, 5)).toBe("/podcasts/5/9");
  });

  it("übersetzt die Ansicht in die Abfrage der Folgen", () => {
    expect(zuAbfrage({ ...leer(), abos: [3], wahl: "ungehoert", sortierung: "laenge" }))
      .toEqual({ abos: [3], filter: "ungehoert", sortierung: "dauer", absteigend: false });
    expect(zuAbfrage(leer())).toMatchObject({ sortierung: "datum", absteigend: true });
  });
});

describe("Alle speichern", async () => {
  const { Speicherauftrag } = await import("../src/lib/podcasts/speicherauftrag.svelte");

  it("lädt der Reihe nach mit Fortschritt, hält an, setzt fort und bricht ab", async () => {
    const geladen: number[] = [];
    const offen: { id: number; gut: () => void; schlecht: () => void }[] = [];
    const quelle = { speichern: (id: number) => new Promise<void>((gut, schlecht) => offen.push({ id, gut, schlecht: () => schlecht(new Error("x")) })) };
    const ruhe = () => new Promise((r) => setTimeout(r, 0));
    const auftrag = new Speicherauftrag(quelle as never, (id) => geladen.push(id));
    const lauf = auftrag.starten(7, [1, 2, 3, 4]);
    expect([auftrag.laeuft, auftrag.gesamt]).toEqual([true, 4]);
    offen.shift()!.gut(); await ruhe();               // 1 geladen
    offen.shift()!.schlecht(); await ruhe();          // 2 scheitert, zählt als fertig mit Fehler
    expect([auftrag.fertig, auftrag.fehler, geladen]).toEqual([2, 1, [1]]);
    auftrag.anhalten();
    offen.shift()!.gut(); await ruhe();               // 3 lief schon, danach steht er
    expect([auftrag.fertig, auftrag.angehalten, offen.length]).toEqual([3, true, 0]);
    auftrag.fortsetzen(); await ruhe();               // 4 beginnt
    expect(offen.map((o) => o.id)).toEqual([4]);
    auftrag.abbrechen();
    offen.shift()!.gut();
    await lauf;
    expect([auftrag.laeuft, geladen]).toEqual([false, [1, 3, 4]]);
  });
});

describe("Anzeige der Podcasts", async () => {
  const { datumKurz, dauerText, standVon, stelleText, tageHer } = await import("../src/lib/podcasts/anzeige");
  it("Datum mit Jahr nur aus einem anderen Jahr, Tage her, Längen, Stand", () => {
    const heute = new Date(2026, 10, 20, 12);
    expect(datumKurz("2025-09-09T09:20:15", heute)).toMatch(/2025/);
    expect(datumKurz("2026-04-09T07:15:07", heute)).not.toMatch(/2026/);
    expect([tageHer("2026-11-20T01:00:00", heute), tageHer("2026-11-19 23:00:00", heute), tageHer("", heute)]).toEqual([0, 1, null]);
    expect([dauerText(6000), dauerText(2880), stelleText(723), stelleText(3723)]).toEqual(["1 h 40 min", "48 min", "12:03", "1:02:03"]);
    const f = { dauer: 600, stelle: 0, gehoert: false } as never;
    expect(standVon(f).art).toBe("neu");
    expect(standVon({ ...(f as object), stelle: 300 } as never)).toMatchObject({ art: "laeuft", anteil: 0.5, rest: 300 });
    expect(standVon({ ...(f as object), stelle: 598 } as never).art).toBe("gehoert");
  });
});


describe("Anheften und Sortierung je Abo", () => {
  it("angeheftete stehen vor den übrigen, ein gelöstes kehrt an seine Stelle zurück; Sortierung je Abo", async () => {
    const abos = [{ ...ABO, id: 1, sortierung: "alt", angeheftet: 0 }, { ...ABO, id: 2, sortierung: "boese", angeheftet: 0 }, { ...ABO, id: 3, angeheftet: 1 }];
    const { quelle } = backend({
      "/api/podcasts/subscriptions": () => ({ subscriptions: [...abos].sort((a, b) => b.angeheftet - a.angeheftet || a.id - b.id) }),
      "/api/podcasts/1/anheften": () => ({}), "/api/podcasts/2/anheften": () => { abos[1].angeheftet = 1; return {}; },
      "/api/podcasts/3/anheften": () => { abos[2].angeheftet = 0; return {}; },
    });
    const liste = new Aboliste(quelle);
    await liste.laden();
    expect(liste.abos.map((a) => [a.id, a.sortierung, a.angeheftet])).toEqual([[3, "", true], [1, "alt", false], [2, "", false]]);
    await liste.anheften(2, true);
    expect(liste.abos.map((a) => a.id)).toEqual([2, 3, 1]);
    await liste.anheften(3, false);
    expect(liste.abos.map((a) => a.id)).toEqual([2, 1, 3]);
    await liste.sortierungSetzen(1, "titel");
    expect(liste.abo(1)?.sortierung).toBe("titel");
  });
});

describe("Ordner der Abos (RAD-23)", () => {
  it("lädt Ordner mit den Abos, legt an, ordnet zu, und Löschen nimmt nur die Gruppierung", async () => {
    const { quelle, aufrufe } = backend({
      "/api/podcasts/subscriptions": { subscriptions: [{ ...ABO, id: 1, ordner_id: "o1" }, { ...ABO, id: 2, ordner_id: null }, { ...ABO, id: 3, ordner_id: "o1", angeheftet: 1 }] },
      "/api/podcast-ordner/abo/": {},
      "/api/podcast-ordner/o1": (p: string) => (p === "/api/podcast-ordner/o1" ? { id: "o1", name: "Wissen", offen: false, geloest: 2 } : {}),
      "/api/podcast-ordner": (p: string) => (p === "/api/podcast-ordner" ? { ordner: [{ id: "o1", name: "Nachrichten", offen: true }], id: "o2", name: "Neu", offen: true } : {}),
    });
    const liste = new Aboliste(quelle);
    await liste.laden();
    expect(liste.ordner).toEqual([{ id: "o1", name: "Nachrichten", offen: true }]);
    expect(liste.imOrdner("o1").map((a) => a.id)).toEqual([1]);                      // angeheftete stehen oben, nicht im Ordner
    expect(liste.imOrdner(null).map((a) => a.id)).toEqual([2]);
    await liste.ordnerAnlegen("Neu");
    expect(liste.ordner.map((o) => o.id)).toEqual(["o1", "o2"]);
    await liste.ordnerAendern("o1", { name: "Wissen", offen: false });
    expect(liste.ordner[0]).toEqual({ id: "o1", name: "Wissen", offen: false });
    await liste.zuordnen(2, "o1");
    expect(liste.imOrdner("o1").map((a) => a.id)).toEqual([1, 2]);
    await liste.ordnerLoeschen("o1");
    expect(liste.ordner.map((o) => o.id)).toEqual(["o2"]);
    expect(liste.abos.map((a) => a.id)).toEqual([1, 2, 3]);                           // die Abos bleiben, nur lose
    expect(liste.imOrdner(null).map((a) => a.id)).toEqual([1, 2]);
    const wege = aufrufe.map((a) => `${a.optionen?.method ?? "GET"} ${a.pfad}`);
    expect(wege).toContain("PUT /api/podcast-ordner/abo/2");
    expect(wege).toContain("DELETE /api/podcast-ordner/o1");
  });
});

describe("Übersicht der Abos am Telefon (RAD-14)", () => {
  it("steht als ?liste=abos in der Adresse und kommt so zurück", async () => {
    const { ausAdresse, zuAdresse } = await import("../src/lib/podcasts/ansicht.svelte");
    const a = ausAdresse("/podcasts", "liste=abos");
    expect(a.aboUebersicht).toBe(true);
    expect(zuAdresse(a)).toBe("/podcasts?liste=abos");
    expect(ausAdresse("/podcasts", "").aboUebersicht).toBe(false);
  });
});
