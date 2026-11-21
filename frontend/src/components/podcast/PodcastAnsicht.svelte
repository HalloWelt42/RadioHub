<script lang="ts">
  // Podcasts am Rechner nach dem abgenommenen Entwurf (mockups/radio-filter/podcasts.html, RAD-17): Seitenleiste mit Wahl
  // und Abos, Werkzeugleiste, Kopf eines gewählten Abos, Folgen seitenweise, Abonnieren über das Verzeichnis, Band mit
  // Rückgängig. Zustand und Adresse in lib/podcasts (Quelle, Aboliste, Folgenliste, Podcastzustand), hier nur die Ansicht.
  import { onMount, tick, untrack } from "svelte";
  import { Nachladen } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { actions, appState } from "../../lib/store.svelte.js";
  import { appPfad } from "../../lib/router.js";
  import * as sfx from "../../lib/uiSounds.js";
  import { aboliste, Folgenliste, Speicherauftrag, podcastquelle, podcastzustand, zuAbfrage, type Aktualisierungsstand, type Folge,
    type Podcastansicht, type Podcastsortierung } from "../../lib/podcasts";
  import { fokus as folgen } from "../../spieler/fokus.svelte";
  import type { BandInhalt } from "../../lib/radio/bedienung.svelte";
  import Band from "../radio/Band.svelte";
  import AboKopf from "./AboKopf.svelte";
  import FolgeZeile from "./FolgeZeile.svelte";
  import SortSpalte from "../radio/SortSpalte.svelte";
  import PodcastLeiste from "./PodcastLeiste.svelte";
  import PodcastWerkzeug from "./PodcastWerkzeug.svelte";
  import Verzeichnis from "./Verzeichnis.svelte";

  const liste = new Folgenliste(podcastquelle);
  const auftrag = new Speicherauftrag(podcastquelle, (id) => liste.aendern(id, { gespeichert: true }));
  const kann = podcastquelle.faehig;
  let band = $state<BandInhalt | null>(null);
  let stand = $state<Aktualisierungsstand | null>(null);
  let leisteOffen = $state(false);
  let aktualisiert = $state(false);

  const ansicht = $derived(podcastzustand.ansicht);
  const einAbo = $derived(ansicht.abos.length === 1 ? aboliste.abo(ansicht.abos[0]) : undefined);
  const spielend = $derived((appState.currentEpisode as { id?: number } | null)?.id ?? null);
  const ungehoert = $derived(ansicht.abos.length ? ansicht.abos.reduce((s, id) => s + (aboliste.abo(id)?.ungehoert ?? 0), 0)
    : aboliste.abos.reduce((s, a) => s + a.ungehoert, 0));

  onMount(() => {
    podcastzustand.oeffnen();
    if (!aboliste.geladen) void aboliste.laden();
    void podcastquelle.aktualisierungsstand().then((s) => (stand = s)).catch(() => (stand = null));
    const zurueck = () => { if (appPfad().startsWith("/podcasts")) podcastzustand.ausAdresse(); };
    window.addEventListener("popstate", zurueck);
    return () => window.removeEventListener("popstate", zurueck);
  });

  // Folgen neu, wenn sich Abos, Wahl, Sortierung oder Suche ändern (nicht beim Auf- und Zuklappen)
  const schluessel = $derived(JSON.stringify([ansicht.abos, ansicht.wahl, ansicht.sortierung, ansicht.suche, ansicht.verzeichnis]));
  $effect(() => {
    void schluessel;
    untrack(() => { if (!ansicht.verzeichnis) void liste.laden(zuAbfrage(ansicht), ansicht.suche); });
  });

  function aendern(arbeit: (a: Podcastansicht) => Podcastansicht) {
    podcastzustand.aendern(arbeit);
  }

  // Sortierung je Abo (Nutzer 20.11.2026): ist genau ein Abo gewählt, gilt seine gemerkte Sortierung, und ein Wechsel
  // merkt sie für dieses Abo; sonst gilt die der Ansicht
  function sortieren(s: Podcastsortierung) {
    aendern((a) => ({ ...a, sortierung: s }));
    if (einAbo) void sicher(() => aboliste.sortierungSetzen(einAbo.id, s));
  }
  const aboSortierung = $derived(einAbo?.sortierung ?? "");
  $effect(() => {
    const s = aboSortierung;
    untrack(() => { if (s && s !== ansicht.sortierung) aendern((a) => ({ ...a, sortierung: s })); });
  });

  // Fokus der Kanzel (RAD-19) auch für Folgen: ist er an, klappt die Liste die laufende Folge auf und rollt hin, beim
  // Öffnen und bei jedem Wechsel; dazwischen rollt man frei
  let listeEl = $state<HTMLElement>();
  let gefolgt: number | null = null;
  $effect(() => {
    const id = spielend;
    const an = folgen.an;
    untrack(() => {
      if (!an) { gefolgt = null; return; }
      if (id === null || id === gefolgt) return;
      gefolgt = id;
      const aboId = (appState.currentEpisode as { podcast_id?: number } | null)?.podcast_id ?? null;
      podcastzustand.folge(id, aboId);
      void hinrollen(id);
    });
  });
  async function hinrollen(id: number) {
    await tick();
    listeEl?.querySelector<HTMLElement>(`[data-folge="${id}"]`)?.scrollIntoView({ block: "center", behavior: "smooth" });
  }

  function meldung(symbol: string, name: string, text: string, rueckgaengig?: () => Promise<void>) {
    band = { symbol, name, text, rueckgaengig };
  }

  async function sicher(arbeit: () => Promise<void>) {
    try {
      await arbeit();
    } catch (f) {
      actions.showToast((f as Error).message || t("common.fehler"), "error");
    }
  }

  async function spielen(f: Folge, vonVorn = false) {
    sfx.click();
    await sicher(async () => {
      const w = await podcastquelle.wiedergabe(f, liste.folgen);
      const folge = vonVorn ? { ...w.folge, resume_position: 0 } : w.folge;
      actions.playEpisodeFromList(folge, w.abo, w.liste);
    });
  }

  /** in der Kellerwolke speichern (an) oder dort löschen (aus, nach der Rückfrage in der Zeile) */
  async function speichern(f: Folge, an: boolean) {
    await sicher(async () => {
      await podcastquelle.speichern(f.id, an);
      liste.aendern(f.id, { gespeichert: an, ablagePfad: an ? f.ablagePfad : "" });
      aboliste.aendern(f.aboId, { gespeichert: Math.max(0, (aboliste.abo(f.aboId)?.gespeichert ?? 0) + (an ? 1 : -1)) });
      meldung(an ? "fa-cloud" : "fa-trash-can", f.titel, an ? t("podcastAnsicht.bandGespeichert") : t("podcastAnsicht.bandGeloescht"));
    });
  }

  function gehoert(f: Folge) {
    const an = !(f.gehoert || (f.dauer > 0 && f.stelle >= f.dauer - 5));
    void sicher(async () => {
      await podcastquelle.gehoert(f.id, an);
      liste.aendern(f.id, { gehoert: an, stelle: an ? f.stelle : 0 });
      aboliste.aendern(f.aboId, { ungehoert: Math.max(0, (aboliste.abo(f.aboId)?.ungehoert ?? 0) + (an ? -1 : 1)) });
    });
  }

  function details(f: Folge) {
    sfx.click();
    podcastzustand.folge(ansicht.offen === f.id ? null : f.id, f.aboId);
  }

  async function aktualisieren(id?: number) {
    aktualisiert = true;
    const vorher = id ? (aboliste.abo(id)?.folgen ?? 0) : aboliste.abos.reduce((s, a) => s + a.folgen, 0);
    await sicher(async () => {
      await aboliste.aktualisieren(id);
      const nachher = id ? (aboliste.abo(id)?.folgen ?? 0) : aboliste.abos.reduce((s, a) => s + a.folgen, 0);
      const neu = Math.max(0, nachher - vorher);
      meldung("fa-rotate", id ? (aboliste.abo(id)?.titel ?? "") : "", neu ? t("podcastAnsicht.bandNeueFolgen", { n: neu }) : t("podcastAnsicht.bandKeineNeuen"));
      void liste.laden(zuAbfrage(ansicht), ansicht.suche);
      stand = await podcastquelle.aktualisierungsstand().catch(() => stand);
    });
    aktualisiert = false;
  }

  async function alleSpeichern(aboId: number) {
    const offen = liste.folgen.filter((f) => f.aboId === aboId && !f.gespeichert).map((f) => f.id);
    await auftrag.starten(aboId, offen);
    void aboliste.laden();
  }

  function abbestellen(aboId: number) {
    const a = aboliste.abo(aboId);
    if (!a) return;
    void sicher(async () => {
      await aboliste.abbestellen(aboId);
      aendern((x) => ({ ...x, abos: x.abos.filter((id) => id !== aboId), offen: null }));
      meldung("fa-trash-can", a.titel, t("podcastAnsicht.bandAbbestellt"), async () => {
        await aboliste.abonnieren(a.feed);
      });
    });
  }

  async function abonnieren(feed: string, titel: string) {
    await sicher(async () => {
      const neu = await aboliste.abonnieren(feed);
      meldung("fa-podcast", neu.titel || titel, t("podcastAnsicht.bandAbonniert"));
    });
  }
