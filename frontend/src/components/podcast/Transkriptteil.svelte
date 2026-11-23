<script lang="ts">
  // Transkript einer Folge (RAD-22): derselbe laufende Text wie beim Live-Mitlesen. Spielt die Folge, läuft er mit der Stelle, die man
  // hört; ein Klick auf die Zeit springt hin. Fehlt er, startet die Taste die Transkription, ihr Fortschritt steht da, bis sie fertig ist.
  import { untrack } from "svelte";
  import { kopieren } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { actions } from "../../lib/store.svelte.js";
  import { stelleText } from "../../lib/podcasts/anzeige";
  import { absatzBei, Folgentext } from "../../lib/podcasts/transkript.svelte";
  import { anhaengen, tonelement } from "../../spieler/tonelement";
  import Lesefeld, { type Lesezeile } from "../bausteine/Lesefeld.svelte";
  import Schalter from "../bausteine/Schalter.svelte";

  let { folgeId, spielt, onanhoeren }: {
    folgeId: number;
    /** diese Folge läuft gerade */
    spielt: boolean;
    /** ab einer Stelle hören */
    onanhoeren: (von: number) => void;
  } = $props();

  let text = $state<Folgentext>();
  $effect(() => {
    const neu = new Folgentext(folgeId);
    text = neu;
    untrack(() => void neu.laden());
    return () => neu.beenden();
  });

  /** beim Öffnen rollt die Liste so weit, dass das Feld ganz zu sehen ist */
  const ganzZeigen = (e: HTMLElement) => { requestAnimationFrame(() => e.scrollIntoView({ block: "nearest", behavior: "smooth" })); };
  let lesefeld = $state<Lesefeld>();
  let mitlaufen = $state(true);
  let stelle = $state(0);
  $effect(() => {
    if (!spielt) return;
    const merken = () => (stelle = tonelement().currentTime);
    merken();
    return anhaengen({ timeupdate: merken, seeked: merken });
  });

  const transkript = $derived(text?.stand?.transkript ?? null);
  const lauf = $derived(text?.stand?.lauf ?? null);
  const absaetze = $derived(transkript?.absaetze ?? []);
  const zeilen = $derived(absaetze.map((a, i): Lesezeile => ({ nr: a.nr, zeit: stelleText(a.von), text: a.text,
    sprecher: a.sprecher && a.sprecher !== absaetze[i - 1]?.sprecher ? a.sprecher : "" })));
  const aktiv = $derived(spielt ? absatzBei(absaetze, stelle) : null);
  const prozent = $derived(lauf?.fortschritt == null ? null : Math.round(lauf.fortschritt * 100));
  const springen = (nr: number) => { const a = absaetze.find((x) => x.nr === nr); if (a) { mitlaufen = true; onanhoeren(a.von); } };

  async function kopiere() {
    const alles = absaetze.map((a) => `${stelleText(a.von)}  ${a.sprecher ? `${a.sprecher}: ` : ""}${a.text}`).join("\n\n");
    const ok = await kopieren(lesefeld?.markiert() || alles);
    actions.showToast(ok ? t("radio.kopiert", { was: t("podcastAnsicht.transkript.titel") }) : t("radio.kopierenFehler"), ok ? "success" : "error");
  }
</script>

<section class="rh-mitlesen rh-transkript" {@attach ganzZeigen} aria-label={t("podcastAnsicht.transkript.titel")}>
  <div class="rh-mitlese-tasten">
    {#if transkript}
      <Schalter an={mitlaufen && spielt} symbol="fa-angles-down" text={t("radio.mitlesen.mitlaufen")} hilfe={t("radio.mitlesen.mitlaufenHilfe")} onwechsel={(an) => (mitlaufen = an)} />
    {/if}
    {#if !lauf && text?.stand?.kann_transkribieren && transkript?.herkunft !== "gehoert"}
      <button class="knopf" type="button" title={t("podcastAnsicht.transkript.startenHilfe")} onclick={() => void text?.transkribieren()}>
        <i class="fa-solid fa-closed-captioning"></i>{t("podcastAnsicht.transkript.starten")}</button>
    {:else if lauf}
      <button class="knopf" type="button" onclick={() => void text?.abbrechen()}><i class="fa-solid fa-stop"></i>{t("podcastAnsicht.transkript.abbrechen")}</button>
    {/if}
    <span class="rh-mitlese-fuss">
      {#if transkript}<button class="rund rh-mini" type="button" title={t("radio.mitlesen.kopieren")} aria-label={t("radio.mitlesen.kopieren")} onclick={() => void kopiere()}><i class="fa-regular fa-copy"></i></button>{/if}
      <span class="rh-mitlese-lage" class:gestoert={!!text?.fehler} aria-live="polite">{text?.fehler || (transkript ? t(`podcastAnsicht.transkript.${transkript.herkunft}`) : "")}</span>
    </span>
  </div>
  {#if lauf}
    <div class="rh-transkript-lauf" role="status">
      <span>{lauf.schritt || t("podcastAnsicht.transkript.laeuft")}{prozent === null ? "" : ` · ${prozent} %`}</span>
      <span class="balken" class:unbestimmt={prozent === null}><span style:width="{prozent ?? 100}%"></span></span>
    </div>
  {:else}
    <Lesefeld bind:this={lesefeld} bind:mitlaufen {zeilen} {aktiv} folgtAktiv onzeit={springen} beschriftung={t("podcastAnsicht.transkript.titel")}
              leer={text?.stand ? t("podcastAnsicht.transkript.keins") : t("podcastAnsicht.transkript.laedt")} />
  {/if}
</section>
