<script lang="ts">
  // Ein Punktfeld (lib/telefon/punktmatrix.js) als Canvas: zeichnet neu, wenn sich Inhalt, Farben oder Größe ändern.
  // Farben kommen als Namen von Marken (--an, --aus, --akzent ...) aus der Gestaltung, damit Hell, Dunkel und Nacht nur
  // in der Stildatei stehen. `lauf`: ist eine Textebene breiter als das Feld, läuft sie durch (nicht bei RGB-Feldern).
  import { breite, zeichnen } from "../../../lib/telefon/punktmatrix.js";

  type Farbe = string | ((x: number, y: number) => string);
  export interface Ebene { text: string; x?: number; y: number; mass?: number; farbe: Farbe; mitte?: boolean; schrift?: "klein"; lauf?: boolean;
    /** Breite des Fensters der Laufschrift in Spalten (ohne: bis zum rechten Rand) */
    fenster?: number }
  export interface Bild { x: number; y: number; pixel: string[]; farben: Record<string, string> }

  let { spalten, zeilen, ebenen = [], bilder = [], aus = "--aus", form = "rund", glanz = true, klasse = "matrix", modus = "" }: {
    spalten: number; zeilen: number; ebenen?: Ebene[]; bilder?: Bild[]; aus?: string; form?: "rund" | "quadrat"; glanz?: boolean; klasse?: string;
    /** Modus der Gestaltung: ein Wechsel liest die Farbmarken neu */
    modus?: string;
  } = $props();

  let canvas: HTMLCanvasElement | undefined = $state();
  let groesse = $state(0);
  let lauf = $state(0);

  /** Marke oder fester Wert: "--akzent" wird zur Farbe der Gestaltung */
  function aufloesen(el: HTMLElement, f: Farbe): Farbe {
    return typeof f === "string" && f.startsWith("--") ? getComputedStyle(el).getPropertyValue(f).trim() : f;
  }

  const laeuft = $derived(ebenen.some((e) => e.lauf));
  $effect(() => {
    if (!laeuft) return;
    const takt = setInterval(() => { lauf += 1; }, 160);
    return () => clearInterval(takt);
  });

  $effect(() => {
    if (!canvas) return;
    const el = canvas;
    const beobachter = new ResizeObserver(() => { groesse = el.clientWidth * 10000 + el.clientHeight; });
    beobachter.observe(el);
    return () => beobachter.disconnect();
  });

  $effect(() => {
    void groesse; void modus;
    if (!canvas) return;
    const el = canvas;
    const sichtbar = ebenen.map((e) => {
      const farbe = aufloesen(el, e.farbe);
      if (!e.lauf) return { ...e, farbe };
      // Laufschrift wie auf echten Matrixanzeigen: zeichenweise im eigenen Fenster, mit Lücke zwischen den Durchläufen
      const frei = e.fenster ?? spalten - (e.x ?? 0);
      if (breite(e.text, e.mass ?? 1, e.schrift) <= frei) return { ...e, farbe };
      const zeichen = Math.max(1, Math.floor((frei + (e.mass ?? 1)) / (6 * (e.mass ?? 1))));
      const band = `${e.text}   `;
      const start = lauf % band.length;
      return { ...e, farbe, text: (band + band).slice(start, start + zeichen) };
    });
    zeichnen(el, { spalten, zeilen, aus: aufloesen(el, aus) as string, ebenen: sichtbar, bilder, form, glanz });
  });
</script>

<canvas class={klasse} bind:this={canvas}></canvas>
