<script lang="ts">
  // Werbung in einer Folge (Entwurf podcast-werbung.html, Zustände 2, 3 und 6; RAD-32): Leiste mit den Stellen, je Stelle
  // Zeit, Länge und Herkunft, anhören und "keine Werbung" (mit Rückgängig); Überspringen (Schalter des Abos), Werbung
  // suchen über die möglichen Quellen mit Fortschritt, eine Stelle beim Hören markieren (Beginn, dann Ende) und eine
  // Fassung ohne Werbung als neue Datei neben die gespeicherte legen. Am Rechner im Detail der Folge, am Telefon im Blatt.
  import { untrack } from "svelte";
  import { t } from "../../lib/i18n.svelte.js";
  import { actions } from "../../lib/store.svelte.js";
  import { stelleText } from "../../lib/podcasts/anzeige";
  import { aboliste, werbequelle, type Abo, type Folge, type Werbestelle, type Werbeherkunft } from "../../lib/podcasts";
  import type { Fortschritt } from "../../lib/ereignisstrom";
  import { tonelement } from "../../spieler/tonelement";
  import { werbesprung } from "../../spieler/werbesprung.svelte";
  import Schalter from "../bausteine/Schalter.svelte";

  let { folge, abo, spielt, schmal = false, onanhoeren, ongeaendert }: {
    folge: Folge;
    abo: Abo | undefined;
    /** diese Folge läuft gerade (dann geht Markieren am Abspielkopf) */
    spielt: boolean;
    /** Telefon: Stellen ohne eigene Spalte für die Zeit */
    schmal?: boolean;
    /** ab einer Stelle hören (die Stelle wird dabei nicht übersprungen) */
    onanhoeren: (von: number) => void;
    /** Zahl und Dauer der Stellen haben sich geändert (für die Zeile) */
    ongeaendert: (werbung: { anzahl: number; dauer: number }) => void;
  } = $props();

  const SYMBOL: Record<Werbeherkunft, string> = { kapitel: "fa-list-ol", hand: "fa-hand-pointer", vergleich: "fa-code-compare", transkript: "fa-comment-dots" };

  let stellen = $state<Werbestelle[]>([]);
  let quellen = $state<Werbeherkunft[]>([]);
  let geladen = $state(false);
  let verworfen = $state<Werbestelle | null>(null);
  let beginn = $state<number | null>(null);
  let auftrag = $state<{ was: string; f: Fortschritt | null } | null>(null);

  async function laden(): Promise<void> {
    try {
      const r = await werbequelle.stellen(folge.id);
      stellen = r.stellen;
      quellen = r.quellen;
    } finally {
      geladen = true;
    }
  }
  $effect(() => {
    void folge.id;
    untrack(() => void laden());
  });

  function gemeldet(): void {
    ongeaendert({ anzahl: stellen.length, dauer: stellen.reduce((s, x) => s + x.bis - x.von, 0) });
    werbesprung.neu(folge.id);
  }

  async function sicher(arbeit: () => Promise<void>): Promise<void> {
    try {
      await arbeit();
    } catch (f) {
      actions.showToast((f as Error).message || t("common.fehler"), "error");
    }
  }

  const keineWerbung = (s: Werbestelle) => sicher(async () => {
    await werbequelle.verwerfen(s.id, true);
    stellen = stellen.filter((x) => x.id !== s.id);
    verworfen = s;
    gemeldet();
  });
  const dochWerbung = () => sicher(async () => {
    const s = verworfen;
    if (!s) return;
    await werbequelle.verwerfen(s.id, false);
    verworfen = null;
    stellen = [...stellen, s].sort((a, b) => a.von - b.von);
    gemeldet();
  });

  function markieren(): void {
    const jetzt = tonelement().currentTime;
    if (beginn === null) { beginn = jetzt; return; }
    const [von, bis] = [Math.min(beginn, jetzt), Math.max(beginn, jetzt)];
    beginn = null;
    void sicher(async () => {
      const neu = await werbequelle.setzen(folge.id, von, bis);
      stellen = [...stellen, neu].sort((a, b) => a.von - b.von);
      gemeldet();
    });
  }

  async function suchen(): Promise<void> {
    const was = t("podcastAnsicht.werbung.suchen");
    auftrag = { was, f: null };
    await sicher(async () => {
      const gefunden = await werbequelle.suchen(folge.id, (f) => (auftrag = { was, f }));
      const zahl = Object.values(gefunden).reduce((s, n) => s + n, 0);
      actions.showToast(t(zahl === 1 ? "podcastAnsicht.werbung.gefundenEins" : "podcastAnsicht.werbung.gefunden", { n: zahl }), "success");
      await laden();
      gemeldet();
    });
    auftrag = null;
  }

  async function ohneWerbung(): Promise<void> {
    const was = t("podcastAnsicht.werbung.ohneSpeichern");
    auftrag = { was, f: null };
    await sicher(async () => {
      const pfad = await werbequelle.ohneWerbung(folge.id, (f) => (auftrag = { was, f }));
      actions.showToast(t("podcastAnsicht.werbung.ohneFertig", { pfad }), "success");
    });
    auftrag = null;
  }

  const ueberspringen = (an: boolean) => sicher(async () => {
    if (!abo) return;
    await werbequelle.aboSetzen(abo.id, { ueberspringen: an });
    aboliste.aendern(abo.id, { werbungUeberspringen: an });
  });

  const summe = $derived(stellen.reduce((s, x) => s + x.bis - x.von, 0));
  const dauer = $derived(folge.dauer || Math.max(0, ...stellen.map((s) => s.bis)));
  const prozent = (x: number) => (dauer ? Math.min(100, (x / dauer) * 100) : 0);
