// RAD-7: Schnellfilter als eine Wahrheit, abgeglichen mit der Adresse (Vorgabe 1). Hin und zurück ohne Verlust, frühere
// Direktlinks gelten weiter, Unsinn aus der Adresse wird verworfen, Chips nehmen genau einen Filter zurück.
import { describe, expect, it } from "vitest";
import { Filterzustand, type Ort } from "../src/lib/radio/filterzustand.svelte";
import {
  aktive, ausAdresse, ausOrt, inAdresse, leer, ohne, radioPfad, umschalten, zuAbfrage, zurueckgesetzt, type Schnellfilter,
} from "../src/lib/radio/schnellfilter";

const voll: Schnellfilter = {
  laender: ["DE", "AT"], genres: ["Rock", "Jazz, Soul"], qualitaet: ["hoch"], codecs: ["AAC"], bewertungen: ["sterne:3", "werbung"],
  kategorien: [5], nurFavoriten: true, nurErreichbar: false, stimmen: 100, bitrate: 128, suche: "wdr 5", sortierung: "name",
};

describe("Schnellfilter in der Adresse", () => {
  it("schreibt nur, was von der Vorgabe abweicht", () => {
    expect(inAdresse(leer()).toString()).toBe("");
    expect(radioPfad(leer())).toBe("/radio");
    expect(inAdresse({ ...leer(), laender: ["DE"] }).toString()).toBe("land=DE");
  });

  it("liest zurück, was es geschrieben hat", () => {
    expect(ausAdresse(inAdresse(voll))).toEqual(voll);
  });

  it("nimmt Listen mit Komma und wiederholte Schlüssel, Genres mit Komma bleiben ganz", () => {
    const f = ausAdresse(new URLSearchParams("land=de,at&land=CH&genre=Jazz%2C+Soul&codec=AAC,MP3"));
    expect(f.laender).toEqual(["DE", "AT", "CH"]);
    expect(f.genres).toEqual(["Jazz, Soul"]);
    expect(f.codecs).toEqual(["AAC", "MP3"]);
  });

  it("verwirft Unsinn und rundet Stufen nach unten", () => {
    const f = ausAdresse(new URLSearchParams("land=Deutschland&qualitaet=super&sort=zufall&stimmen=500&bitrate=abc&kategorie=x,7&bewertung=<b>"));
    expect(f.laender).toEqual([]);
    expect(f.qualitaet).toEqual([]);
    expect(f.sortierung).toBe("stimmen");
    expect(f.stimmen).toBe(100);
    expect(f.bitrate).toBe(0);
    expect(f.kategorien).toEqual([7]);
    expect(f.bewertungen).toEqual([]);
  });

  it("nur erreichbare ist die Vorgabe und steht nur ausgeschaltet in der Adresse", () => {
    expect(ausAdresse(new URLSearchParams("")).nurErreichbar).toBe(true);
    expect(inAdresse({ ...leer(), nurErreichbar: false }).toString()).toBe("erreichbar=0");
  });

  it("frühere Direktlinks gelten: /radio/search/<suche> und /radio/<uuid>", () => {
    expect(ausOrt("/radio/search/deutschlandfunk%20kultur", "").filter.suche).toBe("deutschlandfunk kultur");
    const uuid = "9606f727-0601-11e8-ae97-52543be04c81";
    const o = ausOrt(`/radio/${uuid}`, "land=DE");
    expect(o.offen).toBe(uuid);
    expect(o.filter.laender).toEqual(["DE"]);
    expect(ausOrt("/radio/keine-kennung", "").offen).toBeNull();
    expect(radioPfad({ ...leer(), laender: ["DE"] }, uuid)).toBe(`/radio/${uuid}?land=DE`);
  });

  it("baut die Abfrage der Senderquelle", () => {
    expect(zuAbfrage(voll)).toMatchObject({ suche: "wdr 5", laender: ["DE", "AT"], nur_favoriten: true, nur_erreichbar: false,
      stimmen_min: 100, bitrate_min: 128, sortierung: "name", kategorien: [5] });
    expect(zuAbfrage(leer())).toMatchObject({ stimmen_min: null, bitrate_min: null, nur_erreichbar: true });
  });
});

