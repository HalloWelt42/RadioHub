<script lang="ts">
  // Das Feld zum Mitlesen im Steckbrief (RAD-129): der laufende Text in lesbarer Breite, die Tasten daneben. Es läuft mit dem
  // neuesten Text mit, spricht der Übersetzer (RAD-130), mit der gesprochenen Stelle; bis man selbst rollt oder es fixiert.
  // Text ist frei wählbar und kopierbar.
  import type { Snippet } from "svelte";
  import { Auswahl, kopieren } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { actions } from "../../lib/store.svelte.js";
  import { alsText, mitlesen, uhrzeit } from "../../lib/radio/mitlesen.svelte";
  import { server, type Wahlwert } from "../../lib/einstellungen";
  import { uebersetzer } from "../../spieler/uebersetzer.svelte";
  import Lesefeld, { type Lesezeile } from "../bausteine/Lesefeld.svelte";
  import Schalter from "../bausteine/Schalter.svelte";

  /** `schalter`: die Schalter, die an ihrem Platz bleiben (Mitlesen, Werbung) */
  /** `onweiter`: das Mitlesen nach einem Ende (Radio aus, Server neu gestartet) fortsetzen */
  let { schalter, onweiter }: { schalter: Snippet; onweiter: () => Promise<void> } = $props();

  let lesefeld = $state<Lesefeld>();
  let mitlaufen = $state(true);
  const uebersetzt = $derived(mitlesen.fremd && !!mitlesen.stand?.uebersetzen);
  const zeilen = $derived(mitlesen.absaetze.map((a): Lesezeile => ({ nr: a.nr, zeit: uhrzeit(a.zeit), datetime: a.zeit,
    ...(uebersetzt && a.uebersetzung ? { text: a.uebersetzung, klein: a.text } : { text: a.text }) })));

  /** das Feld nutzt die Höhe der Liste: sie rollt so weit, dass es ganz zu sehen ist */
  const ganzZeigen = (e: HTMLElement) => { requestAnimationFrame(() => e.scrollIntoView({ block: "nearest", behavior: "smooth" })); };
  async function kopiere() {
    const text = lesefeld?.markiert() || alsText(mitlesen.absaetze, uebersetzt);
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
    <Schalter an={mitlaufen} symbol="fa-angles-down" text={t("radio.mitlesen.mitlaufen")} hilfe={t("radio.mitlesen.mitlaufenHilfe")} onwechsel={(an) => (mitlaufen = an)} />
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
      {#if mitlesen.stand?.ablegen}<i class="fa-solid fa-cloud-arrow-up rh-mitlese-wolke" role="img" title={t("radio.mitlesen.ablegen")} aria-label={t("radio.mitlesen.ablegen")}></i>{/if}
      <span class="rh-mitlese-lage" class:gestoert={!!mitlesen.fehler} title={lage} aria-live="polite">{lage}</span>
    </span>
  </div>
  {@render schalter()}
  <Lesefeld bind:this={lesefeld} bind:mitlaufen {zeilen} aktiv={uebersetzer.spricht} folgtAktiv={uebersetzer.an} leer={t("radio.mitlesen.leer")} beschriftung={t("radio.mitlesen.text")} />
</section>
