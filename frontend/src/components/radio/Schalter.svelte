<script lang="ts">
  // Schalter als gewöhnlicher Knopf mit eingelassenem Licht: gleich hoch wie die Knöpfe daneben, der Zustand zeigt sich
  // nur am Licht, die Fläche bleibt wie bei jedem Knopf (Mitlaufen, Mono, Behalten). Das Licht ist das Tastenlicht (Schlitz
  // oben in der Kappe) wie bei den Tasten der Kanzel, keine runde Leuchte (RAD-64).
  // Ein Symbol vor der Schrift erlaubt kurze Beschriftungen; dann nennt `name` den Schalter für Vorleser ganz (RAD-59).
  let { an, text, symbol = "", name = "", farbe = "gruen", hilfe = "", onwechsel }: {
    an: boolean;
    text: string;
    /** Font-Awesome-Klasse vor der Schrift, etwa fa-ban */
    symbol?: string;
    /** voller Name für Vorleser, wenn die Schrift kurz ist */
    name?: string;
    farbe?: "gruen" | "blau" | "gelb" | "rot" | "bernstein";
    hilfe?: string;
    onwechsel: (an: boolean) => void;
  } = $props();
</script>

<button class="knopf rh-schalter" type="button" aria-pressed={an} aria-label={name || undefined} title={hilfe || undefined} onclick={() => onwechsel(!an)}>
  <ak-led art="schlitz" {farbe} zustand={an ? "an" : "aus"}></ak-led>{#if symbol}<i class="fa-solid {symbol}" aria-hidden="true"></i>{/if}{text}</button>
