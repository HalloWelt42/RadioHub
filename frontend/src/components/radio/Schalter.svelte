<script lang="ts">
  // Schalter als gewöhnlicher Knopf mit eingelassenem Licht: gleich hoch wie die Knöpfe daneben, der Zustand zeigt sich
  // nur am Licht, die Fläche bleibt wie bei jedem Knopf (Mitlaufen, Mono, Behalten). Das Licht ist das Tastenlicht (Schlitz
  // oben in der Kappe) wie bei den Tasten der Kanzel, keine runde Leuchte (RAD-64).
  let { an, text, farbe = "gruen", hilfe = "", onwechsel }: {
    an: boolean;
    text: string;
    farbe?: "gruen" | "blau" | "gelb" | "rot" | "bernstein";
    hilfe?: string;
    onwechsel: (an: boolean) => void;
  } = $props();
</script>

<button class="knopf rh-schalter" type="button" aria-pressed={an} title={hilfe || undefined} onclick={() => onwechsel(!an)}>
  <ak-led art="schlitz" {farbe} zustand={an ? "an" : "aus"}></ak-led>{text}</button>
