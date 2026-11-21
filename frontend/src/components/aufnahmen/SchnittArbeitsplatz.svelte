<script lang="ts">
  // Schnitt als Arbeitsplatz über die ganze Breite (Entwurf aufnahmen.html, RAD-17), gleich für eine Aufnahme und eine
  // Datei der Kellerwolke: Kopf mit Schritten und Rückgängig, Ausschnitt, Höhe, Mitlaufen, Marker (Knopf, Doppelklick,
  // Taste M, aus Titeln), Wellenform und Übersicht, Stücke mit Namen und Behalten, Schneiden mit Rückfrage,
  // Normalisieren, Umwandeln, Fortschritt. Gehört wird über ein eigenes Tonelement; das Radio hält dafür an.
  import { onMount, untrack } from "svelte";
  import { Auswahl, Rueckfrage } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { actions, appState } from "../../lib/store.svelte.js";
  import { dauer as dauerText, zeit } from "../../lib/aufnahmen/anzeige";
  import { Arbeitsplatz, schnittquelle, type Fortschritt, type Schnittgegenstand, type Schnittinfo } from "../../lib/schnitt";
  import Wellenform from "./Wellenform.svelte";
  import Schalter from "../radio/Schalter.svelte";

  let { gegenstand, bereich = null, onschliessen, ongeaendert }: {
    gegenstand: Schnittgegenstand;
    /** beim Öffnen zeigen (Schneiden an einem Titel: dessen Stelle) */
    bereich?: { von: number; bis: number } | null;
    onschliessen: () => void;
    /** nach einem Schritt: die Liste weiß von neuen Titeln oder Dateien */
    ongeaendert: () => void;
  } = $props();

  const platz = new Arbeitsplatz();
  let info = $state<Schnittinfo | null>(null);
  let fehler = $state("");
  let spitzen = $state(new Float32Array(0));
  let laedtWelle = $state(false);
  let ton = $state<HTMLAudioElement>();
  let spielt = $state(false);
  let fragt = $state(false);
  let auftrag = $state<{ was: string; f: Fortschritt | null } | null>(null);
  let format = $state<"mp3" | "ogg" | "aac">("mp3");
  let bitrate = $state(192);
  let mono = $state(false);
  /** Tastenkürzel nur auf Wunsch (Nutzer 21.11.2026: "hilfe verbergen") */
  let tastenhilfe = $state(false);
  const BITRATEN = [96, 128, 192, 256, 320].map((b) => ({ wert: String(b), titel: `${b} kbit/s` }));
  const HOEHEN = [1, 2, 4, 8, 16].map((h) => ({ wert: String(h), titel: `${h}x` }));

  async function laden(neuWelle: boolean): Promise<void> {
    fehler = "";
    try {
      info = await schnittquelle.info(gegenstand);
      platz.uebernehmen(info);
      if (bereich && neuWelle) {
        platz.von = Math.max(0, bereich.von - 5);
        platz.bis = Math.min(info.dauer, bereich.bis + 5);
        platz.kopf = bereich.von;
      }
      if (neuWelle) await welleLaden(info.dauer);
    } catch (f) {
      fehler = (f as Error).message;
    }
  }

  async function welleLaden(dauer: number): Promise<void> {
    laedtWelle = true;
    const alle = new Float32Array(Math.ceil(dauer * 100) + 1);
    spitzen = alle;
    try {
      for (let start = 0; start < dauer; start += 600) {
        const teil = await schnittquelle.wellenform(gegenstand, start, 600);
        alle.set(teil.subarray(0, Math.max(0, alle.length - start * 100)), start * 100);
        spitzen = alle.slice();
      }
    } finally {
      laedtWelle = false;
    }
  }

  $effect(() => {
    void [gegenstand.art, gegenstand.kennung];
    untrack(() => void laden(true));
  });

  // ----- Hören -----
  /** Ende eines gehörten Stücks (RAD-42): dort hält die Wiedergabe an; null spielt bis zum Ende der Aufnahme */
  let stueckEnde: number | null = null;
  function abspielen(ab?: number, bis: number | null = null): void {
    if (!ton) return;
    if (!appState.isRecording && appState.isPlaying) actions.stop();
    if (ab !== undefined) ton.currentTime = ab;
    stueckEnde = bis;
    void ton.play();
  }
  /** Leertaste und großer Knopf: anhalten oder weiter; ein angehaltenes Stück spielt bis zu seinem Ende weiter */
  function umschalten(): void {
    if (!ton) return;
    if (!ton.paused) { ton.pause(); return; }
    abspielen(undefined, stueckEnde !== null && ton.currentTime < stueckEnde ? stueckEnde : null);
  }
  function suchen(tz: number): void {
    platz.kopf = tz;
    if (ton) ton.currentTime = tz;
  }
  $effect(() => {
    if (!spielt) return;
    let lauf = 0;
    const schritt = () => {
      if (ton && stueckEnde !== null && ton.currentTime >= stueckEnde) {
        ton.pause();
        ton.currentTime = stueckEnde;
        stueckEnde = null;
      }
      if (ton) { platz.kopf = ton.currentTime; if (platz.mitlaufen) platz.zeigen(ton.currentTime); }
      lauf = requestAnimationFrame(schritt);
    };
    lauf = requestAnimationFrame(schritt);
    return () => cancelAnimationFrame(lauf);
  });

  // ----- Tastatur: Leertaste, M, Entf, Plus, Minus, Pfeile -----
  function taste(e: KeyboardEvent): void {
    const ziel = e.target as HTMLElement;
    if (ziel.tagName === "INPUT" || ziel.isContentEditable) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const arbeit = TASTEN[e.key];
    if (!arbeit) return;
    // der Schnitt behält seine Tasten für sich: die Tasten der App (etwa M für stumm) wirken hier nicht
    e.preventDefault();
    e.stopPropagation();
    arbeit();
  }
  function naechsterMarkerWeg(): void {
    if (!platz.marker.length) return;
    platz.markerEntfernen(platz.marker.reduce((b, m, i) => (Math.abs(m - platz.kopf) < Math.abs(platz.marker[b] - platz.kopf) ? i : b), 0));
  }
  const springen = (s: number) => suchen(Math.max(0, Math.min(platz.dauer, platz.kopf + s)));
  const TASTEN: Record<string, () => void> = {
    " ": umschalten, m: () => platz.markerSetzen(platz.kopf), M: () => platz.markerSetzen(platz.kopf),
    Delete: naechsterMarkerWeg, Backspace: naechsterMarkerWeg, "+": () => platz.zoomen(0.5, platz.kopf), "-": () => platz.zoomen(2, platz.kopf),
    ArrowLeft: () => springen(-5), ArrowRight: () => springen(5),
  };
  onMount(() => {
    window.addEventListener("keydown", taste, true);
    return () => { window.removeEventListener("keydown", taste, true); ton?.pause(); };
  });

  // ----- Arbeiten -----
  async function arbeiten(was: string, arbeit: (melden: (f: Fortschritt) => void) => Promise<number>, neuWelle: boolean): Promise<void> {
    auftrag = { was, f: null };
    try {
      await arbeit((f) => (auftrag = { was, f }));
      actions.showToast(t("aufnahmenAnsicht.schnitt.fertig", { was }), "success");
      ton?.pause();
      await laden(neuWelle);
      ongeaendert();
    } catch (f) {
      actions.showToast((f as Error).message, "error");
    } finally {
      auftrag = null;
    }
  }
  const verandertTon = $derived(gegenstand.art === "sitzung");
  const schneiden = () => { fragt = false; void arbeiten(t("aufnahmenAnsicht.schnitt.schneiden"), (m) => schnittquelle.schneiden(gegenstand, platz.wahl(), m), verandertTon); };
  const normalisieren = () => void arbeiten(t("aufnahmenAnsicht.schnitt.normalisieren"), (m) => schnittquelle.normalisieren(gegenstand, m), verandertTon);
  const umwandeln = () => void arbeiten(t("aufnahmenAnsicht.schnitt.umwandeln"),
    (m) => schnittquelle.umwandeln(gegenstand, { format, bitrate, mono }, m), verandertTon);

  async function rueckgaengig(): Promise<void> {
    try {
      const was = await schnittquelle.rueckgaengig(gegenstand);
      actions.showToast(t("aufnahmenAnsicht.schnitt.zurueckgenommen", { was }), "success");
      ton?.pause();
      await laden(verandertTon);
      ongeaendert();
    } catch (f) {
      actions.showToast((f as Error).message, "error");
    }
  }

  const kopfzeile = $derived(info ? [gegenstand.art === "datei" ? gegenstand.kennung : "", [info.format, info.bitrate ? `${info.bitrate} kbit/s` : ""].filter(Boolean).join(" "),
    zeit(info.dauer)].filter(Boolean).join(" · ") : "");
  const stuecke = $derived(platz.stuecke);
  const weg = $derived(stuecke.length - platz.behalten);
