<script lang="ts">
  // Podcasts am Telefon nach dem abgenommenen Entwurf (mockups/radio-filter/telefon-podcasts.html, RAD-14): Suche,
  // Zählwerk und Abonnieren oben, darunter die Wahl Neu, Ungehört, Gespeichert, Abos. Neu zeigt die Folgen aller Abos,
  // neueste zuerst; Abos die Übersicht nach Ordnern; ein Abo seinen Kopf und seine Folgen; ein Tipp auf eine Folge ihr
  // Blatt. Zustand und Adresse wie am Rechner (lib/podcasts), hier nur die Ansicht.
  import { onMount, untrack } from "svelte";
  import { Nachladen } from "appkern-oberflaeche";
  import { t } from "../../../lib/i18n.svelte.js";
  import { actions, appState } from "../../../lib/store.svelte.js";
  import { appPfad } from "../../../lib/router.js";
  import { zahl } from "../../../lib/radio/anzeige";
  import { Suchverlauf } from "../../../lib/radio/suchverlauf";
  import { aboaustausch, aboliste, dateiWaehlen, Folgenliste, leerhinweis, podcastquelle, uebernahmeText, podcastzustand, werbequelle, zuAbfrage, type Abo, type Folge, type Folgenwahl, type Podcastansicht,
    type Podcastsortierung } from "../../../lib/podcasts";
  import type { BandInhalt } from "../../../lib/radio/bedienung.svelte";
  import AboBild from "../../podcast/AboBild.svelte";
  import Leerhinweis from "../../podcast/Leerhinweis.svelte";
  import Neuzahl from "../../podcast/Neuzahl.svelte";
  import Band from "../../radio/Band.svelte";
  import Suchfeld from "../../radio/Suchfeld.svelte";
  import TAboKopf from "./TAboKopf.svelte";
  import TFolge from "./TFolge.svelte";
  import TFolgeBlatt from "./TFolgeBlatt.svelte";
  import TVerzeichnis from "./TVerzeichnis.svelte";
  import { tonelement } from "../../../spieler/tonelement";
  import { werbesprung } from "../../../spieler/werbesprung.svelte";

  const verlaufFolgen = new Suchverlauf("radiohub_podcast_suche");
  const verlaufAbos = new Suchverlauf("radiohub_podcast_abosuche");
  const liste = new Folgenliste(podcastquelle);
  const kann = podcastquelle.faehig;
  let band = $state<BandInhalt | null>(null);
  let aboSuche = $state("");
  let arbeitet = $state(false);

  const ansicht = $derived(podcastzustand.ansicht);
  const einAbo = $derived(ansicht.abos.length === 1 ? aboliste.abo(ansicht.abos[0]) : undefined);
  const spielend = $derived((appState.currentEpisode as { id?: number } | null)?.id ?? null);
  const offen = $derived(ansicht.offen === null ? null : (liste.folgen.find((f) => f.id === ansicht.offen) ?? null));

  onMount(() => {
    podcastzustand.oeffnen();
    if (!aboliste.geladen) void aboliste.laden();
    const zurueck = () => { if (appPfad().startsWith("/podcasts")) podcastzustand.ausAdresse(); };
    window.addEventListener("popstate", zurueck);
    return () => window.removeEventListener("popstate", zurueck);
  });

  // Folgen neu, wenn sich Abo, Wahl, Sortierung oder Suche ändern (nicht beim Öffnen einer Folge)
  const schluessel = $derived(JSON.stringify([ansicht.abos, ansicht.wahl, ansicht.sortierung, ansicht.suche, ansicht.aboUebersicht, ansicht.verzeichnis]));
  $effect(() => {
    void schluessel;
    untrack(() => { if (!ansicht.aboUebersicht && !ansicht.verzeichnis) void liste.laden(zuAbfrage(ansicht), ansicht.suche); });
  });

  // je Abo gemerkte Sortierung wie am Rechner
  const aboSortierung = $derived(einAbo?.sortierung ?? "");
  $effect(() => {
    const s = aboSortierung;
    untrack(() => { if (s && s !== ansicht.sortierung) podcastzustand.aendern((a) => ({ ...a, sortierung: s })); });
  });

  const aendern = (arbeit: (a: Podcastansicht) => Podcastansicht) => podcastzustand.aendern(arbeit);
  const gehen = (arbeit: (a: Podcastansicht) => Podcastansicht) => podcastzustand.gehen(arbeit);
  const grund = (a: Podcastansicht): Podcastansicht => ({ ...a, abos: [], offen: null, verzeichnis: false, aboUebersicht: false });

  type Wahl = Folgenwahl | "abos";
  const wahl = $derived<Wahl>(ansicht.aboUebersicht ? "abos" : ansicht.wahl);
  const WAHLEN: [Wahl, string][] = ([["alle", "neu"], ["ungehoert", "ungehoert"], ["gespeichert", "gespeichert"], ["abos", "abos"]] as [Wahl, string][])
    .filter(([w]) => w !== "gespeichert" || kann.speichern);   // ohne Ablage (Webversion) kein Gespeichert (RAD-102)
  function waehlen(w: Wahl) {
    if (w === "abos") aendern((a) => ({ ...grund(a), aboUebersicht: true }));
    else aendern((a) => ({ ...grund(a), wahl: w, sortierung: "neu" }));
  }

  async function sicher(arbeit: () => Promise<void>) {
    try {
      await arbeit();
    } catch (f) {
      actions.showToast((f as Error).message || t("common.fehler"), "error");
    }
  }

  /** Abos aus einer Datei übernehmen (RAD-102): Datei wählen, nacheinander abonnieren, Ergebnis im Band */
  async function uebernehmen() {
    const text = await dateiWaehlen();
    if (text === null) return;
    await sicher(async () => {
      const e = await aboaustausch.uebernehmen(text);
      band = { symbol: "fa-file-import", name: t("podcastAnsicht.austausch.ergebnis"), text: uebernahmeText(e) };
    });
  }

  async function hoeren(f: Folge, vonVorn = false) {
    await sicher(async () => {
      const w = await podcastquelle.wiedergabe(f, liste.folgen);
      actions.playEpisodeFromList(vonVorn ? { ...w.folge, resume_position: 0 } : w.folge, w.abo, w.liste);
    });
  }

  /** eine Werbestelle bewusst hören (RAD-32): läuft die Folge, springt sie dorthin, sonst startet sie dort */
  async function anhoeren(f: Folge, von: number) {
    werbesprung.durchlassen(f.id, von);
    if (spielend === f.id) { tonelement().currentTime = von; return; }
    await sicher(async () => {
      const w = await podcastquelle.wiedergabe(f, liste.folgen);
      actions.playEpisodeFromList({ ...w.folge, resume_position: Math.floor(von) }, w.abo, w.liste);
    });
  }

  async function werbungSetzen(a: Abo, teil: { ueberspringen?: boolean; pruefen?: boolean }) {
    await sicher(async () => {
      await werbequelle.aboSetzen(a.id, teil);
      aboliste.aendern(a.id, { ...(teil.ueberspringen !== undefined ? { werbungUeberspringen: teil.ueberspringen } : {}),
        ...(teil.pruefen !== undefined ? { werbungPruefen: teil.pruefen } : {}) });
    });
  }

  async function speichern(f: Folge, an: boolean) {
    await sicher(async () => {
      await podcastquelle.speichern(f.id, an);
      liste.aendern(f.id, { gespeichert: an, ablagePfad: an ? f.ablagePfad : "" });
      aboliste.aendern(f.aboId, { gespeichert: Math.max(0, (aboliste.abo(f.aboId)?.gespeichert ?? 0) + (an ? 1 : -1)) });
      band = { symbol: an ? "fa-cloud" : "fa-trash-can", name: f.titel, text: an ? t("podcastAnsicht.bandGespeichert") : t("podcastAnsicht.bandGeloescht") };
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

  async function aktualisieren(a: Abo) {
    arbeitet = true;
    await sicher(async () => {
      // die Quelle zählt die wirklich neuen Folgen (RAD-107)
      const neu = await aboliste.aktualisieren(a.id);
      band = { symbol: "fa-rotate", name: a.titel, text: neu ? t("podcastAnsicht.bandNeueFolgen", { n: neu }) : t("podcastAnsicht.bandKeineNeuen") };
      void liste.laden(zuAbfrage(ansicht), ansicht.suche);
    });
    arbeitet = false;
  }

  async function abbestellen(a: Abo) {
    await sicher(async () => {
      await aboliste.abbestellen(a.id);
      gehen((x) => ({ ...grund(x), aboUebersicht: true }));
      band = { symbol: "fa-trash-can", name: a.titel, text: t("podcastAnsicht.bandAbbestellt"), rueckgaengig: async () => { await aboliste.abonnieren(a.feed); } };
    });
  }

  function sortieren(s: Podcastsortierung) {
    aendern((a) => ({ ...a, sortierung: s }));
    if (einAbo) void sicher(() => aboliste.sortierungSetzen(einAbo.id, s));
  }

  // Übersicht der Abos: nach den eigenen Ordnern, danach die losen; die Suche filtert Titel und Autor
  const gruppen = $derived.by(() => {
    const s = aboSuche.trim().toLowerCase();
    const passend = aboliste.abos.filter((a) => !s || `${a.titel} ${a.autor}`.toLowerCase().includes(s));
    const mitOrdner = aboliste.ordner.map((o) => ({ name: o.name, symbol: "fa-folder", abos: passend.filter((a) => a.ordnerId === o.id) }));
    const lose = { name: t("podcastAnsicht.telefon.ohneOrdner"), symbol: "fa-inbox", abos: passend.filter((a) => !a.ordnerId || !aboliste.ordner.some((o) => o.id === a.ordnerId)) };
    return [...mitOrdner, lose].filter((g) => g.abos.length);
  });
</script>

<div class="tf-radio tp-podcasts" class:tp-mit-kopf={!!einAbo || ansicht.verzeichnis}>
  {#if ansicht.verzeichnis}
    <TVerzeichnis quelle={podcastquelle} abonniert={(feed) => aboliste.abonniert(feed)} onzurueck={() => history.back()}
                  onoeffnen={(feed) => { const a = aboliste.vonFeed(feed); if (a) gehen((x) => ({ ...grund(x), abos: [a.id] })); }}
                  onabonnieren={(feed, titel) => sicher(async () => { const neu = await aboliste.abonnieren(feed);
                    band = { symbol: "fa-podcast", name: neu.titel || titel, text: t("podcastAnsicht.bandAbonniert"),
                             verweis: { text: t("podcastAnsicht.telefon.oeffnen"), aktion: () => gehen((x) => ({ ...grund(x), abos: [neu.id] })) } }; })} />
  {:else if einAbo}
    <div class="t-kopf-zurueck tf-a-kopf">
      <button class="rund" type="button" aria-label={t("podcastAnsicht.telefon.zurueck")} title={t("podcastAnsicht.telefon.zurueck")}
              onclick={() => gehen((a) => ({ ...grund(a), aboUebersicht: true }))}><i class="fa-solid fa-chevron-left"></i></button>
      <div><b>{einAbo.titel}</b>{#if einAbo.autor}<span class="rh-still">{einAbo.autor}</span>{/if}</div>
    </div>
    <div class="tf-liste">
      <TAboKopf abo={einAbo} sortierung={ansicht.sortierung} {arbeitet} kannSpeichern={kann.speichern} kannWerbung={kann.werbung} onaktualisieren={() => void aktualisieren(einAbo)}
                onauto={(an) => void sicher(() => aboliste.autoLaden(einAbo.id, an))} onabbestellen={() => abbestellen(einAbo)} onsortieren={sortieren}
                onwerbung={(teil) => void werbungSetzen(einAbo, teil)} />
      {@render folgenliste(false)}
    </div>
  {:else}
    <div class="t-suche tp-suche">
      {#if ansicht.aboUebersicht}
        {#key "abos"}<Suchfeld wert={aboSuche} gedaechtnis={verlaufAbos} name="abo-suche" platzhalter={t("podcastAnsicht.telefon.inAbosSuchen")}
                  beschriftung={t("podcastAnsicht.telefon.inAbosSuchen")} hilfe={t("podcastAnsicht.telefon.inAbosSuchen")} onsuche={(s) => (aboSuche = s)} />{/key}
      {:else}
        {#key "folgen"}<Suchfeld wert={ansicht.suche} gedaechtnis={verlaufFolgen} name="folgen-suche" platzhalter={t("podcastAnsicht.telefon.inFolgenSuchen")}
                  beschriftung={t("podcastAnsicht.telefon.inFolgenSuchen")} hilfe={t("podcastAnsicht.sucheHilfe")} onsuche={(s) => aendern((a) => ({ ...a, suche: s }))} />{/key}
      {/if}
      <span class="t-treffer" title={ansicht.aboUebersicht ? t("podcastAnsicht.telefon.abos") : t("podcastAnsicht.folgenHilfe")}>
        <ak-segmente art="7" stellen="5" farbe="gruen" text={ansicht.aboUebersicht ? zahl(aboliste.abos.length) : liste.gesamt === null ? "-----" : zahl(liste.gesamt)}></ak-segmente>
        <span class="tp-treffer-wort">{ansicht.aboUebersicht ? t("podcastAnsicht.telefon.abosZahl") : t("podcastAnsicht.telefon.folgenZahl")}</span></span>
      {#if kann.abonnieren}
        <button class="rund" type="button" aria-label={t("podcastAnsicht.abonnieren")} title={t("podcastAnsicht.abonnierenHilfe")}
                onclick={() => gehen((a) => ({ ...grund(a), verzeichnis: true }))}><i class="fa-solid fa-plus"></i></button>
      {/if}
    </div>
    <div class="tp-wahl"><div class="segment" role="group" aria-label={t("podcastAnsicht.telefon.wahl")}>
      {#each WAHLEN as [w, text] (w)}<button type="button" class:aktiv={wahl === w} aria-pressed={wahl === w} onclick={() => waehlen(w)}>{t(`podcastAnsicht.telefon.${text}`)}</button>{/each}
    </div></div>
    <div class="tf-liste">
      {#if ansicht.aboUebersicht}
        {#if aboliste.abos.length}<p class="tp-neues-alle">{t("podcastAnsicht.alleAbos")} <Neuzahl abos={aboliste.abos} alle /></p>{/if}
        {#each gruppen as g (g.name)}
          <p class="tp-ordner"><i class="fa-solid {g.symbol}"></i>{g.name}</p>
          {#each g.abos as a (a.id)}
            <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
            <div class="tf-sender tp-abo" onclick={() => gehen((x) => ({ ...grund(x), abos: [a.id] }))}>
              <AboBild abo={a} />
              <div><b>{a.titel}</b>{#if a.autor}<div class="tf-meta"><span>{a.autor}</span></div>{/if}
                <div class="tf-meta">
                  {#if a.ungehoert}<span class="tp-ungehoert"><Neuzahl abos={[a]} /> {t("podcastAnsicht.ungehoert")}</span>
                  {:else}<span>{t("podcastAnsicht.telefon.alleGehoert")}</span>{/if}
                  {#if kann.speichern}<span title={t("podcastAnsicht.telefon.gespeichertHilfe")}><i class="fa-solid fa-cloud"></i> {t("podcastAnsicht.telefon.gespeichertVon", { n: a.gespeichert, von: a.folgen })}</span>{/if}
                  {#if a.autoLaden}<span class="tp-auto"><i class="fa-solid fa-bolt"></i>{t("podcastAnsicht.telefon.neueSpeichernAn")}</span>{/if}
                </div></div>
              <span class="tf-aktionen"><button class="rund" type="button" aria-label={t("podcastAnsicht.telefon.oeffnen")} title={t("podcastAnsicht.telefon.oeffnen")}
                      onclick={(e) => { e.stopPropagation(); gehen((x) => ({ ...grund(x), abos: [a.id] })); }}><i class="fa-solid fa-chevron-right"></i></button></span>
            </div>
          {/each}
        {:else}
          {#if aboliste.geladen}
            <Leerhinweis hinweis={leerhinweis(0, ansicht)} telefon onweiter={() => gehen((x) => ({ ...grund(x), verzeichnis: true }))} />
          {:else}<p class="tf-hinweis tp-laedt"><i class="fa-solid fa-spinner fa-spin"></i>{t("podcastAnsicht.laedt")}</p>{/if}
        {/each}
        {#if aboliste.geladen}
          <!-- Abos sichern und übernehmen unter der Liste, gleich breit (RAD-102, Wahl A) -->
          <div class="tp-abo-aktionen tp-austausch">
            <button class="knopf" type="button" disabled={!aboliste.abos.length} title={t("podcastAnsicht.austausch.sichernHilfe")}
                    onclick={() => aboaustausch.sichern()}><i class="fa-solid fa-file-export"></i>{t("podcastAnsicht.austausch.sichern")}</button>
            <button class="knopf" type="button" disabled={!!aboaustausch.stand} title={t("podcastAnsicht.austausch.uebernehmenHilfe")} onclick={() => void uebernehmen()}>
              <i class="fa-solid {aboaustausch.stand ? 'fa-spinner fa-spin' : 'fa-file-import'}"></i>{aboaustausch.stand
                ? t("podcastAnsicht.austausch.laeuft", aboaustausch.stand) : t("podcastAnsicht.austausch.uebernehmen")}</button>
          </div>
          <p class="tf-hinweis">{t("podcastAnsicht.austausch.erklaerung")}</p>
        {/if}
      {:else}
        {@render folgenliste(true)}
      {/if}
    </div>
  {/if}
</div>

{#snippet folgenliste(mitAbo: boolean)}
  {#if !liste.geladen}
    <p class="tf-hinweis tp-laedt"><i class="fa-solid fa-spinner fa-spin"></i>{aboliste.abos.length ? t(aboliste.abos.length === 1 ? "podcastAnsicht.laedtAbo" : "podcastAnsicht.laedtAbos", { n: aboliste.abos.length }) : t("podcastAnsicht.laedt")}</p>
  {:else if liste.fehler && !liste.folgen.length}
    <p class="tf-hinweis">{liste.fehler}</p>
  {:else if !liste.folgen.length}
    {@const leer = leerhinweis(mitAbo ? aboliste.abos.length : 1, ansicht)}
    <Leerhinweis hinweis={leer} suche={ansicht.suche} telefon onweiter={() => leer.grund !== "ohneFolgen" ? gehen(leer.weiter) : einAbo ? void aktualisieren(einAbo)
                  : void sicher(async () => { await aboliste.aktualisieren(); void liste.laden(zuAbfrage(ansicht), ansicht.suche); })} />
  {:else}
    {#each liste.folgen as f (f.id)}
      <TFolge folge={f} abo={aboliste.abo(f.aboId)} spielt={spielend === f.id} {mitAbo}
              onoeffnen={() => podcastzustand.folge(f.id, f.aboId)} onhoeren={() => void hoeren(f)} />
    {/each}
    <Nachladen geladen={liste.folgen.length} gesamt={liste.gesamt} laedt={liste.laedtMehr} fehler={liste.fehler} onmehr={() => void liste.mehr()}
               einheit={t("podcastAnsicht.geladen")} />
  {/if}
{/snippet}

{#if offen}
  <TFolgeBlatt folge={offen} abo={aboliste.abo(offen.aboId)} spielt={spielend === offen.id}
               onanhoeren={(von) => void anhoeren(offen, von)} onwerbung={(w) => liste.aendern(offen.id, { werbung: w })} kannSpeichern={kann.speichern} dateiAdresse={kann.herunterladenInListen ? podcastquelle.dateiAdresse(offen.id) : ""}
               onhoeren={() => void hoeren(offen)} onvorn={() => void hoeren(offen, true)} onspeichern={() => void speichern(offen, true)}
               onloeschen={() => speichern(offen, false)} ongehoert={() => gehoert(offen)} onzu={() => history.back()} />
{/if}
<Band bind:inhalt={band} />
