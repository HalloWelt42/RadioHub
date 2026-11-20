<script lang="ts">
  // Radio am Rechner (Entwurf mockups/radio-filter/rechner.html, RAD-7): Seitenleiste der Schnellfilter, Kopf der Liste
  // und die Senderliste seitenweise. Kennt nur die Senderquelle; Schnellfilter, Suche und Sortierung stehen in der
  // Adresse (/radio?land=DE ..., aufgeklappt /radio/<uuid>). Tastatur in der Liste: Pfeile wählen, Eingabe und
  // Leertaste spielen, Escape schließt die Details. Nach 90 Sekunden ohne Bedienung rollt die Liste zum spielenden Sender.
  import { onMount, tick, untrack } from "svelte";
  import { Nachladen } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { appState } from "../../lib/store.svelte.js";
  import * as sfx from "../../lib/uiSounds.js";
  import { filterzustand, senderquelle } from "../../lib/radio";
  import { Radiobedienung } from "../../lib/radio/bedienung.svelte";
  import { zurueckgesetzt, zuAbfrage, type Schnellfilter } from "../../lib/radio/schnellfilter";
  import type { Kategorie } from "../../lib/radio/quelle";
  import type { SenderEintrag } from "../../lib/radio/typen";
  import Band from "./Band.svelte";
  import Seitenleiste from "./Seitenleiste.svelte";
  import SenderZeile from "./SenderZeile.svelte";
  import Werkzeugleiste from "./Werkzeugleiste.svelte";

  const RUHE_MS = 90_000;
  const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

  const bedienung = new Radiobedienung(senderquelle);
  const liste = bedienung.liste;
  let listeEl = $state<HTMLElement>();
  let filterOffen = $state(false);
  let variantenOffen = $state<string[]>([]);
  let fokus = $state(-1);

  const filter = $derived(filterzustand.filter);
  const kategorien = $derived<Kategorie[]>((liste.facetten?.kategorien ?? []).map((k) => ({ id: Number(k.wert), name: k.name })));
  const spielend = $derived((appState.currentStation as { uuid?: string } | null)?.uuid ?? null);

  function aendern(arbeit: (f: Schnellfilter) => Schnellfilter) {
    filterzustand.aendern(arbeit);
  }

  // Liste zum Filter laden (jede Änderung, auch über Zurück und Vor)
  $effect(() => {
    const abfrage = zuAbfrage(filterzustand.filter);
    untrack(() => {
      fokus = -1;
      void liste.laden(abfrage);
    });
  });

  // Adresse: beim ersten Mal gilt sie, danach folgt die Ansicht ihr (aufgeklappter Sender, Sprung von der Spielerleiste)
  let erstes = true;
  $effect(() => {
    const seg = appState.routeSegments as string[];
    const bereich = appState.activeTab;
    untrack(() => {
      if (bereich !== "radio" && bereich !== "wecker") return;
      if (erstes) {
        erstes = false;
        filterzustand.ansicht();
        return;
      }
      if (seg[0] === "search") return filterzustand.ausAdresse();
      const uuid = seg[0] && UUID.test(seg[0]) ? seg[0] : null;
      if (uuid !== filterzustand.offen) filterzustand.offen = uuid;
      filterzustand.schreiben();
      if (uuid) void bedienung.sicherstellen(uuid).then((da) => { if (da) void rollenZu(uuid); });
    });
  });

  // Zurück und Vor im Browser: Filter aus der Adresse
  onMount(() => {
    const zurueck = () => { if (window.location.pathname.startsWith("/radio")) filterzustand.ausAdresse(); };
    window.addEventListener("popstate", zurueck);
    void bedienung.bestandLaden();
    return () => window.removeEventListener("popstate", zurueck);
  });

  // Vor und Zurück der Wiedergabe folgen der sichtbaren Liste (Vorgabe 7); die Nachbarn bekommen ihre Felder vorab
  $effect(() => {
    (appState as { stations: unknown[] }).stations = bedienung.fuerWiedergabe();
  });
  $effect(() => {
    const uuid = spielend;
    void liste.eintraege.length;
    untrack(() => bedienung.nachbarnVorbereiten(uuid));
  });

  // Sprung von der Spielerleiste zur Quelle: die Adresse /radio/<uuid> klappt auf, hier nur hinrollen
  let letzterSprung = 0;
  $effect(() => {
    const anfrage = appState.sourceJumpRequest as { type: string; id: string; ts: number } | null;
    if (!anfrage || anfrage.type !== "radio" || anfrage.ts <= letzterSprung) return;
    letzterSprung = anfrage.ts;
    untrack(() => { if (anfrage.id) void bedienung.sicherstellen(anfrage.id).then((da) => { if (da) void rollenZu(anfrage.id); }); });
  });

  async function rollenZu(uuid: string, sanft = true) {
    await tick();
    listeEl?.querySelector(`[data-uuid="${CSS.escape(uuid)}"]`)?.scrollIntoView({ block: "center", behavior: sanft ? "smooth" : "auto" });
  }

  // Nach 90 Sekunden ohne Bedienung zum spielenden Sender
  let ruheUhr: ReturnType<typeof setTimeout> | undefined;
  function bedient() {
    clearTimeout(ruheUhr);
    ruheUhr = setTimeout(() => {
      if (appState.activeTab === "radio" && spielend && liste.eintraege.some((e) => e.uuid === spielend)) void rollenZu(spielend);
    }, RUHE_MS);
  }
  onMount(() => {
    bedient();
    return () => clearTimeout(ruheUhr);
  });

  function spielen(e: SenderEintrag) {
    sfx.click();
    void bedienung.spielen(e);
  }

  function details(e: SenderEintrag) {
    sfx.click();
    filterzustand.oeffnen(filterzustand.offen === e.uuid ? null : e.uuid);
  }

  function varianten(e: SenderEintrag) {
    variantenOffen = variantenOffen.includes(e.uuid) ? variantenOffen.filter((u) => u !== e.uuid) : [...variantenOffen, e.uuid];
  }

  function taste(ev: KeyboardEvent) {
    const eintraege = liste.eintraege;
    if (!eintraege.length || (ev.target as HTMLElement) !== listeEl) return;
    if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
      fokus = ev.key === "ArrowDown" ? Math.min(fokus + 1, eintraege.length - 1) : Math.max(fokus - 1, 0);
      void tick().then(() => listeEl?.querySelector(".rh-sender.fokus")?.scrollIntoView({ block: "nearest" }));
    } else if ((ev.key === "Enter" || ev.key === " ") && fokus >= 0) {
      spielen(eintraege[fokus]);
    } else if (ev.key === "Escape" && filterzustand.offen) {
      filterzustand.oeffnen(null);
    } else {
      return;
    }
    ev.preventDefault();
    ev.stopPropagation();
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="rh-radio" onpointerdown={bedient} onkeydown={bedient} onwheel={bedient}>
  <Seitenleiste {filter} facetten={liste.facetten} offen={filterOffen} onaendern={aendern} onzu={() => (filterOffen = false)} />
  <button class="rh-schleier" class:offen={filterOffen} type="button" aria-label={t("radio.filterSchliessen")} tabindex="-1"
          onclick={() => (filterOffen = false)}></button>

  <main class="rh-haupt">
    <Werkzeugleiste {filter} gesamt={liste.gesamt} sichtbar={bedienung.bestand?.sichtbar ?? null} ausgeblendet={bedienung.bestand?.ausgeblendet ?? null}
                    kategorieName={(id) => kategorien.find((k) => String(k.id) === id)?.name ?? id} {filterOffen} laedt={liste.laedt}
                    onaendern={aendern} onfilter={() => (filterOffen = true)}
                    onneuladen={() => { void liste.laden(zuAbfrage(filter)); void bedienung.bestandLaden(); }} />
    <!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
    <div class="rh-liste" bind:this={listeEl} tabindex="0" role="list" aria-label={t("radio.senderliste")} onkeydown={taste}>
      <div class="rh-spalten" aria-hidden="true"><span>{t("radio.sender")}</span><span>{t("radio.genres")}</span><span>{t("radio.qualitaetTitel")}</span>
        <span class="rechts">{t("radio.stimmen")}</span><span></span></div>
      {#if !liste.geladen}
        <div class="rh-ohne-treffer"><i class="fa-solid fa-spinner fa-spin"></i><b>{t("radio.laedt")}</b></div>
      {:else if liste.fehler && !liste.eintraege.length}
        <div class="rh-ohne-treffer"><i class="fa-solid fa-triangle-exclamation"></i><b>{t("radio.ladenFehler")}</b><span>{liste.fehler}</span>
          <button class="knopf" type="button" onclick={() => void liste.laden(zuAbfrage(filter))}><i class="fa-solid fa-rotate"></i>{t("radio.nochmal")}</button></div>
      {:else if !liste.eintraege.length}
        <div class="rh-ohne-treffer"><i class="fa-solid fa-filter-circle-xmark"></i><b>{t("radio.keineTreffer")}</b><span>{t("radio.keineTrefferHilfe")}</span>
          <button class="knopf" type="button" onclick={() => aendern(zurueckgesetzt)}>{t("radio.alleZuruecksetzen")}</button></div>
      {:else}
        {#each liste.eintraege as e, i (e.uuid)}
          <SenderZeile eintrag={e} spielt={spielend === e.uuid} aufnahme={appState.isRecording} titel={appState.streamTitle}
                       offen={filterzustand.offen === e.uuid} fokus={fokus === i} variantenOffen={variantenOffen.includes(e.uuid)} {spielend} {kategorien}
                       onspielen={spielen} ondetails={() => details(e)} onvarianten={() => varianten(e)} onfavorit={() => bedienung.favorit(e)}
                       onausblenden={() => bedienung.ausblenden(e)} onaendern={(teil) => liste.aendern(e.uuid, teil)} />
        {/each}
        <Nachladen geladen={liste.eintraege.length} gesamt={liste.gesamt} laedt={liste.laedtMehr} fehler={liste.fehler} onmehr={() => void liste.mehr()}
                   einheit={t("radio.geladen")} />
      {/if}
    </div>
  </main>
</div>
<Band bind:inhalt={bedienung.band} />
