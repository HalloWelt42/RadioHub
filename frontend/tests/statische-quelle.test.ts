// RAD-4: Statische Senderquelle der Webversion. Dieselben Fälle wie backend/tests/test_senderquelle.py (soweit sie für
// die Webversion gelten: ohne Werbung, Abgleich und Verschwundene), auf einer kleinen Probe im Format von sender.json
// (backend/app/werkzeuge/statische_liste.py); dazu Speicher, Sichern und Einspielen, Fähigkeiten und die Zeit einer
// Abfrage auf der erzeugten Liste web/daten/sender.json.
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { FORMAT, SPALTEN, StatischeQuelle, fluechtigerSpeicher, NichtVerfuegbar, SPEICHER_SCHLUESSEL, type Speicher } from "../src/lib/radio/statisch";
import type { Abfrageergebnis, SenderEintrag, StationQuery } from "../src/lib/radio/typen";

// ----- Probe im Format von sender.json --------------------------------------------------------------------------------

interface Probesender {
  uuid: string;
  name: string;
  land?: string;
  sprachen?: string[];
  eintraege?: string[];
  genres?: string[];
  tags?: string[];
  codec?: string;
  kbps?: number;
  qualitaet?: string;
  stimmen?: number;
  /** uuid des Gruppenschlüssels (ohne Angabe: eigene Gruppe) */
  gruppe?: string;
  logo?: string;
}

const SPRACHNAMEN = { de: "Deutsch", ru: "Russisch", zh: "Chinesisch (Mandarin)", yue: "Chinesisch (Kantonesisch)" };
const EINTRAGSCODES = { german: "de", ger: "de", russian: "ru", ru: "ru", chinese: "zh", mandarin: "zh", cantonese: "yue" };
const LANDNAMEN: Record<string, string> = { DE: "Germany", RU: "Russia", AT: "Austria" };

function probe(sender: Probesender[]): unknown {
  const liste = [...sender].sort((a, b) => (a.uuid < b.uuid ? -1 : 1));
  const woerter: Record<string, string[]> = { land: [], land_name: [], region: [""], bundesland: [""], sprache: [], spracheintrag: [],
                                              genre: [], tag: [], codec: [], qualitaet: [] };
  const nr = (w: string, wert: string) => {
    const n = woerter[w].indexOf(wert);
    return n >= 0 ? n : woerter[w].push(wert) - 1;
  };
  const zeile = liste.findIndex.bind(liste);
  const zeilen = liste.map((s) => {
    const land = s.land ?? "DE";
    return [s.uuid, s.name, `https://strom.test/${s.uuid}`, "", s.logo ?? "", "", nr("land", land), nr("land_name", LANDNAMEN[land] ?? ""),
            0, 0, (s.sprachen ?? ["de"]).map((x) => nr("sprache", x)), (s.eintraege ?? ["german"]).map((x) => nr("spracheintrag", x)),
            (s.genres ?? []).map((x) => nr("genre", x)), (s.tags ?? []).map((x) => nr("tag", x)), nr("codec", s.codec ?? "MP3"),
            s.kbps ?? 128, nr("qualitaet", s.qualitaet ?? "mittel"), s.stimmen ?? 10, 0, zeile((x) => x.uuid === (s.gruppe ?? s.uuid))];
  });
  return { kopf: { format: FORMAT, aufbereitung: 1, erzeugt: "2026-11-20T12:00:00+00:00", quelle: "datenbank", anzahl: zeilen.length,
                   spalten: [...SPALTEN], woerter, sprachnamen: SPRACHNAMEN, eintragscodes: EINTRAGSCODES }, zeilen };
}

function quelle(sender: Probesender[], speicher: Speicher = fluechtigerSpeicher()) {
  let geladen = 0;
  const q = new StatischeQuelle({ laden: async () => { geladen++; return probe(sender); }, speicher });
  return { q, speicher, geladen: () => geladen };
}

const namen = (r: Abfrageergebnis | SenderEintrag[]) => ("eintraege" in r ? r.eintraege : r).map((e) => e.name);
const zahlen = (f: { wert: string; anzahl: number }[]) => Object.fromEntries(f.map((x) => [x.wert, x.anzahl]));

// ----- Abfrage ----------------------------------------------------------------------------------------------------------

