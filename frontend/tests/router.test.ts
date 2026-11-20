// RAD-7: Der Router vergleicht mit der echten Adresse samt Abfrage. Früher merkte er sich den Pfad ohne Abfrage; eine
// neue Adresse mit Schnellfiltern blieb dann stehen, und der Abgleich der Radio-Ansicht mit der Adresse lief im Kreis.
import { afterEach, beforeEach, describe, expect, it } from "vitest";

let adresse = "/";
const verlauf: string[] = [];
const stelle = (u: string) => { adresse = u; };

beforeEach(() => {
  adresse = "/radio/search/wdr";
  verlauf.length = 0;
  const location = { get pathname() { return adresse.split("?")[0]; }, get search() { const a = adresse.split("?")[1]; return a ? `?${a}` : ""; }, hash: "" };
  const history = {
    replaceState: (_: unknown, __: string, u: string) => { stelle(u); verlauf.push(`R ${u}`); },
    pushState: (_: unknown, __: string, u: string) => { stelle(u); verlauf.push(`P ${u}`); },
  };
  Object.assign(globalThis, { window: { location, addEventListener: () => {}, removeEventListener: () => {} }, history });
});
afterEach(() => { delete (globalThis as Record<string, unknown>).window; delete (globalThis as Record<string, unknown>).history; });

describe("Router und Abfrage", () => {
  it("schreibt eine Adresse, auch wenn der gemerkte Pfad ohne Abfrage gleich aussieht", async () => {
    const router = await import("../src/lib/router.js");
    router.navigate("/radio?suche=wdr", { replace: true });
    router.init(() => {});                       // merkt sich den Pfad ohne Abfrage: /radio
    router.navigate("/radio", { replace: true }); // Suche entfernt
    expect(adresse).toBe("/radio");
    router.navigate("/radio", { replace: true }); // schon da: nichts
    expect(verlauf).toEqual(["R /radio?suche=wdr", "R /radio"]);
    router.destroy();
  });
});