</script>

<section class="rh-werbeteil" class:schmal aria-label={t("podcastAnsicht.werbung.titel")}>
  <div class="rh-werbe-kopf"><h3><i class="fa-solid fa-rectangle-ad"></i>{t("podcastAnsicht.werbung.titel")}</h3>
    <span class="rh-still">{stellen.length === 1 ? t("podcastAnsicht.werbung.zusammenEins", { zeit: stelleText(summe) }) : stellen.length ? t("podcastAnsicht.werbung.zusammen", { n: stellen.length, zeit: stelleText(summe) }) : geladen ? t("podcastAnsicht.werbung.keine") : t("podcastAnsicht.laedt")}</span></div>
  {#if stellen.length}
    <div class="rh-werbeleiste" role="img" aria-label={t("podcastAnsicht.werbung.leiste", { n: stellen.length })}>
      <span class="gehoert" style:width="{prozent(folge.stelle)}%"></span>
      {#each stellen as s (s.id)}<span class="werbung" style:left="{prozent(s.von)}%" style:width="{Math.max(0.8, prozent(s.bis) - prozent(s.von))}%"></span>{/each}
      <span class="kopf" style:left="{prozent(folge.stelle)}%"></span>
    </div>
  {/if}
  {#if auftrag}
    <div class="rh-auftrag" role="status">
      <span>{auftrag.was}{auftrag.f ? `: ${auftrag.f.text}` : ""}</span>
      <div class="balken"><span style:width="{auftrag.f ? Math.round((auftrag.f.schritt / Math.max(1, auftrag.f.gesamt)) * 100) : 5}%"></span></div>
      <span class="rh-zahl">{auftrag.f ? `${auftrag.f.schritt}/${auftrag.f.gesamt}` : ""}</span></div>
  {:else if stellen.length}
    <ol class="rh-werbestellen">
      {#each stellen as s, i (s.id)}
        <li>
          <span class="rh-a-nr">{String(i + 1).padStart(2, "0")}</span>
          <span class="zeit"><b>{t("podcastAnsicht.werbung.vonBis", { von: stelleText(s.von), bis: stelleText(s.bis) })}</b><span>{stelleText(s.bis - s.von)}</span></span>
          <span class="herkunft"><span><i class="fa-solid {SYMBOL[s.herkunft]}"></i>{t(`schale.werbeherkunft_${s.herkunft}`)}</span>{#if s.text}<span class="rh-still">{s.text}</span>{/if}</span>
          <span class="aktionen">
            <button class="rund" type="button" title={t("podcastAnsicht.werbung.anhoeren")} aria-label={t("podcastAnsicht.werbung.anhoeren")}
                    onclick={() => onanhoeren(s.von)}><i class="fa-solid fa-play"></i></button>
            <button class="rund" type="button" title={t("podcastAnsicht.werbung.keineWerbungHilfe")} aria-label={t("podcastAnsicht.werbung.keineWerbung")}
                    onclick={() => void keineWerbung(s)}><i class="fa-solid fa-xmark"></i></button>
          </span>
        </li>
      {/each}
    </ol>
  {/if}
  {#if verworfen}
    <p class="rh-still rh-werbe-zurueck"><i class="fa-solid fa-check"></i>{t("podcastAnsicht.werbung.verworfen", { von: stelleText(verworfen.von) })}
      <button class="knopf still" type="button" onclick={() => void dochWerbung()}><i class="fa-solid fa-rotate-left"></i>{t("podcastAnsicht.werbung.rueckgaengig")}</button></p>
  {/if}
  <div class="rh-detail-knoepfe">
    {#if abo}<Schalter an={abo.werbungUeberspringen} farbe="bernstein" text={t("podcastAnsicht.werbung.ueberspringen")} hilfe={t("podcastAnsicht.werbung.ueberspringenHilfe")}
              onwechsel={(an) => void ueberspringen(an)} />{/if}
    {#if quellen.length}
      <button class="knopf" type="button" disabled={!!auftrag} title={t("podcastAnsicht.werbung.suchenHilfe")} onclick={() => void suchen()}>
        <i class="fa-solid fa-magnifying-glass"></i>{t("podcastAnsicht.werbung.suchen")}</button>
    {/if}
    {#if spielt}
      <button class="knopf" class:aktiv={beginn !== null} type="button" title={t("podcastAnsicht.werbung.markierenHilfe")} onclick={markieren}>
        <i class="fa-solid {beginn === null ? 'fa-flag' : 'fa-flag-checkered'}"></i>
        {beginn === null ? t("podcastAnsicht.werbung.beginnt") : t("podcastAnsicht.werbung.endet", { von: stelleText(beginn) })}</button>
    {/if}
    {#if folge.gespeichert && stellen.length}
      <button class="knopf" type="button" disabled={!!auftrag} title={t("podcastAnsicht.werbung.ohneSpeichernHilfe")} onclick={() => void ohneWerbung()}>
        <i class="fa-solid fa-scissors"></i>{t("podcastAnsicht.werbung.ohneSpeichern")}</button>
    {/if}
  </div>
</section>
