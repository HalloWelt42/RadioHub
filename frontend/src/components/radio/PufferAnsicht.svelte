<script lang="ts">
  // Großansicht des Zeitversatzes (RAD-46, Entwurf mockups/radio-filter/puffer.html Zustände 3 bis 5), Adresse
  // /radio/puffer: Kopf mit Sender und Sprüngen, Zeitleiste des ganzen Puffers (Übersicht und Ausschnitt mit Zoom; Rad
  // oder Ziehen verschiebt, Doppelklick springt hin) und die Abschnitte als Liste, neuester oben. Je Titel: hier hören,
  // Aufnahme ab hier, in den Bereich nehmen; ein Bereich (Titel A bis B) wird als fertige Aufnahme gesichert.
  import { appState, actions } from "../../lib/store.svelte.js";
  import { t } from "../../lib/i18n.svelte.js";
  import * as sfx from "../../lib/uiSounds.js";
  import { formatTimeShort } from "../../lib/formatters.js";
  import { bei, bereichAus, fenster, imBereich, naechster, prozent, vorheriger, type Abschnitt } from "../../lib/radio/abschnitte";
  import { puffer } from "../../spieler/puffer.svelte";
  import { live } from "../../spieler/aktionen";
  import Logo from "./Logo.svelte";

  /** zurück zur Liste; wohin genau, weiß die Radio-Ansicht (RAD-55) */
  let { onzu }: { onzu: () => void } = $props();

  type Zoom = "alles" | 30 | 10;
  const ZOOMS: Zoom[] = ["alles", 30, 10];
  /** unter dieser Länge gilt der Puffer als jung (Hinweis, dass es davor nichts gibt) */
  const JUNG_S = 300;

  let zoom = $state<Zoom>(30);
  /** Mitte des Ausschnitts; null: folgt der Stelle, die man hört */
  let mitte = $state<number | null>(null);
  let wahl = $state<{ a: Abschnitt; b: Abschnitt } | null>(null);
  let beschaeftigt = $state(false);

  const sender = $derived(appState.currentStation as { uuid: string; name: string; favicon?: string } | null);
  const liste = $derived(puffer.abschnitte);
  const anfang = $derived(puffer.anfang);
  const ende = $derived(puffer.ende);
  const stelle = $derived(puffer.stelle ?? ende);
  /** junger Puffer (Entwurf Zustand 5): nur der Ausschnitt über alles, ohne Übersicht, Zoom und Titelsprünge */
  const jung = $derived(ende - anfang < JUNG_S);
  const breite = $derived(zoom === "alles" || jung ? ende - anfang : zoom * 60);
  const sicht = $derived(fenster(mitte ?? stelle, breite, anfang, ende));
  const imAusschnitt = $derived(liste.filter((a) => a.bis > sicht[0] && a.von < sicht[1]));
  const werbungSumme = $derived(liste.filter((a) => a.art === "werbung").reduce((s, a) => s + a.bis - a.von, 0));
  const bereich = $derived(wahl ? bereichAus(wahl.a, wahl.b) : null);
  const gewaehlt = $derived(bereich ? imBereich(liste, bereich.von, bereich.bis) : []);
  const aufnahme = $derived(!!appState.isRecording);

  const uhr = (s: number) => puffer.uhr(s);
  const name = (a: Abschnitt) => puffer.benennen(a);
  const p = (s: number) => prozent(s, sicht[0], sicht[1]);
  const skala = $derived.by(() => {
    const schritt = breite > 3600 ? 900 : breite > 1200 ? 300 : 60, werte: number[] = [];
    for (let s = Math.ceil(sicht[0] / schritt) * schritt; s <= sicht[1]; s += schritt) if (p(s) > 4 && p(s) < 96) werte.push(s);
    return werte;
  });

  function schliessen(): void {
    sfx.click();
    onzu();
  }

  function hoeren(a: Abschnitt): void {
    sfx.click();
    puffer.springen(a.von);
  }

  function waehlen(a: Abschnitt): void {
    sfx.click();
    if (!wahl) wahl = { a, b: a };
    else if (wahl.a.von === a.von && wahl.b.von === a.von) wahl = null;
    else wahl = { a: wahl.a, b: a };
  }

  async function aufnehmenAb(a: Abschnitt): Promise<void> {
    if (aufnahme) return actions.showToast(t("puffer.aufnahmeLaeuft"), "error");
    beschaeftigt = true;
    try {
      await puffer.aufnehmenAb(a.von);
      actions.showToast(t("puffer.aufnahmeGestartet", { titel: name(a) }), "success");
    } catch (e) {
      actions.showToast(t("puffer.fehler", { text: (e as Error).message }), "error");
    } finally {
      beschaeftigt = false;
    }
  }

  async function sichern(): Promise<void> {
    if (!bereich) return;
    if (aufnahme) return actions.showToast(t("puffer.aufnahmeLaeuft"), "error");
    beschaeftigt = true;
    try {
      await puffer.bereichSichern(bereich.von, bereich.bis);
      actions.showToast(t("puffer.bereichGesichert", { laenge: formatTimeShort(bereich.bis - bereich.von) }), "success");
      wahl = null;
    } catch (e) {
      actions.showToast(t("puffer.fehler", { text: (e as Error).message }), "error");
    } finally {
      beschaeftigt = false;
    }
  }

  // Zeitleiste: Rad und Ziehen verschieben den Ausschnitt, Doppelklick springt hin, Klick in die Übersicht holt ihn dorthin
  let ausschnitt = $state<HTMLDivElement>();
  let zug: { x: number; mitte: number } | null = null;
  const sekundeBei = (x: number, el: HTMLElement, von: number, bis: number) => {
    const r = el.getBoundingClientRect();
    return von + ((x - r.left) / Math.max(1, r.width)) * (bis - von);
  };
  function rad(e: WheelEvent): void {
    if (zoom === "alles" || jung) return;
    e.preventDefault();
    mitte = Math.min(ende, Math.max(anfang, (mitte ?? stelle) + Math.sign(e.deltaY || e.deltaX) * breite * 0.1));
  }
  function ziehenStart(e: PointerEvent): void {
    if (zoom === "alles" || jung) return;
    zug = { x: e.clientX, mitte: mitte ?? stelle };
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  }
  function ziehen(e: PointerEvent): void {
    if (!zug || !ausschnitt) return;
    const r = ausschnitt.getBoundingClientRect();
    mitte = Math.min(ende, Math.max(anfang, zug.mitte - ((e.clientX - zug.x) / Math.max(1, r.width)) * breite));
  }
  function doppelklick(e: MouseEvent): void {
    if (!ausschnitt) return;
    puffer.springen(Math.min(ende, Math.max(anfang, sekundeBei(e.clientX, ausschnitt, sicht[0], sicht[1]))));
  }
  function uebersichtKlick(e: MouseEvent): void {
    mitte = sekundeBei(e.clientX, e.currentTarget as HTMLElement, anfang, ende);
  }