describe("Abfrage", () => {
  const sender: Probesender[] = [
    { uuid: "k", name: "Klassik", genres: ["Klassik"], tags: ["classical"], codec: "FLAC", kbps: 0, qualitaet: "verlustfrei", stimmen: 500 },
    { uuid: "p", name: "Pop", genres: ["Pop", "Hip-Hop"], tags: ["pop", "hip hop"], stimmen: 300 },
    { uuid: "r", name: "Russisch", land: "RU", sprachen: ["ru"], eintraege: ["russian"], genres: ["Nachrichten"], tags: ["news"], stimmen: 200 },
    { uuid: "l", name: "Leise", genres: ["Pop"], tags: ["pop"], kbps: 32, qualitaet: "niedrig", stimmen: 5 },
  ];

  it("filtert, sortiert, blättert über den Zeiger und zählt Facetten", async () => {
    const { q, geladen } = quelle(sender);
    await q.favorit({ uuid: "k" } as SenderEintrag, true);
    const alle = await q.abfragen({});
    expect(alle.gesamt).toBe(4);
    expect(namen(alle)).toEqual(["Klassik", "Pop", "Russisch", "Leise"]);
    const erster = alle.eintraege[0];
    expect([erster.qualitaet, erster.codec, erster.favorit, erster.genres, erster.kbps]).toEqual(["verlustfrei", "FLAC", true, ["Klassik"], null]);
    expect(erster.sprachen).toEqual([{ schluessel: "de", name: "Deutsch" }]);
    expect([erster.adresse, erster.adresse_aufgeloest, erster.erreichbar]).toEqual(["https://strom.test/k", "https://strom.test/k", true]);
    expect(namen(await q.abfragen({ laender: ["DE"], genres: ["Hip-Hop"] }))).toEqual(["Pop"]);
    expect(namen(await q.abfragen({ nur_favoriten: true, laender: ["DE"] }))).toEqual(["Klassik"]);
    expect(namen(await q.abfragen({ qualitaet: ["niedrig"] }))).toEqual(["Leise"]);
    expect(namen(await q.abfragen({ sortierung: "name" }))).toEqual(["Klassik", "Leise", "Pop", "Russisch"]);
    expect(namen(await q.abfragen({ sortierung: "bitrate" }))).toEqual(["Pop", "Russisch", "Leise", "Klassik"]);
    expect(namen(await q.abfragen({ suche: "nachrichten" }))).toEqual(["Russisch"]);      // Suchtext mit Genres
    expect(namen(await q.abfragen({ suche: "ei" }))).toEqual(["Leise"]);                // kurz: nur im Namen
    // Minus schließt aus, wie im Backend (Nutzer 20.11.2026): im Suchtext mit Genres, kurz nur im Namen; Minus allein zählt nicht
    expect(namen(await q.abfragen({ suche: "-nachrichten" }))).toEqual(["Klassik", "Pop", "Leise"]);
    expect(namen(await q.abfragen({ suche: "-ei -klassik" }))).toEqual(["Pop", "Russisch"]);
    expect(namen(await q.abfragen({ suche: "pop -" }))).toEqual(["Pop", "Leise"]);
    expect(namen(await q.abfragen({ nur_erreichbar: false }))).toHaveLength(4);

    // Seiten über den Zeiger: lückenlos, ohne Doppel, Gesamtzahl und Facetten nur auf der ersten Seite
    const gesehen: string[] = [];
    let zeiger: string | null = null;
    do {
      const s: Abfrageergebnis = await q.abfragen({ anzahl: 1, nach: zeiger });
      gesehen.push(...namen(s));
      expect(s.gesamt === null).toBe(zeiger !== null);
      expect(s.facetten === null).toBe(zeiger !== null);
      zeiger = s.weiter;
    } while (zeiger);
    expect(gesehen).toEqual(["Klassik", "Pop", "Russisch", "Leise"]);
    await expect(q.abfragen({ nach: "kaputt" })).rejects.toMatchObject({ status: 400 });
    const nachName = await q.abfragen({ sortierung: "name", anzahl: 2 });
    await expect(q.abfragen({ sortierung: "stimmen", nach: nachName.weiter })).rejects.toThrow("passt nicht zur Sortierung");
    expect(namen(await q.abfragen({ sortierung: "name", anzahl: 2, nach: nachName.weiter }))).toEqual(["Pop", "Russisch"]);

    const f = alle.facetten!;
    expect(f.genres).toContainEqual({ wert: "Hip-Hop", name: "Hip-Hop", anzahl: 1 });
    expect(zahlen(f.qualitaet).verlustfrei).toBe(1);
    expect(f.qualitaet.map((x) => x.wert)).toEqual(["verlustfrei", "hoch", "mittel", "niedrig", "unbekannt"]);
    expect(zahlen(f.laender)).toEqual({ DE: 3, RU: 1 });
    expect(f.laender[0].name).toBe("Germany");
    expect(f.kategorien).toEqual([]);
    // die Gruppe "Länder" zählt ohne ihren eigenen Filter
    expect(zahlen((await q.abfragen({ laender: ["RU"] })).facetten!.laender)).toEqual({ DE: 3, RU: 1 });
    expect(geladen()).toBe(1);                                                        // Liste einmal geladen
  });

  it("prüft die Abfrage wie das Backend", async () => {
    const { q } = quelle(sender);
    await expect(q.abfragen({ anzahl: 0 })).rejects.toMatchObject({ status: 422 });
    await expect(q.abfragen({ bewertungen: ["gibtsnicht" as never] })).rejects.toThrow("Unbekannte Bewertung");
    expect((await q.abfragen({ kategorien: [1] })).gesamt).toBe(0);                    // keine Kategorien in der Webversion
  });

  it("zeigt die Länder der Seitenleiste und die gewählten", async () => {
    const { q } = quelle([...sender, { uuid: "a", name: "Wien", land: "AT" }]);
    expect(await q.laenderLeiste()).toEqual([]);
    expect((await q.abfragen({})).facetten!.laender.map((l) => l.wert)).toEqual(["DE", "AT", "RU"]);
    await q.laenderLeisteSetzen(["at", "XYZ", "AT"]);
    expect(await q.laenderLeiste()).toEqual(["AT"]);
    expect(zahlen((await q.abfragen({ laender: ["RU"] })).facetten!.laender)).toEqual({ AT: 1, RU: 1 });
    expect(await q.laender()).toEqual([{ code: "DE", name: "Germany", anzahl: 3 }, { code: "AT", name: "Austria", anzahl: 1 },
                                        { code: "RU", name: "Russia", anzahl: 1 }]);
  });
});