describe("Chips", () => {
  it("zeigen jede Abweichung und nehmen genau sie zurück", () => {
    const chips = aktive(voll);
    expect(chips.map((c) => c.art)).toEqual(["land", "land", "genre", "genre", "qualitaet", "codec", "bewertung", "bewertung",
      "kategorie", "favoriten", "erreichbar", "stimmen", "bitrate", "suche"]);
    const ohneAt = ohne(voll, { art: "land", wert: "AT" });
    expect(ohneAt.laender).toEqual(["DE"]);
    expect(ohne(voll, { art: "erreichbar", wert: "0" }).nurErreichbar).toBe(true);
    expect(aktive(leer())).toEqual([]);
  });

  it("Zurücksetzen behält die Sortierung", () => {
    expect(zurueckgesetzt(voll)).toEqual({ ...leer(), sortierung: "name" });
    expect(umschalten(["a"], "b")).toEqual(["a", "b"]);
    expect(umschalten(["a", "b"], "a")).toEqual(["b"]);
  });
});

/** Adresse zum Nachstellen: was geschrieben wird, wird wieder gelesen */
function ort(start: string): Ort & { verlauf: string[]; jetzt: string } {
  const o = {
    jetzt: start,
    verlauf: [start],
    pfad: () => o.jetzt.split("?")[0],
    abfrage: () => o.jetzt.split("?")[1] ?? "",
    ersetzen: (p: string) => { o.jetzt = p; o.verlauf[o.verlauf.length - 1] = p; },
    neu: (p: string) => { o.jetzt = p; o.verlauf.push(p); },
  };
  return o;
}

describe("Abgleich mit der Adresse", () => {
  it("Neuladen behält die Filter", () => {
    const o = ort("/radio");
    const z = new Filterzustand(o);
    z.ausAdresse();
    z.setzen({ ...leer(), laender: ["DE"], genres: ["Rock"], nurFavoriten: true });
    expect(o.jetzt).toBe("/radio?land=DE&genre=Rock&favoriten=1");
    const nachNeuladen = new Filterzustand(ort(o.jetzt));
    nachNeuladen.ausAdresse();
    expect(nachNeuladen.filter).toEqual(z.filter);
  });

  it("ändert die Adresse ohne neuen Eintrag, nur Aufklappen legt einen an", () => {
    const o = ort("/radio");
    const z = new Filterzustand(o);
    z.ausAdresse();
    z.aendern((f) => ({ ...f, suche: "jazz" }));
    z.aendern((f) => ({ ...f, sortierung: "bitrate" }));
    expect(o.verlauf).toEqual(["/radio?suche=jazz&sort=bitrate"]);
    z.oeffnen("9606f727-0601-11e8-ae97-52543be04c81");
    expect(o.verlauf).toHaveLength(2);
    expect(o.jetzt).toBe("/radio/9606f727-0601-11e8-ae97-52543be04c81?suche=jazz&sort=bitrate");
  });

  it("schreibt eine frühere Suchadresse in die neue Form um", () => {
    const o = ort("/radio/search/wdr");
    const z = new Filterzustand(o);
    z.ausAdresse();
    expect(z.filter.suche).toBe("wdr");
    expect(o.jetzt).toBe("/radio?suche=wdr");
  });

  it("setzt die Adresse nach der Rückkehr in den Bereich wieder aus dem Zustand", () => {
    const o = ort("/radio?land=FR");
    const z = new Filterzustand(o);
    z.ausAdresse();
    o.neu("/radio");   // Knopf Radio in der Navigation
    z.schreiben();
    expect(o.jetzt).toBe("/radio?land=FR");
  });
});
