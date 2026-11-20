<script lang="ts">
  // Die drei Tasten der ruhigen Ansicht (Abspielen, Zeitansage, Nachtschaltung) mit Symbol, Zustand und Beschriftung an
  // einer Stelle; `klasse` gibt das Aussehen der Gestaltung (rund, taste ...).
  import type { Gestaltungsprops } from "./typen";
  let { bild, tun, t, klasse = "wa-rund" }: Gestaltungsprops & { klasse?: string } = $props();
  const NACHT_SYMBOL = { auto: "fa-circle-half-stroke", an: "fa-moon", aus: "fa-sun" } as const;
  const NACHT_TEXT = { auto: "nachtAuto", an: "nachtAn", aus: "nachtAus" } as const;
  const spielSymbol = $derived(bild.spielt ? (bild.stoppStattPause ? "fa-stop" : "fa-pause") : "fa-play");
  const ansageSymbol = $derived(bild.ansage.laeuft ? "fa-volume-high" : !bild.ansage.an ? "fa-comment-slash" : bild.ansage.gesperrt ? "fa-volume-xmark" : "fa-comment-dots");
</script>

<div class="wa-reihe">
  <button type="button" class={klasse} class:an={bild.spielt} class:wa-licht={bild.spielt} disabled={!bild.sender} onclick={tun.umschalten}
    aria-label={bild.spielt ? t("pause") : t("abspielen")}><i class="fa-solid {spielSymbol}"></i></button>
  <button type="button" class={klasse} class:an={bild.ansage.an && !bild.ansage.gesperrt} class:wa-licht={bild.ansage.an} aria-pressed={bild.ansage.an} onclick={tun.ansage}
    aria-label={t("zeitansage")} title={bild.ansage.an ? (bild.ansage.gesperrt ? t("tonGesperrt") : t("ansageAn")) : t("ansageAus")}><i class="fa-solid {ansageSymbol}"></i></button>
  <button type="button" class={klasse} class:an={bild.nachtWahl !== "aus"} class:wa-licht={bild.nachtWahl !== "aus"} onclick={tun.nacht}
    aria-label="{t('nacht')}: {t(NACHT_TEXT[bild.nachtWahl])}" title={t(NACHT_TEXT[bild.nachtWahl])}><i class="fa-solid {NACHT_SYMBOL[bild.nachtWahl]}"></i></button>
</div>
