<script lang="ts">
  // Modul Anzeige: Statuszeile (Leuchte, was geschieht, Codec und Bitrate, Aktion), Punktmatrix mit dem Sender und die
  // Titelzeile, nur mit Titel. Die Matrix hat so viele Stellen, wie ihre Breite trägt (rasterbreite.ts), und läuft über
  // ihr Merkmal lauf, wenn der Name länger ist; sie führt zur Quelle. Aktion je Zustand: neu verbinden nach einem
  // Fehler, Hinweis auf den gesperrten Wechsel während der Aufnahme, sonst bei Sendern die Bitrate des Zeitversatzes
  // (wählbar, solange er puffert, sonst gesperrt sichtbar).
  import { Auswahl } from "appkern-oberflaeche";
  import { t } from "../lib/i18n.svelte.js";
  import * as sfx from "../lib/uiSounds.js";
  import { BITRATEN, bitrateLesen, bitrateSetzen, quelleStarten, zurQuelle } from "./aktionen";
  import type { Anzeige } from "./kanzel";
  import { rasterStellen } from "./rasterbreite";

  let { anzeige, bitrate: bitrateLage, erkannt, aufnahme }: {
    anzeige: Anzeige;
    /** Bitrate des Zeitversatzes: wählbar (Puffer steht), gesperrt (Originalstrom), fest (Folge im Puffer), keine */
    bitrate: "frei" | "gesperrt" | "fest" | null;
    /** erkannte Bitrate des Senders in kbit/s, 0 ohne Angabe */
    erkannt: number;
    /** eine Aufnahme läuft (Sprung zum aufnehmenden Sender) */
    aufnahme: boolean;
  } = $props();

  let bitrate = $state<number | null>(bitrateLesen());
  let wechselt = $state(false);
  let stellen = $state(16);
  const optionen = $derived([
    { wert: null, titel: t("kanzel.bitrateWieGesendet"), hinweis: erkannt > 0 ? t("kanzel.bitrateErkannt", { n: erkannt }) : undefined },
    ...BITRATEN.map((n) => ({ wert: n, titel: t("kanzel.kbit", { n }) })),
  ]);

  async function bitrateWaehlen(wert: number | null) {
    wechselt = true;
    try {
      await bitrateSetzen(wert);
    } finally {
      wechselt = false;
    }
  }

  const quelleHilfe = $derived(aufnahme ? t("player.zumSender") : t("player.zurQuelle"));
</script>

<section class="rh-modul rh-m-anzeige" aria-label={t("kanzel.anzeige")}><span class="ak-etikett">{t("kanzel.anzeige")}</span>
  <div class="ak-glas rh-display" data-ton={anzeige.ton}>
    <div class="rh-display-zeile">
      <ak-led farbe={anzeige.led.farbe} zustand={anzeige.led.zustand} groesse="klein"></ak-led>
      <span>{anzeige.art}</span>
      {#if anzeige.format}<span class="rh-display-format">{anzeige.format}</span>{/if}
      <span class="rh-display-aktion">
        {#if anzeige.zustand === "fehler"}
          <button class="knopf primaer" type="button" title={t("kanzel.neuVerbindenHilfe")} onclick={() => { quelleStarten(); sfx.click(); }}>
            <i class="fa-solid fa-rotate-right"></i>{t("kanzel.neuVerbinden")}</button>
        {:else if anzeige.zustand === "aufnahme"}
          <span title={t("kanzel.wechselGesperrtHilfe")}><ak-led farbe="bernstein" zustand="an" groesse="klein"></ak-led> {t("kanzel.wechselGesperrt")}</span>
        {:else if bitrateLage === "frei" && !wechselt}
          <Auswahl klein wert={bitrate} {optionen} symbol="fa-gauge" titel={t("kanzel.bitrate")}
            onwahl={(w) => { bitrate = w; bitrateWaehlen(w); }} />
        {:else if bitrateLage}
          <!-- gesperrt wie die Leuchten in HiFiPlayer: sichtbar, nicht bedienbar -->
          <span class="auswahl"><button class="auswahl-knopf klein" type="button" disabled
            title={wechselt ? t("playerLabel.bitrateWechsel") : bitrateLage === "fest" ? t("kanzel.bitrateFest") : t("playerLabel.hlsBitrateNurHls")}>
            <i class="fa-solid fa-gauge"></i><span class="auswahl-text">{wechselt ? t("kanzel.bitrateWechsel")
              : bitrateLage === "fest" ? t("kanzel.kbit", { n: 128 }) : optionen.find((o) => o.wert === bitrate)?.titel}</span></button></span>
        {/if}
      </span>
    </div>
    <button class="rh-display-quelle" type="button" disabled={!anzeige.sender} title={anzeige.sender ? quelleHilfe : undefined}
      aria-label={anzeige.sender ? `${anzeige.sender}: ${quelleHilfe}` : t("kanzel.senderHilfe")}
      onclick={() => { zurQuelle(); sfx.click(); }} use:rasterStellen={(n) => (stellen = n)}>
      <!-- der Appkern liest die Stellen beim Einhängen: neue Stellenzahl, neue Anzeige (nur wenn sich die Breite ändert) -->
      {#key stellen}<ak-segmente art="punkt" {stellen} lauf="280" farbe="gruen" text={anzeige.sender}></ak-segmente>{/key}
    </button>
    {#if anzeige.titel}<div class="rh-display-titel" title={anzeige.titel}>{anzeige.titel}</div>{/if}
  </div>
</section>
