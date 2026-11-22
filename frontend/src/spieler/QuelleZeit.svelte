<script lang="ts">
  // Modul Quelle und Zeit: Quelle in 14 Segmenten (Farbe nach Zustand), Zeit in 7 Segmenten; darunter im Zeitversatz
  // 30 Sekunden zurück, Puffer, 30 Sekunden vor und Live, bei Folgen und Aufnahmen 10 Sekunden zurück, Position und 10
  // Sekunden vor. Gilt keins von beiden, steht die Zeile des Zeitversatzes gesperrt da (sie verschwindet nie).
  import { t } from "../lib/i18n.svelte.js";
  import * as sfx from "../lib/uiSounds.js";
  import Spulzeile from "./Spulzeile.svelte";
  import { werbemarken } from "./werbehinweis.svelte";
  import { live, spulen } from "./aktionen";
  import { lageZuSekunde, positionStand, pufferAufnahme, pufferZeile, pufferMarken, pufferProzent, pufferSekunde, pufferStriche, sekundeZuLage, SPUL_RUHE,
    zeitversatzStand, type Anzeige, type Stand } from "./kanzel";
  import Titelzeile from "./Titelzeile.svelte";
  import { puffer } from "./puffer.svelte";
  import { bei } from "../lib/radio/abschnitte";
  import { formatTimeShort } from "../lib/formatters.js";
  import { app } from "./app";
  import { faehigkeiten } from "../lib/playerEngine.js";

  // ohne Zeitversatz und ohne Folgen (Webversion) gibt es nichts zu spulen: die Zeile entfällt dort
  const kann = faehigkeiten();
  const spulbar = kann.zeitversatz || kann.folgen;
  import type { Wiedergabe } from "./wiedergabe.svelte";

  let { anzeige, stand, wiedergabe }: { anzeige: Anzeige; stand: Stand; wiedergabe: Wiedergabe } = $props();

  const ruht = $derived(anzeige.zeile === null);
  const versatz = $derived(anzeige.zeile === "zeitversatz" ? zeitversatzStand(stand, t) : ruht && spulbar ? SPUL_RUHE : null);
  const position = $derived(anzeige.zeile === "position" ? positionStand(stand, t) : null);
  // die Aufnahme hängt am Empfang des Senders, nicht an der Stelle, die man hört (RAD-46): Spulen im Zeitversatz bleibt frei
  const spulenGesperrt = $derived((anzeige.zeile !== "zeitversatz" && stand.isRecording) || anzeige.zustand === "laedt" || anzeige.zustand === "fehler");
  const imVersatz = $derived(anzeige.zeile === "zeitversatz");

  // Marken im Zeitversatz: Titelgrenzen, laufende Aufnahme dieses Senders, Titel beim Überfahren, Einrasten an Grenzen
  const striche = $derived(imVersatz ? pufferStriche(stand, puffer.abschnitte) : []);
  const aufnahme = $derived(imVersatz && stand.isRecording && (app.recordingStationUuid ?? null) === (stand.currentStation?.uuid ?? null)
    ? pufferAufnahme(stand, stand.recordingElapsed) : null);
  // Angabe unter dem Balken wie im Entwurf: hinter live, Länge von höchstens, Titel; rot der Beginn einer Aufnahme
  const versatzZeile = $derived(imVersatz && versatz ? { ...versatz, text: pufferZeile({ hinter: puffer.hinter,
    gepuffert: puffer.ende - puffer.anfang, max: puffer.groesste, titel: puffer.titelZahl, aufnahme: aufnahme !== null }, t) } : versatz);
  const aufnahmeAb = $derived(aufnahme ? t("puffer.aufnahmeAbUhr", { uhr: puffer.uhr(puffer.ende - stand.recordingElapsed) }) : null);
  function tipp(prozent: number) {
    const t0 = pufferSekunde(stand, prozent);
    const a = t0 === null ? null : bei(puffer.abschnitte, t0);
    if (!a || t0 === null) return null;
    const titel = a.art === "werbung" ? t("puffer.werbung") : a.art === "einschub" ? t("puffer.einschub") : a.titel;
    return { titel, links: pufferProzent(stand, a.von), text: `${t("puffer.tippText", { vor: formatTimeShort(Math.max(0, puffer.ende - a.von)), laenge: formatTimeShort(a.bis - a.von) })} · ${t("puffer.tippKlick")}` };
  }
  /** loslassen nahe einer Titelgrenze (höchstens 1 % der Bahn): genau an die Grenze */
  function einrasten(lage: number): number {
    const sek = lageZuSekunde(stand, lage);
    if (sek === null) return lage;
    const naechste = puffer.abschnitte.map((a) => a.von).reduce<number | null>((b, v) => (b === null || Math.abs(v - sek) < Math.abs(b - sek) ? v : b), null);
    if (naechste === null) return lage;
    const n = sekundeZuLage(stand, naechste);
    return Math.abs(n - lage) <= 1 ? n : lage;
  }
