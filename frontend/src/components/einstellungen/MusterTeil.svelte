<script lang="ts">
  // Einstellungen > Aufnahmen > Titel ignorieren (RAD-11): Titel im Strom, die eine Aufnahme nicht in Stücke teilen.
  // Eingebaute Muster bleiben (auch das Backend schützt sie), eigene lassen sich nach Rückfrage entfernen.
  import { Rueckfrage } from "appkern-oberflaeche";
  import { api } from "../../lib/api.js";
  import { t } from "../../lib/i18n.svelte.js";
  import { actions } from "../../lib/store.svelte.js";
  import Karte from "./Karte.svelte";
  import NeuZeile from "./NeuZeile.svelte";

  interface Muster { id: number; pattern: string; match_type: "exact" | "contains"; source: string }

  let liste = $state<Muster[]>([]);
  let fragt = $state<number | null>(null);
  let art = $state<"exact" | "contains">("exact");

  async function laden() {
    try {
      liste = (await api.getIcyIgnoreList()).items ?? [];
    } catch (f) {
      actions.showToast((f as Error).message, "error");
    }
  }
  $effect(() => { void laden(); });

  async function entfernen(m: Muster) {
    fragt = null;
    try {
      await api.removeIcyIgnore(m.id);
      actions.showToast(t("einstellungen.muster.entfernt", { muster: m.pattern }), "success");
    } catch (f) {
      actions.showToast((f as Error).message, "error");
    }
    await laden();
  }
</script>

<Karte titel={t("einstellungen.muster.titel")} symbol="fa-ban" still={t("einstellungen.muster.hilfe")}>
  <div class="rh-regeln rh-feste" style="--aktion: 0px; --weg: calc(var(--gross) * 8)">
    {#each liste as m (m.id)}
      {@const eigen = m.source === "user"}
      <div class="rh-regel">
        <ak-led farbe="gelb" zustand="an" groesse="klein"></ak-led>
        <span class="rh-regel-art" title={m.match_type === "exact" ? t("einstellungen.muster.genauHilfe") : t("einstellungen.muster.enthaeltHilfe")}>
          <i class="fa-solid {m.match_type === 'exact' ? 'fa-equals' : 'fa-magnifying-glass'}"></i></span>
        <span class="rh-regel-text"><b>{m.pattern}</b>
          <span>{m.match_type === "exact" ? t("einstellungen.muster.genauHilfe") : t("einstellungen.muster.enthaeltHilfe")} · {eigen ? t("einstellungen.muster.eigenes") : t("einstellungen.muster.eingebaut")}</span></span>
        <span class="rh-regel-zahl"></span>
        {#if eigen}
          <button class="knopf gefahr" type="button" onclick={() => (fragt = m.id)}><i class="fa-solid fa-trash"></i>{t("einstellungen.entfernen")}</button>
        {:else}
          <span class="rh-geltung fest" title={t("einstellungen.muster.eingebautHilfe")}><i class="fa-solid fa-lock"></i>{t("einstellungen.muster.eingebaut")}</span>
        {/if}
        {#if fragt === m.id}
          <Rueckfrage frage={t("einstellungen.muster.loeschenFrage", { muster: m.pattern })} knopf={t("einstellungen.entfernen")}
                      onabbrechen={() => (fragt = null)} onja={() => void entfernen(m)} />
        {/if}
      </div>
    {/each}
  </div>
  <NeuZeile platzhalter={t("einstellungen.muster.neu")} knopf={t("einstellungen.muster.hinzu")}
            onanlegen={async (muster) => { await api.addIcyIgnore(muster, art); await laden(); }}>
    {#snippet extra()}
      <div class="segment" role="group" aria-label={t("einstellungen.muster.titel")}>
        <button type="button" class:aktiv={art === "exact"} aria-pressed={art === "exact"} onclick={() => (art = "exact")}><i class="fa-solid fa-equals"></i>{t("einstellungen.muster.genau")}</button>
        <button type="button" class:aktiv={art === "contains"} aria-pressed={art === "contains"} onclick={() => (art = "contains")}><i class="fa-solid fa-magnifying-glass"></i>{t("einstellungen.muster.enthaelt")}</button>
      </div>
    {/snippet}
  </NeuZeile>
</Karte>
