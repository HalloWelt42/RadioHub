<script lang="ts">
  // Transkript einer Folge (RAD-22): derselbe laufende Text wie beim Live-Mitlesen. Fehlt er, entsteht er beim Öffnen von selbst. Eine
  // einzige Taste stellt Ton und Text auf die eigene Sprache (RAD-26, RAD-138): beim ersten Mal wird dafür übersetzt und gesprochen,
  // danach wechselt sie jederzeit zwischen Fassung und Original, auch während noch vertont wird. Wie transkribiert und vertont wird,
  // steht in den Voreinstellungen; das kleine Symbol lässt neu entstehen, was man gerade sieht.
  import { untrack, type Snippet } from "svelte";
  import { kopieren } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { actions, appState } from "../../lib/store.svelte.js";
  import { podcastquelle } from "../../lib/podcasts";
  import { Folgenfassung } from "../../lib/podcasts/fassung.svelte";
  import { stelleText } from "../../lib/podcasts/anzeige";
  import { absatzBei, Folgentext } from "../../lib/podcasts/transkript.svelte";
  import { anhaengen, tonelement } from "../../spieler/tonelement";
  import Lesefeld, { type Lesezeile } from "../bausteine/Lesefeld.svelte";
  import Schalter from "../bausteine/Schalter.svelte";

  let { folgeId, spielt, schalter, onanhoeren }: {
    folgeId: number;
    /** diese Folge läuft gerade */
    spielt: boolean;
    /** die Taste, die hierher führte, bleibt bei den anderen (am Telefon steht sie darüber) */
    schalter?: Snippet;
    /** ab einer Stelle hören */
    onanhoeren: (von: number) => void;
  } = $props();

  let text = $state<Folgentext>();
  let fassung = $state<Folgenfassung>();
  /** beim laufenden Vertonen gewünschte Sprache (null: keine eigene Wahl), danach gilt sie für Ton und Text */
  let wunsch = $state<string | null>(null);
  $effect(() => {
    const neu = new Folgentext(folgeId);
    const vertont = new Folgenfassung(folgeId);
    text = neu;
    fassung = vertont;
    wunsch = null;
    untrack(() => void vertont.laden().then(() => textLaden(neu, vertont)));
    return () => { neu.beenden(); vertont.beenden(); };
  });

  // ----- Text
  const transkript = $derived(text?.stand?.transkript ?? null);
  const lauf = $derived(text?.stand?.lauf ?? null);
  const vertonung = $derived(fassung?.stand?.lauf ?? null);
  const ziel = $derived(fassung?.stand?.ziel ?? "");
  const zielname = $derived(fassung?.stand?.zielname ?? "");
  const da = $derived(!!fassung?.stand?.fassungen.some((f) => f.sprache === ziel));

  // ----- Sprache: was man hört, sonst was gewählt ist; während des Vertonens, was man sich wünscht
  const laufend = () => appState.currentEpisode as { id?: number; fassung?: string } | null;
  const imSpieler = $derived(laufend()?.id === folgeId);
  const gewaehlt = $derived(imSpieler ? (laufend()?.fassung ?? "") : (fassung?.stand?.gewaehlt ?? ""));
  const sprache = $derived(vertonung ? (wunsch ?? ziel) : gewaehlt);
  const fremd = $derived(!!fassung?.stand && (da || !!vertonung || (fassung.stand.kann_vertonen && (transkript === null || transkript.sprache !== ziel))));

  /** Text der gewählten Sprache; gibt es beim Vertonen noch keinen übersetzten, bleibt der des Originals stehen */
  async function textLaden(x: Folgentext, f: Folgenfassung) {
    x.fassung = untrack(() => sprache);
    await x.laden();
    if (x.fassung && !x.stand?.transkript && f.stand?.lauf) { x.fassung = ""; await x.laden(); }
    // noch kein Text: er entsteht von selbst (beim Vertonen gehört er dazu)
    if (x.stand && !x.stand.transkript && !x.stand.lauf && !x.stand.fehler && x.stand.kann_transkribieren && !f.stand?.lauf && !x.fassung) void x.transkribieren();
  }
  $effect(() => {
    void sprache;
    void vertonung?.schritt;
    untrack(() => { if (text?.stand && fassung?.stand) void textLaden(text, fassung); });
  });

  // ----- Die eine Taste
  async function umschalten(s: string) {
    if (!(await fassung?.waehlen(s))) return;
    if (imSpieler) void actions.folgenfassung(s);
  }
  function deutsch(an: boolean) {
    const s = an ? ziel : "";
    if (vertonung) wunsch = s;
    else if (da || !an) void umschalten(s);
    else { wunsch = ziel; void fassung?.vertonen(); }
  }
  // die gewählte Fassung gilt beim nächsten Abspielen
  $effect(() => { if (fassung?.stand) podcastquelle.fassungMerken(folgeId, fassung.stand.gewaehlt); });
  // fertig vertont: Ton und Text folgen dem Wunsch
  let lief = false;
  $effect(() => {
    const laeuft = !!vertonung;
    untrack(() => {
      if (lief && !laeuft && da && !fassung?.fehler) {
        if (wunsch !== null || !imSpieler) void umschalten(wunsch ?? ziel);
        wunsch = null;
        actions.showToast(t("podcastAnsicht.vertonung.fertig", { sprache: zielname }), "success");
      }
      lief = laeuft;
    });
  });
  function neu() {
    if (sprache && da) { wunsch = ziel; void fassung?.vertonen(); }
    else void text?.transkribieren();
  }

  // ----- Mitlaufen
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
  const springen = (nr: number) => { const a = absaetze.find((x) => x.nr === nr); if (a) { mitlaufen = true; onanhoeren(a.von); } };

  // ----- Stand
  const arbeit = $derived(vertonung ?? lauf);
  const prozent = $derived(arbeit?.fortschritt == null ? null : Math.round(arbeit.fortschritt * 100));
  const lage = $derived(arbeit ? [prozent === null ? "" : `${prozent} %`, arbeit.schritt].filter(Boolean).join(" · ")
    : text?.fehler || fassung?.fehler || (transkript ? t(`podcastAnsicht.transkript.${transkript.herkunft}`) : ""));

  async function kopiere() {
    const alles = absaetze.map((a) => `${stelleText(a.von)}  ${a.sprecher ? `${a.sprecher}: ` : ""}${a.text}`).join("\n\n");
    const ok = await kopieren(lesefeld?.markiert() || alles);
    actions.showToast(ok ? t("radio.kopiert", { was: t("podcastAnsicht.transkript.titel") }) : t("radio.kopierenFehler"), ok ? "success" : "error");
  }