</script>

<section class="rh-schnitt" aria-label={info ? t("aufnahmenAnsicht.schnitt.titel", { name: info.titel }) : ""}>
  <div class="rh-schnitt-kopf">
    <div><h2><i class="fa-solid fa-scissors"></i>{t("aufnahmenAnsicht.schnitt.titel", { name: info?.titel ?? "" })}</h2>
      {#if info}<p class="rh-still">{kopfzeile}</p>{/if}</div>
    <div class="rh-schritte">
      <span class="ak-etikett">{t("aufnahmenAnsicht.schnitt.schritte")}</span>
      <ol>
        {#each info?.schritte ?? [] as s, i (s.id)}<li class:jetzt={i === (info?.schritte.length ?? 0) - 1}><b>{i + 1}</b>{s.was}</li>{:else}<li>{t("aufnahmenAnsicht.schnitt.keineSchritte")}</li>{/each}
      </ol>
      <button class="knopf" type="button" disabled={!info?.schritte.length || !!auftrag} title={t("aufnahmenAnsicht.schnitt.rueckgaengigHilfe")} onclick={() => void rueckgaengig()}>
        <i class="fa-solid fa-rotate-left"></i>{t("aufnahmenAnsicht.schnitt.rueckgaengig")}</button>
    </div>
    <button class="knopf" type="button" onclick={onschliessen}><i class="fa-solid fa-xmark"></i>{t("aufnahmenAnsicht.schnitt.schliessen")}</button>
  </div>

  {#if fehler}
    <p class="hinweis-band"><i class="fa-solid fa-triangle-exclamation"></i><span>{fehler}</span></p>
  {:else if info}
    <audio bind:this={ton} src={schnittquelle.ton(gegenstand)} preload="none" onplay={() => (spielt = true)} onpause={() => (spielt = false)} onended={() => (spielt = false)}></audio>
    <div class="rh-schnitt-werkzeug">
      <button class="rund rh-schnitt-spielen" class:an={spielt} type="button" aria-label={t("aufnahmenAnsicht.hoeren")} title="{t('aufnahmenAnsicht.hoeren')} ({t('aufnahmenAnsicht.schnitt.tasteLeer')})" onclick={umschalten}>
        <i class="fa-solid {spielt ? 'fa-pause' : 'fa-play'}"></i></button>
      <output class="rh-zahl rh-schnitt-kopfzeit">{zeit(platz.kopf)}</output>
      <div class="rh-knopfgruppe" role="group">
        <button class="rund" type="button" title={t("aufnahmenAnsicht.schnitt.weiterWeg")} aria-label={t("aufnahmenAnsicht.schnitt.weiterWeg")} onclick={() => platz.zoomen(2)}><i class="fa-solid fa-magnifying-glass-minus"></i></button>
        <output class="rh-zahl">{dauerText(platz.bis - platz.von)}</output>
        <button class="rund" type="button" title={t("aufnahmenAnsicht.schnitt.naeher")} aria-label={t("aufnahmenAnsicht.schnitt.naeher")} onclick={() => platz.zoomen(0.5)}><i class="fa-solid fa-magnifying-glass-plus"></i></button>
        <button class="knopf" type="button" title={t("aufnahmenAnsicht.schnitt.alles_hilfe")} onclick={() => platz.alles()}><i class="fa-solid fa-arrows-left-right-to-line"></i>{t("aufnahmenAnsicht.schnitt.alles")}</button>
      </div>
      <Auswahl wert={String(platz.hoehe)} optionen={HOEHEN} symbol="fa-arrows-up-down" titel={t("aufnahmenAnsicht.schnitt.hoeheHilfe")}
               onwahl={(w: string) => (platz.hoehe = Number(w))} />
      <Schalter an={platz.mitlaufen} text={t("aufnahmenAnsicht.schnitt.mitlaufen")} farbe="blau" hilfe={t("aufnahmenAnsicht.schnitt.mitlaufenHilfe")}
                onwechsel={(an) => (platz.mitlaufen = an)} />
      <div class="rh-knopfgruppe" role="group">
        <button class="knopf" type="button" title={t("aufnahmenAnsicht.schnitt.markerHilfe")} onclick={() => platz.markerSetzen(platz.kopf)}><i class="fa-solid fa-location-pin"></i>{t("aufnahmenAnsicht.schnitt.marker")}</button>
        {#if info.titelwechsel.length}<button class="knopf" type="button" title={t("aufnahmenAnsicht.schnitt.ausTitelnHilfe")} onclick={() => platz.ausTitelwechseln(info!.titelwechsel)}><i class="fa-solid fa-tags"></i>{t("aufnahmenAnsicht.schnitt.ausTiteln")}</button>{/if}
        <button class="knopf" type="button" disabled={!platz.marker.length} title={t("aufnahmenAnsicht.schnitt.leerenHilfe")} onclick={() => platz.leeren()}><i class="fa-solid fa-eraser"></i>{t("aufnahmenAnsicht.schnitt.leeren", { n: platz.marker.length })}</button>
      </div>
      <button class="rund rh-schnitt-hilfe" type="button" aria-pressed={tastenhilfe} title={t("aufnahmenAnsicht.schnitt.tastenHilfe")}
              aria-label={t("aufnahmenAnsicht.schnitt.tastenHilfe")} onclick={() => (tastenhilfe = !tastenhilfe)}><i class="fa-solid fa-keyboard"></i></button>
      {#if tastenhilfe}<p class="rh-still rh-schnitt-tasten"><kbd>{t("aufnahmenAnsicht.schnitt.tasteLeer")}</kbd> {t("aufnahmenAnsicht.schnitt.tasten")} <kbd>M</kbd> {t("aufnahmenAnsicht.schnitt.tastenMarker")} <kbd>{t("aufnahmenAnsicht.schnitt.tasteEntf")}</kbd> {t("aufnahmenAnsicht.schnitt.tastenWeg")}
        <kbd>+</kbd><kbd>-</kbd> {t("aufnahmenAnsicht.schnitt.tastenAusschnitt")} <kbd>{t("aufnahmenAnsicht.schnitt.tastePfeile")}</kbd> {t("aufnahmenAnsicht.schnitt.tastenSpringen")}</p>{/if}
    </div>

    <div class="rh-wellenform">
      <Wellenform {spitzen} dauer={platz.dauer} von={platz.von} bis={platz.bis} marker={platz.marker} {stuecke} kopf={platz.kopf} hoehe={platz.hoehe}
                  beschriftung={t("aufnahmenAnsicht.schnitt.wellenform")} onsuchen={(tz) => { suchen(tz); if (spielt) abspielen(tz); }}
                  onmarker={(tz) => platz.markerSetzen(tz)} onziehen={(i, tz) => platz.markerVerschieben(i, tz)} />
      {#if laedtWelle}<span class="rh-schnitt-laedt"><i class="fa-solid fa-spinner fa-spin"></i>{t("aufnahmenAnsicht.schnitt.laedtWelle")}</span>{/if}
    </div>
    <div class="rh-uebersicht">
      <Wellenform {spitzen} dauer={platz.dauer} von={platz.von} bis={platz.bis} marker={platz.marker} {stuecke} kopf={platz.kopf} gross={false}
                  beschriftung={t("aufnahmenAnsicht.schnitt.uebersicht")} onsuchen={suchen} onausschnitt={(m) => { platz.zoomen(1, m); suchen(m); }} />
    </div>

    <div class="rh-stuecke">
      <div class="rh-spalten rh-stueck-spalten" aria-hidden="true"><span>{t("aufnahmenAnsicht.schnitt.stueck")}</span><span>{t("aufnahmenAnsicht.schnitt.von")}</span>
        <span>{t("aufnahmenAnsicht.schnitt.bis")}</span><span class="rechts">{t("aufnahmenAnsicht.schnitt.laenge")}</span><span>{t("aufnahmenAnsicht.schnitt.behalten")}</span></div>
      {#each stuecke as s (s.von)}
        <div class="rh-stueck" class:weg={!s.behalten && !s.werbung} class:werbung={s.werbung}>
          <span class="rh-a-nr">{String(s.nr).padStart(2, "0")}</span>
          <label class="suche rh-stueck-name"><input type="text" value={s.name} spellcheck="false" maxlength="200" aria-label={t("aufnahmenAnsicht.schnitt.stueckName", { n: s.nr })}
                 onchange={(e) => platz.benennen(s, (e.currentTarget as HTMLInputElement).value)} /></label>
          <span class="rh-zahl">{zeit(s.von)}</span><span class="rh-zahl">{zeit(s.bis)}</span><span class="rh-zahl rechts">{zeit(s.bis - s.von)}</span>
          {#if s.werbung}
            <Schalter an={true} text={t("aufnahmenAnsicht.schnitt.werbung")} farbe="bernstein" hilfe={t("aufnahmenAnsicht.schnitt.werbungHilfe")}
                      onwechsel={() => platz.umschalten(s)} />
          {:else}
            <Schalter an={s.behalten} text={s.behalten ? t("aufnahmenAnsicht.schnitt.behalten") : t("aufnahmenAnsicht.schnitt.weg")}
                      hilfe={t("aufnahmenAnsicht.schnitt.behaltenHilfe")} onwechsel={() => platz.umschalten(s)} />
          {/if}
          <button class="rund" type="button" title={t("aufnahmenAnsicht.schnitt.stueckHoeren")} aria-label={t("aufnahmenAnsicht.schnitt.stueckHoeren")} onclick={() => abspielen(s.von, s.bis)}><i class="fa-solid fa-play"></i></button>
        </div>
      {/each}
    </div>

    <div class="rh-schnitt-aktionen">
      {#if info.werbestellen.length}
        <div class="rh-schnitt-block"><span class="ak-etikett">{t("aufnahmenAnsicht.schnitt.werbung")}</span>
          <button class="knopf" type="button" disabled={!!auftrag} title={t("aufnahmenAnsicht.schnitt.werbungUebernehmenHilfe")}
                  onclick={() => platz.werbestellenUebernehmen(info!.werbestellen, (w) => t("aufnahmenAnsicht.schnitt.werbungName", { wer: w.text }))}>
            <i class="fa-solid fa-rectangle-ad"></i>{info.werbestellen.length === 1 ? t("aufnahmenAnsicht.schnitt.werbungUebernehmenEins")
              : t("aufnahmenAnsicht.schnitt.werbungUebernehmen", { n: info.werbestellen.length })}</button></div>
      {/if}
      <div class="rh-schnitt-block"><span class="ak-etikett">{t("aufnahmenAnsicht.schnitt.schneiden")}</span>
        <button class="knopf primaer" type="button" disabled={!!auftrag || !platz.behalten} onclick={() => (fragt = true)}><i class="fa-solid fa-scissors"></i>
          {platz.behalten === 1 ? t("aufnahmenAnsicht.schnitt.behaltenEins") : t("aufnahmenAnsicht.schnitt.behaltenKnopf", { n: platz.behalten })}</button></div>
      <div class="rh-schnitt-block"><span class="ak-etikett">{t("aufnahmenAnsicht.schnitt.lautheit")}</span>
        <button class="knopf" type="button" disabled={!!auftrag} title={t("aufnahmenAnsicht.schnitt.normalisierenHilfe")} onclick={normalisieren}><i class="fa-solid fa-volume-high"></i>{t("aufnahmenAnsicht.schnitt.normalisieren")}</button></div>
      <div class="rh-schnitt-block"><span class="ak-etikett">{t("aufnahmenAnsicht.schnitt.umwandeln")}</span>
        <div class="segment" role="group" aria-label={t("aufnahmenAnsicht.schnitt.format")}>
          {#each ["mp3", "ogg", "aac"] as const as f (f)}<button type="button" class:aktiv={format === f} aria-pressed={format === f} onclick={() => (format = f)}>{f.toUpperCase()}</button>{/each}
        </div>
        <Auswahl wert={String(bitrate)} optionen={BITRATEN} symbol="fa-gauge" titel={t("aufnahmenAnsicht.schnitt.bitrate")} onwahl={(w: string) => (bitrate = Number(w))} />
        <Schalter an={mono} text={t("aufnahmenAnsicht.schnitt.mono")} farbe="gelb" hilfe={t("aufnahmenAnsicht.schnitt.monoHilfe")} onwechsel={(an) => (mono = an)} />
        <button class="knopf" type="button" disabled={!!auftrag} onclick={umwandeln}><i class="fa-solid fa-arrows-rotate"></i>{t("aufnahmenAnsicht.schnitt.umwandeln")}</button></div>
      <p class="rh-still rh-schnitt-ziel"><i class="fa-solid fa-circle-info"></i>{platz.behalten ? info.ziel : t("aufnahmenAnsicht.schnitt.keinStueck")}</p>
    </div>

    {#if fragt}
      <Rueckfrage frage={t("aufnahmenAnsicht.schnitt.schneidenFrage", { behalten: platz.behalten, weg, ziel: info.ziel })} knopf={t("aufnahmenAnsicht.schnitt.schneiden")}
                  onabbrechen={() => (fragt = false)} onja={schneiden} />
    {/if}
    {#if auftrag}
      <div class="rh-auftrag" role="status"><ak-led farbe="gruen" zustand="blinkt" groesse="klein"></ak-led>
        <span>{auftrag.was}{auftrag.f ? `: ${auftrag.f.text}` : ""}</span>
        <div class="balken"><span style:width="{auftrag.f ? Math.round((auftrag.f.schritt / Math.max(1, auftrag.f.gesamt)) * 100) : 5}%"></span></div>
        <span class="rh-zahl">{auftrag.f ? `${auftrag.f.schritt}/${auftrag.f.gesamt}` : ""}</span></div>
    {/if}
  {/if}
</section>
