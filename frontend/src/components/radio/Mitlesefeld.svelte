<script lang="ts">
  // Das Feld zum Mitlesen im Steckbrief (RAD-129): der laufende Text in lesbarer Breite, die Tasten daneben. Es läuft mit dem
  // neuesten Text mit, spricht der Übersetzer (RAD-130), mit der gesprochenen Stelle; bis man selbst rollt oder es fixiert.
  // Text ist frei wählbar und kopierbar.
  import { tick, type Snippet } from "svelte";
  import { Auswahl, kopieren } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { actions } from "../../lib/store.svelte.js";
  import { alsText, mitlesen, uhrzeit } from "../../lib/radio/mitlesen.svelte";
  import { server, type Wahlwert } from "../../lib/einstellungen";
  import { uebersetzer } from "../../spieler/uebersetzer.svelte";
  import Schalter from "../bausteine/Schalter.svelte";

  /** `schalter`: die Schalter, die an ihrem Platz bleiben (Mitlesen, Werbung) */
  /** `onweiter`: das Mitlesen nach einem Ende (Radio aus, Server neu gestartet) fortsetzen */
  let { schalter, onweiter }: { schalter: Snippet; onweiter: () => Promise<void> } = $props();

  const NAH_PX = 32;
  /** so weit von oben steht der gesprochene Absatz */
  const LESEHOEHE = 0.15;
  let feld = $state<HTMLElement>();
  let fixiert = $state(false);
  /** von Hand weggerollt */
  let weg = $state(false);
  const laeuftMit = $derived(!weg && !fixiert);
  const uebersetzt = $derived(mitlesen.fremd && !!mitlesen.stand?.uebersetzen);

  $effect(() => {
    void uebersetzer.an;              // ein anderes Ziel: gleich dorthin, auch wenn man gerade woanders las
    weg = fixiert = false;
  });
  $effect(() => {
    void [mitlesen.absaetze, uebersetzer.spricht, uebersetzer.an];
    if (laeuftMit) void tick().then(folgen);
  });
  /** das Feld nutzt die Höhe der Liste: sie rollt so weit, dass es ganz zu sehen ist */
  const ganzZeigen = (e: HTMLElement) => { requestAnimationFrame(() => e.scrollIntoView({ block: "nearest", behavior: "smooth" })); };
  function folgen() {
    if (!feld) return;
    if (!uebersetzer.an) return void (feld.scrollTop = feld.scrollHeight);
    const p = feld.querySelector("p.spricht");
    if (p) feld.scrollTop += p.getBoundingClientRect().top - feld.getBoundingClientRect().top - feld.clientHeight * LESEHOEHE;
  }
  // Ohne Stimme sagt die Stelle, ob man mitläuft: unten angekommen wieder. Mit Stimme rollt auch das Folgen selbst, dann zählt die Hand.
  function gerollt() {
    if (feld && !uebersetzer.an) weg = feld.scrollHeight - feld.scrollTop - feld.clientHeight >= NAH_PX;
  }
  function vonHand(e: Event) {
    const taste = e instanceof KeyboardEvent ? /^(Arrow|Page|Home|End)/.test(e.key) : e.type !== "pointerdown" || e.target === feld;
    if (uebersetzer.an && taste) weg = true;
  }
  function mitlaufen(an: boolean) {
    fixiert = !an;
    if (an) {
      weg = false;
      folgen();
    }
  }
  async function kopiere() {
    const auswahl = getSelection();
    const text = auswahl && !auswahl.isCollapsed && feld?.contains(auswahl.anchorNode) ? auswahl.toString() : alsText(mitlesen.absaetze, uebersetzt);
    const ok = await kopieren(text);
    actions.showToast(ok ? t("radio.kopiert", { was: t("radio.mitlesen.text") }) : t("radio.kopierenFehler"), ok ? "success" : "error");
  }
  // Stimme des Übersetzers: das Angebot kommt frisch aus der Vertonung, gewählt gilt sie ab dem nächsten Absatz
  let stimmen = $state<Wahlwert[]>([]);
  let stimme = $state("");
  $effect(() => {
    if (!uebersetzer.an || stimmen.length) return;
    void server.laden().then(() => { stimme = String(server.zeile("uebersetzerstimme")?.wert ?? ""); });
    void server.angebot("uebersetzerstimme").then((a) => { stimmen = [{ wert: "", titel: t("radio.mitlesen.zeitstimme") }, ...a.optionen]; }).catch(() => undefined);
  });
  const waehlen = (w: string) => void server.sofortSpeichern("uebersetzerstimme", w).catch((f: Error) => actions.showToast(f.message, "error"));
  async function sprechen(an: boolean) {
    if (an && !mitlesen.stand?.laeuft) await onweiter();
    await uebersetzer.schalten(an);
  }
  const richtung = $derived(`${mitlesen.stand?.sprache.toUpperCase()} > ${mitlesen.stand?.ziel.toUpperCase()}`);
  const lage = $derived(mitlesen.fehler || (uebersetzer.spricht !== null ? t("radio.mitlesen.spricht") : "") || mitlesen.stand?.grund || (uebersetzer.an ? t("radio.mitlesen.stimmeKommt") : "") || t(`radio.mitlesen.${mitlesen.beginnt ? "beginnt" : mitlesen.stand?.zustand ?? "sammelt"}`));
