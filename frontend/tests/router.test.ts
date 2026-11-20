// RAD-7: Der Router vergleicht mit der echten Adresse samt Abfrage. Früher merkte er sich den Pfad ohne Abfrage; eine
// neue Adresse mit Schnellfiltern blieb dann stehen, und der Abgleich der Radio-Ansicht mit der Adresse lief im Kreis.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

// RAD-4: In der Webversion liegt die App unter einer Basis (GitHub Pages: /RadioHub/). Die App rechnet nur mit Pfaden
// ohne Basis; der Router setzt sie beim Schreiben an und nimmt sie beim Lesen ab, auch mit Abfrage und tiefer Adresse.
describe("Router mit Basis der Webversion", () => {
  afterEach(() => { vi.unstubAllEnvs(); vi.resetModules(); });

  it("liest und schreibt Pfade unter der Basis", async () => {
    vi.stubEnv("BASE_URL", "/RadioHub/");
    vi.resetModules();
    const router = await import("../src/lib/router.js");
    adresse = "/RadioHub/radio/abc?land=DE";
    expect(router.appPfad()).toBe("/radio/abc");
    expect(router.init(() => {}).tab).toBe("radio");
    expect(verlauf).toEqual([]);                          // tiefe Adresse bleibt, wie sie ist
    router.navigate("/einstellungen/radio/regeln");
    expect(adresse).toBe("/RadioHub/einstellungen/radio/regeln");
    expect(router.current().tab).toBe("settings");
    adresse = "/RadioHub/";
    router.init(() => {});
    expect(adresse).toBe("/RadioHub/radio");              // Wurzel der Seite führt zum Radio, unter der Basis
    router.destroy();
  });
});
