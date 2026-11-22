<script lang="ts">
  // Folge am Telefon (Entwurf telefon-podcasts.html): Bild des Abos, Titel, Abo, Datum, Länge, Wolke wenn gespeichert,
  // Stand (neu, Balken mit Rest, gehört). Tipp auf die Zeile öffnet das Blatt, der Knopf rechts hört sofort (weiter ab
  // der Stelle).
  import { t } from "../../../lib/i18n.svelte.js";
  import { datumKurz, minuten, standVon, stelleText, tageHer } from "../../../lib/podcasts/anzeige";
  import type { Abo, Folge } from "../../../lib/podcasts";
  import AboBild from "../../podcast/AboBild.svelte";

  let { folge: f, abo, spielt, mitAbo = true, onoeffnen, onhoeren }: {
    folge: Folge;
    abo: Abo | undefined;
    spielt: boolean;
    mitAbo?: boolean;
    onoeffnen: () => void;
    onhoeren: () => void;
  } = $props();

  const stand = $derived(standVon(f));
  const tag = $derived.by(() => {
    const n = tageHer(f.datum);
    return n === 0 ? t("podcastAnsicht.heute") : n === 1 ? t("podcastAnsicht.gestern") : datumKurz(f.datum);
  });
  const weiter = $derived(stand.art === "laeuft");
  const knopfText = $derived(weiter ? t("podcastAnsicht.telefon.weiterAb", { zeit: stelleText(f.stelle) }) : t("podcastAnsicht.telefon.hoeren"));
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="tf-sender tp-folge" class:spielt class:gehoert={stand.art === "gehoert"} onclick={onoeffnen}>
  <AboBild abo={abo ?? { titel: f.aboTitel ?? "", bild: f.bild }} bild={f.bild || undefined} />
  <div><b>{f.titel}</b>
    <div class="tf-meta">{#if mitAbo}<span>{abo?.titel ?? f.aboTitel ?? ""}</span>{/if}<span>{tag}</span>{#if f.dauer}<span>{t("podcastAnsicht.minuten", { n: minuten(f.dauer) })}</span>{/if}
      {#if f.gespeichert}<span class="tp-gespeichert" title={t("podcastAnsicht.telefon.gespeichertHilfe")}><i class="fa-solid fa-cloud"></i></span>{/if}
      {#if f.werbung.anzahl}<span class="rh-werbemarke-text"><i class="fa-solid fa-forward"></i>{t("podcastAnsicht.werbung.marke", { n: f.werbung.anzahl, zeit: stelleText(f.werbung.dauer) })}</span>{/if}</div>
    <div class="tp-stand-zeile">
      {#if stand.art === "gehoert"}<span class="rh-stand fertig"><i class="fa-solid fa-check"></i>{t("podcastAnsicht.gehoert")}</span>
      {:else if stand.art === "neu"}<span class="rh-stand neu">{t("podcastAnsicht.neu")}</span>
      {:else}<span class="rh-stand tp-stand"><span class="balken"><span style:width="{Math.round(stand.anteil * 100)}%"></span></span>{t("podcastAnsicht.noch", { n: minuten(stand.rest) })}</span>{/if}
    </div>
  </div>
  <span class="tf-aktionen"><button class="rund" type="button" aria-label={knopfText} title={knopfText} onclick={(e) => { e.stopPropagation(); onhoeren(); }}>
    <i class="fa-solid {spielt ? 'fa-volume-high' : weiter ? 'fa-forward' : 'fa-play'}"></i></button></span>
</div>
