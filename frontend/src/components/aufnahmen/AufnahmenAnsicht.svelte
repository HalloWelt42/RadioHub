<script lang="ts">
  // Aufnahmen am Rechner nach dem abgenommenen Entwurf (mockups/radio-filter/aufnahmen.html, RAD-17): Seitenleiste mit
  // Quelle (eigene Aufnahmen oder die ganze Kellerwolke) und Ordnern, Werkzeugleiste, Kopf der laufenden oder gewählten
  // Aufnahme, Liste der Aufnahmen, Titel einer Aufnahme oder Dateien eines Ordners der Kellerwolke, und der Schnitt als
  // Arbeitsplatz über die ganze Breite. Zustand und Adresse in lib/aufnahmen, Schnitt in lib/schnitt; hier nur die Ansicht.
  import { onMount, untrack } from "svelte";
  import { Nachladen } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { actions, appState } from "../../lib/store.svelte.js";
  import { api } from "../../lib/api.js";
  import { appPfad } from "../../lib/router.js";
  import * as sfx from "../../lib/uiSounds.js";
  import { abwaerts, aufnahmeliste as liste, aufnahmequelle as quelle, aufnahmezustand as zustand, ordnerliste,
    type Aufnahme, type Aufnahmeansicht, type Aufnahmesortierung, type Titel, type Wolkendatei, type Wolkenebene } from "../../lib/aufnahmen";
  import { dauer } from "../../lib/aufnahmen/anzeige";
  import { schnittquelle, type Schnittgegenstand } from "../../lib/schnitt";
  import type { BandInhalt } from "../../lib/radio/bedienung.svelte";
  import Band from "../radio/Band.svelte";
  import SortSpalte from "../radio/SortSpalte.svelte";
  import AufnahmenLeiste from "./AufnahmenLeiste.svelte";
  import AufnahmenWerkzeug, { type Chip } from "./AufnahmenWerkzeug.svelte";
  import AufnahmeKopf from "./AufnahmeKopf.svelte";
  import AufnahmeZeile from "./AufnahmeZeile.svelte";
  import LaufendeAufnahme from "./LaufendeAufnahme.svelte";
  import TitelZeile from "./TitelZeile.svelte";
  import WolkenZeile from "./WolkenZeile.svelte";
  import SchnittArbeitsplatz from "./SchnittArbeitsplatz.svelte";

  const kann = quelle.faehig;
  const ansicht = $derived(zustand.ansicht);
  let band = $state<BandInhalt | null>(null);
  let leisteOffen = $state(false);

  // ----- Laden: Liste, Ordner, Kennzahlen -------------------------------------------------------------------------
  let alle = $state<number | null>(null);
  let kennzahlen = $state<{ dateien: number; mb: number; freiGb: number } | null>(null);

  async function zaehlen(): Promise<void> {
    try {
      alle = (await quelle.aufnahmen({ suche: "", ordner: "", sort: "datum", absteigend: true }, 0, 1)).gesamt;
      const s = await api.getRecordingsStats();
      kennzahlen = { dateien: Number(s.file_count) || 0, mb: Number(s.used_mb) || 0, freiGb: Number(s.disk_free_gb) || 0 };
    } catch {
      kennzahlen = null;
    }
  }

  onMount(() => {
    zustand.oeffnen();
    void ordnerliste.laden().catch(() => undefined);
    void zaehlen();
    const zurueck = () => { if (appPfad().startsWith("/aufnahmen")) zustand.ausAdresse(); };
    window.addEventListener("popstate", zurueck);
    return () => window.removeEventListener("popstate", zurueck);
  });

  const schluessel = $derived(JSON.stringify([ansicht.quelle, ansicht.ordner, ansicht.suche, ansicht.sort, ansicht.absteigend]));
  $effect(() => {
    void schluessel;
    untrack(() => { if (ansicht.quelle === "aufnahmen") void liste.laden(zustand.abfrage()); });
  });

  // Solange aufgenommen oder danach fein geschnitten wird (RAD-45), wächst die laufende Aufnahme: Liste und gewählte
  // Aufnahme holen alle fünf Sekunden nach; am Ende der Aufnahme einmal alles neu samt Ordnern und Kennzahlen, und das
  // Band sagt, wo sie liegt
  let nahmAuf = false;
  $effect(() => {
    const an = !!appState.isRecording;
    untrack(() => {
      if (!an && nahmAuf) {
        void allesNeu();
        band = { symbol: "fa-circle-check", text: t("aufnahmenAnsicht.gespeichert", { name: zielName }), art: "gut" };
      }
      nahmAuf = an;
    });
  });

  async function allesNeu(): Promise<void> {
    if (ansicht.quelle === "aufnahmen") void liste.laden(zustand.abfrage());
    else void ebeneLaden(wolkenOrdner);
    void ordnerliste.laden().catch(() => undefined);
    void zaehlen();
    if (gewaehlt) void details(gewaehlt.id);
  }

  // ----- Gewählte Aufnahme ----------------------------------------------------------------------------------------
  let gewaehlt = $state<Aufnahme | null>(null);
  let titel = $state<Titel[]>([]);
  let titelwechsel = $state(0);
  let gesperrt = $state<Set<string>>(new Set());
  let detailFehler = $state("");

  async function details(id: string): Promise<void> {
    detailFehler = "";
    try {
      const [a, x, w, g] = await Promise.all([quelle.aufnahme(id), quelle.titel(id), quelle.titelwechsel(id).catch(() => 0), quelle.gesperrt().catch(() => new Set<string>())]);
      if (zustand.ansicht.aufnahme !== id) return;
      gewaehlt = a; titel = x; titelwechsel = w; gesperrt = g;
    } catch (f) {
      detailFehler = (f as Error).message;
    }
  }

  const gewaehltId = $derived(ansicht.quelle === "aufnahmen" ? ansicht.aufnahme : null);
  $effect(() => {
    const id = gewaehltId;
    untrack(() => {
      if (!id) { gewaehlt = null; titel = []; return; }
      if (gewaehlt?.id !== id) { gewaehlt = liste.aufnahmen.find((a) => a.id === id) ?? null; titel = []; }
      void details(id);
    });
  });

  // laufende oder fein geschnittene Aufnahme (RAD-45): alle fünf Sekunden nachholen (siehe oben)
  const imGange = $derived(!!appState.isRecording || gewaehlt?.status === "laeuft" || liste.aufnahmen.some((a) => a.status === "laeuft"));
  $effect(() => {
    if (!imGange) return;
    const uhr = setInterval(() => {
      if (ansicht.quelle !== "aufnahmen") return;
      void liste.laden(zustand.abfrage());
      if (gewaehlt?.status === "laeuft") void details(gewaehlt.id);
    }, 5000);
    return () => clearInterval(uhr);
  });

  // ----- Kellerwolke ----------------------------------------------------------------------------------------------
  let ebene = $state<Wolkenebene | null>(null);
  let wolkeFehler = $state("");
  let wolkeSuche = $state("");
  let wolkeLaedt = $state(false);
  type Wolkensortierung = "name" | "datum" | "groesse";
  let wolkeSort = $state<{ feld: Wolkensortierung; ab: boolean }>({ feld: "name", ab: false });

  const elternOrdner = (pfad: string) => pfad.split("/").slice(0, -1).join("/");
  /** der Ordner, dessen Inhalt die Leiste zeigt: im Schnitt der Ordner der Datei */
  const wolkenOrdner = $derived(ansicht.quelle === "wolke" ? (ansicht.schnitt ? elternOrdner(ansicht.pfad) : ansicht.pfad) : null);

  async function ebeneLaden(pfad: string | null): Promise<void> {
    if (pfad === null) return;
    wolkeLaedt = true;
    try {
      ebene = await quelle.wolke(pfad);
      wolkeFehler = "";
    } catch (f) {
      ebene = null;
      wolkeFehler = (f as Error).message;
    } finally {
      wolkeLaedt = false;
    }
  }
  async function wolkeMehr(): Promise<void> {
    if (!ebene || wolkeLaedt) return;
    wolkeLaedt = true;
    try {
      const weiter = await quelle.wolke(ebene.pfad, ebene.dateien.length);
      ebene = { ...ebene, dateien: [...ebene.dateien, ...weiter.dateien] };
    } catch (f) {
      wolkeFehler = (f as Error).message;
    } finally {
      wolkeLaedt = false;
    }
  }
  $effect(() => {
    const pfad = wolkenOrdner;
    untrack(() => { if (pfad !== null && pfad !== ebene?.pfad) { wolkeSuche = ""; void ebeneLaden(pfad); } });
  });

  const dateien = $derived.by(() => {
    const s = wolkeSuche.trim().toLowerCase();
    const reihe = (ebene?.dateien ?? []).filter((d) => !s || d.name.toLowerCase().includes(s));
    const v = { name: (a: Wolkendatei, b: Wolkendatei) => a.name.localeCompare(b.name, "de", { numeric: true }),
      datum: (a: Wolkendatei, b: Wolkendatei) => (a.geaendert ?? "").localeCompare(b.geaendert ?? ""),
      groesse: (a: Wolkendatei, b: Wolkendatei) => a.groesse - b.groesse }[wolkeSort.feld];
    return reihe.sort((a, b) => v(a, b) * (wolkeSort.ab ? -1 : 1));
  });

  // ----- Ändern und Gehen -----------------------------------------------------------------------------------------
  function aendern(arbeit: (a: Aufnahmeansicht) => Aufnahmeansicht) { zustand.aendern(arbeit); }
  function gehen(arbeit: (a: Aufnahmeansicht) => Aufnahmeansicht) { zustand.gehen(arbeit); }

  function sortieren(s: Aufnahmesortierung) {
    aendern((a) => ({ ...a, sort: s, absteigend: a.sort === s ? !a.absteigend : abwaerts(s) }));
  }
  function wolkeSortieren(feld: Wolkensortierung) {
    wolkeSort = { feld, ab: wolkeSort.feld === feld ? !wolkeSort.ab : feld !== "name" };
  }

  async function sicher(arbeit: () => Promise<void>) {
    try {
      await arbeit();
    } catch (f) {
      actions.showToast((f as Error).message || t("common.fehler"), "error");
    }
  }

  // ----- Hören über die Kanzel ------------------------------------------------------------------------------------
  type Eintrag = { path: string; name: string; session_id?: string; station_name: string; date?: string; duration: number; playUrl: string; source: "recording" };
  const jetzt = $derived(appState.isPlaying ? ((appState.currentRecording as Eintrag | null) ?? null) : null);

  const ganzEintrag = (a: Aufnahme): Eintrag => ({ path: `sitzung:${a.id}`, name: a.sender, session_id: a.id, station_name: a.sender, date: a.beginn,
    duration: a.dauer, playUrl: schnittquelle.ton({ art: "sitzung", kennung: a.id }), source: "recording" });
  const titelEintrag = (a: Aufnahme, x: Titel): Eintrag => ({ path: x.pfad, name: x.titel || a.sender, session_id: a.id, station_name: a.sender,
    duration: x.dauer, playUrl: quelle.titelTon(x.id), source: "recording" });
  const wolkeEintrag = (d: Wolkendatei): Eintrag => ({ path: d.pfad, name: d.name, station_name: t("aufnahmenAnsicht.kellerwolke"), duration: 0,
    playUrl: quelle.wolkeTon(d.pfad), source: "recording" });

  function abspielen(reihe: Eintrag[], start: Eintrag) {
    sfx.click();
    if (appState.isRecording) { actions.showToast(t("aufnahmenAnsicht.erstBeenden"), "error"); return; }
    if (jetzt?.path === start.path) { actions.stop(); return; }
    appState.recordingPlaylist = reihe;
    void actions.playRecording(start);
  }

  async function hoeren(a: Aufnahme, ab?: Titel) {
    if (a.status === "laeuft") return;
    await sicher(async () => {
      const reihe = a.id === gewaehlt?.id && titel.length ? titel : await quelle.titel(a.id);
      if (!reihe.length) { abspielen([ganzEintrag(a)], ganzEintrag(a)); return; }
      const eintraege = reihe.map((x) => titelEintrag(a, x));
      abspielen(eintraege, eintraege[ab ? reihe.findIndex((x) => x.id === ab.id) : 0] ?? eintraege[0]);
    });
  }
  const spielt = (a: Aufnahme) => jetzt?.session_id === a.id;

  // ----- Schnitt --------------------------------------------------------------------------------------------------
  let schnittBereich = $state<{ von: number; bis: number } | null>(null);
  const schnittGegenstand = $derived<Schnittgegenstand | null>(!ansicht.schnitt ? null
    : ansicht.quelle === "wolke" ? (ansicht.pfad ? { art: "datei", kennung: ansicht.pfad } : null)
    : ansicht.aufnahme ? { art: "sitzung", kennung: ansicht.aufnahme } : null);

  function schneiden(a: Aufnahme, x?: Titel) {
    if (a.status === "laeuft") return;
    schnittBereich = x ? { von: x.start, bis: x.start + x.dauer } : null;
    gehen((v) => ({ ...v, quelle: "aufnahmen", aufnahme: a.id, schnitt: true }));
  }
  function dateiSchneiden(d: Wolkendatei) {
    schnittBereich = null;
    gehen((v) => ({ ...v, quelle: "wolke", schnitt: true, pfad: d.pfad }));
  }
  function schnittZu() {
    gehen((v) => ({ ...v, schnitt: false, pfad: v.quelle === "wolke" ? elternOrdner(v.pfad) : v.pfad }));
  }

  // ----- Verwalten ------------------------------------------------------------------------------------------------
  async function loeschen(a: Aufnahme) {
    if (jetzt?.session_id === a.id) actions.stop();
    await quelle.loeschen(a.id);
    liste.entfernen(a.id);
    if (ansicht.aufnahme === a.id) gehen((v) => ({ ...v, aufnahme: null, schnitt: false }));
    band = { symbol: "fa-trash-can", name: a.sender, text: t("aufnahmenAnsicht.geloescht") };
    void ordnerliste.laden().catch(() => undefined);
    void zaehlen();
  }

  async function titelLoeschen(a: Aufnahme, x: Titel) {
    if (jetzt?.path === x.pfad) actions.stop();
    const letzter = titel.length === 1;
    await sicher(async () => {
      await quelle.titelLoeschen(a.id, x.id);
      band = { symbol: "fa-trash-can", name: x.titel, text: t("aufnahmenAnsicht.geloescht") };
      if (letzter) {
        liste.entfernen(a.id);
        gehen((v) => ({ ...v, aufnahme: null }));
      } else {
        await details(a.id);
        void liste.laden(zustand.abfrage());
      }
      void zaehlen();
    });
  }

  function sperren(x: Titel) {
    const an = !gesperrt.has(x.titel);
    void sicher(async () => {
      await quelle.sperren(x.titel, an);
      const neu = new Set(gesperrt);
      an ? neu.add(x.titel) : neu.delete(x.titel);
      gesperrt = neu;
    });
  }

  async function teilen(a: Aufnahme) {
    await sicher(async () => {
      const n = await quelle.nachTitelnTeilen(a.id);
      band = { symbol: "fa-wand-magic-sparkles", name: a.sender, text: t("aufnahmenAnsicht.geteilt", { n }), art: "gut" };
      await details(a.id);
      void liste.laden(zustand.abfrage());
    });
  }

  function verschieben(a: Aufnahme, ordnerId: number | null) {
    void sicher(async () => {
      await quelle.verschieben(a.id, ordnerId);
      if (gewaehlt?.id === a.id) gewaehlt = { ...gewaehlt, ordnerId };
      band = { symbol: "fa-folder-tree", name: a.sender, text: t("aufnahmenAnsicht.verschoben", { name: ordnerliste.name(ordnerId) ?? t("aufnahmenAnsicht.ohneOrdner") }) };
      void ordnerliste.laden();
      void liste.laden(zustand.abfrage());
    });
  }

  // ----- Anzeige --------------------------------------------------------------------------------------------------
  const zielName = $derived(ordnerliste.ziel?.name ?? t("aufnahmenAnsicht.ohneOrdner"));
  const ordnerName = (id: number | null) => ordnerliste.name(id) ?? t("aufnahmenAnsicht.ohneOrdner");
  const laufend = $derived(appState.isRecording ? (liste.aufnahmen.find((a) => a.status === "laeuft") ?? null) : null);
  // das begonnene Stück der gewählten laufenden Aufnahme (RAD-45): ab dem Ende der abgelegten, Titel aus den Sendedaten
  const begonnen = $derived.by((): Titel | null => {
    if (!appState.isRecording || !gewaehlt || gewaehlt.id !== laufend?.id) return null;
    const start = titel.reduce((ende, x) => Math.max(ende, x.start + x.dauer), 0);
    const angaben = ((appState.recordingIcyEntries as { title: string; ignored?: boolean }[]) ?? []).filter((e) => !e.ignored);
    return { id: -1, nr: titel.length + 1, titel: angaben.at(-1)?.title || t("aufnahmenAnsicht.begonnen"), start,
             dauer: Math.max(0, (appState.recordingElapsed as number) - start), groesse: 0, pfad: "" };
  });
  const ohneOrdner = $derived(alle === null ? null : Math.max(0, alle - ordnerliste.ordner.reduce((s, o) => s + o.anzahl, 0)));
  const wolke = $derived(ansicht.quelle === "wolke");

  const chips = $derived.by<Chip[]>(() => {
    if (wolke) return wolkeSuche ? [{ art: "suche", titel: t("aufnahmenAnsicht.chipSuche"), text: wolkeSuche, weg: () => (wolkeSuche = "") }] : [];
    const c: Chip[] = [];
    if (ansicht.ordner) c.push({ art: "ordner", titel: t("aufnahmenAnsicht.chipOrdner"), text: ansicht.ordner === "ohne" ? t("aufnahmenAnsicht.ohneOrdner") : ordnerName(Number(ansicht.ordner)),
      weg: () => gehen((a) => ({ ...a, ordner: "" })) });
    if (gewaehlt) c.push({ art: "aufnahme", titel: t("aufnahmenAnsicht.chipAufnahme"), text: gewaehlt.sender, weg: () => gehen((a) => ({ ...a, aufnahme: null })) });
    if (ansicht.suche) c.push({ art: "suche", titel: t("aufnahmenAnsicht.chipSuche"), text: ansicht.suche, weg: () => aendern((a) => ({ ...a, suche: "" })) });
    return c;
  });
  const zusatz = $derived(wolke ? (ebene?.kette.map((k) => k.name).join(" / ") || t("aufnahmenAnsicht.wolkeWurzel"))
    : !liste.mehr && liste.aufnahmen.length ? dauer(liste.aufnahmen.reduce((s, a) => s + a.dauer, 0)) : "");
