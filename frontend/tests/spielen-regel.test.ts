// Regel der Taste Spielen (Nutzer 20.11.2026): sie bleibt Spielen und beendet nie, beendet wird nur über Stopp.
// Gestoppt startet sie die Quelle, beim Spielen hält sie an, in der Pause geht es weiter; während der Aufnahme nichts.
import { beforeEach, describe, expect, it, vi } from "vitest";

const zustand = vi.hoisted(() => ({
  appState: {
    isPlaying: false, isPaused: false, isRecording: false, playerMode: "none",
    currentStation: null as { uuid: string; name: string } | null, currentEpisode: null, currentRecording: null,
  },
}));
const engine = vi.hoisted(() => ({
  pause: vi.fn(), resume: vi.fn(), stop: vi.fn(), playStation: vi.fn(), playPodcast: vi.fn(), playRecording: vi.fn(), togglePause: vi.fn(),
}));
vi.mock("../src/lib/store.svelte.js", () => ({ appState: zustand.appState, actions: {} }));
vi.mock("../src/lib/playerEngine.js", () => engine);

import { spielenOderPause, stoppen } from "../src/spieler/aktionen";

const SENDER = { uuid: "a", name: "Sender A" };
function setzen(teil: Partial<typeof zustand.appState>) {
  Object.assign(zustand.appState, { isPlaying: false, isPaused: false, isRecording: false, playerMode: "direct", currentStation: SENDER }, teil);
}

describe("Taste Spielen", () => {
  beforeEach(() => { for (const f of Object.values(engine)) f.mockClear(); });

  it("gestoppt: startet die gewählte Quelle", () => {
    setzen({});
    spielenOderPause();
    expect(engine.playStation).toHaveBeenCalledWith(SENDER);
    expect(engine.stop).not.toHaveBeenCalled();
  });
  it("spielt: hält an, auch beim direkten Strom, und beendet nie", () => {
    for (const playerMode of ["direct", "hls", "podcast", "recording"]) {
      setzen({ isPlaying: true, playerMode });
      spielenOderPause();
    }
    expect(engine.pause).toHaveBeenCalledTimes(4);
    expect(engine.stop).not.toHaveBeenCalled();
    expect(engine.playStation).not.toHaveBeenCalled();
  });
  it("Pause: geht weiter (die Engine verbindet einen direkten Strom neu ab live)", () => {
    setzen({ isPlaying: true, isPaused: true });
    spielenOderPause();
    expect(engine.resume).toHaveBeenCalledTimes(1);
    expect(engine.stop).not.toHaveBeenCalled();
  });
  it("während der Aufnahme: nichts", () => {
    setzen({ isPlaying: true, isRecording: true });
    spielenOderPause();
    expect(Object.values(engine).every((f) => f.mock.calls.length === 0)).toBe(true);
  });
  it("nur Stopp beendet", () => {
    setzen({ isPlaying: true });
    stoppen();
    expect(engine.stop).toHaveBeenCalledTimes(1);
  });
});
