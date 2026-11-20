<script lang="ts">
  // Kopf der Liste (Entwurf rechner.html): Knopf Filter (unter 1100 Pixel), Trefferzähler als Segmentanzeige mit der
  // echten Gesamtzahl, Suche mit Verlauf, Neu laden (sortiert wird am Tabellenkopf, RAD-25) (nur die Liste, Vorgabe 4); darunter die aktiven Filter
  // als Chips, der Hinweis auf die durch Regeln ausgeblendeten Sender mit Sprung und Alle zurücksetzen.
  import { t } from "../../lib/i18n.svelte.js";
  import { actions } from "../../lib/store.svelte.js";
  import * as sfx from "../../lib/uiSounds.js";
  import { bewertungName, landName, qualitaetName, zahl } from "../../lib/radio/anzeige";
  import { aktive, ohne, zurueckgesetzt, type Chip, type Schnellfilter } from "../../lib/radio/schnellfilter";
  import type { Qualitaet } from "../../lib/radio/typen";
  import Suchfeld from "./Suchfeld.svelte";

  let { filter, gesamt, sichtbar, ausgeblendet, kategorieName, filterOffen, laedt, onaendern, onfilter, onneuladen }: {
    filter: Schnellfilter;
    gesamt: number | null;
    sichtbar: number | null;
    ausgeblendet: number | null;
    kategorieName: (id: string) => string;
    filterOffen: boolean;
    laedt: boolean;
    onaendern: (arbeit: (f: Schnellfilter) => Schnellfilter) => void;
    onfilter: () => void;
    onneuladen: () => void;
  } = $props();

  const chips = $derived(aktive(filter));

  /** Beschriftung eines Chips: Art und Wert */
  function beschriftung(c: Chip): { art: string; wert: string } {
    switch (c.art) {
      case "land": return { art: t("radio.chip.land"), wert: landName(c.wert) };
      case "genre": return { art: t("radio.chip.genre"), wert: c.wert };
      case "qualitaet": return { art: "", wert: `${t("radio.qualitaetTitel")} ${qualitaetName(c.wert as Qualitaet)}` };
      case "codec": return { art: t("radio.chip.codec"), wert: c.wert === "unbekannt" ? t("radio.unbekannt") : c.wert };
      case "bewertung": return { art: t("radio.chip.bewertung"), wert: bewertungName(c.wert) };
      case "kategorie": return { art: t("radio.chip.kategorie"), wert: kategorieName(c.wert) };
      case "favoriten": return { art: "", wert: t("radio.nurFavoriten") };
      case "erreichbar": return { art: "", wert: t("radio.auchNichtErreichbare") };
      case "stimmen": return { art: t("radio.chip.stimmen"), wert: t("radio.abZahl", { n: zahl(Number(c.wert)) }) };
      case "bitrate": return { art: t("radio.chip.bitrate"), wert: t("radio.abKbps", { n: c.wert }) };
      case "suche": return { art: t("radio.chip.suche"), wert: c.wert };
    }
  }

  function zuDenRegeln(e: MouseEvent) {
    e.preventDefault();
    actions.navigateTo("/einstellungen/radio/regeln");
  }
</script>

<div class="rh-werkzeug">
  <div class="rh-werkzeug-zeile">
    <button class="knopf rh-filter-auf" type="button" aria-expanded={filterOffen} aria-controls="rh-filter" onclick={onfilter}>
      <i class="fa-solid fa-sliders"></i>{t("radio.filter")}{#if chips.length}<span class="pille">{chips.length}</span>{/if}</button>
    <div class="rh-zaehler" title={t("radio.trefferHilfe")}>
      <ak-segmente art="7" stellen="5" farbe="gruen" text={gesamt === null ? "-----" : zahl(gesamt)}></ak-segmente>
      <span class="ak-etikett">{t("radio.treffer")}</span>
      <span class="rh-breit">{sichtbar === null ? "" : t("radio.vonSichtbaren", { n: zahl(sichtbar) })}</span>
    </div>
    <Suchfeld wert={filter.suche} onsuche={(s) => onaendern((f) => ({ ...f, suche: s }))} />
    <button class="knopf rh-neu-laden" type="button" title={t("radio.neuLadenHilfe")} aria-label={t("radio.neuLaden")} disabled={laedt}
            onclick={() => { onneuladen(); sfx.click(); }}>
      <i class="fa-solid fa-rotate" class:fa-spin={laedt}></i><span class="rh-breit">{t("radio.neuLaden")}</span></button>
  </div>
  <div class="rh-werkzeug-zeile">
    <div class="rh-aktiv-chips" aria-label={t("radio.aktiveFilter")}>
      {#each chips as c (`${c.art}:${c.wert}`)}
        {@const b = beschriftung(c)}
        <span class="chip">{#if b.art}{`${b.art}: `}{/if}<b>{b.wert}</b><button type="button" aria-label={t("radio.filterEntfernen")}
              title={t("radio.entfernen")} onclick={() => onaendern((f) => ohne(f, c))}><i class="fa-solid fa-xmark"></i></button></span>
      {:else}
        <span class="rh-leer-chips">{t("radio.keineFilter")}</span>
      {/each}
    </div>
    {#if ausgeblendet}
      <p class="rh-hinweis" title={t("radio.hinweisHilfe")}>
        <ak-led farbe="bernstein" zustand="an" groesse="klein" hilfe={t("radio.durchRegeln")}></ak-led>
        <span><b>{zahl(ausgeblendet)}</b> <span class="rh-breit">{t("radio.senderDurchRegeln")}</span> {t("radio.ausgeblendet")}</span>
        <a href="/einstellungen/radio/regeln" onclick={zuDenRegeln}>{t("radio.regelnAnsehen")}<i class="fa-solid fa-arrow-right"></i></a>
      </p>
    {/if}
    <button class="knopf rh-alle-zurueck" type="button" disabled={!chips.length} onclick={() => onaendern(zurueckgesetzt)}>
      <i class="fa-solid fa-filter-circle-xmark"></i>{t("radio.alleZuruecksetzen")}</button>
  </div>
</div>
