<script lang="ts">
  // Schalter mit Licht, überall derselbe Baustein (RAD-70): der flache Taster des Appkerns, die Variante mit Licht der
  // gewöhnlichen Knöpfe (gleiche Kappe, Kante und Schrift). Gesteuert: er zeigt immer `an`; ein Klick meldet nur den
  // Wunsch über onwechsel, den neuen Stand bringt `an` zurück. Ein Symbol vor der Schrift erlaubt kurze Beschriftungen.
  // Der Taster baut sich beim Einhängen auf; ändern sich Schrift, Symbol, Farbe oder Hinweis, entsteht er neu.
  type Taster = HTMLElement & { an: boolean };
  let { an, text, symbol = "", farbe = "gruen", hilfe = "", onwechsel }: {
    an: boolean;
    text: string;
    /** Font-Awesome-Klasse vor der Schrift, etwa fa-ban */
    symbol?: string;
    farbe?: "gruen" | "blau" | "gelb" | "rot" | "bernstein";
    hilfe?: string;
    onwechsel: (an: boolean) => void;
  } = $props();

  let taster = $state<Taster>();
  $effect(() => {
    if (taster) taster.an = an;
  });

  function eingabe() {
    if (!taster) return;
    const gewuenscht = taster.an;
    taster.an = an;                     // zurück auf den gemeldeten Stand, bis `an` den neuen bringt
    onwechsel(gewuenscht);
  }
</script>

{#key `${text}|${symbol}|${farbe}|${hilfe}`}
  <ak-taster bind:this={taster} class="rh-schalter" art="flach" beschriftung={text} symbol={symbol || undefined} {farbe}
             hilfe={hilfe || undefined} an={an || undefined} oninput={eingabe}></ak-taster>
{/key}