describe("Varianten", () => {
  it("bündelt mit der besten vorn, zeigt nach Codec jede Variante, ein Favorit ist Vertreter", async () => {
    const { q } = quelle([
      { uuid: "gut", name: "Welle | AAC 256k", codec: "AAC", kbps: 256, qualitaet: "hoch", stimmen: 10 },
      { uuid: "schwach", name: "Welle | MP3 64k", codec: "MP3", kbps: 64, qualitaet: "niedrig", stimmen: 900, gruppe: "gut" },
    ]);
    const liste = await q.abfragen({});
    expect(liste.eintraege.map((e) => [e.uuid, e.varianten, e.gruppe])).toEqual([["gut", 2, "gut"]]);
    expect((await q.varianten("schwach")).map((e) => e.uuid)).toEqual(["gut", "schwach"]);
    expect((await q.abfragen({ codecs: ["MP3"] })).eintraege.map((e) => e.uuid)).toEqual(["schwach"]);
    expect((await q.abfragen({ varianten_buendeln: false })).gesamt).toBe(2);
    expect((await q.sender("schwach"))?.name).toBe("Welle | MP3 64k");
    expect(await q.sender("gibtsnicht")).toBeNull();
    await q.favorit({ uuid: "schwach" } as SenderEintrag, true);
    expect((await q.abfragen({})).eintraege.map((e) => e.uuid)).toEqual(["schwach"]);
  });
});

// ----- Regeln -----------------------------------------------------------------------------------------------------------

