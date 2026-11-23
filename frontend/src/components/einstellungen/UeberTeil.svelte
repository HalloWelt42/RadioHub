<script lang="ts">
  // Einstellungen > Allgemein > Über (RAD-11): Info, Lizenz, Datenschutz und Nutzungsbedingungen aus /legal/<sprache>/
  // (Rückfall Englisch, dann Deutsch), je Text gekürzt mit "Mehr zeigen".
  import { t, currentLanguage } from "../../lib/i18n.svelte.js";
  import { rechtstexte } from "../../lib/rechtstexte";
  import { EINSTELLUNGEN } from "$ziel/einstellungen";
  import Karte from "./Karte.svelte";

  // welche Texte eine Fassung zeigt, sagt ihr Bauziel (die Basic ohne die technischen Informationen des Servers)
  const TEXTE = ([
    { id: "info", dateien: ["info.md"], symbol: "fa-microchip" },
    { id: "lizenz", dateien: ["lizenz.md"], symbol: "fa-scale-balanced" },
    { id: "recht", dateien: EINSTELLUNGEN.recht as readonly string[], symbol: "fa-shield-halved" },
  ] as const).filter((x) => (EINSTELLUNGEN.ueber as readonly string[]).includes(x.id));

  let inhalt = $state<Record<string, string>>({});
  let offen = $state<Record<string, boolean>>({});

  $effect(() => {
    void t("einstellungen.einstellungen");          // folgt dem Sprachwechsel
    const sprache = currentLanguage() || "de";
    for (const text of TEXTE) {
      void rechtstexte(text.dateien, sprache).then((html) => (inhalt[text.id] = html));
    }
  });
</script>

{#each TEXTE as text (text.id)}
  <Karte titel={t(`einstellungen.ueber.${text.id}`)} symbol={text.symbol}>
    {#if inhalt[text.id]}
      <div class="rh-md" class:gekuerzt={!offen[text.id]}>{@html inhalt[text.id]}</div>
      <button class="knopf still rh-mehr" type="button" aria-expanded={!!offen[text.id]} onclick={() => (offen[text.id] = !offen[text.id])}>
        <i class="fa-solid {offen[text.id] ? 'fa-chevron-up' : 'fa-chevron-down'}"></i>{offen[text.id] ? t("radio.langtextWeniger") : t("radio.langtextMehr")}</button>
    {:else if inhalt[text.id] === ""}
      <p class="rh-still">{t("einstellungen.ueber.fehlt")}</p>
    {/if}
  </Karte>
{/each}
