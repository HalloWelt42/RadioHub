<script lang="ts">
  // Das Feld zum Mitlesen im Steckbrief (RAD-129): eine Zeile mit eigenen Tasten, darunter der laufende Text. Es läuft mit,
  // bis man nach oben rollt oder es fixiert; unten angekommen läuft es wieder mit. Text ist frei wählbar und kopierbar.
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
  let feld = $state<HTMLElement>();
  let unten = $state(true);
  let fixiert = $state(false);
  const laeuftMit = $derived(unten && !fixiert);
  const uebersetzt = $derived(mitlesen.fremd && !!mitlesen.stand?.uebersetzen);

  $effect(() => {
    void mitlesen.absaetze;
    if (laeuftMit) void tick().then(ansEnde);
  });
  function ansEnde() {
    if (feld) feld.scrollTop = feld.scrollHeight;
  }
  function gerollt() {
    if (feld) unten = feld.scrollHeight - feld.scrollTop - feld.clientHeight < NAH_PX;
  }
  function mitlaufen(an: boolean) {
    fixiert = !an;
    if (an) {
      unten = true;
      ansEnde();
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
  const lage = $derived(mitlesen.fehler || (uebersetzer.spricht !== null ? t("radio.mitlesen.spricht") : "") || mitlesen.stand?.grund || t(`radio.mitlesen.${mitlesen.beginnt ? "beginnt" : mitlesen.stand?.zustand ?? "sammelt"}`));
</script>

<section class="rh-mitlesen" aria-label={t("radio.mitlesen.titel")}>
  <div class="rh-mitlesen-kopf">
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
    <button class="rund rh-mini" type="button" title={t("radio.mitlesen.kopieren")} aria-label={t("radio.mitlesen.kopieren")} disabled={!mitlesen.absaetze.length}
            onclick={() => void kopiere()}><i class="fa-regular fa-copy"></i></button>
    <span class="rh-mitlese-lage" class:gestoert={!!mitlesen.fehler} aria-live="polite">{lage}</span>
    {@render schalter()}
  </div>
  <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
  <div class="rh-mitlese-feld" bind:this={feld} onscroll={gerollt} role="log" tabindex="0" aria-label={t("radio.mitlesen.text")}>
    {#each mitlesen.absaetze as a (a.nr)}
      <p class:spricht={uebersetzer.spricht === a.nr}><time datetime={a.zeit}>{uhrzeit(a.zeit)}</time>
        {#if uebersetzt && a.uebersetzung}<span>{a.uebersetzung}</span><span class="rh-mitlese-original">{a.text}</span>{:else}<span>{a.text}</span>{/if}</p>
    {:else}
      <p class="rh-mitlese-leer">{t("radio.mitlesen.leer")}</p>
    {/each}
  </div>
</section>
