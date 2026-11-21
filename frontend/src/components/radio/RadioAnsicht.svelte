<script lang="ts">
  // Radio am Rechner (Entwurf mockups/radio-filter/rechner.html, RAD-7): Seitenleiste der Schnellfilter, Kopf der Liste
  // und die Senderliste seitenweise. Kennt nur die Senderquelle; Schnellfilter, Suche und Sortierung stehen in der
  // Adresse (/radio?land=DE ..., aufgeklappt /radio/<uuid>). Tastatur in der Liste: Pfeile wählen, Eingabe und
  // Leertaste spielen, Escape schließt die Details. Nach 90 Sekunden ohne Bedienung rollt die Liste zum spielenden Sender.
  import { onMount, tick, untrack } from "svelte";
  import { Nachladen } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { appState } from "../../lib/store.svelte.js";
  import { appPfad } from "../../lib/router.js";
  import * as sfx from "../../lib/uiSounds.js";
  import { filterzustand, senderquelle } from "../../lib/radio";
  import { Radiobedienung } from "../../lib/radio/bedienung.svelte";
  import { zurueckgesetzt, zuAbfrage, type Schnellfilter } from "../../lib/radio/schnellfilter";
  import type { Kategorie } from "../../lib/radio/quelle";
  import type { SenderEintrag } from "../../lib/radio/typen";
  import Band from "./Band.svelte";
  import Seitenleiste from "./Seitenleiste.svelte";
  import SenderZeile from "./SenderZeile.svelte";
  import SortSpalte from "./SortSpalte.svelte";
  import type { Sortierung } from "../../lib/radio/typen";
  import Werkzeugleiste from "./Werkzeugleiste.svelte";
  import { fokus as folgen } from "../../spieler/fokus.svelte";
  import { werbende } from "../../lib/radio/werbende.svelte";

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
      gesucht = null;
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
    });
  });

  // Aufgeklappter Sender aus der Adresse (Direktlink, Zurück, Sprung von der Spielerleiste): nach jedem Laden in der
  // Liste (sonst vorn eingefügt) und einmal hingerollt; ein Klick auf Details in der Liste rollt nicht
  let gesucht: string | null = null;
  let gerollt: string | null = null;
  let vonHier: string | null = null;
  $effect(() => {
    const offen = filterzustand.offen;
    const bereit = liste.geladen && !liste.laedt;
    const da = liste.eintraege.some((e) => e.uuid === offen);
    untrack(() => {
      if (!offen) { gesucht = gerollt = null; return; }
      if (!bereit) return;
      if (!da) {
        if (gesucht !== offen) { gesucht = offen; void bedienung.sicherstellen(offen); }
        return;
      }
      if (gerollt === offen) return;
      gerollt = offen;
      if (vonHier !== offen) void rollenZu(offen);
    });
  });

  // Zurück und Vor im Browser: Filter aus der Adresse
  onMount(() => {
    const zurueck = () => { if (appPfad().startsWith("/radio")) filterzustand.ausAdresse(); };
    window.addEventListener("popstate", zurueck);
    void bedienung.bestandLaden();
    return () => window.removeEventListener("popstate", zurueck);
  });

  // Sender mit Werbung in den Sendedaten (RAD-33): beim Öffnen, wenn ein anderer Sender spielt und sobald im
  // Zeitversatz eine Werbestelle abgeschlossen ist (dann ist ihr Spot gezählt, der Sender womöglich neu werbend)
  const fertigeStellen = $derived(((appState.hlsStatus as { werbestellen?: { bis: number | null }[] } | null)?.werbestellen ?? [])
    .filter((w) => w.bis !== null).length);
  $effect(() => {
    void spielend;
    if (senderquelle.faehig.werbung) untrack(() => void werbende.laden());
  });
  $effect(() => {
    if (fertigeStellen && senderquelle.faehig.werbung) untrack(() => void werbende.laden(true));
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

  // Sprung von der Spielerleiste zur Quelle: die Adresse /radio/<uuid> klappt auf (oben); war er schon offen, hinrollen
  let letzterSprung = 0;
  $effect(() => {
    const anfrage = appState.sourceJumpRequest as { type: string; id: string; ts: number; varianten?: boolean } | null;
    if (!anfrage || anfrage.type !== "radio" || anfrage.ts <= letzterSprung) return;
    letzterSprung = anfrage.ts;
    // andere Variante wählen: die Varianten des Senders gleich aufklappen
    if (anfrage.varianten && anfrage.id && !variantenOffen.includes(anfrage.id)) variantenOffen = [...variantenOffen, anfrage.id];
    untrack(() => { if (anfrage.id && anfrage.id === filterzustand.offen && gerollt === anfrage.id) void rollenZu(anfrage.id); });
  });

  async function rollenZu(uuid: string, sanft = true) {
    await tick();
    const zeile = listeEl?.querySelector<HTMLElement>(`[data-uuid="${CSS.escape(uuid)}"]`);
    if (!zeile || !listeEl) return;
    // eine aufgeklappte Zeile ist höher als das halbe Rollfeld: oben unter dem Spaltenkopf, sonst in die Mitte
    const hoch = zeile.offsetHeight > listeEl.clientHeight / 2;
    zeile.scrollIntoView({ block: hoch ? "start" : "center", behavior: sanft ? "smooth" : "auto" });
  }

  // Fokus auf den laufenden Sender (RAD-19, Schalter der Kanzel): ist er an, klappt die Liste den laufenden Sender auf und
  // rollt hin, beim Öffnen der Ansicht und bei jedem Senderwechsel; dazwischen rollt man frei. Aus: nichts springt von
  // selbst (die frühere Rückkehr nach 90 Sekunden ohne Bedienung entfällt, Nutzer 20.11.2026).
  let gefolgt: string | null = null;
  $effect(() => {
    const uuid = spielend;
    const an = folgen.an;
    untrack(() => {
      if (!an) { gefolgt = null; return; }
      if (!uuid || uuid === gefolgt) return;
      gefolgt = uuid;
      vonHier = null;
      if (filterzustand.offen === uuid && gerollt === uuid) void rollenZu(uuid);
      else filterzustand.oeffnen(uuid);
    });
  });

  /** Ausblenden (Auge): war der Sender aufgeklappt, rückt der nächste der Reihe nach (der letzte: der davor) */
  async function ausblenden(e: SenderEintrag) {
    const offen = filterzustand.offen === e.uuid;
    const stelle = liste.eintraege.findIndex((x) => x.uuid === e.uuid);
    await bedienung.ausblenden(e);
    if (!offen || liste.eintraege.some((x) => x.uuid === e.uuid)) return;     // blieb sichtbar (etwa als Favorit)
    const naechster = liste.eintraege[Math.min(stelle, liste.eintraege.length - 1)];
    vonHier = null;
    filterzustand.oeffnen(naechster?.uuid ?? null);
  }

  function spielen(e: SenderEintrag) {
    sfx.click();
    void bedienung.spielen(e);
  }

  function details(e: SenderEintrag) {
    sfx.click();
    vonHier = filterzustand.offen === e.uuid ? null : e.uuid;
    filterzustand.oeffnen(vonHier);
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

<div class="rh-radio">
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
      {#snippet sortspalte(s: Sortierung, titel: string)}
        <SortSpalte {titel} hilfe={t(`radio.sortierungHinweis.${s}`)} aktiv={filter.sortierung === s} absteigend={s !== "name"}
                    onwahl={() => aendern((f) => ({ ...f, sortierung: s }))} />
      {/snippet}
      <div class="rh-spalten" role="group" aria-label={t("radio.sortierungTitel")}>
        <span>{@render sortspalte("name", t("radio.sender"))}</span><span class="rh-ohne-sort">{t("radio.genres")}</span>
        <span>{@render sortspalte("bitrate", t("radio.sortierung.bitrate"))}</span>
        <span class="rechts">{@render sortspalte("stimmen", t("radio.stimmen"))}</span><span class="rh-ohne-sort"></span></div>
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
                       onausblenden={() => ausblenden(e)} oneinblenden={() => void bedienung.einblenden(e)} onaendern={(teil) => liste.aendern(e.uuid, teil)} />
        {/each}
        <Nachladen geladen={liste.eintraege.length} gesamt={liste.gesamt} laedt={liste.laedtMehr} fehler={liste.fehler} onmehr={() => void liste.mehr()}
                   einheit={t("radio.geladen")} />
      {/if}
    </div>
  </main>
</div>
<Band bind:inhalt={bedienung.band} />
