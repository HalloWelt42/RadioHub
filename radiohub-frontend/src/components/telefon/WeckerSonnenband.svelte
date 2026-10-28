<script>
  /** Band über 24 Stunden: hell der Tag (Sonnenauf- bis -untergang), dunkel die Nacht, der Strich ist jetzt. */
  let { jetzt, sonne = null } = $props();

  const anteil = (d) => ((d.getHours() * 60 + d.getMinutes()) / 1440) * 100;
  const hhmm = (d) => `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  const tag = $derived(
    !sonne ? null
      : sonne.polar === 'tag' ? { von: 0, bis: 100 }
      : sonne.polar === 'nacht' ? null
      : { von: anteil(sonne.aufgang), bis: anteil(sonne.untergang) }
  );
</script>

<div class="band" aria-hidden="true">
  <div class="nachtteil"></div>
  {#if tag}<div class="tag" style:left="{tag.von}%" style:right="{100 - tag.bis}%"></div>{/if}
  <div class="jetzt" style:left="{anteil(jetzt)}%"></div>
  {#if sonne && !sonne.polar}
    <span class="m" style:left="{anteil(sonne.aufgang)}%">{hhmm(sonne.aufgang)}</span>
    <span class="m" style:left="{anteil(sonne.untergang)}%">{hhmm(sonne.untergang)}</span>
  {/if}
</div>

<style>
  .band { position: relative; height: 40px; flex: none; margin: 0 24px; }
  .nachtteil, .tag { position: absolute; top: 12px; height: 6px; border-radius: 3px; }
  .nachtteil { left: 0; right: 0; background: var(--w-fein); }
  .tag { background: var(--w-akzent); opacity: 0.6; }
  .jetzt { position: absolute; top: 4px; width: 3px; height: 22px; margin-left: -1.5px; background: var(--w-text); border-radius: 2px; }
  .m { position: absolute; top: 22px; font-size: 15px; color: var(--w-text-2); transform: translateX(-50%); font-variant-numeric: tabular-nums; }
</style>
