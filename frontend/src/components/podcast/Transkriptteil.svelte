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

  // beim Vertonen entsteht zuerst der Text: er erscheint, sobald er da ist; am Ende sagt es ein Hinweis
  let lief = false;
  $effect(() => {
    const laeuft = !!vertonung;
    void vertonung?.schritt;
    untrack(() => {
      if (laeuft && text?.stand && !transkript) void text.laden();
      if (lief && !laeuft && fassung?.da) actions.showToast(t("podcastAnsicht.vertonung.fertig", { sprache: zielname }), "success");
      lief = laeuft;
    });
  });

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
  const zielname = $derived(fassung?.stand?.zielname ?? "");
  const kannTranskribieren = $derived(!gewaehlt && !!text?.stand?.kann_transkribieren && transkript?.herkunft !== "gehoert");
  const laufText = (l: { fortschritt: number | null; schritt: string }, sonst: string) => [anteil(l) === null ? "" : `${anteil(l)} %`, l.schritt || sonst].filter(Boolean).join(" · ");
  const lage = $derived(vertonung && transkript ? laufText(vertonung, t("podcastAnsicht.vertonung.laeuft")) : text?.fehler || fassung?.fehler || (transkript ? t(`podcastAnsicht.transkript.${transkript.herkunft}`) : ""));
  const springen = (nr: number) => { const a = absaetze.find((x) => x.nr === nr); if (a) { mitlaufen = true; onanhoeren(a.von); } };

  async function kopiere() {
    const alles = absaetze.map((a) => `${stelleText(a.von)}  ${a.sprecher ? `${a.sprecher}: ` : ""}${a.text}`).join("\n\n");
    const ok = await kopieren(lesefeld?.markiert() || alles);
    actions.showToast(ok ? t("radio.kopiert", { was: t("podcastAnsicht.transkript.titel") }) : t("radio.kopierenFehler"), ok ? "success" : "error");
  }
</script>

{#snippet transkribieren()}
  <button class="knopf" type="button" title={t("podcastAnsicht.transkript.startenHilfe")} onclick={() => void text?.transkribieren()}>
    <i class="fa-solid fa-closed-captioning"></i>{t("podcastAnsicht.transkript.starten")}</button>
{/snippet}
{#snippet vertonen()}
  {#if stimmen.length}<Auswahl bind:wert={stimme} optionen={stimmen} titel={t("podcastAnsicht.vertonung.stimme")} klein onwahl={stimmeWaehlen} />{/if}
  <button class="knopf" type="button" title={t("podcastAnsicht.vertonung.hilfe", { sprache: zielname })} onclick={() => void fassung?.vertonen()}>
    <i class="fa-solid fa-language"></i>{t("podcastAnsicht.vertonung.auf", { sprache: zielname })}</button>
{/snippet}
{#snippet balken(wert: number | null)}
  <span class="balken" class:unbestimmt={wert === null}><span style:width="{wert ?? 100}%"></span></span>
{/snippet}

<section class="rh-mitlesen rh-transkript" {@attach ganzZeigen} aria-label={t("podcastAnsicht.transkript.titel")}>
  <div class="rh-mitlese-tasten">
    {#if transkript}
      <Schalter an={mitlaufen && spielt} symbol="fa-angles-down" text={t("radio.mitlesen.mitlaufen")} hilfe={t("radio.mitlesen.mitlaufenHilfe")} onwechsel={(an) => (mitlaufen = an)} />
    {/if}
    {#if fassung?.da}
      <Schalter an={gewaehlt === fassung.stand?.ziel} farbe="blau" symbol="fa-language" text={zielname} hilfe={t("podcastAnsicht.vertonung.umschalten", { sprache: zielname })}
        onwechsel={(an) => void umschalten(an ? (fassung?.stand?.ziel ?? "") : "")} />
    {/if}
    {#if vertonung}
      <button class="knopf" type="button" title={t("podcastAnsicht.vertonung.abbrechenHilfe")} onclick={() => void fassung?.abbrechen()}><i class="fa-solid fa-stop"></i>{t("podcastAnsicht.transkript.abbrechen")}</button>
      {#if transkript}{@render balken(anteil(vertonung))}{/if}
    {:else if lauf}
      <button class="knopf" type="button" onclick={() => void text?.abbrechen()}><i class="fa-solid fa-stop"></i>{t("podcastAnsicht.transkript.abbrechen")}</button>
    {:else if transkript}
      {#if kannTranskribieren}{@render transkribieren()}{/if}
      {#if anbieten}{@render vertonen()}{/if}
    {/if}
    <span class="rh-mitlese-fuss">
      {#if transkript}<button class="rund rh-mini" type="button" title={t("radio.mitlesen.kopieren")} aria-label={t("radio.mitlesen.kopieren")} onclick={() => void kopiere()}><i class="fa-regular fa-copy"></i></button>{/if}
      <span class="rh-mitlese-lage" class:gestoert={!vertonung && !!(text?.fehler || fassung?.fehler)} title={lage} aria-live="polite">{lage}</span>
    </span>
  </div>
  {#if lauf || (vertonung && !transkript)}
    {@const l = lauf ?? vertonung!}
    <div class="rh-transkript-lauf" role="status">
      <span>{laufText(l, t(lauf ? "podcastAnsicht.transkript.laeuft" : "podcastAnsicht.vertonung.laeuft"))}</span>
      {@render balken(anteil(l))}
    </div>
  {:else if text?.stand && !transkript && (kannTranskribieren || anbieten)}
    <!-- noch kein Text: was man damit tun kann, steht mit Worten im leeren Feld (RAD-26) -->
    <div class="rh-transkript-lauf rh-transkript-start">
      <b>{t("podcastAnsicht.transkript.keins")}</b>
      <span class="rh-transkript-wahl">{#if kannTranskribieren}{@render transkribieren()}{/if}</span>
      <span class="rh-transkript-wahl">{#if anbieten}{@render vertonen()}{/if}</span>
      <span>{t("podcastAnsicht.transkript.vonSelbst")}</span>
    </div>
  {:else}
    <Lesefeld bind:this={lesefeld} bind:mitlaufen {zeilen} {aktiv} folgtAktiv onzeit={springen} beschriftung={t("podcastAnsicht.transkript.titel")}
              leer={text?.stand ? t("podcastAnsicht.transkript.keins") : t("podcastAnsicht.transkript.laedt")} />
  {/if}
</section>
