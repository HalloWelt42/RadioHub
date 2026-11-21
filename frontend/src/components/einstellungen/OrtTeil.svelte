<script lang="ts">
  // Einstellungen > Wecker und Zeitansage > Ort (RAD-11): Ort der Sonnenzeiten für die Nachtschaltung der Weckansicht.
  // Suchen (wo das Bauziel eine Ortssuche hat), Standort des Geräts oder Eingabe; jede Änderung wartet als Teil-Entwurf
  // in der Leiste Speichern und geht dann über die Weckerablage (volle App: Server, Basic: Browser). Darunter die
  // Sonnenzeiten von heute für den eingetragenen Ort.
  import { weckerablage } from "$ziel/telefon";
  import { t } from "../../lib/i18n.svelte.js";
  import { server } from "../../lib/einstellungen";
  import { sonnenzeiten } from "../../lib/sonne.js";
  import { ortSpeichern } from "../../lib/telefon/weckerdaten.svelte.js";
  import type { Fundort, Ort } from "../../lib/telefon/weckerablage";
  import Karte from "./Karte.svelte";

  let gespeichert = $state<Ort>({ name: "", breite: null, laenge: null });
  let name = $state("");
  let breite = $state("");
  let laenge = $state("");
  let suche = $state("");
  let treffer = $state<Fundort[] | null>(null);
  let meldung = $state("");

  const zahlText = (z: number | null) => (z === null ? "" : String(z).replace(".", ","));
  const zahl = (s: string): number | null => (s.trim() === "" ? null : Number(s.trim().replace(",", ".")));

  function zeigen(o: Ort) {
    name = o.name;
    breite = zahlText(o.breite);
    laenge = zahlText(o.laenge);
  }

  $effect(() => {
    weckerablage.ort().then((o) => { gespeichert = o; zeigen(o); }).catch((f: Error) => (meldung = f.message));
    return () => server.teilZurueck("ort");
  });

  const entwurf = $derived<Ort>({ name: name.trim(), breite: zahl(breite), laenge: zahl(laenge) });
  const gueltig = $derived([entwurf.breite, entwurf.laenge].every((z) => z === null || Number.isFinite(z)));

  function geaendert() {
    if (JSON.stringify(entwurf) === JSON.stringify(gespeichert)) { server.teilZurueck("ort"); return; }
    meldung = gueltig ? "" : t("einstellungen.ort.zahlFalsch");
    if (!gueltig) return;
    server.teilMelden("ort", {
      titel: t("einstellungen.ort.titelLeiste"),
      speichern: async () => { await ortSpeichern(entwurf); gespeichert = { ...entwurf }; },
      verwerfen: () => zeigen(gespeichert),
    });
  }

  function waehlen(f: Fundort) {
    name = f.name;
    breite = zahlText(Math.round(f.breite * 1e4) / 1e4);
    laenge = zahlText(Math.round(f.laenge * 1e4) / 1e4);
    geaendert();
  }

  async function suchen() {
    if (suche.trim().length < 2) return;
    meldung = "";
    try {
      treffer = await weckerablage.orteSuchen(suche.trim());
      if (!treffer.length) meldung = t("einstellungen.ort.keineTreffer");
    } catch (f) {
      treffer = [];
      meldung = (f as Error).message;
    }
  }

  function standort() {
    if (!navigator.geolocation) { meldung = t("einstellungen.ort.standortFehlt"); return; }
    navigator.geolocation.getCurrentPosition(
      (p) => waehlen({ name: t("einstellungen.ort.standortName"), art: "", breite: p.coords.latitude, laenge: p.coords.longitude }),
      () => (meldung = t("einstellungen.ort.standortFehlt")));
  }

  const uhr = (d: Date | null) => (d ? `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}` : "--:--");
  const sonne = $derived(entwurf.breite !== null && entwurf.laenge !== null && gueltig ? sonnenzeiten(new Date(), entwurf.breite, entwurf.laenge) : null);
</script>

<Karte titel={t("einstellungen.ort.titel")} symbol="fa-location-dot" still={t("einstellungen.ort.hilfe")}>
  {#snippet kopf()}
    {#if server.amServer}
      <span class="rh-geltung alle" title={t("einstellungen.geltung.alleHilfe")}><i class="fa-solid fa-house"></i>{t("einstellungen.geltung.alle")}</span>
    {:else}
      <span class="rh-geltung geraet" title={t("einstellungen.geltung.geraetHilfe")}><i class="fa-solid fa-display"></i>{t("einstellungen.geltung.geraet")}</span>
    {/if}
  {/snippet}
  <div class="rh-ort">
    <div class="rh-ort-suche">
      {#if weckerablage.faehig.ortssuche}
        <label class="suche" role="search"><i class="fa-solid fa-magnifying-glass"></i>
          <input type="search" bind:value={suche} placeholder={t("einstellungen.ort.suche")} aria-label={t("einstellungen.ort.suche")}
                 onkeydown={(e) => { if (e.key === "Enter") void suchen(); }} /></label>
        <button class="knopf" type="button" disabled={suche.trim().length < 2} onclick={() => void suchen()}><i class="fa-solid fa-magnifying-glass"></i>{t("einstellungen.ort.suchen")}</button>
      {/if}
      <button class="knopf" type="button" onclick={standort}><i class="fa-solid fa-location-crosshairs"></i>{t("einstellungen.ort.standort")}</button>
    </div>
    {#if treffer?.length}
      <div class="rh-ort-treffer">
        {#each treffer as f (`${f.name}${f.breite}${f.laenge}`)}
          <button type="button" class:aktiv={entwurf.name === f.name} onclick={() => waehlen(f)}>
            <b>{f.name}</b><span>{f.art}</span><span class="rh-zahl">{zahlText(Math.round(f.breite * 1e4) / 1e4)} · {zahlText(Math.round(f.laenge * 1e4) / 1e4)}</span></button>
        {/each}
      </div>
    {/if}
    {#if meldung}<p class="rh-still">{meldung}</p>{/if}
    <div class="rh-ort-felder">
      <label><span class="ak-etikett">{t("einstellungen.ort.name")}</span><span class="suche"><input type="text" bind:value={name} oninput={geaendert} aria-label={t("einstellungen.ort.name")} /></span></label>
      <label><span class="ak-etikett">{t("einstellungen.ort.breite")}</span><span class="suche"><input type="text" inputmode="decimal" bind:value={breite} oninput={geaendert} aria-label={t("einstellungen.ort.breite")} /></span></label>
      <label><span class="ak-etikett">{t("einstellungen.ort.laenge")}</span><span class="suche"><input type="text" inputmode="decimal" bind:value={laenge} oninput={geaendert} aria-label={t("einstellungen.ort.laenge")} /></span></label>
    </div>
    {#if sonne && !sonne.polar}
      <div class="ak-geraet rh-sonne" data-bauform="inspektor">
        <span class="ak-schraube lo" style="--dreh:20deg"></span><span class="ak-schraube ro" style="--dreh:-40deg"></span>
        <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="bernstein" text={uhr(sonne.aufgang)}></ak-segmente><span class="ak-etikett">{t("einstellungen.ort.aufgang")}</span></div>
        <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="rot" text={uhr(sonne.untergang)}></ak-segmente><span class="ak-etikett">{t("einstellungen.ort.untergang")}</span></div>
      </div>
    {/if}
  </div>
</Karte>
