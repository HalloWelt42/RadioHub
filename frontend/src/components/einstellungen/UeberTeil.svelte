<script lang="ts">
  // Einstellungen > Allgemein > Über (RAD-11): Info, Lizenz, Datenschutz und Nutzungsbedingungen aus /legal/<sprache>/
  // (Rückfall Englisch, dann Deutsch), je Text gekürzt mit "Mehr zeigen".
  import { t, currentLanguage } from "../../lib/i18n.svelte.js";
  import { parseMarkdown } from "../../lib/markdown.js";
  import { EINSTELLUNGEN } from "$ziel/einstellungen";
  import Karte from "./Karte.svelte";

  // welche Texte eine Fassung zeigt, sagt ihr Bauziel (die Basic ohne die technischen Informationen des Servers)
  const TEXTE = ([
    { id: "info", dateien: ["info.md"], symbol: "fa-microchip" },
    { id: "lizenz", dateien: ["lizenz.md"], symbol: "fa-scale-balanced" },
    { id: "recht", dateien: ["datenschutz.md", "agb.md"], symbol: "fa-shield-halved" },
  ] as const).filter((x) => (EINSTELLUNGEN.ueber as readonly string[]).includes(x.id));

  let inhalt = $state<Record<string, string>>({});
  let offen = $state<Record<string, boolean>>({});

  async function laden(datei: string, sprache: string): Promise<string> {
    for (const s of [...new Set([sprache, "en", "de"])]) {
      try {
        const r = await fetch(`${import.meta.env.BASE_URL}legal/${s}/${datei}`);
        if (r.ok) return await r.text();
      } catch { /* nächste Sprache */ }
    }
    return "";
  }

  $effect(() => {
    void t("einstellungen.einstellungen");          // folgt dem Sprachwechsel
    const sprache = currentLanguage() || "de";
    for (const text of TEXTE) {
      Promise.all(text.dateien.map((d) => laden(d, sprache))).then((teile) => {
        inhalt[text.id] = teile.filter(Boolean).map((md) => parseMarkdown(md)).join("<hr>");
      });
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
