<script lang="ts">
  // Puffer am Telefon (RAD-46, Entwurf puffer.html Zustände 7 und 8): oben der Balken mit Titelgrenzen und Werbung,
  // darunter die Abschnitte als Liste, neuester oben. Antippen (auch auf dem Balken) klappt Hören, Aufnehmen und Bereich auf; im Bereich
  // werden Titel angehakt, unten steht Sichern. Ein fertiger Titel hat in seiner Zeile die Taste zum Speichern (RAD-132).
  import { appState, actions } from "../../lib/store.svelte.js";
  import { t } from "../../lib/i18n.svelte.js";
  import { formatTimeShort } from "../../lib/formatters.js";
  import { abwaehlbar, bei, bereichAus, imBereich, type Abschnitt } from "../../lib/radio/abschnitte";
  import { puffer } from "../../spieler/puffer.svelte";
  import { tick, untrack } from "svelte";
  import { titelsichern } from "../../spieler/titelsichern.svelte";
  import PufferBalken from "./PufferBalken.svelte";

  /** `ziel`: dieser Abschnitt ist beim Öffnen aufgeklappt und im Blick */
  let { onzu, ziel = null }: { onzu: () => void; ziel?: Abschnitt | null } = $props();

  let offen = $state<number | null>(null);
  let bereichAn = $state(false);
  let wahl = $state<{ a: Abschnitt; b: Abschnitt } | null>(null);
  let beschaeftigt = $state(false);

  const liste = $derived(puffer.abschnitte);
  const stelle = $derived(puffer.stelle ?? puffer.ende);
  const bereich = $derived(wahl ? bereichAus(wahl.a, wahl.b) : null);
  const gewaehlt = $derived(bereich ? imBereich(liste, bereich.von, bereich.bis) : []);
  const name = (a: Abschnitt) => puffer.benennen(a);

  let listeEl = $state<HTMLElement>();
  async function zeigen(a: Abschnitt): Promise<void> {
    if (bereichAn) return antippen(a);
    offen = a.von;
    await tick();
    listeEl?.querySelector(`[data-von="${a.von}"]`)?.scrollIntoView({ block: "center" });
  }
  $effect(() => { const a = ziel; if (a && listeEl) untrack(() => void zeigen(a)); });

  function antippen(a: Abschnitt): void {
    if (!bereichAn) { offen = offen === a.von ? null : a.von; return; }
    if (a.art === "werbung" || a.laufend) return;
    if (!wahl) wahl = { a, b: a };
    else if (wahl.a.von === a.von && wahl.b.von === a.von) wahl = null;
    else wahl = { a: wahl.a, b: a };
  }

  async function aufnehmen(a: Abschnitt): Promise<void> {
    if (appState.isRecording) return actions.showToast(t("puffer.aufnahmeLaeuft"), "error");
    beschaeftigt = true;
    try {
      await puffer.aufnehmenAb(a.von);
      actions.showToast(t("puffer.aufnahmeGestartet", { titel: name(a) }), "success");
      offen = null;
    } catch (e) {
      actions.showToast(t("puffer.fehler", { text: (e as Error).message }), "error");
    } finally {
      beschaeftigt = false;
    }
  }

  async function abwaehlen(a: Abschnitt) {
    beschaeftigt = true;
    try {
      await puffer.abwaehlen(a, !a.abgewaehlt);
      offen = null;
    } catch (e) {
      actions.showToast(t("puffer.fehler", { text: (e as Error).message }), "error");
    } finally {
      beschaeftigt = false;
    }
  }

  async function sichern(): Promise<void> {
    if (!bereich) return;
    if (appState.isRecording) return actions.showToast(t("puffer.aufnahmeLaeuft"), "error");
    beschaeftigt = true;
    try {
      await puffer.bereichSichern(bereich.von, bereich.bis);
      actions.showToast(t("puffer.bereichGesichert", { laenge: formatTimeShort(bereich.bis - bereich.von) }), "success");
      wahl = null;
      bereichAn = false;
    } catch (e) {
      actions.showToast(t("puffer.fehler", { text: (e as Error).message }), "error");
    } finally {
      beschaeftigt = false;
    }
  }
</script>

