// @vitest-environment happy-dom
// Podcasts der Webversion (RAD-102): Feed lesen, OPML, die Browserquelle mit Speicher, Stelle, gehört und Feeds ohne
// Freigabe. Netz und Speicher sind Proben.
import { describe, expect, it } from "vitest";
import { dauerAus, feedLesen } from "../src/lib/podcasts/browser/feed";
import { BrowserPodcastquelle, FeedGesperrt } from "../src/lib/podcasts/browser/browser-quelle";
import { kennung, PODCAST_SCHLUESSEL } from "../src/lib/podcasts/browser/ablage";
import { feedsAus, opmlAus } from "../src/lib/podcasts/opml";
import { fluechtigerSpeicher } from "../src/lib/radio/statisch/speicher";

const FEED = "https://beispiel.test/feed.xml";
const XML = `<?xml version="1.0"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Probe-Podcast</title>
    <itunes:author>Probe-Autor</itunes:author>
    <description>Über alles</description>
    <itunes:image href="https://beispiel.test/bild.jpg"/>
    <item>
      <title>Folge 2</title><guid>f2</guid><pubDate>Tue, 10 Nov 2026 08:00:00 GMT</pubDate>
      <itunes:duration>1:02:03</itunes:duration>
      <enclosure url="http://beispiel.test/f2.mp3" length="1000" type="audio/mpeg"/>
    </item>
    <item>
      <title>Folge 1</title><guid>f1</guid><pubDate>Mon, 02 Nov 2026 08:00:00 GMT</pubDate>
      <itunes:duration>600</itunes:duration>
      <enclosure url="https://beispiel.test/f1.mp3" type="audio/mpeg"/>
    </item>
    <item><title>ohne Datei</title><guid>f0</guid></item>
  </channel>
</rss>`;

const parser = () => new DOMParser();

function abruf(antworten: Record<string, string | "gesperrt">): typeof fetch {
  return (async (adresse: string | URL | Request) => {
    const a = antworten[String(adresse)];
    if (a === undefined || a === "gesperrt") throw new TypeError("Failed to fetch");
    return new Response(a, { status: 200 });
  }) as typeof fetch;
}

function quelle(antworten: Record<string, string | "gesperrt"> = { [FEED]: XML }, speicher = fluechtigerSpeicher()) {
  return {
    speicher,
    q: new BrowserPodcastquelle({ speicher, abruf: abruf(antworten), parser, hinweis: (p) => `problem:${p.art}`,
                                  verzeichnis: { weltweit: "https://w.test", deutsch: "https://d.test" } }),
  };
}

describe("Feed lesen", () => {
  it("liest Kanal und Folgen mit Datei, ohne Folgen ohne Datei", () => {
    const f = feedLesen(XML, new DOMParser());
    expect(f).toMatchObject({ titel: "Probe-Podcast", autor: "Probe-Autor", bild: "https://beispiel.test/bild.jpg" });
    expect(f.folgen.map((x) => x.guid)).toEqual(["f2", "f1"]);
    expect(f.folgen[0]).toMatchObject({ dauer: 3723, groesse: 1000, adresse: "http://beispiel.test/f2.mp3" });
    expect(f.folgen[0].datum).toBe("2026-11-10T08:00:00.000Z");
  });

  it("wirft bei kaputtem oder fremdem XML", () => {
    expect(() => feedLesen("<kaputt", new DOMParser())).toThrow();
    expect(() => feedLesen("<html><body/></html>", new DOMParser())).toThrow();
  });

  it("rechnet Längen aus Stunden, Minuten und Sekunden", () => {
    expect(dauerAus("62:03")).toBe(3723);
    expect(dauerAus("45")).toBe(45);
    expect(dauerAus("x")).toBe(0);
  });
});

