<script lang="ts">
  // Einstellungen > Aufnahmen > Ordner (RAD-11): wohin neue Aufnahmen gehen (Licht am aktiven Ordner, sonst der
  // Stammordner), anlegen, umbenennen, löschen. Ein Ordner mit Aufnahmen lässt sich nicht löschen (das sagt die Zeile
  // vorher, das Backend sperrt es ohnehin); ein leerer fragt vorher.
  import { Rueckfrage } from "appkern-oberflaeche";
  import { api } from "../../lib/api.js";
  import { t } from "../../lib/i18n.svelte.js";
  import { actions } from "../../lib/store.svelte.js";
  import Karte from "./Karte.svelte";
  import NeuZeile from "./NeuZeile.svelte";

  interface Ordner { id: number; name: string; is_active: number | boolean; session_count: number }

  let liste = $state<Ordner[]>([]);
  let fragt = $state<number | null>(null);
  let bearbeitet = $state<number | null>(null);
  let neuerName = $state("");
  const aktiv = $derived(liste.find((o) => o.is_active));

  async function laden() {
    try {
      liste = (await api.getRecordingFolders()).folders ?? [];
    } catch (f) {
      actions.showToast((f as Error).message, "error");
    }
  }
  $effect(() => { void laden(); });

  async function sicher(arbeit: () => Promise<unknown>) {
    try {
      await arbeit();
    } catch (f) {
      actions.showToast((f as Error).message, "error");
    }
    await laden();
  }

  function hierhin(o: Ordner | null) {
    void sicher(async () => {
      if (o) await api.activateRecordingFolder(o.id); else await api.deactivateRecordingFolder();
      actions.showToast(o ? t("einstellungen.ordner.aktivGesetzt", { name: o.name }) : t("einstellungen.ordner.stammGesetzt"), "success");
    });
  }

  function umbenennen(o: Ordner) {
    const name = neuerName.trim();
    bearbeitet = null;
    if (name && name !== o.name) void sicher(() => api.updateRecordingFolder(o.id, { name }));
  }

  function loeschen(o: Ordner) {
    fragt = null;
    void sicher(async () => {
      await api.deleteRecordingFolder(o.id);
      actions.showToast(t("einstellungen.ordner.geloescht", { name: o.name }), "success");
    });
  }

  function fokus(el: HTMLInputElement) { el.focus(); el.select(); }
</script>

<Karte titel={t("einstellungen.ordner.titel")} symbol="fa-folder-tree" still={t("einstellungen.ordner.hilfe")}>
  <div class="rh-regeln rh-feste" style="--aktion: calc(var(--gross) * 11); --weg: 94px">
    <div class="rh-regel" class:aus={!!aktiv}>
      <span class="rh-regel-art"><i class="fa-solid fa-house"></i></span>
      <span class="rh-regel-text"><b>{t("einstellungen.ordner.stamm")}</b><span>{t("einstellungen.ordner.stammHilfe")}</span></span>
      <span class="rh-regel-zahl"></span>
      <button class="knopf rh-regel-aktion" type="button" disabled={!aktiv} onclick={() => hierhin(null)}>
        <i class="fa-solid fa-circle-dot"></i>{aktiv ? t("einstellungen.ordner.hierhin") : t("einstellungen.ordner.nimmtAuf")}</button>
    </div>
    {#each liste as o (o.id)}
      <div class="rh-regel" class:aus={!o.is_active}>
        <span class="rh-regel-art"><i class="fa-solid fa-folder"></i></span>
        <span class="rh-regel-text">
          {#if bearbeitet === o.id}
            <span class="rh-ordner-eingabe"><input type="text" bind:value={neuerName} maxlength="80" aria-label={t("einstellungen.ordner.umbenennen")} use:fokus
                   onkeydown={(e) => { if (e.key === "Enter") umbenennen(o); if (e.key === "Escape") bearbeitet = null; }} onblur={() => umbenennen(o)} /></span>
          {:else}<b>{o.name}</b>{/if}
          <span>{o.is_active ? t("einstellungen.ordner.landetHier") : t("einstellungen.ordner.ordner")}</span></span>
        <span class="rh-regel-zahl"><b>{o.session_count}</b>{t("einstellungen.ordner.aufnahmen")}</span>
        <button class="knopf rh-regel-aktion" type="button" disabled={!!o.is_active} onclick={() => hierhin(o)}>
          <i class="fa-solid fa-circle-dot"></i>{o.is_active ? t("einstellungen.ordner.nimmtAuf") : t("einstellungen.ordner.hierhin")}</button>
        <span class="rh-e-zeilenknoepfe">
          <button class="rund" type="button" title={t("einstellungen.ordner.umbenennen")} aria-label="{o.name}: {t('einstellungen.ordner.umbenennen')}"
                  onclick={() => { neuerName = o.name; bearbeitet = o.id; }}><i class="fa-solid fa-pen"></i></button>
          <button class="rund" type="button" title={t("einstellungen.ordner.loeschen")} aria-label="{o.name}: {t('einstellungen.ordner.loeschen')}"
                  onclick={() => (fragt = o.id)}><i class="fa-solid fa-trash"></i></button></span>
        {#if fragt === o.id}
          {#if o.session_count}
            <p class="hinweis-band rh-e-gesperrt"><i class="fa-solid fa-lock"></i><span>{t("einstellungen.ordner.voll", { name: o.name, n: o.session_count })}</span>
              <button class="knopf" type="button" onclick={() => (fragt = null)}>{t("einstellungen.ordner.verstanden")}</button></p>
          {:else}
            <Rueckfrage frage={t("einstellungen.ordner.loeschenFrage", { name: o.name })} knopf={t("einstellungen.ordner.loeschen")}
                        onabbrechen={() => (fragt = null)} onja={() => loeschen(o)} />
          {/if}
        {/if}
      </div>
    {/each}
  </div>
  <NeuZeile platzhalter={t("einstellungen.ordner.neu")} knopf={t("einstellungen.ordner.anlegen")} symbol="fa-folder-plus"
            onanlegen={async (name) => { await api.createRecordingFolder(name); await laden(); }} />
</Karte>
