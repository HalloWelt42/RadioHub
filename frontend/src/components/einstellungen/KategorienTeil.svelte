<script lang="ts">
  // Einstellungen > Radio > Kategorien (RAD-11, neues Aussehen): eigene Sammlungen von Sendern anlegen, umbenennen und
  // löschen. Löschen fragt vorher und nennt, wie viele Zuordnungen mitgehen; die Sender selbst bleiben.
  import { Rueckfrage } from "appkern-oberflaeche";
  import { api } from "../../lib/api.js";
  import { t } from "../../lib/i18n.svelte.js";
  import { actions } from "../../lib/store.svelte.js";
  import Karte from "./Karte.svelte";
  import NeuZeile from "./NeuZeile.svelte";

  interface Kategorie { id: number; name: string; station_count?: number }

  let liste = $state<Kategorie[]>([]);
  let fragt = $state<number | null>(null);
  let bearbeitet = $state<number | null>(null);
  let neuerName = $state("");

  async function laden() {
    try {
      const r = await api.getCategories("radio");
      liste = Array.isArray(r) ? r : r?.categories ?? [];
    } catch (f) {
      actions.showToast((f as Error).message, "error");
    }
  }
  $effect(() => { void laden(); });

  async function anlegen(name: string) {
    await api.createCategory(name, liste.length, "radio");
    await laden();
  }

  async function umbenennen(k: Kategorie) {
    const name = neuerName.trim();
    bearbeitet = null;
    if (!name || name === k.name) return;
    await api.updateCategory(k.id, { name });
    await laden();
  }

  async function loeschen(k: Kategorie) {
    await api.deleteCategory(k.id);
    fragt = null;
    actions.showToast(t("einstellungen.kategorien.geloescht", { name: k.name }), "success");
    await laden();
  }

  function fokus(el: HTMLInputElement) { el.focus(); el.select(); }
</script>

<Karte titel={t("einstellungen.kategorien.titel")} symbol="fa-folder" still={t("einstellungen.kategorien.hilfe")}>
  <div class="rh-regeln rh-feste" style="--aktion: calc(var(--gross) * 8.5); --weg: calc(var(--gross) * 7)">
    {#each liste as k (k.id)}
      {@const n = k.station_count ?? 0}
      <div class="rh-regel">
        <span class="rh-regel-art"><i class="fa-solid fa-folder"></i></span>
        <span class="rh-regel-text">
          {#if bearbeitet === k.id}
            <span class="rh-ordner-eingabe"><input type="text" bind:value={neuerName} maxlength="80" aria-label={t("einstellungen.kategorien.umbenennen")} use:fokus
                   onkeydown={(e) => { if (e.key === "Enter") void umbenennen(k); if (e.key === "Escape") bearbeitet = null; }} onblur={() => void umbenennen(k)} /></span>
          {:else}<b>{k.name}</b>{/if}
          <span>{n ? `${n} ${t("einstellungen.kategorien.sender")}` : t("einstellungen.kategorien.leer")}</span></span>
        <span class="rh-regel-zahl"><b>{n}</b>{t("einstellungen.kategorien.sender")}</span>
        <button class="knopf rh-regel-aktion" type="button" onclick={() => { neuerName = k.name; bearbeitet = k.id; }}><i class="fa-solid fa-pen"></i>{t("einstellungen.kategorien.umbenennen")}</button>
        <button class="knopf gefahr" type="button" onclick={() => (fragt = k.id)}><i class="fa-solid fa-trash"></i>{t("einstellungen.kategorien.loeschen")}</button>
        {#if fragt === k.id}
          <Rueckfrage frage={n ? t("einstellungen.kategorien.loeschenFrage", { name: k.name, n }) : t("einstellungen.kategorien.loeschenLeer", { name: k.name })}
                      knopf={t("einstellungen.kategorien.loeschen")} onabbrechen={() => (fragt = null)} onja={() => void loeschen(k)} />
        {/if}
      </div>
    {/each}
  </div>
  <NeuZeile platzhalter={t("einstellungen.kategorien.neu")} knopf={t("einstellungen.kategorien.anlegen")} symbol="fa-folder-plus" onanlegen={anlegen} />
</Karte>
