// Abschnitte des Zeitversatzes (RAD-46): Titel an einer Stelle, Vorheriger und Nächster Titel (Werbung wird
// übersprungen, kurz nach dem Anfang geht es zum vorigen), Bereich aus zwei Titeln, Zeitleiste und Ausschnitt, dazu
// die Striche und die Aufnahme auf dem Balken der Kanzel. Daten wie 90s90s am 22.11.2026.
import { describe, expect, it } from "vitest";
import { anfangstitel, bei, bereichAus, fenster, imBereich, naechster, prozent, vorheriger, type Abschnitt } from "../src/lib/radio/abschnitte";
import { lageZuSekunde, pufferAufnahme, pufferSekunde, pufferStriche, sekundeZuLage, type Stand } from "../src/spieler/kanzel";

const A = (von: number, bis: number, titel: string, art: Abschnitt["art"] = "titel", laufend = false): Abschnitt =>
  ({ von, bis, titel, art, sicher: true, laufend, komplett: von > 0 && art !== "werbung" && !laufend, gesichert: "" });
const LISTE: Abschnitt[] = [A(0, 9.4, "90s90s - DIGITAL WEB", "werbung"), A(9.4, 288.3, "OMC - How Bizarre"),
  A(288.3, 524.9, "Shaggy - Boombastic"), A(524.9, 600, "Werbung", "werbung"), A(600, 845, "Cut 'n' Move - Give It Up", "titel", true)];

describe("Abschnitte", () => {
  it("findet den Abschnitt an einer Stelle, am Ende den laufenden", () => {
    expect(bei(LISTE, 100)?.titel).toBe("OMC - How Bizarre");
    expect(bei(LISTE, 288.3)?.titel).toBe("Shaggy - Boombastic");
    expect(bei(LISTE, 900)?.laufend).toBe(true);
    expect(bei([], 5)).toBeNull();
  });

  it("Vorheriger Titel: an den Anfang, kurz danach zum vorigen, über Werbung hinweg", () => {
    expect(vorheriger(LISTE, 400)).toBe(288.3);            // mitten in Shaggy: an seinen Anfang
    expect(vorheriger(LISTE, 290)).toBe(9.4);              // kurz nach dem Anfang: der vorige
    expect(vorheriger(LISTE, 601)).toBe(288.3);            // vor dem laufenden liegt Werbung: übersprungen
    expect(vorheriger(LISTE, 10)).toBeNull();              // davor nur der Vorlauf
  });

  it("Nächster Titel überspringt Werbung, am laufenden Ende gibt es keinen", () => {
    expect(naechster(LISTE, 100)).toBe(288.3);
    expect(naechster(LISTE, 400)).toBe(600);
    expect(naechster(LISTE, 700)).toBeNull();
  });

  it("Bereich aus zwei Titeln in beliebiger Reihenfolge", () => {
    const b = bereichAus(LISTE[2], LISTE[1]);
    expect(b).toEqual({ von: 9.4, bis: 524.9 });
    expect(imBereich(LISTE, b.von, b.bis).map((a) => a.titel)).toEqual(["OMC - How Bizarre", "Shaggy - Boombastic"]);
  });

  it("Zeitleiste: Prozent gekappt, Ausschnitt um die Stelle und am Rand", () => {
    expect(prozent(50, 0, 200)).toBe(25);
    expect(prozent(-5, 0, 200)).toBe(0);
    expect(fenster(1000, 600, 0, 4790)).toEqual([700, 1300]);
    expect(fenster(4700, 600, 0, 4790)).toEqual([4190, 4790]);   // am Ende: bis live
    expect(fenster(100, 9000, 0, 4790)).toEqual([0, 4790]);       // breiter als der Puffer: alles
  });
});

describe("Balken der Kanzel", () => {
  // 2 h größter Puffer, gefüllt von Stück 100 bis 899 (800 s)
  const stand = { hlsStatus: { segment_duration: 1, max_segments: 7200, first_segment: 100, last_segment: 899 } } as unknown as Stand;

  it("Striche an den Titelgrenzen im Maßstab des größten Puffers", () => {
    const s = pufferStriche(stand, [{ von: 100 }, { von: 460 }, { von: 820 }, { von: 950 }]);
    expect(s).toEqual([5, 10]);                               // der älteste und Grenzen nach live fallen weg
  });

  it("Aufnahme: die letzten Sekunden bis live", () => {
    const r = pufferAufnahme(stand, 180)!;                    // live ist Stück 899 + 1 = 900 s, Aufnahme ab 720 s
    expect(r.von).toBeCloseTo(((720 - 100) / 7200) * 100, 6);
    expect(r.breite).toBeCloseTo(2.5, 6);
    expect(pufferAufnahme(stand, 0)).toBeNull();
  });

  it("Stelle auf dem Balken und Lage des Reglers in Sekunden und zurück", () => {
    expect(pufferSekunde(stand, 5)).toBe(460);
    expect(pufferSekunde(stand, 50)).toBeNull();              // jenseits des Gepufferten
    expect(lageZuSekunde(stand, 50)).toBe(500);
    expect(sekundeZuLage(stand, 500)).toBe(50);
  });
});

describe("Titel am Beginn einer Aufnahme (RAD-147)", () => {
  const liste = [A(0, 100, "Vorher"), A(100, 300, "Meiner", "titel", true)];
  it("trifft den Titel auch, wenn Uhr und Puffer einige Sekunden auseinander liegen", () => {
    for (const abweichung of [-3, -1, 0, 1, 3]) expect(anfangstitel(liste, 140, 40 + abweichung)).toBe("Meiner");
  });
  it("kurzer Vorlauf: nie über das Ende des Puffers hinaus", () => {
    expect(anfangstitel(liste, 101, 1)).toBe("Meiner");
  });
  it("ohne Abschnitte oder in der Werbung steht er noch nicht fest", () => {
    expect(anfangstitel([], 140, 40)).toBe("");
    expect(anfangstitel([A(0, 300, "Werbung", "werbung")], 140, 40)).toBe("");
  });
});
