<script>
  /**
   * Uhr der Weckeransicht: Chakra Petch fett, in der Höhe gestreckt, so groß wie ihr Rahmen erlaubt. Jede Ziffer steht
   * in einer Zelle von der Breite der breitesten Ziffer, der Doppelpunkt in seiner eigenen, nach Messung mittig zu den
   * Ziffern; so wackelt nichts, wenn die Zahlen wechseln.
   */
  import '@fontsource/chakra-petch/700.css';

  let { text } = $props();   // "05:34"

  const SCHRIFT = '700 100px "Chakra Petch"';
  const STRECKUNG = 1.6;     // Nutzer: "knapp 1,6-fache Höhe"
  let flaeche = $state(null);
  let zifferBreite = $state(0.6);
  let doppelpunktBreite = $state(0.3);
  let doppelpunktHoehe = $state(0);
  let groesse = $state(80);

  function anpassen() {
    if (!flaeche) return;
    const breite = flaeche.clientWidth;
    const hoehe = flaeche.clientHeight;
    groesse = Math.max(24, Math.floor(Math.min(breite / (4 * zifferBreite + doppelpunktBreite), hoehe / STRECKUNG)));
  }

  async function vermessen() {
    try { await document.fonts.load(SCHRIFT, '0123456789:'); } catch { /* Ersatzschrift misst dann */ }
    const ctx = document.createElement('canvas').getContext('2d');
    ctx.font = SCHRIFT;
    zifferBreite = Math.max(...'0123456789'.split('').map((z) => ctx.measureText(z).width)) / 100;
    doppelpunktBreite = ctx.measureText(':').width / 100;
    const mitte = (m) => (m.actualBoundingBoxAscent - m.actualBoundingBoxDescent) / 2;
    doppelpunktHoehe = (mitte(ctx.measureText('0')) - mitte(ctx.measureText(':'))) / 100;
    anpassen();
  }

  $effect(() => {
    if (!flaeche) return;
    vermessen();
    const beobachter = new ResizeObserver(anpassen);
    beobachter.observe(flaeche);
    return () => beobachter.disconnect();
  });
</script>

<div class="flaeche" bind:this={flaeche}>
  <div class="uhr" style:font-size="{groesse}px" style:--streckung={STRECKUNG} role="timer" aria-label={text}>
    {#each text.split('') as zeichen, i (i)}
      <span style:width="{zeichen === ':' ? doppelpunktBreite : zifferBreite}em"
        style:transform={zeichen === ':' ? `translateY(${-doppelpunktHoehe}em)` : null}>{zeichen}</span>
    {/each}
  </div>
</div>

<style>
  .flaeche { width: 100%; height: 100%; min-width: 0; min-height: 0; display: flex; align-items: center; justify-content: center; overflow: hidden; }
  .uhr { font-family: 'Chakra Petch', var(--hifi-font-body); font-weight: 700; line-height: 1; letter-spacing: 0; white-space: nowrap; display: flex;
    /* gestreckt ohne die Breite zu ändern */
    transform: scaleY(var(--streckung)); }
  span { display: inline-block; text-align: center; }
</style>