</script>

<div class="rh-radio rh-podcasts">
  <PodcastLeiste abos={aboliste.abos} ordner={aboliste.ordner} gewaehlt={ansicht.abos} wahl={ansicht.wahl} offen={leisteOffen}
                 onwahl={(w) => aendern((a) => ({ ...a, wahl: w, offen: null }))}
                 onabos={(ids) => aendern((a) => ({ ...a, abos: ids, offen: null, verzeichnis: false }))}
                 onordnen={(ids) => void sicher(() => aboliste.ordnen(ids))}
                 onanheften={(id, an) => void sicher(() => aboliste.anheften(id, an))}
                 onordnerneu={(name) => void sicher(async () => { await aboliste.ordnerAnlegen(name); })}
                 onordneraendern={(id, teil) => void sicher(() => aboliste.ordnerAendern(id, teil))}
                 onordnerloeschen={(id) => sicher(() => aboliste.ordnerLoeschen(id))}
                 onordnerordnen={(ids) => void sicher(() => aboliste.ordnerOrdnen(ids))}
                 onzuordnen={(abo, ordner, ids) => void sicher(() => aboliste.zuordnen(abo, ordner, ids))}
                 onabonnieren={() => { leisteOffen = false; aendern((a) => ({ ...a, verzeichnis: true })); }}
                 onzu={() => (leisteOffen = false)} />
  <button class="rh-schleier" class:offen={leisteOffen} type="button" aria-label={t("radio.schliessen")} tabindex="-1"
          onclick={() => (leisteOffen = false)}></button>

  <main class="rh-haupt">
    <PodcastWerkzeug {ansicht} abos={aboliste.abos} gesamt={liste.gesamt} {ungehoert} {stand} laedt={aktualisiert} {leisteOffen}
                     onaendern={aendern} onleiste={() => (leisteOffen = true)} onaktualisieren={() => void aktualisieren()}
                     onabonnieren={() => aendern((a) => ({ ...a, verzeichnis: true, offen: null }))}
                     oneinstellungen={() => actions.navigateTo("/einstellungen/podcasts")} />
    <div class="rh-liste" role="list" aria-label={t("podcastAnsicht.folgen")} bind:this={listeEl}>
      {#if ansicht.verzeichnis}
        <Verzeichnis quelle={podcastquelle} abonniert={(feed) => aboliste.abonniert(feed)} onabonnieren={abonnieren}
                     onzu={() => aendern((a) => ({ ...a, verzeichnis: false }))} />
      {:else}
        {#if einAbo}
          <AboKopf abo={einAbo} {auftrag} arbeitet={aktualisiert} kannSpeichern={kann.speichern} onauto={(an) => void sicher(() => aboliste.autoLaden(einAbo.id, an))}
                   onaktualisieren={() => void aktualisieren(einAbo.id)} onallespeichern={() => void alleSpeichern(einAbo.id)}
                   onanheften={() => void sicher(() => aboliste.anheften(einAbo.id, !einAbo.angeheftet))}
                   onabbestellen={() => abbestellen(einAbo.id)} />
        {/if}
        {#snippet sortspalte(titel: string, s: Podcastsortierung, absteigend: boolean, aktiv: boolean, weiter: Podcastsortierung)}
          <SortSpalte {titel} hilfe={t(`podcastAnsicht.sortHinweis_${s}`)} {aktiv} {absteigend} onwahl={() => sortieren(weiter)} />
        {/snippet}
        {@const datum = ansicht.sortierung === "neu" || ansicht.sortierung === "alt"}
        <div class="rh-spalten rh-folgen-spalten" role="group" aria-label={t("podcastAnsicht.sortierungTitel")}>
          <span>{@render sortspalte(t("podcastAnsicht.folge"), "titel", false, ansicht.sortierung === "titel", "titel")}
            {@render sortspalte(t("podcastAnsicht.datum"), datum ? ansicht.sortierung : "neu", ansicht.sortierung !== "alt", datum,
                                ansicht.sortierung === "neu" ? "alt" : "neu")}</span>
          <span class="rh-ohne-sort">{t("podcastAnsicht.stand")}</span>
          <span class="rechts">{@render sortspalte(t("podcastAnsicht.laenge"), "laenge", false, ansicht.sortierung === "laenge", "laenge")}</span>
          <span class="rh-ohne-sort"></span></div>
        {#if !liste.geladen}
          <div class="rh-ohne-treffer"><i class="fa-solid fa-spinner fa-spin"></i><b>{t("podcastAnsicht.laedt")}</b></div>
        {:else if liste.fehler && !liste.folgen.length}
          <div class="rh-ohne-treffer"><i class="fa-solid fa-triangle-exclamation"></i><b>{t("podcastAnsicht.ladenFehler")}</b><span>{liste.fehler}</span>
            <button class="knopf" type="button" onclick={() => void liste.laden(zuAbfrage(ansicht), ansicht.suche)}><i class="fa-solid fa-rotate"></i>{t("podcastAnsicht.nochmal")}</button></div>
        {:else if !liste.folgen.length}
          <div class="rh-ohne-treffer"><i class="fa-solid fa-filter-circle-xmark"></i><b>{t("podcastAnsicht.keineTreffer")}</b><span>{t("podcastAnsicht.keineTrefferHilfe")}</span>
            <button class="knopf" type="button" onclick={() => aendern((a) => ({ ...a, abos: [], wahl: "alle", suche: "", offen: null }))}>{t("podcastAnsicht.zuruecksetzen")}</button></div>
        {:else}
          {#each liste.folgen as f (f.id)}
            <FolgeZeile folge={f} abo={aboliste.abo(f.aboId)} spielt={spielend === f.id} offen={ansicht.offen === f.id}
                        onspielen={() => void spielen(f)} onvorn={() => void spielen(f, true)} kannSpeichern={kann.speichern}
                        dateiAdresse={kann.herunterladen ? podcastquelle.dateiAdresse(f.id) : ""} onspeichern={() => void speichern(f, true)}
                        onloeschen={() => speichern(f, false)}
                        ongehoert={() => gehoert(f)} ondetails={() => details(f)}
                        onabo={() => aendern((a) => ({ ...a, abos: [f.aboId], offen: null }))} />
          {/each}
          <Nachladen geladen={liste.folgen.length} gesamt={liste.gesamt} laedt={liste.laedtMehr} fehler={liste.fehler} onmehr={() => void liste.mehr()}
                     einheit={t("podcastAnsicht.geladen")} />
        {/if}
      {/if}
    </div>
  </main>
</div>
<Band bind:inhalt={band} />
