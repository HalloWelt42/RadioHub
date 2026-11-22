<script lang="ts">
  // Blatt einer Folge am Telefon (Entwurf telefon-podcasts.html, Zustände 4 und 5): Abo, Datum, Länge, Größe in der
  // Kellerwolke, Stand, Beschreibung (drei Zeilen, Rest aufklappbar). Weiter ab der Stelle oder hören, von vorn,
  // speichern (gespeichert: löschen fragt mit Datei und Größe), herunterladen aufs Telefon, gehört.
  import { Rueckfrage } from "appkern-oberflaeche";
  import { t } from "../../../lib/i18n.svelte.js";
  import { datumKurz, megabyte, minuten, standVon, stelleText, textAus } from "../../../lib/podcasts/anzeige";
  import type { Abo, Folge } from "../../../lib/podcasts";
  import Langtext from "../../radio/Langtext.svelte";
  import Schalter from "../../radio/Schalter.svelte";
  import Werbeteil from "../../podcast/Werbeteil.svelte";

  let { folge: f, abo, spielt, kannSpeichern, dateiAdresse, onhoeren, onvorn, onspeichern, onloeschen, ongehoert, onzu, onanhoeren, onwerbung }: {
    folge: Folge;
    abo: Abo | undefined;
    kannSpeichern: boolean;
    dateiAdresse: string;
    onhoeren: () => void;
    onvorn: () => void;
    onspeichern: () => void;
    onloeschen: () => Promise<void>;
    ongehoert: () => void;
    onzu: () => void;
    spielt: boolean;
    onanhoeren: (von: number) => void;
    onwerbung: (werbung: { anzahl: number; dauer: number }) => void;
  } = $props();

  let fragt = $state(false);
  let loescht = $state(false);
  const stand = $derived(standVon(f));
  const weiter = $derived(stand.art === "laeuft");

  async function loeschen() {
    loescht = true;
    try { await onloeschen(); fragt = false; } finally { loescht = false; }
  }
</script>

<button class="t-schleier" type="button" aria-label={t("podcastAnsicht.telefon.schliessen")} onclick={onzu}></button>
<div class="t-blatt tp-blatt" role="dialog" aria-label={f.titel}>
  <div class="t-blatt-kopf"><h2>{f.titel}</h2>
    <button class="rund" type="button" aria-label={t("podcastAnsicht.telefon.schliessen")} onclick={onzu}><i class="fa-solid fa-xmark"></i></button></div>
  <div class="t-blatt-rollt">
    <div class="tf-meta"><span>{abo?.titel ?? f.aboTitel ?? ""}</span><span>{datumKurz(f.datum)}</span>{#if f.dauer}<span>{t("podcastAnsicht.minuten", { n: minuten(f.dauer) })}</span>{/if}
      {#if f.gespeichert && f.groesse}<span>{t("podcastAnsicht.telefon.mbWolke", { mb: megabyte(f.groesse) })}</span>{/if}</div>
    <div class="tp-stand-zeile">
      {#if stand.art === "gehoert"}<span class="rh-stand fertig"><i class="fa-solid fa-check"></i>{t("podcastAnsicht.gehoert")}</span>
      {:else if stand.art === "neu"}<span class="rh-stand neu">{t("podcastAnsicht.neu")}</span>
      {:else}<span class="rh-stand tp-stand"><span class="balken"><span style:width="{Math.round(stand.anteil * 100)}%"></span></span>{t("podcastAnsicht.noch", { n: minuten(stand.rest) })}</span>{/if}
    </div>
    {#if f.beschreibung}<Langtext text={textAus(f.beschreibung)} klasse="tp-text" />{/if}
    {#if fragt}
      <Rueckfrage frage={t("podcastAnsicht.loeschenFrage")} hinweis={t("podcastAnsicht.loeschenHinweis", { pfad: f.ablagePfad, mb: megabyte(f.groesse) })}
                  knopf={t("podcastAnsicht.loeschen")} beschaeftigt={loescht} onabbrechen={() => (fragt = false)} onja={() => void loeschen()} />
    {:else}
      <div class="tp-aktionen">
        <button class="knopf primaer" type="button" onclick={onhoeren}><i class="fa-solid {weiter ? 'fa-forward' : 'fa-play'}"></i>
          {weiter ? t("podcastAnsicht.telefon.weiterAb", { zeit: stelleText(f.stelle) }) : t("podcastAnsicht.telefon.hoeren")}</button>
        {#if weiter}<button class="knopf" type="button" onclick={onvorn}><i class="fa-solid fa-backward-step"></i>{t("podcastAnsicht.telefon.vonVorn")}</button>{/if}
        {#if kannSpeichern}
          <Schalter an={f.gespeichert} farbe="blau" text={f.gespeichert ? t("podcastAnsicht.telefon.gespeichertKnopf") : t("podcastAnsicht.telefon.speichern")}
                    hilfe={f.gespeichert ? t("podcastAnsicht.gespeichertLoeschen", { mb: megabyte(f.groesse) }) : t("podcastAnsicht.speichern")}
                    onwechsel={(an) => { if (an) onspeichern(); else fragt = true; }} />
        {/if}
        {#if dateiAdresse}<a class="knopf" href={dateiAdresse} download><i class="fa-solid fa-download"></i>{t("podcastAnsicht.telefon.herunterladen")}</a>{/if}
        <Schalter an={stand.art === "gehoert"} text={t("podcastAnsicht.telefon.gehoert")} onwechsel={ongehoert} />
      </div>
      <Werbeteil folge={f} {abo} {spielt} schmal {onanhoeren} ongeaendert={onwerbung} />
    {/if}
  </div>
</div>
