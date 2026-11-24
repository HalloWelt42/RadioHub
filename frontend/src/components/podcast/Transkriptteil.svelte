<script lang="ts">
  // Transkript einer Folge (RAD-22): derselbe laufende Text wie beim Live-Mitlesen. Spielt die Folge, läuft er mit der Stelle, die man
  // hört; ein Klick auf die Zeit springt hin. Fehlt er, startet die Taste die Transkription, ihr Fortschritt steht da, bis sie fertig ist.
  // Eine fremdsprachige Folge lässt sich übersetzt neu sprechen (RAD-26); danach schaltet eine Taste Ton und Text zwischen Fassung und
  // Original um, an derselben Stelle.
  import { untrack } from "svelte";
  import { Auswahl, kopieren } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { actions, appState } from "../../lib/store.svelte.js";
  import { server, type Wahlwert } from "../../lib/einstellungen";
  import { podcastquelle } from "../../lib/podcasts";
  import { Folgenfassung } from "../../lib/podcasts/fassung.svelte";
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
    const vertont = new Folgenfassung(folgeId);
    text = neu;
    fassung = vertont;
    untrack(() => void vertont.laden());
    return () => { neu.beenden(); vertont.beenden(); };
  });

  const transkript = $derived(text?.stand?.transkript ?? null);
  const lauf = $derived(text?.stand?.lauf ?? null);

  // ----- Vertonte Fassung
  const laufend = () => appState.currentEpisode as { id?: number; fassung?: string } | null;
  let fassung = $state<Folgenfassung>();
  /** wer die Folge gerade hört, sieht die Fassung, die er hört, sonst die gewählte */
  const imSpieler = $derived(laufend()?.id === folgeId);
  const gewaehlt = $derived(imSpieler ? (laufend()?.fassung ?? "") : (fassung?.stand?.gewaehlt ?? ""));
  $effect(() => {
    const sprache = gewaehlt;
    const bereit = !!fassung?.stand || !!fassung?.fehler;
    untrack(() => {
      if (!text || !bereit || (text.stand && text.fassung === sprache)) return;
      text.fassung = sprache;
      void text.laden();
    });
  });
  const vertonung = $derived(fassung?.stand?.lauf ?? null);
  const anbieten = $derived(!!fassung?.stand?.kann_vertonen && !fassung.da && !vertonung && transkript?.sprache !== fassung.stand.ziel);
  let stimmen = $state<Wahlwert[]>([]);
  let stimme = $state("");
  $effect(() => {
    if (!anbieten || stimmen.length) return;
    void server.laden().then(() => { stimme = String(server.zeile("podcast_stimme")?.wert ?? ""); });
    void server.angebot("podcast_stimme").then((a) => { stimmen = a.optionen; }).catch(() => undefined);
  });
  const stimmeWaehlen = (w: string) => void server.sofortSpeichern("podcast_stimme", w).catch((f: Error) => actions.showToast(f.message, "error"));

  // die gewählte Fassung (auch eine gerade fertige) gilt beim nächsten Abspielen
  $effect(() => { if (fassung?.stand) podcastquelle.fassungMerken(folgeId, fassung.stand.gewaehlt); });

  async function umschalten(sprache: string) {
    if (!(await fassung?.waehlen(sprache))) return;
    if (imSpieler) void actions.folgenfassung(sprache);
  }

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

  const absaetze = $derived(transkript?.absaetze ?? []);
  const zeilen = $derived(absaetze.map((a, i): Lesezeile => ({ nr: a.nr, zeit: stelleText(a.von), text: a.text,
    sprecher: a.sprecher && a.sprecher !== absaetze[i - 1]?.sprecher ? a.sprecher : "" })));
  const aktiv = $derived(spielt ? absatzBei(absaetze, stelle) : null);
  const anteil = (l: { fortschritt: number | null } | null) => (l?.fortschritt == null ? null : Math.round(l.fortschritt * 100));
  const prozent = $derived(anteil(lauf));
  const laufText = (l: { fortschritt: number | null; schritt: string }, sonst: string) => [anteil(l) === null ? "" : `${anteil(l)} %`, l.schritt || sonst].filter(Boolean).join(" · ");
  const lage = $derived(vertonung ? laufText(vertonung, t("podcastAnsicht.vertonung.laeuft")) : text?.fehler || fassung?.fehler || (transkript ? t(`podcastAnsicht.transkript.${transkript.herkunft}`) : ""));
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
    {#if fassung?.da}
      <Schalter an={gewaehlt === fassung.stand?.ziel} farbe="blau" symbol="fa-language" text={fassung.stand?.zielname ?? ""} hilfe={t("podcastAnsicht.vertonung.umschalten", { sprache: fassung.stand?.zielname ?? "" })}
        onwechsel={(an) => void umschalten(an ? (fassung?.stand?.ziel ?? "") : "")} />
    {/if}
    {#if vertonung}
      <button class="knopf" type="button" title={t("podcastAnsicht.vertonung.abbrechenHilfe")} aria-label={t("podcastAnsicht.vertonung.abbrechenHilfe")} onclick={() => void fassung?.abbrechen()}><i class="fa-solid fa-stop"></i>{t("podcastAnsicht.transkript.abbrechen")}</button>
    {:else if !lauf && !gewaehlt && text?.stand?.kann_transkribieren && transkript?.herkunft !== "gehoert"}
      <button class="knopf" type="button" title={t("podcastAnsicht.transkript.startenHilfe")} aria-label={t("podcastAnsicht.transkript.starten")} onclick={() => void text?.transkribieren()}>
        <i class="fa-solid fa-closed-captioning"></i>{t("podcastAnsicht.transkript.starten")}</button>
    {:else if lauf}
      <button class="knopf" type="button" aria-label={t("podcastAnsicht.transkript.abbrechen")} onclick={() => void text?.abbrechen()}><i class="fa-solid fa-stop"></i>{t("podcastAnsicht.transkript.abbrechen")}</button>
    {/if}
    {#if anbieten && !lauf}
      <button class="knopf" type="button" title={t("podcastAnsicht.vertonung.hilfe", { sprache: fassung?.stand?.zielname ?? "" })} aria-label={t("podcastAnsicht.vertonung.auf", { sprache: fassung?.stand?.zielname ?? "" })} onclick={() => void fassung?.vertonen()}>
        <i class="fa-solid fa-language"></i>{t("podcastAnsicht.vertonung.auf", { sprache: fassung?.stand?.zielname ?? "" })}</button>
      {#if stimmen.length}<Auswahl bind:wert={stimme} optionen={stimmen} titel={t("podcastAnsicht.vertonung.stimme")} klein onwahl={stimmeWaehlen} />{/if}
    {/if}
    <span class="rh-mitlese-fuss">
      {#if transkript}<button class="rund rh-mini" type="button" title={t("radio.mitlesen.kopieren")} aria-label={t("radio.mitlesen.kopieren")} onclick={() => void kopiere()}><i class="fa-regular fa-copy"></i></button>{/if}
      <span class="rh-mitlese-lage" class:gestoert={!vertonung && !!(text?.fehler || fassung?.fehler)} title={lage} aria-live="polite">{lage}</span>
    </span>
  </div>
  {#if lauf}
    <div class="rh-transkript-lauf" role="status">
      <span>{laufText(lauf, t("podcastAnsicht.transkript.laeuft"))}</span>
      <span class="balken" class:unbestimmt={prozent === null}><span style:width="{prozent ?? 100}%"></span></span>
    </div>
  {:else}
    <Lesefeld bind:this={lesefeld} bind:mitlaufen {zeilen} {aktiv} folgtAktiv onzeit={springen} beschriftung={t("podcastAnsicht.transkript.titel")}
              leer={text?.stand ? t("podcastAnsicht.transkript.keins") : t("podcastAnsicht.transkript.laedt")} />
  {/if}
</section>
