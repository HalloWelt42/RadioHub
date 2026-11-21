<script lang="ts">
  // Wellenform des Schnitts (Entwurf aufnahmen.html): groß der Ausschnitt mit Stücknamen, Markern (Nummer, ziehbar) und
  // Abspielkopf, klein die Übersicht der ganzen Aufnahme mit dem Rahmen des Ausschnitts. Klick springt an die Stelle,
  // Doppelklick (groß) setzt einen Marker, in der Übersicht verschiebt ein Klick den Ausschnitt. Farben aus den Marken
  // (über ein verstecktes Element aufgelöst, damit auch Mischungen wie color-mix gehen), neu bei Hell und Dunkel.
  import { onMount } from "svelte";
  import type { Stueck } from "../../lib/schnitt";

  let { spitzen, dauer, von, bis, marker, stuecke, kopf, hoehe = 1, gross = true, beschriftung, onsuchen, onmarker, onziehen, onausschnitt }: {
    /** 100 Werte je Sekunde, 0 bis 1; noch nicht geladene sind 0 */
    spitzen: Float32Array;
    dauer: number;
    von: number;
    bis: number;
    marker: number[];
    stuecke: Stueck[];
    kopf: number;
    hoehe?: number;
    gross?: boolean;
    beschriftung: string;
    onsuchen: (t: number) => void;
    onmarker?: (t: number) => void;
    onziehen?: (i: number, t: number) => void;
    onausschnitt?: (mitte: number) => void;
  } = $props();

  let leinwand = $state<HTMLCanvasElement>();
  let probe = $state<HTMLElement>();
  let breite = $state(0);
  let thema = $state(0);
  let gezogen = $state<number | null>(null);
  const RATE = 100;

  function farbe(name: string): string {
    if (!probe) return "#888";
    probe.style.color = `var(${name})`;
    return getComputedStyle(probe).color;
  }

  /** Zeit an der Stelle x bei der Breite w (beim Zeigen frisch gemessen, nicht die gemerkte Breite des Zeichnens) */
  const zeit = (x: number, w: number) => (gross ? von + (x / Math.max(1, w)) * (bis - von) : (x / Math.max(1, w)) * dauer);

  function zeichnen(): void {
    const c = leinwand?.getContext("2d");
    if (!leinwand || !c || !breite) return;
    void thema;
    const dpr = devicePixelRatio || 1, h = leinwand.clientHeight, w = breite;
    leinwand.width = w * dpr;
    leinwand.height = h * dpr;
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    const a = gross ? von : 0, b = gross ? bis : dauer;
    const x = (t: number) => ((t - a) / Math.max(0.001, b - a)) * w;
    const oben = gross ? 18 : 0, mitte = oben + (h - oben) / 2, halb = (h - oben) / 2 - 2;
    const schrift = getComputedStyle(leinwand).fontFamily;
    stuecke.forEach((s, i) => {
      c.fillStyle = farbe(i % 2 ? "--flaeche-2" : "--mulde");
      c.fillRect(x(s.von), 0, x(s.bis) - x(s.von), h);
      if (!s.behalten) { c.fillStyle = farbe("--rh-verworfen"); c.fillRect(x(s.von), 0, x(s.bis) - x(s.von), h); }
      if (gross && x(s.bis) - x(s.von) > 60) {
        c.fillStyle = farbe("--text-3");
        c.font = `600 11px ${schrift}`;
        c.fillText(s.name.slice(0, 48), Math.max(0, x(s.von)) + 6, 13);
      }
    });
    const gruen = farbe("--led-gruen");
    const verworfen = stuecke.filter((s) => !s.behalten);
    for (let px = 0; px < w; px += gross ? 2 : 1) {
      const t0 = a + (px / w) * (b - a), t1 = a + ((px + (gross ? 2 : 1)) / w) * (b - a);
      let spitze = 0;
      for (let i = Math.floor(t0 * RATE); i < Math.min(spitzen.length, Math.ceil(t1 * RATE) + 1); i++) spitze = Math.max(spitze, spitzen[i] || 0);
      const weg = verworfen.some((s) => t0 >= s.von && t0 < s.bis);
      c.globalAlpha = weg ? 0.35 : 1;
      c.fillStyle = gruen;
      const y = Math.max(0.5, Math.min(1, spitze * hoehe) * halb);
      c.fillRect(px, mitte - y, gross ? 1.4 : 1, y * 2);
    }
    c.globalAlpha = 1;
    const akzent = farbe("--akzent"), grund = farbe("--hg");
    marker.forEach((m, i) => {
      const mx = x(m);
      if (mx < -10 || mx > w + 10) return;
      c.fillStyle = akzent;
      c.fillRect(mx - 1, gross ? 16 : 0, 2, h);
      if (gross) {
        c.beginPath(); c.arc(mx, 22, 8, 0, Math.PI * 2); c.fill();
        c.fillStyle = grund; c.font = `700 10px ${schrift}`; c.textAlign = "center"; c.fillText(String(i + 1), mx, 25.5); c.textAlign = "left";
      }
    });
    c.fillStyle = farbe("--led-blau");
    c.fillRect(x(kopf) - 1, 0, 2, h);
    if (!gross) { c.strokeStyle = farbe("--text"); c.lineWidth = 1.5; c.strokeRect(x(von) + 0.75, 0.75, Math.max(2, x(bis) - x(von) - 1.5), h - 1.5); }
  }

  $effect(() => {
    void [spitzen, dauer, von, bis, marker, stuecke, kopf, hoehe, breite, thema];
    zeichnen();
  });

  onMount(() => {
    const beobachter = new ResizeObserver(() => { breite = leinwand?.clientWidth ?? 0; });
    if (leinwand) beobachter.observe(leinwand);
    const themenwechsel = new MutationObserver(() => thema++);
    themenwechsel.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme", "data-vorlage"] });
    return () => { beobachter.disconnect(); themenwechsel.disconnect(); };
  });

  function stelle(e: PointerEvent | MouseEvent): number {
    const r = leinwand!.getBoundingClientRect();
    return Math.min(dauer, Math.max(0, zeit(e.clientX - r.left, r.width)));
  }

  function naherMarker(e: PointerEvent): number | null {
    if (!gross) return null;
    const r = leinwand!.getBoundingClientRect();
    const x = e.clientX - r.left, proPx = (bis - von) / Math.max(1, r.width);
    const i = marker.findIndex((m) => Math.abs((m - von) / proPx - x) < 7);
    return i >= 0 ? i : null;
  }

  function runter(e: PointerEvent) {
    gezogen = naherMarker(e);
    if (gezogen !== null) leinwand!.setPointerCapture(e.pointerId);
  }

  function bewegen(e: PointerEvent) {
    if (gezogen !== null) onziehen?.(gezogen, stelle(e));
  }

  function hoch(e: PointerEvent) {
    if (gezogen !== null) { gezogen = null; return; }
    if (gross) onsuchen(stelle(e));
    else onausschnitt?.(stelle(e));
  }
</script>

<i class="rh-farbprobe" bind:this={probe} hidden></i>
<canvas bind:this={leinwand} class:gross aria-label={beschriftung} onpointerdown={runter} onpointermove={bewegen} onpointerup={hoch}
        ondblclick={(e) => onmarker?.(stelle(e))}></canvas>
