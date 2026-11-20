// Podcastschicht (RAD-17): Quelle gegen ein nachgestelltes Backend, Folgenliste seitenweise, eine Aboliste.
import { describe, expect, it } from "vitest";
import { Aboliste } from "../src/lib/podcasts/abos.svelte";
import { BackendPodcastquelle, type Anfrager } from "../src/lib/podcasts/backend";
import { Folgenliste } from "../src/lib/podcasts/folgenliste.svelte";

const ABO = { id: 3, title: "Probefunk", author: "Haus", description: "<p>x</p>", feed_url: "https://feed.test/a", auto_download: 1,
              last_updated: "2026-11-20T08:00:00", episode_count: 12, downloaded_count: 2, unplayed_count: 5, today_unplayed: 1,
              week_unplayed: 3, total_duration: 3600 };
const folge = (id: number, extra = {}) => ({ id, podcast_id: 3, title: `Folge ${id}`, description: "", duration: 600,
  published_at: "2026-11-19", resume_position: 30, is_played: 0, is_downloaded: id === 1 ? 1 : 0, file_size: 1000, image_url: null, ...extra });

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
    expect(abo).toMatchObject({ id: 3, titel: "Probefunk", autoLaden: true, ungehoert: 5, heuteUngehoert: 1, bild: "/api/podcasts/3/image" });
    const s = await quelle.folgen({ abos: [3] });
    expect(s.folgen[0]).toMatchObject({ id: 1, aboId: 3, gemerkt: true, gehoert: false, stelle: 30, bild: "/api/podcasts/3/image" });
    expect(s.folgen[1].bild).toBe("/api/podcasts/episodes/2/image");                 // nie direkt der fremde Server
    expect(s.weiter).toBeNull();
  });

  it("übersetzt Filter, Sortierung und Seiten in die Parameter des Backends", async () => {
    const { quelle, aufrufe } = backend({ "/api/podcasts/episodes/all": { episodes: [folge(1), folge(2)], total: 5 } });
    const s = await quelle.folgen({ abos: [3, 4], filter: "gemerkt", sortierung: "dauer", absteigend: false, anzahl: 2, nach: "2" });
    const q = new URLSearchParams(aufrufe[0].pfad.split("?")[1]);
    expect(Object.fromEntries(q)).toEqual({ limit: "2", offset: "2", filter_status: "downloaded", sort_by: "duration", sort_order: "asc", podcast_ids: "3,4" });
    expect(s.weiter).toBe("4");
  });

  it("schreibt Gehört, Stelle, Merken und mehrere merken an die richtigen Stellen", async () => {
    const { quelle, aufrufe } = backend({ "/api/podcasts/3/download-batch": { total: 3, success: 1, skipped: 1, failed: 1 } });
    await quelle.gehoert(7, true);
    await quelle.gehoert(7, false);
    await quelle.stelleMerken(7, 61.6);
    await quelle.merken(7, true);
    await quelle.merken(7, false);
    expect(await quelle.mehrereMerken(3, [7, 8, 9])).toEqual({ gesamt: 3, neu: 1, schonDa: 1, fehler: 1 });
    expect(aufrufe.map((a) => `${a.optionen?.method} ${a.pfad}`)).toEqual([
      "PUT /api/podcasts/episodes/7/played", "PUT /api/podcasts/episodes/7/unplayed", "PUT /api/podcasts/episodes/7/position",
      "POST /api/podcasts/episodes/7/download", "DELETE /api/podcasts/episodes/7/download", "POST /api/podcasts/3/download-batch"]);
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

  it("sucht mit Suchtext im Volltext", async () => {
    const { quelle, aufrufe } = backend({ "/api/podcasts/episodes/search": { episodes: [folge(9)], total: 1 } });
    const liste = new Folgenliste(quelle);
    await liste.laden({}, " Wetter ");
    expect(aufrufe[0].pfad).toContain("q=Wetter");
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