describe("Regeln", () => {
  it("Vorschau, Anlegen, Folgen, Ausschalten und Entfernen", async () => {
    const { q } = quelle([
      { uuid: "r", name: "Russisch", sprachen: ["ru"], eintraege: ["russian"] },
      { uuid: "k", name: "Kürzel", sprachen: ["ru"], eintraege: ["ru"] },
      { uuid: "d", name: "Deutsch" },
    ]);
    const entwurf = { art: "sprache" as const, schluessel: ["RU "], eintraege: [] };
    const vorschau = await q.vorschau(entwurf);
    expect([vorschau.betroffen, vorschau.neu_ausgeblendet, vorschau.favoriten]).toEqual([2, 2, 0]);
    expect(vorschau.titel).toBe("Sprache ist Russisch (ru)");
    expect(new Set(vorschau.beispiele.map((b) => b.uuid))).toEqual(new Set(["r", "k"]));
    expect((await q.abfragen({})).gesamt).toBe(3);                                     // Vorschau ändert nichts

    const aenderung = await q.anlegen(entwurf);
    const regel = aenderung.regel!;
    expect([aenderung.ausgeblendet, regel.betroffen, regel.nur_diese, regel.herkunft, regel.an]).toEqual([2, 2, 2, "nutzer", true]);
    expect(regel.entwurf).toEqual({ art: "sprache", schluessel: ["ru"], eintraege: [] });
    expect(namen(await q.abfragen({}))).toEqual(["Deutsch"]);
    await expect(q.anlegen({ art: "sprache", schluessel: ["ru"], eintraege: [] })).rejects.toMatchObject({ status: 409 });
    expect((await q.vorschau(entwurf)).gleiche_regel).toBe(regel.id);

    const grund = await q.sichtbarkeit("r");
    expect([grund.sichtbar, grund.gruende.map((g) => g.titel)]).toEqual([false, ["Sprache ist Russisch (ru)"]]);
    const seite = await q.ausgeblendet({ regel: regel.id });
    expect(seite.gesamt).toBe(2);
    expect(seite.eintraege.every((e) => e.gruende[0].regel === regel.id)).toBe(true);
    expect(seite.gruende).toEqual([{ regel: regel.id, titel: "Sprache ist Russisch (ru)", anzahl: 2 }]);
    expect((await q.ausgeblendet({ suche: "kür" })).eintraege.map((e) => e.uuid)).toEqual(["k"]);

    const aus = await q.schalten(regel.id, false);
    expect([aus.wieder_sichtbar, aus.regel?.an, aus.regel?.betroffen]).toEqual([2, false, 2]);   // Zahlen bleiben sichtbar
    expect((await q.abfragen({})).gesamt).toBe(3);
    await q.schalten(regel.id, true);
    const folgen = await q.folgen(regel.id);
    expect(folgen.wieder_sichtbar).toBe(2);
    const weg = await q.entfernen(regel.id);
    expect([weg.wieder_sichtbar, weg.regel]).toEqual([2, null]);
    expect((await q.abfragen({})).gesamt).toBe(3);
    await expect(q.entfernen("einzelsperren")).rejects.toMatchObject({ status: 400 });
    await expect(q.entfernen(regel.id)).rejects.toMatchObject({ status: 404 });
    await expect(q.schalten("gibtsnicht", true)).rejects.toMatchObject({ status: 404 });
  });

  it("gilt auch für neue Sender einer neuen Liste und trifft genaue Einträge", async () => {
    const speicher = fluechtigerSpeicher();
    const erste = quelle([{ uuid: "alt", name: "Alt", tags: ["tv"] }], speicher).q;
    const regel = (await erste.anlegen({ art: "tag", tags: [" #TV "] })).regel!;
    expect(regel.entwurf).toEqual({ art: "tag", tags: ["tv"] });
    // neue Liste: dieselben eigenen Angaben, mehr Sender
    const q = quelle([
      { uuid: "alt", name: "Alt", tags: ["tv"] }, { uuid: "neu", name: "Neu", tags: ["tv", "news"] },
      { uuid: "turm", name: "Fernsehturm", tags: ["tvturm"] },                            // kein Wortteil
      { uuid: "eintrag", name: "Eintrag", eintraege: ["ger"] }, { uuid: "ganz", name: "Ganz", eintraege: ["german"] },
    ], speicher).q;
    expect(namen(await q.abfragen({ sortierung: "name" }))).toEqual(["Eintrag", "Fernsehturm", "Ganz"]);
    expect((await q.regeln()).regeln[0].id).toBe(regel.id);
    await q.anlegen({ art: "sprache", schluessel: [], eintraege: ["ger"] });            // genau der Eintrag, nicht "german"
    expect(namen(await q.abfragen({ sortierung: "name" }))).toEqual(["Fernsehturm", "Ganz"]);
    expect((await q.sichtbarkeit("eintrag")).sichtbar).toBe(false);
    const titel = (await q.regeln()).regeln.map((r) => r.titel);
    expect(titel).toEqual(['Sprache ist "ger"', "Tag ist tv", "Einzeln ausgeblendet"]);       // neueste zuerst, Einzelsperren am Ende
  });

  it("Titel für genaue Einträge einer Sprache, Genres, Stimmen und Bewertungen", async () => {
    const { q } = quelle([{ uuid: "a", name: "A", genres: ["Pop"], stimmen: 3 }]);
    expect((await q.vorschau({ art: "sprache", schluessel: [], eintraege: ["ger", "german"] })).titel)
      .toBe('Sprache ist Deutsch, genau die Einträge "ger", "german"');
    expect((await q.vorschau({ art: "genre", genres: ["Pop", "Rock", "Jazz", "Klassik", "Folk"] })).titel)
      .toBe("Genre ist Pop, Rock, Jazz, Klassik und 1 weitere");
    const stimmen = await q.vorschau({ art: "stimmen", mindeststimmen: 5 });
    expect([stimmen.titel, stimmen.betroffen]).toEqual(["Beliebtheit unter 5 Stimmen", 1]);
    expect((await q.vorschau({ art: "bewertung", bewertungen: ["sterne:1", "religioes"] })).titel)
      .toBe("meine Einschätzung Geht so, Religiös");
    await expect(q.vorschau({ art: "werbung", stufe: "hoch" })).rejects.toThrow("Werbung");
    await expect(q.vorschau({ art: "stimmen", mindeststimmen: 0 })).rejects.toMatchObject({ status: 422 });
  });

  it("Favoriten bleiben als Ausnahme sichtbar", async () => {
    const { q } = quelle([{ uuid: "f", name: "Favorit", sprachen: ["frei:rad7-sprache"], eintraege: ["rad7-sprache"], stimmen: 1 }]);
    await q.favorit({ uuid: "f" } as SenderEintrag, true);
    const entwurf = { art: "sprache" as const, schluessel: [], eintraege: ["rad7-sprache"] };
    const vorschau = await q.vorschau(entwurf);
    expect([vorschau.betroffen, vorschau.favoriten, vorschau.neu_ausgeblendet, vorschau.favoriten_namen]).toEqual([1, 1, 0, ["Favorit"]]);
    await q.anlegen(entwurf);
    const e = (await q.abfragen({})).eintraege[0];
    expect([e.uuid, e.ausnahme.map((g) => g.titel)]).toEqual(["f", ['Sprache ist "rad7-sprache"']]);
    const { bestand } = await q.regeln();
    expect(bestand).toEqual({ gesamt: 1, sichtbar: 1, ausgeblendet: 0, verschwunden: 0, favoriten: 1, ausnahmen: 1 });
    expect((await q.regeln()).regeln[0]).toMatchObject({ betroffen: 1, favoriten: 1, nur_diese: 0 });
  });

  it("Einzelsperre und Freigabe mit Rückgängig", async () => {
    const { q } = quelle([{ uuid: "auge", name: "Auge", stimmen: 50 }, { uuid: "getroffen", name: "Getroffen", sprachen: ["ru"], eintraege: ["russian"] }]);
    const gesperrt = await q.sperren("auge");
    expect([gesperrt.sichtbar, gesperrt.gesperrt, gesperrt.gruende.map((g) => g.titel)]).toEqual([false, true, ["Einzeln ausgeblendet"]]);
    expect(namen(await q.abfragen({}))).toEqual(["Getroffen"]);
    expect((await q.vorschau({ art: "sprache", schluessel: ["ru"], eintraege: [] })).betroffen).toBe(1);
    expect((await q.entsperren("auge")).sichtbar).toBe(true);
    await q.anlegen({ art: "sprache", schluessel: ["ru"], eintraege: [] });
    const frei = await q.freigeben("getroffen");
    expect([frei.sichtbar, frei.freigegeben]).toEqual([true, true]);
    const e = (await q.abfragen({})).eintraege.find((x) => x.uuid === "getroffen")!;
    expect(e.ausnahme[0].art).toBe("sprache");
    expect((await q.freigabeZuruecknehmen("getroffen")).sichtbar).toBe(false);
    // Freigeben eines nur per Auge gesperrten Senders hebt die Sperre auf, ohne Freigabe
    await q.sperren("auge");
    expect(await q.freigeben("auge")).toMatchObject({ sichtbar: true, freigegeben: false, gesperrt: false });
    await expect(q.sperren("gibtsnicht")).rejects.toMatchObject({ status: 404 });
    await expect(q.sichtbarkeit("gibtsnicht")).rejects.toMatchObject({ status: 404 });
  });

  it("Kandidaten mit Zahlen", async () => {
    const { q } = quelle([
      { uuid: "c", name: "Chinesisch", sprachen: ["zh"], eintraege: ["chinese", "mandarin"], genres: ["Nachrichten"] },
      { uuid: "y", name: "Kanton", sprachen: ["yue"], eintraege: ["cantonese"], genres: ["Weihnachten", "Pop"], tags: ["xmas"] },
    ]);
    await q.favorit({ uuid: "c" } as SenderEintrag, true);
    const nachCode = Object.fromEntries((await q.kandidaten("sprache", "chin")).map((k) => [k.schluessel, k]));
    expect(nachCode.zh).toMatchObject({ name: "Chinesisch (Mandarin)", code: "zh", anzahl: 1, favoriten: 1 });
    expect(nachCode.yue.anzahl).toBe(1);
    expect((await q.kandidaten("sprache", "")).length).toBe(2);
    expect((await q.kandidaten("genre", "nach")).map((g) => g.name)).toEqual(["Nachrichten", "Weihnachten"]);
    expect((await q.kandidaten("tag", "XM")).map((g) => [g.name, g.anzahl])).toEqual([["xmas", 1]]);
    expect((await q.kandidaten("einzeln", "k"))).toEqual([]);                           // erst ab zwei Zeichen
    expect((await q.kandidaten("einzeln", "kan")).map((k) => [k.schluessel, k.code, k.favoriten])).toEqual([["y", "DE", 0]]);
    await q.bewerten("y", "religioes", true);
    expect(await q.kandidaten("bewertung", "")).toEqual([{ schluessel: "religioes", name: "Religiös", code: null, anzahl: 1, favoriten: 0 }]);
    await expect(q.kandidaten("werbung" as never, "")).rejects.toMatchObject({ status: 400 });
  });
});