</script>

<div class="rh-radio rh-podcasts rh-aufnahmen" class:rh-im-schnitt={!!schnittGegenstand}>
  <AufnahmenLeiste {ansicht} ordner={ordnerliste.ordner} gesamt={alle} {ohneOrdner} {ebene} {wolkeFehler} {kennzahlen} offen={leisteOffen} wolkeMoeglich={kann.wolke}
                   onquelle={(q) => gehen((a) => ({ ...a, quelle: q, aufnahme: null, schnitt: false, pfad: "" }))}
                   onordner={(o) => { leisteOffen = false; gehen((a) => ({ ...a, ordner: o, aufnahme: null })); }}
                   onziel={(id) => void sicher(() => ordnerliste.zielSetzen(id))}
                   onumbenennen={(id, name) => void sicher(() => ordnerliste.umbenennen(id, name))}
                   onloeschen={(id) => sicher(async () => { await ordnerliste.loeschen(id); if (ansicht.ordner === String(id)) gehen((a) => ({ ...a, ordner: "" })); })}
                   onanlegen={(name) => void sicher(() => ordnerliste.anlegen(name))}
                   onpfad={(p) => { leisteOffen = false; gehen((a) => ({ ...a, pfad: p, schnitt: false })); }}
                   onzu={() => (leisteOffen = false)} />
  <button class="rh-schleier" class:offen={leisteOffen} type="button" aria-label={t("radio.schliessen")} tabindex="-1" onclick={() => (leisteOffen = false)}></button>

  <main class="rh-haupt">
    {#if !schnittGegenstand}
      <AufnahmenWerkzeug {wolke} anzahl={wolke ? (ebene?.gesamt ?? null) : liste.gesamt} {zusatz} suche={wolke ? wolkeSuche : ansicht.suche} {chips}
                         ziel={zielName} nimmtAuf={!!appState.isRecording} laedt={wolke ? wolkeLaedt : liste.laedt} {leisteOffen}
                         onsuche={(s) => { if (wolke) wolkeSuche = s; else aendern((a) => ({ ...a, suche: s })); }}
                         onleiste={() => (leisteOffen = true)} onaktualisieren={() => void allesNeu()} />
    {/if}
    <div class="rh-liste" role="list" aria-label={t("aufnahmenAnsicht.aufnahmen")}>
      {#if schnittGegenstand}
        {#key `${schnittGegenstand.art}:${schnittGegenstand.kennung}`}
          <SchnittArbeitsplatz gegenstand={schnittGegenstand} bereich={schnittBereich} onschliessen={schnittZu} ongeaendert={() => void allesNeu()} />
        {/key}
      {:else if wolke}
        {#snippet wsort(titel: string, feld: Wolkensortierung)}
          <SortSpalte {titel} hilfe={t(`aufnahmenAnsicht.sortWolke_${feld}`)} aktiv={wolkeSort.feld === feld} absteigend={wolkeSort.ab} onwahl={() => wolkeSortieren(feld)} />
        {/snippet}
        <div class="rh-spalten rh-a-spalten" role="group" aria-label={t("aufnahmenAnsicht.sortierung")}>
          <span>{@render wsort(t("aufnahmenAnsicht.spalteDatei"), "name")}{@render wsort(t("aufnahmenAnsicht.spalteDatum"), "datum")}</span>
          <span class="rh-ohne-sort">{t("aufnahmenAnsicht.spalteArt")}</span><span class="rh-ohne-sort"></span>
          <span class="rechts">{@render wsort(t("aufnahmenAnsicht.spalteGroesse"), "groesse")}</span><span class="rh-ohne-sort"></span></div>
        {#if !ebene && wolkeLaedt}
          <div class="rh-ohne-treffer"><i class="fa-solid fa-spinner fa-spin"></i><b>{t("aufnahmenAnsicht.laedt")}</b></div>
        {:else if wolkeFehler}
          <div class="rh-ohne-treffer"><i class="fa-solid fa-lock"></i><b>{t("aufnahmenAnsicht.wolkeGesperrt")}</b><span>{wolkeFehler}</span>
            <button class="knopf" type="button" onclick={() => void ebeneLaden(wolkenOrdner)}><i class="fa-solid fa-rotate"></i>{t("aufnahmenAnsicht.nochmal")}</button></div>
        {:else if !dateien.length}
          <div class="rh-ohne-treffer"><i class="fa-solid fa-folder-open"></i><b>{t("aufnahmenAnsicht.wolkeLeer")}</b><span>{t("aufnahmenAnsicht.wolkeLeerHilfe")}</span></div>
        {:else}
          {#each dateien as d (d.pfad)}
            <WolkenZeile datei={d} spielt={jetzt?.path === d.pfad} ordner={elternOrdner(d.pfad) || t("aufnahmenAnsicht.wolkeWurzel")} laden={quelle.wolkeTon(d.pfad, true)}
                         onhoeren={() => abspielen(dateien.map(wolkeEintrag), wolkeEintrag(d))} onschneiden={() => dateiSchneiden(d)} />
          {/each}
          {#if ebene}<Nachladen geladen={ebene.dateien.length} gesamt={ebene.gesamt} laedt={wolkeLaedt} fehler={wolkeFehler} onmehr={() => void wolkeMehr()}
                                einheit={t("aufnahmenAnsicht.geladen")} />{/if}
        {/if}
      {:else if gewaehlt}
        <AufnahmeKopf aufnahme={gewaehlt} ordner={ordnerliste.ordner} {titelwechsel} zip={quelle.alsZip(gewaehlt.id)} eineDatei={quelle.alsEineDatei(gewaehlt.id)}
                      kannSchneiden={kann.schnitt && gewaehlt.status !== "laeuft"} kannVerwalten={kann.verwalten && gewaehlt.status !== "laeuft"}
                      onhoeren={() => void hoeren(gewaehlt!)} onschneiden={() => schneiden(gewaehlt!)} onteilen={() => teilen(gewaehlt!)}
                      onverschieben={(o) => verschieben(gewaehlt!, o)} onloeschen={() => loeschen(gewaehlt!)} />
        <div class="rh-spalten rh-a-spalten" aria-hidden="true"><span>{t("aufnahmenAnsicht.spalteTitel")}</span><span class="rh-ohne-sort">{t("aufnahmenAnsicht.spalteAb")}</span>
          <span class="rechts">{t("aufnahmenAnsicht.spalteLaenge")}</span><span class="rechts">{t("aufnahmenAnsicht.spalteGroesse")}</span><span></span></div>
        {#if detailFehler}
          <div class="rh-ohne-treffer"><i class="fa-solid fa-triangle-exclamation"></i><b>{t("aufnahmenAnsicht.ladenFehler")}</b><span>{detailFehler}</span></div>
        {:else}
          {#if gewaehlt.status === "laeuft" && !appState.isRecording}
            <p class="rh-still rh-a-feinschnitt"><i class="fa-solid fa-spinner fa-spin"></i>{t("aufnahmenAnsicht.feinschnittLaeuft")}</p>
          {/if}
          {#each titel as x (x.id)}
            <TitelZeile titel={x} spielt={jetzt?.path === x.pfad} gesperrt={gesperrt.has(x.titel)} letzter={titel.length === 1} datei={quelle.titelDatei(x.id)}
                        imGange={gewaehlt.status === "laeuft"}
                        kannSchneiden={kann.schnitt} kannVerwalten={kann.verwalten} onhoeren={() => void hoeren(gewaehlt!, x)} onschneiden={() => schneiden(gewaehlt!, x)}
                        onsperren={() => sperren(x)} onloeschen={() => titelLoeschen(gewaehlt!, x)} />
          {/each}
          {#if begonnen}
            <TitelZeile titel={begonnen} spielt={false} gesperrt={false} letzter={false} datei="" imGange={true} laeuft={true}
                        kannSchneiden={false} kannVerwalten={false} onhoeren={() => {}} onschneiden={() => {}} onsperren={() => {}} onloeschen={async () => {}} />
          {/if}
        {/if}
      {:else}
        {#if laufend}<LaufendeAufnahme aufnahme={laufend} ziel={zielName} />{/if}
        {#snippet asort(titel: string, s: Aufnahmesortierung)}
          <SortSpalte {titel} hilfe={t(`aufnahmenAnsicht.sort_${s}`)} aktiv={ansicht.sort === s} absteigend={ansicht.absteigend} onwahl={() => sortieren(s)} />
        {/snippet}
        <div class="rh-spalten rh-a-spalten" role="group" aria-label={t("aufnahmenAnsicht.sortierung")}>
          <span>{@render asort(t("aufnahmenAnsicht.spalteAufnahme"), "sender")}{@render asort(t("aufnahmenAnsicht.spalteDatum"), "datum")}</span>
          <span class="rh-ohne-sort">{t("aufnahmenAnsicht.spalteTitel")}</span>
          <span class="rechts">{@render asort(t("aufnahmenAnsicht.spalteLaenge"), "dauer")}</span>
          <span class="rechts">{@render asort(t("aufnahmenAnsicht.spalteGroesse"), "groesse")}</span><span class="rh-ohne-sort"></span></div>
        {#if !liste.geladen}
          <div class="rh-ohne-treffer"><i class="fa-solid fa-spinner fa-spin"></i><b>{t("aufnahmenAnsicht.laedt")}</b></div>
        {:else if liste.fehler && !liste.aufnahmen.length}
          <div class="rh-ohne-treffer"><i class="fa-solid fa-triangle-exclamation"></i><b>{t("aufnahmenAnsicht.ladenFehler")}</b><span>{liste.fehler}</span>
            <button class="knopf" type="button" onclick={() => void liste.laden(zustand.abfrage())}><i class="fa-solid fa-rotate"></i>{t("aufnahmenAnsicht.nochmal")}</button></div>
        {:else if !liste.aufnahmen.length}
          {#if chips.length}
            <div class="rh-ohne-treffer"><i class="fa-solid fa-filter-circle-xmark"></i><b>{t("aufnahmenAnsicht.keineTreffer")}</b><span>{t("aufnahmenAnsicht.keineTrefferHilfe")}</span>
              <button class="knopf" type="button" onclick={() => gehen((a) => ({ ...a, ordner: "", suche: "", aufnahme: null }))}>{t("aufnahmenAnsicht.zuruecksetzen")}</button></div>
          {:else}
            <div class="rh-ohne-treffer"><i class="fa-solid fa-circle-dot"></i><b>{t("aufnahmenAnsicht.leer")}</b><span>{t("aufnahmenAnsicht.leerHilfe")}</span></div>
          {/if}
        {:else}
          {#each liste.aufnahmen as a (a.id)}
            <AufnahmeZeile aufnahme={a} ordner={ordnerName(a.ordnerId)} spielt={spielt(a)} laufendeSekunden={a.status === "laeuft" ? (appState.recordingElapsed as number) : null}
                           kannSchneiden={kann.schnitt} onwaehlen={() => gehen((v) => ({ ...v, aufnahme: a.id }))} onhoeren={() => void hoeren(a)} onschneiden={() => schneiden(a)} />
          {/each}
          <Nachladen geladen={liste.aufnahmen.length} gesamt={liste.gesamt} laedt={liste.laedt} fehler={liste.fehler} onmehr={() => void liste.nachladen()}
                     einheit={t("aufnahmenAnsicht.geladen")} />
        {/if}
      {/if}
    </div>
  </main>
</div>
<Band bind:inhalt={band} />