<div class="tp" role="dialog" aria-modal="true" aria-label={t("puffer.puffer")}>
  <div class="tp-kopf">
    <button class="tp-knopf-rund" type="button" onclick={onzu} aria-label={t("puffer.schliessen")}><i class="fa-solid fa-chevron-left"></i></button>
    <span class="tp-titel">{t("puffer.puffer")} · {formatTimeShort(puffer.ende - puffer.anfang)}</span>
    <span></span>
  </div>
  <div class="tp-oben"><PufferBalken {stelle} {bereich} links={puffer.uhr(puffer.anfang)} mitte={t("puffer.zahlTitel", { n: puffer.titelZahl })} onwahl={(a) => void zeigen(a)} /></div>
  <ol class="tp-liste" bind:this={listeEl}>
    {#each [...liste].reverse() as a (a.von)}
      {@const hoert = bei(liste, stelle)?.von === a.von}
      {@const imBer = gewaehlt.some((g) => g.von === a.von)}
      <li class="tp-zeile {a.art}" class:abgewaehlt={a.abgewaehlt} class:hoert class:gewaehlt={imBer} class:mit-sichern={a.komplett && !bereichAn} data-von={a.von}>
        <button class="tp-kern" class:mit-wahl={bereichAn} type="button" onclick={() => antippen(a)} aria-expanded={!bereichAn ? offen === a.von : undefined}>
          {#if bereichAn}
            <i class="tp-wahl {imBer ? 'fa-solid fa-square-check' : 'fa-regular fa-square'}" class:aus={a.art === "werbung" || a.laufend}></i>
          {/if}
          <span class="tp-text"><b>{#if a.art === "werbung"}<i class="fa-solid fa-rectangle-ad"></i>{/if}{name(a)}</b>
            <span class="tp-meta"><span>{puffer.uhr(a.von)}</span><span>{formatTimeShort(a.bis - a.von)}</span>{#if a.laufend}<span class="tp-laeuft">{t("puffer.laeuft")}</span>{/if}</span></span>
        </button>
        {#if a.komplett && !bereichAn}
          <button class="tp-sichern" type="button" title={titelsichern.hilfe(a)} aria-label="{titelsichern.hilfe(a)}: {name(a)}" disabled={!titelsichern.geht(a)}
            onclick={() => void titelsichern.tun(a)}><i class={titelsichern.symbol(a)}></i></button>
        {/if}
        {#if !bereichAn && offen === a.von}
          <div class="tp-tat">
            <button type="button" onclick={() => { puffer.springen(a.von); offen = null; }}><i class="fa-solid fa-play"></i>{t("puffer.hierHoeren")}</button>
            {#if appState.isRecording && abwaehlbar(a)}
              <button type="button" aria-pressed={!!a.abgewaehlt} title={a.abgewaehlt ? t("puffer.anwaehlen") : t("puffer.abwaehlen")} disabled={beschaeftigt}
                onclick={() => void abwaehlen(a)}><i class="fa-solid {a.abgewaehlt ? 'fa-rotate-left' : 'fa-ban'}"></i>{a.abgewaehlt ? t("puffer.anwaehlenKurz") : t("puffer.abwaehlenKurz")}</button>
            {:else}
            <button type="button" class="tp-rec" title={t("puffer.aufnahmeAbHier")} disabled={a.art === "werbung" || !!appState.isRecording || beschaeftigt}
              onclick={() => void aufnehmen(a)}><i class="fa-solid fa-circle"></i>{t("puffer.aufnehmen")}</button>
            {/if}
            <button type="button" disabled={a.art === "werbung" || a.laufend} onclick={() => { bereichAn = true; wahl = { a, b: a }; offen = null; }}>
              <i class="fa-solid fa-square-check"></i>{t("puffer.bereich")}</button>
          </div>
        {/if}
      </li>
    {/each}
  </ol>
  {#if bereichAn}
    <div class="tp-fuss">
      <span>{#if bereich}<b>{t("puffer.bereichKurz", { n: gewaehlt.filter((a) => a.art !== "werbung").length, laenge: formatTimeShort(bereich.bis - bereich.von) })}</b>{:else}{t("puffer.bereichWahl")}{/if}</span>
      <button type="button" onclick={() => { bereichAn = false; wahl = null; }}>{t("puffer.abbrechen")}</button>
      <button type="button" class="tp-primaer" disabled={!bereich || !!appState.isRecording || beschaeftigt} onclick={() => void sichern()}>
        <i class="fa-solid fa-circle"></i>{t("puffer.sichernKurz")}</button>
    </div>
  {/if}
</div>

<style>
  .tp { position: fixed; inset: 0; z-index: 30; display: grid; grid-template-rows: auto auto minmax(0, 1fr) auto;
    padding-top: var(--rahmen-sicher-oben); background: var(--t-grund); color: var(--t-text); }
  .tp-kopf { display: grid; grid-template-columns: 48px minmax(0, 1fr) 48px; align-items: center; padding: 0 var(--rahmen-rand); }
  .tp-knopf-rund { width: 48px; height: 48px; border: none; border-radius: 12px; background: transparent; color: var(--t-text); font-size: calc(var(--gross) * 1.3); }
  .tp-titel { text-align: center; font-size: var(--klein); font-weight: 700; letter-spacing: .04em; text-transform: uppercase; color: var(--t-text-2); }
  .tp-oben { padding: 4px var(--rahmen-rand) 10px; }
  .tp-liste { min-height: 0; margin: 0; padding: 0 var(--rahmen-rand) 12px; list-style: none; display: grid; gap: 6px; align-content: start; overflow-y: auto; overflow-x: clip; }
  .tp-zeile { display: grid; gap: 8px; padding: 8px 10px; border-radius: 12px; background: var(--t-flaeche); }
  .tp-zeile.abgewaehlt b { text-decoration: line-through; opacity: .6; }
  .tp-zeile.hoert { background: color-mix(in srgb, var(--led-blau) 16%, var(--t-flaeche)); }
  .tp-zeile.gewaehlt { box-shadow: inset 0 0 0 2px var(--led-rot); }
  .tp-zeile.werbung b { color: var(--violett); }
  .tp-kern { display: grid; grid-template-columns: minmax(0, 1fr); gap: 10px; align-items: start; padding: 0; border: none; background: transparent;
    color: inherit; font: inherit; text-align: left; }
  .tp-kern.mit-wahl { grid-template-columns: 24px minmax(0, 1fr); }
  .tp-wahl { margin-top: .3em; justify-self: center; }
  .tp-wahl { font-size: calc(var(--gross) * 1.15); color: var(--t-text-2); }
  .tp-wahl.aus { opacity: .35; }
  .tp-zeile.gewaehlt .tp-wahl { color: var(--led-rot); }
  .tp-text { display: grid; min-width: 0; }
  .tp-text b { font-size: var(--gross); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tp-text b i { margin-right: 6px; }
  .tp-meta { display: flex; gap: 12px; font-size: var(--klein); color: var(--t-text-2); font-variant-numeric: tabular-nums; }
  .tp-laeuft { padding: 0 6px; border-radius: 4px; background: var(--led-rot); color: var(--rh-auf-rot); font-weight: 700; text-transform: uppercase; }
  .tp-zeile.mit-sichern { grid-template-columns: minmax(0, 1fr) 44px; }
  .tp-zeile.mit-sichern .tp-tat { grid-column: 1 / -1; }
  .tp-sichern { inline-size: 44px; block-size: 44px; border: 1px solid var(--rand); border-radius: 10px; background: var(--t-flaeche-2); color: var(--t-text); font-size: var(--gross); }
  .tp-sichern:disabled { opacity: .6; }
  .tp-tat { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; }
  .tp-tat button, .tp-fuss button { display: inline-flex; align-items: center; justify-content: center; gap: 6px; min-height: 44px; padding: 0 6px;
    border: 1px solid var(--rand); border-radius: 10px; background: var(--t-flaeche-2); color: var(--t-text); font: inherit; font-size: var(--klein); }
  .tp-tat button:disabled, .tp-fuss button:disabled { opacity: .45; }
  .tp-rec i, .tp-primaer i { color: var(--led-rot); }
  .tp-fuss { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; gap: 8px; align-items: center; padding: 10px var(--rahmen-rand) 14px;
    background: color-mix(in srgb, var(--led-rot) 12%, var(--t-flaeche)); font-size: var(--klein); }
  .tp-primaer { font-weight: 700; }
</style>