describe("OPML", () => {
  it("schreibt Abos und liest die Feeds zurück, ohne Doppel", () => {
    const text = opmlAus([{ titel: "A & B", feed: FEED }, { titel: "C", feed: "https://c.test/rss" }]);
    expect(text).toContain("A &amp; B");
    expect(feedsAus(text + "", new DOMParser())).toEqual([FEED, "https://c.test/rss"]);
    expect(feedsAus("<opml><body><outline xmlUrl=\"" + FEED + "\"/><outline xmlUrl=\"" + FEED + "\"/></body></opml>", new DOMParser())).toEqual([FEED]);
    expect(feedsAus("kein xml", new DOMParser())).toEqual([]);
  });
});

describe("Browserquelle", () => {
  it("abonniert, zählt und liefert Folgen neueste zuerst mit https-Datei", async () => {
    const { q } = quelle();
    const abo = await q.abonnieren(FEED);
    expect(abo).toMatchObject({ id: kennung(FEED), titel: "Probe-Podcast", folgen: 2, ungehoert: 2, dauerGesamt: 4323 });
    const seite = await q.folgen({ abos: [abo.id] });
    expect(seite.folgen.map((f) => f.titel)).toEqual(["Folge 2", "Folge 1"]);
    expect(q.dateiAdresse(seite.folgen[0].id)).toBe("https://beispiel.test/f2.mp3");
  });

  it("merkt Stelle und gehört im Speicher und behält sie über einen Neustart", async () => {
    const { q, speicher } = quelle();
    const abo = await q.abonnieren(FEED);
    const [f2, f1] = (await q.folgen({ abos: [abo.id] })).folgen;
    await q.stelleMerken(f2.id, 600.4);
    await q.gehoert(f1.id, true);
    const neu = quelle({ [FEED]: XML }, speicher).q;
    const [n2, n1] = (await neu.folgen({ abos: [abo.id] })).folgen;
    expect(n2).toMatchObject({ stelle: 600, gehoert: false });
    expect(n1).toMatchObject({ gehoert: true });
    expect((await neu.folgen({ filter: "ungehoert" })).folgen.map((f) => f.id)).toEqual([f2.id]);
    const w = await neu.wiedergabe(n2);
    expect(w.folge).toMatchObject({ resume_position: 600, remote_audio_url: "https://beispiel.test/f2.mp3" });
  });

  it("räumt beim Abbestellen auch die Stände der Folgen ab", async () => {
    const { q, speicher } = quelle();
    const abo = await q.abonnieren(FEED);
    await q.stelleMerken((await q.folgen({ abos: [abo.id] })).folgen[0].id, 30);
    await q.abbestellen(abo.id);
    expect(JSON.parse(speicher.inhalt.get(PODCAST_SCHLUESSEL)!)).toEqual({ abos: [], ordner: [], folgen: {} });
  });

  it("ein Feed ohne Freigabe wird nicht abonniert, der Hinweis sagt warum (RAD-109)", async () => {
    const { q, speicher } = quelle({ [FEED]: "gesperrt" });
    await expect(q.abonnieren(FEED)).rejects.toBeInstanceOf(FeedGesperrt);
    await expect(q.abonnieren(FEED)).rejects.toThrow("problem:abruf");
    expect(speicher.inhalt.get(PODCAST_SCHLUESSEL)).toBeUndefined();
  });

  it("ein schon bestehendes Abo, dessen Feed nicht mehr lesbar ist, bleibt und zeigt den Hinweis statt der Folgen", async () => {
    const { q, speicher } = quelle();
    const abo = await q.abonnieren(FEED);
    const spaeter = quelle({ [FEED]: "gesperrt" }, speicher).q;
    await expect(spaeter.folgen({ abos: [abo.id] })).rejects.toThrow("problem:abruf");
    expect((await spaeter.folgen({})).folgen).toEqual([]);
    expect((await spaeter.abos()).map((a) => a.id)).toEqual([abo.id]);
  });

  it("die Suche bietet nur Podcasts an, deren Feed der Browser lesen kann (RAD-109)", async () => {
    const gut = "https://gut.test/feed.xml", gesperrt = "https://gesperrt.test/feed.xml", webseite = "https://seite.test/feed";
    const abruf = (async (adresse: string | URL | Request) => {
      const a = String(adresse);
      if (a.startsWith("https://w.test")) return Response.json({ results: [gut, gesperrt, webseite].map((f, i) => ({ collectionName: `P${i}`, feedUrl: f })) });
      if (a.startsWith("https://d.test")) return Response.json({ data: [] });
      if (a.startsWith(gut)) return new Response(XML, { headers: { "content-type": "application/rss+xml" } });
      if (a.startsWith(webseite)) return new Response("<!DOCTYPE html><html></html>", { headers: { "content-type": "text/html" } });
      throw new TypeError("Load failed");
    }) as typeof fetch;
    const q = new BrowserPodcastquelle({ speicher: fluechtigerSpeicher(), abruf, parser, hinweis: () => "x",
                                         verzeichnis: { weltweit: "https://w.test", deutsch: "https://d.test" } });
    expect((await q.suchen("probe")).map((f) => f.feed)).toEqual([gut]);
  });

  it("nennt die Ursache: Fehler des Servers oder unlesbarer Inhalt", async () => {
    const kaputt = "https://beispiel.test/kaputt.xml";
    const fehlt = "https://beispiel.test/fehlt.xml";
    const speicher = fluechtigerSpeicher();
    const abruf = (async (adresse: string | URL | Request) =>
      String(adresse) === kaputt ? new Response("<kaputt", { status: 200 }) : new Response("weg", { status: 404 })) as typeof fetch;
    const q = new BrowserPodcastquelle({ speicher, abruf, parser, hinweis: (p) => `${p.art}:${p.detail}`,
                                         verzeichnis: { weltweit: "https://w.test", deutsch: "https://d.test" } });
    await expect(q.abonnieren(kaputt)).rejects.toThrow(/^inhalt:/);
    await expect(q.abonnieren(fehlt)).rejects.toThrow("antwort:404");
  });

  it("meldet einen vollen Speicher beim Abonnieren als Fehler, nicht als gesperrten Feed", async () => {
    const speicher = { lesen: () => null, schreiben: () => { throw new Error("voll"); } };
    const q = new BrowserPodcastquelle({ speicher, abruf: abruf({ [FEED]: XML }), parser, hinweis: () => "x",
                                         verzeichnis: { weltweit: "https://w.test", deutsch: "https://d.test" } });
    await expect(q.abonnieren(FEED)).rejects.toThrow("voll");
  });

  it("liefert der Server eine Webseite statt des Feeds, fragt sie mit format=xml nach (RAD-107, iPhone)", async () => {
    const speicher = fluechtigerSpeicher();
    const abruf = (async (adresse: string | URL | Request) => String(adresse).includes("format=xml")
      ? new Response(XML, { status: 200, headers: { "content-type": "text/xml" } })
      : new Response("<html><body>Feed</body></html>", { status: 200, headers: { "content-type": "text/html" } })) as typeof fetch;
    const q = new BrowserPodcastquelle({ speicher, abruf, parser, hinweis: (p) => `${p.art}:${p.detail}`,
                                         verzeichnis: { weltweit: "https://w.test", deutsch: "https://d.test" } });
    expect((await q.abonnieren(FEED)).folgen).toBe(2);
    const immerWebseite = (async () => new Response("<!DOCTYPE html><html></html>", { status: 200 })) as typeof fetch;
    const q2 = new BrowserPodcastquelle({ speicher: fluechtigerSpeicher(), abruf: immerWebseite, parser, hinweis: (p) => `${p.art}:${p.detail}`,
                                          verzeichnis: { weltweit: "https://w.test", deutsch: "https://d.test" } });
    await expect(q2.abonnieren(FEED)).rejects.toThrow("inhalt:Der Server liefert eine Webseite statt des Feeds");
  });

  it("versucht einen http-Feed zuerst über https", async () => {
    const http = "http://beispiel.test/feed.xml";
    const { q } = quelle({ [FEED]: XML });
    const abo = await q.abonnieren(http);
    expect(abo.folgen).toBe(2);
  });
});