// ----- Bewertungen, Fähigkeiten, Datei, Speicher -------------------------------------------------------------------

describe("eigene Angaben", () => {
  it("Sterne ersetzen sich, Bewertungen filtern, zählen in Facetten und tragen Regeln", async () => {
    const { q } = quelle([{ uuid: "a", name: "A", stimmen: 3 }, { uuid: "b", name: "B", stimmen: 2 }]);
    await q.bewerten("a", "sterne:3", true);
    await q.bewerten("a", "sterne:1", true);
    await q.bewerten("a", "haeufig_offline", true);
    expect((await q.abfragen({})).eintraege[0].bewertungen).toEqual(["sterne:1", "haeufig_offline"]);
    expect(namen(await q.abfragen({ bewertungen: ["sterne:1"] }))).toEqual(["A"]);
    expect((await q.abfragen({})).facetten!.bewertungen).toEqual([
      { wert: "sterne:1", name: "Geht so", anzahl: 1 }, { wert: "haeufig_offline", name: "Häufig nicht erreichbar", anzahl: 1 }]);
    await q.anlegen({ art: "bewertung", bewertungen: ["haeufig_offline"] });
    expect(namen(await q.abfragen({}))).toEqual(["B"]);
    await q.bewerten("a", "haeufig_offline", false);                                    // Regel lebt: Sender wieder da
    expect(namen(await q.abfragen({}))).toEqual(["A", "B"]);
    await q.bewerten("a", "sterne:2", false);                                           // aus nimmt die Sterne ganz weg
    expect((await q.abfragen({})).eintraege[0].bewertungen).toEqual([]);
  });

  it("meldet, was die Webversion kann, und wirft für den Rest", async () => {
    const { q } = quelle([{ uuid: "a", name: "A" }]);
    expect(q.faehig).toEqual({ abgleich: false, eigeneAdresse: false, messen: false, kategorien: false, werbung: false, datei: true });
    const e = (await q.abfragen({})).eintraege[0];
    expect(await q.wiedergabe(e)).toMatchObject({ uuid: "a", url: "https://strom.test/a", url_resolved: "https://strom.test/a", countrycode: "DE" });
    expect(await q.gespielt()).toBeNull();
    expect((await q.steckbrief(e)).adresse).toBe("https://strom.test/a");
    for (const aufruf of [q.kategorien(), q.abgleich(), q.abgleichStarten(), q.eigeneAdresse(), q.werbungWidersprechen(),
                          q.kategorieZuordnen()]) {
      await expect(aufruf).rejects.toBeInstanceOf(NichtVerfuegbar);
    }
    expect(e.werbung).toEqual({ stufe: "keine", entscheidung: null });
  });

  it("zeigt das Logo aus der Liste direkt, ohne Logo das Kürzel (RAD-105)", async () => {
    const { q } = quelle([{ uuid: "a", name: "A", logo: "https://logo.test/a.png", stimmen: 20 }, { uuid: "b", name: "B" }]);
    const [a, b] = (await q.abfragen({})).eintraege;
    expect(a.logo).toBe("https://logo.test/a.png");
    expect(q.logoAdresse(a.uuid, a.logo)).toBe("https://logo.test/a.png");
    expect(q.logoAdresse(b.uuid, b.logo)).toBeNull();
  });

  it("sichert, prüft und spielt eigene Angaben ein; der Speicher hält sie über einen Neustart", async () => {
    const sender: Probesender[] = [{ uuid: "a", name: "A", sprachen: ["ru"], eintraege: ["russian"] }, { uuid: "b", name: "B" }];
    const { q, speicher } = quelle(sender);
    await q.favorit({ uuid: "a" } as SenderEintrag, true);
    await q.bewerten("b", "sterne:2", true);
    const regel = (await q.anlegen({ art: "sprache", schluessel: ["ru"], eintraege: [] })).regel!;
    await q.sperren("b");
    await q.laenderLeisteSetzen(["DE"]);
    const datei = await q.sichern();
    const bericht = { favoriten: 1, bewertungen: 1, regeln: 1, sperren: 1, freigaben: 0 };
    expect(await q.pruefen(datei)).toEqual(bericht);

    // Neustart mit demselben Speicher: alles da
    const wieder = quelle(sender, speicher).q;
    expect((await wieder.regeln()).regeln.map((r) => r.id)).toEqual([regel.id, "einzelsperren"]);
    expect((await wieder.sichtbarkeit("b")).gesperrt).toBe(true);
    expect(await wieder.laenderLeiste()).toEqual(["DE"]);

    // in eine frische Quelle einspielen: Prüfen ändert nichts, Einspielen ersetzt
    const frisch = quelle(sender).q;
    expect(await frisch.pruefen(datei)).toEqual(bericht);
    expect((await frisch.abfragen({})).gesamt).toBe(2);
    expect(await frisch.einspielen(datei)).toEqual(bericht);
    expect((await frisch.abfragen({})).eintraege.map((e) => [e.uuid, e.favorit, e.ausnahme.length])).toEqual([["a", true, 1]]);
    expect(JSON.parse(await frisch.sichern()).regeln).toEqual(JSON.parse(datei).regeln);
  });

  it("prüft Dateien streng und übernimmt bei einem Fehler nichts", async () => {
    const { q } = quelle([{ uuid: "a", name: "A" }]);
    const gut = JSON.parse(await q.sichern());
    const falsch = async (aendern: (d: Record<string, unknown>) => void, meldung: string) => {
      const d = structuredClone(gut);
      aendern(d);
      await expect(q.pruefen(JSON.stringify(d))).rejects.toThrow(meldung);
      await expect(q.einspielen(JSON.stringify(d))).rejects.toThrow(meldung);
    };
    await expect(q.pruefen("{kein json")).rejects.toThrow("kein lesbares JSON");
    await falsch((d) => { d.art = "etwas"; }, "keine Sicherung");
    await falsch((d) => { d.fassung = 2; }, "Fassung 2");
    await falsch((d) => { d.mehr = 1; }, "unbekanntes Feld mehr");
    await falsch((d) => { delete d.sperren; }, "es fehlt sperren");
    await falsch((d) => { d.favoriten = ["a", "a"]; }, "doppelte Einträge in favoriten");
    await falsch((d) => { d.favoriten = ["a b"]; }, "ungültiger Eintrag");
    await falsch((d) => { d.bewertungen = { a: ["sterne:1", "sterne:2"] }; }, "mehr als eine Sternstufe");
    await falsch((d) => { d.bewertungen = { a: ["toll"] }; }, "unbekannte Bewertung toll");
    await falsch((d) => { d.sperren = ["a"]; d.freigaben = ["a"]; }, "gesperrt und freigegeben zugleich");
    await falsch((d) => { d.laender_leiste = ["de"]; }, "laender_leiste");
    const regel = { id: "r1", art: "genre", an: true, herkunft: "nutzer", entwurf: { art: "genre", genres: ["Pop"] },
                    angelegt_am: "2026-11-20T10:00:00.000Z", geaendert_am: "2026-11-20T10:00:00.000Z" };
    await falsch((d) => { d.regeln = [regel, { ...regel, id: "r2" }]; }, "zwei Regeln mit demselben Inhalt");
    await falsch((d) => { d.regeln = [{ ...regel, art: "werbung", entwurf: { art: "werbung", stufe: "hoch" } }]; }, "unbekannte Art werbung");
    await falsch((d) => { d.regeln = [{ ...regel, entwurf: { art: "genre", genres: [] } }]; }, "Regel 1");
    await falsch((d) => { d.regeln = [{ ...regel, art: "einzeln" }]; }, "nur die Regel einzelsperren");
    await falsch((d) => { d.regeln = [{ ...regel, angelegt_am: "gestern" }]; }, "kein Zeitpunkt");
    expect((await q.regeln()).regeln.map((r) => r.id)).toEqual(["einzelsperren"]);
    // ohne Regel der Einzelsperren kommt sie dazu
    expect(await q.einspielen(JSON.stringify({ ...gut, regeln: [regel] }))).toMatchObject({ regeln: 1 });
    expect((await q.regeln()).regeln.map((r) => r.id)).toEqual(["r1", "einzelsperren"]);
  });

  it("übernimmt eine Änderung nur, wenn der Speicher sie hält, und bewahrt unlesbare Angaben", async () => {
    let voll = false;
    const inhalt = new Map<string, string>();
    const speicher: Speicher = {
      lesen: (s) => inhalt.get(s) ?? null,
      schreiben: (s, w) => { if (voll) throw new Error("QuotaExceededError"); inhalt.set(s, w); },
    };
    const { q } = quelle([{ uuid: "a", name: "A" }], speicher);
    voll = true;
    await expect(q.favorit({ uuid: "a" } as SenderEintrag, true)).rejects.toMatchObject({ status: 507 });
    expect((await q.abfragen({})).eintraege[0].favorit).toBe(false);

    const kaputt = fluechtigerSpeicher({ [SPEICHER_SCHLUESSEL]: "{kaputt" });
    const neu = quelle([{ uuid: "a", name: "A" }], kaputt).q;
    expect((await neu.regeln()).regeln.map((r) => r.id)).toEqual(["einzelsperren"]);
    expect(kaputt.inhalt.get(`${SPEICHER_SCHLUESSEL}.unlesbar`)).toBe("{kaputt");
  });

  it("lädt eine fehlgeschlagene Liste beim nächsten Zugriff neu und lehnt fremde Formate ab", async () => {
    let versuch = 0;
    const q = new StatischeQuelle({ speicher: fluechtigerSpeicher(), laden: async () => {
      versuch++;
      if (versuch === 1) throw new Error("Netz weg");
      return probe([{ uuid: "a", name: "A" }]);
    } });
    await expect(q.abfragen({})).rejects.toThrow("Netz weg");
    expect((await q.abfragen({})).gesamt).toBe(1);
    const fremd = new StatischeQuelle({ speicher: fluechtigerSpeicher(), laden: async () => ({ kopf: { format: 9 }, zeilen: [] }) });
    await expect(fremd.abfragen({})).rejects.toThrow("Senderliste unlesbar");
  });
});

