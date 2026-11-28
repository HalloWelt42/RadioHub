<script lang="ts">
  // Suchfeld mit Verlauf (Sender am Rechner und am Telefon, Folgen der Podcasts): sucht nach kurzer Pause ab zwei
  // Zeichen, leer sofort; die letzten Suchen klappen unter dem leeren Feld auf (wählen, Verlauf löschen). Gemerkt wird
  // mit Eingabe oder beim Verlassen des Felds, nicht jeder Zwischenstand beim Tippen. Ohne Angaben: die Sendersuche.
  import { untrack } from "svelte";
  import { geraet } from "../../lib/geraet.svelte.js";
  import { t } from "../../lib/i18n.svelte.js";
  import { senderSuchverlauf, type Suchverlauf } from "../../lib/radio/suchverlauf";

  let { wert, onsuche, platzhalter = "", beschriftung = "", hilfe = "", name = "sender-suche", gedaechtnis = senderSuchverlauf, sofortFokus = false }: {
    wert: string; onsuche: (suche: string) => void; platzhalter?: string; beschriftung?: string; hilfe?: string; name?: string;
    /** beim Erscheinen gleich ins Feld (etwa nach "Abonnieren") */
    sofortFokus?: boolean;
    /** wo der Verlauf liegt (je Bereich einer) */
    gedaechtnis?: Suchverlauf;
  } = $props();
  const merken = (s: string) => gedaechtnis.merken(s);
  $effect(() => { if (sofortFokus) untrack(() => feld?.focus()); });
  const vergessen = () => gedaechtnis.vergessen();

  const PAUSE_MS = 300;
  let text = $state("");
  let verlauf = $state<string[]>(untrack(() => gedaechtnis.alle()));
  let offen = $state(false);
  let feld = $state<HTMLInputElement>();
  let wurzel = $state<HTMLElement>();
  let uhr: ReturnType<typeof setTimeout> | undefined;
  /** zuletzt gemeldete Suche: kommt sie zurück, ist es die eigene; jede andere kam von außen */
  let gemeldet: string | null = null;

  // von außen geändert (Chip entfernt, Zurücksetzen, Adresse): das Feld folgt, ohne das Tippen zu stören
  $effect(() => {
    const w = wert;
    untrack(() => {
      if (w === gemeldet) return;
      gemeldet = w;
      text = w;
    });
  });

  function melden(s: string) {
    gemeldet = s;
    onsuche(s);
  }

  function suchen(sofort = false) {
    clearTimeout(uhr);
    const s = text.trim();
    if (s.length === 1) return;
    if (sofort) melden(s);
    else uhr = setTimeout(() => melden(s), PAUSE_MS);
  }

  function eingabe() {
    offen = !text && verlauf.length > 0;
    suchen();
  }

  function taste(e: KeyboardEvent) {
    if (e.key === "Enter") {
      suchen(true);
      verlauf = merken(text);
      offen = false;
    } else if (e.key === "Escape" && offen) {
      e.stopPropagation();
      offen = false;
    }
  }

  function waehlen(s: string) {
    text = s;
    offen = false;
    verlauf = merken(s);
    suchen(true);
    if (geraet.telefon) feld?.blur();   // die Tastatur gibt die Treffer frei
  }

  function leeren() {
    text = "";
    suchen(true);
    feld?.focus();
  }

  function verlassen(e: FocusEvent) {
    if (wurzel?.contains(e.relatedTarget as Node | null)) return;
    offen = false;
    if (text.trim().length >= 2) verlauf = merken(text);
  }
</script>

<div class="auswahl rh-suchfeld" bind:this={wurzel} onfocusout={verlassen}>
  <label class="suche" role="search">
    <i class="fa-solid fa-magnifying-glass"></i>
    <input bind:this={feld} bind:value={text} type="search" {name} placeholder={platzhalter || t("radio.suchePlatzhalter")}
           aria-label={beschriftung || t("radio.sucheLabel")} title={hilfe || t("radio.sucheMinusHilfe")} autocomplete="off" spellcheck="false" enterkeyhint="search" oninput={eingabe} onkeydown={taste}
           onfocus={() => (offen = !text && verlauf.length > 0)} />
    {#if text}
      <button class="rund" type="button" aria-label={t("radio.sucheLeeren")} title={t("radio.sucheLeeren")} onclick={leeren}>
        <i class="fa-solid fa-xmark"></i></button>
    {/if}
  </label>
  {#if offen && verlauf.length}
    <!-- Der Fokus bleibt beim Antippen im Feld: Safari (Telefon wie Rechner) gibt Knöpfen keinen Fokus, sonst schlösse das
         Verlassen des Felds die Liste vor dem Tipp, und nichts würde gewählt (RAD-155) -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="auswahl-liste" role="listbox" tabindex="-1" aria-label={t("radio.verlauf")} onmousedown={(e) => e.preventDefault()}>
      {#each verlauf as s (s)}
        <button type="button" role="option" aria-selected="false" onclick={() => waehlen(s)}><i class="fa-solid fa-clock-rotate-left"></i>{s}</button>
      {/each}
      <button type="button" class="rh-verlauf-weg" onclick={() => { verlauf = vergessen(); offen = false; feld?.focus(); }}>
        {t("radio.verlaufLoeschen")}</button>
    </div>
  {/if}
</div>