</script>

<section class="rh-mitlesen rh-transkript" {@attach ganzZeigen} aria-label={t("podcastAnsicht.transkript.titel")}>
  <div class="rh-mitlese-tasten">
    {@render schalter?.()}
    <Schalter an={mitlaufen && spielt} symbol="fa-angles-down" text={t("radio.mitlesen.mitlaufen")} hilfe={t("radio.mitlesen.mitlaufenHilfe")} onwechsel={(an) => (mitlaufen = an)} />
    {#if fremd}
      <span class="rh-richtung"><Schalter an={sprache === ziel} farbe="blau" symbol="fa-language" text={zielname} hilfe={t("podcastAnsicht.vertonung.umschalten", { sprache: zielname })} onwechsel={deutsch} /></span>
    {/if}
    {#if arbeit}<span class="balken" class:unbestimmt={prozent === null}><span style:width="{prozent ?? 100}%"></span></span>{/if}
    <span class="rh-mitlese-fuss">
      {#if transkript}<button class="rund rh-mini" type="button" title={t("radio.mitlesen.kopieren")} aria-label={t("radio.mitlesen.kopieren")} onclick={() => void kopiere()}><i class="fa-regular fa-copy"></i></button>{/if}
      {#if !arbeit && text?.stand?.kann_transkribieren && (transkript || text.fehler)}
        <button class="rund rh-mini" type="button" title={t("podcastAnsicht.vertonung.neu")} aria-label={t("podcastAnsicht.vertonung.neu")} onclick={neu}><i class="fa-solid fa-rotate-right"></i></button>
      {/if}
      <span class="rh-mitlese-lage" class:gestoert={!arbeit && !!(text?.fehler || fassung?.fehler)} title={lage} aria-live="polite">{lage}</span>
    </span>
  </div>
  <Lesefeld bind:this={lesefeld} bind:mitlaufen {zeilen} {aktiv} folgtAktiv onzeit={springen} beschriftung={t("podcastAnsicht.transkript.titel")}
            leer={arbeit ? t("podcastAnsicht.transkript.entsteht") : text?.stand ? t("podcastAnsicht.transkript.keins") : t("podcastAnsicht.transkript.laedt")} />
</section>
