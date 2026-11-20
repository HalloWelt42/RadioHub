<script lang="ts">
  // Reiter Abgleich (Vorgabe 4): der Abgleich mit dem Senderverzeichnis läuft jede Nacht als Auftrag des Appkerns; hier
  // stehen der letzte Lauf und die Uhrzeit, und er lässt sich sofort anstoßen. Ein laufender Auftrag zeigt Schritt und
  // Fortschritt (die Liste aller Aufträge führt der Appkern).
  import { onMount } from "svelte";
  import { hole, type Auftrag } from "appkern-oberflaeche";
  import { t } from "../../../lib/i18n.svelte.js";
  import { senderquelle } from "../../../lib/radio";
  import type { Abgleichstand } from "../../../lib/radio/typen";

  const TAKT_MS = 2000;
  let stand = $state<Abgleichstand | null>(null);
  let auftrag = $state<Auftrag | null>(null);
  let fehler = $state("");
  let uhr: ReturnType<typeof setTimeout> | undefined;

  const offen = $derived(!!auftrag && (auftrag.zustand === "wartet" || auftrag.zustand === "laeuft"));
  const zeit = (iso: string | null) => (iso ? new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : t("radio.einst.nochNie"));

  async function laden() {
    try {
      stand = await senderquelle.abgleich();
      if (stand.auftrag) await verfolgen(stand.auftrag);
    } catch (f) {
      fehler = (f as Error).message;
    }
  }

  async function verfolgen(id: string) {
    clearTimeout(uhr);
    try {
      auftrag = await hole<Auftrag>(`/auftraege/${encodeURIComponent(id)}`);
    } catch (f) {
      fehler = (f as Error).message;
      return;
    }
    if (auftrag.zustand === "wartet" || auftrag.zustand === "laeuft") uhr = setTimeout(() => void verfolgen(id), TAKT_MS);
    else stand = await senderquelle.abgleich().catch(() => stand);
  }

  async function starten() {
    fehler = "";
    try {
      await verfolgen(await senderquelle.abgleichStarten());
    } catch (f) {
      fehler = (f as Error).message;
    }
  }

  onMount(() => {
    void laden();
    return () => clearTimeout(uhr);
  });
</script>

<section class="rh-reiter">
  <div class="karte rh-karte">
    <div class="rh-karte-kopf"><h2><i class="fa-solid fa-arrows-rotate"></i>{t("radio.einst.abgleichTitel")}</h2>
      <span class="rh-still">{t("radio.einst.abgleichHilfe")}</span></div>
    <dl class="rh-werte">
      <dt>{t("radio.einst.letzterLauf")}</dt><dd>{stand ? zeit(stand.zuletzt) : t("radio.laedt")}</dd>
      <dt>{t("radio.einst.uhrzeit")}</dt><dd>{stand ? (stand.uhrzeit ? t("radio.einst.jedeNacht", { uhrzeit: stand.uhrzeit }) : t("radio.einst.keineUhrzeit")) : ""}</dd>
    </dl>
    {#if auftrag}
      <div class="rh-auftrag" aria-live="polite">
        <div class="rh-auftrag-zeile"><b>{auftrag.titel}</b><span class="stand-pille" class:laeuft={offen} class:fertig={auftrag.zustand === "fertig"}
              class:warn={auftrag.zustand === "fehler"}>{t(`radio.einst.zustand.${auftrag.zustand}`)}</span></div>
        {#if offen}
          <div class="balken"><span style="width:{Math.round((auftrag.fortschritt ?? 0) * 100)}%"></span></div>
          <div class="rh-auftrag-zeile"><span>{auftrag.schritt}</span>{#if auftrag.fortschritt != null}<span class="rh-zahl">{Math.round(auftrag.fortschritt * 100)} %</span>{/if}</div>
        {:else if auftrag.fehler}<span>{auftrag.fehler}</span>{/if}
      </div>
    {/if}
    {#if fehler}<p class="hinweis-band"><i class="fa-solid fa-triangle-exclamation"></i><span>{fehler}</span></p>{/if}
    <div class="rh-knoepfe" style="margin-top:14px">
      <button class="knopf primaer" type="button" disabled={offen} onclick={starten}><i class="fa-solid fa-play"></i>{t("radio.einst.jetztAbgleichen")}</button>
    </div>
  </div>
</section>