</script>

<section class="rh-mitlesen" {@attach ganzZeigen} aria-label={t("radio.mitlesen.titel")}>
  <div class="rh-mitlese-tasten">
    <Schalter an={laeuftMit} symbol="fa-angles-down" text={t("radio.mitlesen.mitlaufen")} hilfe={t("radio.mitlesen.mitlaufenHilfe")} onwechsel={mitlaufen} />
    {#if mitlesen.fremd}
      <span class="rh-richtung"><Schalter an={uebersetzt} farbe="blau" symbol="fa-language" text={richtung} hilfe={t("radio.mitlesen.uebersetzenHilfe")}
        onwechsel={(an) => void mitlesen.uebersetzen(an).catch((f: Error) => actions.showToast(f.message, "error"))} /></span>
    {/if}
    {#if mitlesen.fremd && mitlesen.stand?.kann_sprechen}
      <Schalter an={uebersetzer.an} farbe="gelb" symbol="fa-headset" text={t("radio.mitlesen.stimme")} hilfe={t("radio.mitlesen.stimmeHilfe")}
        onwechsel={(an) => void sprechen(an).catch((f: Error) => actions.showToast(f.message, "error"))} />
    {/if}
    {#if uebersetzer.an && stimmen.length}<Auswahl bind:wert={stimme} optionen={stimmen} titel={t("radio.mitlesen.stimmwahl")} klein onwahl={waehlen} />{/if}
    <span class="rh-mitlese-fuss">
      <button class="rund rh-mini" type="button" title={t("radio.mitlesen.kopieren")} aria-label={t("radio.mitlesen.kopieren")} disabled={!mitlesen.absaetze.length}
              onclick={() => void kopiere()}><i class="fa-regular fa-copy"></i></button>
      <span class="rh-mitlese-lage" class:gestoert={!!mitlesen.fehler} title={lage} aria-live="polite">{lage}</span>
    </span>
  </div>
  {@render schalter()}
  <!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
  <div class="rh-mitlese-feld" bind:this={feld} onscroll={gerollt} onwheel={vonHand} ontouchmove={vonHand} onkeydown={vonHand} onpointerdown={vonHand}
       role="log" tabindex="0" aria-label={t("radio.mitlesen.text")}>
    {#each mitlesen.absaetze as a (a.nr)}
      <p class:spricht={uebersetzer.spricht === a.nr}><time datetime={a.zeit}>{uhrzeit(a.zeit)}</time>
        {#if uebersetzt && a.uebersetzung}<span>{a.uebersetzung}</span><span class="rh-mitlese-original">{a.text}</span>{:else}<span>{a.text}</span>{/if}</p>
    {:else}
      <p class="rh-mitlese-leer">{t("radio.mitlesen.leer")}</p>
    {/each}
  </div>
</section>
