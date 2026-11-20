<script lang="ts">
  // Podcasts am Rechner nach dem abgenommenen Entwurf (mockups/radio-filter/podcasts.html, RAD-17): Seitenleiste mit Wahl
  // und Abos, Werkzeugleiste, Kopf eines gewählten Abos, Folgen seitenweise, Abonnieren über das Verzeichnis, Band mit
  // Rückgängig. Zustand und Adresse in lib/podcasts (Quelle, Aboliste, Folgenliste, Podcastzustand), hier nur die Ansicht.
  import { onMount, untrack } from "svelte";
  import { Nachladen } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { actions, appState } from "../../lib/store.svelte.js";
  import { appPfad } from "../../lib/router.js";
  import * as sfx from "../../lib/uiSounds.js";
  import { aboliste, Folgenliste, Merkauftrag, podcastquelle, podcastzustand, zuAbfrage, type Aktualisierungsstand, type Folge,
    type Podcastansicht } from "../../lib/podcasts";
  import type { BandInhalt } from "../../lib/radio/bedienung.svelte";
  import Band from "../radio/Band.svelte";
  import AboKopf from "./AboKopf.svelte";
  import FolgeZeile from "./FolgeZeile.svelte";
  import PodcastLeiste from "./PodcastLeiste.svelte";
  import PodcastWerkzeug from "./PodcastWerkzeug.svelte";
  import Verzeichnis from "./Verzeichnis.svelte";

  const liste = new Folgenliste(podcastquelle);
  const auftrag = new Merkauftrag(podcastquelle, (id) => liste.aendern(id, { gemerkt: true }));
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

  function merken(f: Folge) {
    void sicher(async () => {
      await podcastquelle.merken(f.id, !f.gemerkt);
      liste.aendern(f.id, { gemerkt: !f.gemerkt });
      aboliste.aendern(f.aboId, { geladen: Math.max(0, (aboliste.abo(f.aboId)?.geladen ?? 0) + (f.gemerkt ? -1 : 1)) });
      meldung(f.gemerkt ? "fa-trash-can" : "fa-circle-down", f.titel, f.gemerkt ? t("podcastAnsicht.bandFreigegeben") : t("podcastAnsicht.bandGemerkt"));
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

  async function alleMerken(aboId: number) {
    const offen = liste.folgen.filter((f) => f.aboId === aboId && !f.gemerkt).map((f) => f.id);
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
  <PodcastLeiste abos={aboliste.abos} gewaehlt={ansicht.abos} wahl={ansicht.wahl} offen={leisteOffen}
                 onwahl={(w) => aendern((a) => ({ ...a, wahl: w, offen: null }))}
                 onabos={(ids) => aendern((a) => ({ ...a, abos: ids, offen: null, verzeichnis: false }))}
                 onordnen={(ids) => void sicher(() => aboliste.ordnen(ids))}
                 onabonnieren={() => { leisteOffen = false; aendern((a) => ({ ...a, verzeichnis: true })); }}
                 onzu={() => (leisteOffen = false)} />
  <button class="rh-schleier" class:offen={leisteOffen} type="button" aria-label={t("radio.schliessen")} tabindex="-1"
          onclick={() => (leisteOffen = false)}></button>

  <main class="rh-haupt">
    <PodcastWerkzeug {ansicht} abos={aboliste.abos} gesamt={liste.gesamt} {ungehoert} {stand} laedt={aktualisiert} {leisteOffen}
                     onaendern={aendern} onleiste={() => (leisteOffen = true)} onaktualisieren={() => void aktualisieren()}
                     oneinstellungen={() => actions.navigateTo("/einstellungen/podcast")} />
    <div class="rh-liste" role="list" aria-label={t("podcastAnsicht.folgen")}>
      {#if ansicht.verzeichnis}
        <Verzeichnis quelle={podcastquelle} abonniert={(feed) => aboliste.abonniert(feed)} onabonnieren={abonnieren}
                     onzu={() => aendern((a) => ({ ...a, verzeichnis: false }))} />
      {:else}
        {#if einAbo}
          <AboKopf abo={einAbo} {auftrag} arbeitet={aktualisiert} onauto={(an) => void sicher(() => aboliste.autoLaden(einAbo.id, an))}
                   onaktualisieren={() => void aktualisieren(einAbo.id)} onallemerken={() => void alleMerken(einAbo.id)}
                   onabbestellen={() => abbestellen(einAbo.id)} />
        {/if}
        <div class="rh-spalten rh-folgen-spalten" aria-hidden="true"><span>{t("podcastAnsicht.folge")}</span><span>{t("podcastAnsicht.stand")}</span>
          <span class="rechts">{t("podcastAnsicht.laenge")}</span><span></span></div>
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
                        onspielen={() => void spielen(f)} onvorn={() => void spielen(f, true)} onmerken={() => merken(f)}
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
