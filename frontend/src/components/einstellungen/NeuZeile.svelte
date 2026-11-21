<script lang="ts">
  // Eingabe unter einer Liste (RAD-11): Name tippen, Eingabe oder Knopf legt an; leer tut nichts.
  import type { Snippet } from "svelte";

  let { platzhalter, knopf, symbol = "fa-plus", onanlegen, extra }: {
    platzhalter: string;
    knopf: string;
    symbol?: string;
    onanlegen: (name: string) => Promise<void>;
    extra?: Snippet;
  } = $props();

  let name = $state("");
  let laeuft = $state(false);

  async function anlegen() {
    const n = name.trim();
    if (!n || laeuft) return;
    laeuft = true;
    try {
      await onanlegen(n);
      name = "";
    } finally {
      laeuft = false;
    }
  }
</script>

<div class="rh-e-neu-zeile">
  <label class="suche rh-e-eingabe"><i class="fa-solid {symbol}"></i>
    <input type="text" bind:value={name} placeholder={platzhalter} aria-label={platzhalter} onkeydown={(e) => { if (e.key === "Enter") void anlegen(); }} /></label>
  {@render extra?.()}
  <button class="knopf primaer" type="button" disabled={!name.trim() || laeuft} onclick={() => void anlegen()}><i class="fa-solid fa-plus"></i>{knopf}</button>
</div>