</script>

<section class="rh-modul rh-m-zeit" aria-label={t("kanzel.quelleUndZeit")}><span class="ak-etikett">{t("kanzel.quelleUndZeit")}</span>
  <div class="rh-zeit" class:rh-zeit-spulbar={spulbar}>
    <div class="ak-glas rh-zeit-glas">
      <ak-segmente class="rh-zeit-quelle" art="14" stellen="7" text={anzeige.quelle.text} hilfe={t("kanzel.quelleHilfe")}
        style:--farbe="var(--led-{anzeige.quelle.farbe})"></ak-segmente>
      <ak-segmente class="rh-zeit-uhr" art="7" stellen="7" farbe="gruen" text={anzeige.zeit} hilfe={t("kanzel.zeitHilfe")}></ak-segmente>
    </div>
    {#if versatz}
      <Spulzeile stand={versatzZeile ?? versatz} zusatz={aufnahmeAb} {wiedergabe} hilfe={t("kanzel.pufferHilfe", { max: versatz.max })} marken={imVersatz ? pufferMarken(stand) : []}
                 {striche} {aufnahme} tipp={imVersatz ? tipp : undefined} einrasten={imVersatz ? einrasten : undefined}>
        {#snippet links()}
          <button class="knopf" type="button" title={t("kanzel.zurueck30Hilfe")} aria-label={t("kanzel.zurueck30Hilfe")} disabled={spulenGesperrt || versatz.gesperrt}
            onmouseenter={sfx.hover} onclick={() => { spulen(-30); sfx.click(); }}><i class="fa-solid fa-rotate-left"></i>{t("kanzel.sekunden30")}</button>
        {/snippet}
        {#snippet rechts()}
          <span class="rh-puffer-rechts">
            <button class="knopf" type="button" title={t("kanzel.vor30Hilfe")} aria-label={t("kanzel.vor30Hilfe")} disabled={spulenGesperrt || versatz.gesperrt || versatz.live}
              onmouseenter={sfx.hover} onclick={() => { spulen(30); sfx.click(); }}><i class="fa-solid fa-rotate-right"></i>{t("kanzel.sekunden30")}</button>
            <button class="knopf" type="button" title={versatz.live ? t("player.bereitsLive") : t("player.goLive")} disabled={ruht || versatz.live}
              onmouseenter={sfx.hover} onclick={() => { live(); sfx.click(); }}><i class="fa-solid fa-tower-broadcast"></i>{t("kanzel.live")}</button>
          </span>
        {/snippet}
      </Spulzeile>
      {#if imVersatz}<Titelzeile gesperrt={spulenGesperrt} />{/if}
    {:else if position}
      <Spulzeile stand={position} {wiedergabe} hilfe={t("kanzel.positionHilfe")} marken={stand.currentEpisode ? werbemarken(wiedergabe.dauer) : []}>
        {#snippet links()}
          <button class="knopf" type="button" title={t("player.skipBack")} aria-label={t("player.skipBack")} disabled={spulenGesperrt || position.gesperrt}
            onmouseenter={sfx.hover} onclick={() => { spulen(-10); sfx.click(); }}><i class="fa-solid fa-rotate-left"></i>10 s</button>
        {/snippet}
        {#snippet rechts()}
          <button class="knopf" type="button" title={t("player.skipForward")} aria-label={t("player.skipForward")} disabled={spulenGesperrt || position.gesperrt}
            onmouseenter={sfx.hover} onclick={() => { spulen(10); sfx.click(); }}><i class="fa-solid fa-rotate-right"></i>10 s</button>
        {/snippet}
      </Spulzeile>
    {/if}
  </div>
</section>