// ----- Die erzeugte Liste ---------------------------------------------------------------------------------------------

describe("web/daten/sender.json", () => {
  const datei = new URL("../../web/daten/sender.json", import.meta.url);

  it("beantwortet eine Abfrage nach dem Aufbau des Index in unter 300 ms", async () => {
    const roh: unknown = JSON.parse(readFileSync(datei, "utf-8"));
    const q = new StatischeQuelle({ laden: async () => roh, speicher: fluechtigerSpeicher() });
    let t = performance.now();
    const erste = await q.abfragen({});
    const aufbau = performance.now() - t;
    expect(erste.gesamt).toBeGreaterThan(20_000);

    const abfrage: StationQuery = { suche: "radio", laender: ["DE"], qualitaet: ["hoch", "mittel"], sortierung: "name" };
    t = performance.now();
    const r = await q.abfragen(abfrage);
    const dauer = performance.now() - t;
    expect(r.gesamt).toBeGreaterThan(0);
    expect(r.facetten?.laender.length).toBeGreaterThan(1);
    expect(dauer).toBeLessThan(300);

    // nach einer Regel: neue Sicht und neue Abfrage, ebenfalls schnell
    t = performance.now();
    await q.anlegen({ art: "stimmen", mindeststimmen: 5 });
    const danach = await q.abfragen({ suche: "jazz" });
    const mitRegel = performance.now() - t;
    expect(danach.eintraege.every((e) => e.stimmen >= 5 || e.favorit)).toBe(true);
    expect(mitRegel).toBeLessThan(300);
    console.info(`sender.json: ${erste.gesamt} sichtbar, Aufbau ${aufbau.toFixed(0)} ms, Abfrage ${dauer.toFixed(1)} ms, mit neuer Regel ${mitRegel.toFixed(1)} ms`);
  });
});