</script>

<section class="rh-puffer-gross" aria-label={t("puffer.titel", { sender: sender?.name ?? "" })}>
  {#if !puffer.aktiv || !sender}
    <div class="rh-ohne-treffer"><i class="fa-solid fa-clock-rotate-left"></i><b>{t("puffer.ohneZeitversatz")}</b>
      <button class="knopf" type="button" onclick={schliessen}><i class="fa-solid fa-radio"></i>{t("puffer.schliessen")}</button></div>
  {:else}
    <div class="rh-pg-kopf">
      <Logo uuid={sender.uuid} name={sender.name} logo={sender.favicon ?? ""} />
      <div class="rh-pg-titel"><h2>{t("puffer.titel", { sender: sender.name })}</h2>
        <span class="rh-still">{t("puffer.kopfZeile", { seit: uhr(anfang), laenge: formatTimeShort(ende - anfang), max: formatTimeShort(puffer.groesste), titel: puffer.titelZahl, werbung: formatTimeShort(werbungSumme) })}</span></div>
      <div class="rh-pg-knoepfe">
        {#if !jung}
        <button class="knopf" type="button" title={t("puffer.titelZurueckHilfe")} disabled={vorheriger(liste, stelle) === null}
          onclick={() => { puffer.vorher(); sfx.click(); }}><i class="fa-solid fa-backward-step"></i>{t("puffer.titelZurueck")}</button>
        <button class="knopf" type="button" title={t("puffer.titelVorHilfe")} disabled={naechster(liste, stelle) === null}
          onclick={() => { puffer.weiter(); sfx.click(); }}>{t("puffer.titelVor")}<i class="fa-solid fa-forward-step"></i></button>
        {/if}
        <button class="knopf" type="button" title={appState.isLive ? t("player.bereitsLive") : t("player.goLive")} disabled={!!appState.isLive}
          onclick={() => { live(); mitte = null; sfx.click(); }}><i class="fa-solid fa-tower-broadcast"></i>{t("kanzel.live")}</button>
        <button class="rund" type="button" aria-label={t("puffer.schliessen")} title={t("puffer.schliessen")} onclick={schliessen}><i class="fa-solid fa-xmark"></i></button>
      </div>
    </div>

    <div class="rh-pg-leiste">
      {#if !jung}
      <div class="rh-pg-leiste-kopf"><span class="ak-etikett">{t("puffer.zeitleiste")}</span>
        <div class="rh-pg-zoom" role="group" aria-label={t("puffer.zoom")}>
          {#each ZOOMS as z (z)}
            <button class="knopf" class:aktiv={zoom === z} type="button" aria-pressed={zoom === z} onclick={() => { zoom = z; mitte = null; sfx.click(); }}>
              {z === "alles" ? t("puffer.zoomAlles") : t("puffer.zoomMin", { n: z })}</button>
          {/each}
        </div>
        <span class="rh-still">{t("puffer.zeitleisteHilfe")}</span>
      </div>
      <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
      <div class="rh-pg-uebersicht" onclick={uebersichtKlick}>
        <div class="balken"><span style:width="{prozent(stelle, anfang, ende)}%"></span>
          {#each liste.filter((a) => a.art === "werbung") as a (a.von)}<i class="rh-werbemarke" style:left="{prozent(a.von, anfang, ende)}%" style:width="{Math.max(0.5, prozent(a.bis, anfang, ende) - prozent(a.von, anfang, ende))}%"></i>{/each}</div>
        <div class="rh-titelstriche" aria-hidden="true">{#each liste.filter((a) => a.von > anfang + 0.5) as a (a.von)}<i style:left="{prozent(a.von, anfang, ende)}%"></i>{/each}</div>
        {#if bereich}<i class="rh-pg-bereich" style:left="{prozent(bereich.von, anfang, ende)}%" style:width="{prozent(bereich.bis, anfang, ende) - prozent(bereich.von, anfang, ende)}%"></i>{/if}
        {#if zoom !== "alles"}<i class="rh-pg-fenster" style:left="{prozent(sicht[0], anfang, ende)}%" style:width="{prozent(sicht[1], anfang, ende) - prozent(sicht[0], anfang, ende)}%"></i>{/if}
      </div>
      {/if}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="rh-pg-ausschnitt" bind:this={ausschnitt} class:ziehbar={zoom !== "alles" && !jung} aria-label={t("puffer.ausschnitt")}
           onwheel={rad} onpointerdown={ziehenStart} onpointermove={ziehen} onpointerup={() => (zug = null)} onpointercancel={() => (zug = null)} ondblclick={doppelklick}>
        {#each imAusschnitt as a, i (a.von)}
          {@const l = p(a.von)}
          <div class="rh-pg-block {a.art}" class:zweit={i % 2 === 1} class:gewaehlt={gewaehlt.some((g) => g.von === a.von)} style:left="{l}%" style:width="{p(a.bis) - l}%"
               title="{name(a)}, {formatTimeShort(a.bis - a.von)}">
            <b>{name(a)}</b><span class="rh-zahl">{uhr(a.von)} · {formatTimeShort(a.bis - a.von)}</span></div>
        {/each}
        <i class="rh-pg-kopfstrich" style:left="{p(stelle)}%"></i>
        {#if sicht[1] >= ende - 1}<span class="rh-pg-live">{t("puffer.live")}</span>{/if}
      </div>
      {#if !jung}<div class="rh-pg-skala">{#each skala as s (s)}<span style:left="{p(s)}%">{uhr(s)}</span>{/each}</div>{/if}
    </div>

    {#if jung}
      <p class="rh-pg-hinweis"><i class="fa-solid fa-circle-info"></i><span>{t("puffer.jungHinweis")}</span></p>
    {/if}

    <div class="rh-pg-spalten" aria-hidden="true"><span>{t("puffer.ab")}</span><span>{t("puffer.spalteTitel")}</span><span>{t("puffer.laenge")}</span><span></span></div>
    <ol class="rh-pg-liste">
      {#each [...liste].reverse() as a (a.von)}
        {@const hoert = bei(liste, stelle)?.von === a.von}
        {@const imBer = gewaehlt.some((g) => g.von === a.von)}
        <li class="rh-pg-zeile {a.art}" class:hoert class:gewaehlt={imBer}>
          <span class="rh-zahl rh-pg-ab">{uhr(a.von)}</span>
          <span class="rh-pg-name">{#if a.art === "werbung"}<i class="fa-solid fa-rectangle-ad"></i>{/if}<b title={a.titel}>{name(a)}</b>{#if a.laufend}<span class="rh-pg-laeuft">{t("puffer.laeuft")}</span>{/if}</span>
          <span class="rh-zahl rh-pg-laenge">{formatTimeShort(a.bis - a.von)}</span>
          <span class="rh-pg-aktionen">
            <button class="rund" type="button" title={t("puffer.hierHoeren")} aria-label={t("puffer.hierHoeren")} onclick={() => hoeren(a)}><i class="fa-solid fa-play"></i></button>
            <button class="rund rh-pg-rec" type="button" title={t("puffer.aufnahmeAbHier")} aria-label={t("puffer.aufnahmeAbHier")}
              disabled={a.art === "werbung" || aufnahme || beschaeftigt} onclick={() => void aufnehmenAb(a)}><i class="fa-solid fa-circle"></i></button>
            <button class="rund rh-pg-wahl" type="button" title={t("puffer.bereichWahl")} aria-label={t("puffer.bereichWahl")} aria-pressed={imBer}
              disabled={a.art === "werbung" || a.laufend} onclick={() => waehlen(a)}><i class={imBer ? "fa-solid fa-square-check" : "fa-regular fa-square"}></i></button>
          </span>
        </li>
      {/each}
    </ol>

    {#if bereich}
      {@const titel = gewaehlt.filter((a) => a.art !== "werbung").length}
      <div class="rh-pg-fuss" role="status">
        <i class="fa-solid fa-square-check"></i>
        <span><b>{t("puffer.bereichTitel")}</b>: {t("puffer.bereichFuss", { n: titel, von: uhr(bereich.von), bis: uhr(bereich.bis), laenge: formatTimeShort(bereich.bis - bereich.von) })}</span>
        <button class="knopf primaer rh-pg-sichern" type="button" disabled={aufnahme || beschaeftigt} onclick={() => void sichern()}><i class="fa-solid fa-circle"></i>{t("puffer.sichern")}</button>
        <button class="knopf" type="button" onclick={() => (wahl = null)}>{t("puffer.abbrechen")}</button>
      </div>
    {/if}
  {/if}
</section>
