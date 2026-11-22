<script lang="ts">
  // Aufnahmen am Telefon nach dem Entwurf (mockups/radio-filter/telefon-aufnahmen.html, RAD-17): nur hören. Die Liste
  // mit Suche und Ordnern als Chips, eine geöffnete Aufnahme mit ihren Titeln und "Alles hören". Verwalten und
  // Schneiden gibt es am Rechner. Dieselben Bausteine wie das Radio am Telefon; Zustand und Adresse wie am Rechner.
  import { onMount, untrack } from "svelte";
  import { Nachladen } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { actions, appState } from "../../lib/store.svelte.js";
  import { appPfad } from "../../lib/router.js";
  import { zahl } from "../../lib/radio/anzeige";
  import { Suchverlauf } from "../../lib/radio/suchverlauf";
  import { aufnahmeliste as liste, aufnahmequelle as quelle, aufnahmezustand as zustand, ordnerliste, type Aufnahme, type Titel } from "../../lib/aufnahmen";
  import { datum, zeit } from "../../lib/aufnahmen/anzeige";
  import { schnittquelle } from "../../lib/schnitt";
  import Logo from "../radio/Logo.svelte";
  import Suchfeld from "../radio/Suchfeld.svelte";

  const verlauf = new Suchverlauf("radiohub_aufnahmen_suche");
  const ansicht = $derived(zustand.ansicht);
  let gewaehlt = $state<Aufnahme | null>(null);
  let titel = $state<Titel[]>([]);

  onMount(() => {
    zustand.oeffnen();
    void ordnerliste.laden().catch(() => undefined);
    const zurueck = () => { if (appPfad().startsWith("/aufnahmen")) zustand.ausAdresse(); };
    window.addEventListener("popstate", zurueck);
    return () => window.removeEventListener("popstate", zurueck);
  });

  const schluessel = $derived(JSON.stringify([ansicht.ordner, ansicht.suche]));
  $effect(() => {
    void schluessel;
    untrack(() => void liste.laden(zustand.abfrage()));
  });

  const id = $derived(ansicht.quelle === "aufnahmen" ? ansicht.aufnahme : null);
  $effect(() => {
    const kennung = id;
    untrack(async () => {
      if (!kennung) { gewaehlt = null; titel = []; return; }
      gewaehlt = liste.aufnahmen.find((a) => a.id === kennung) ?? gewaehlt;
      try {
        const [a, x] = await Promise.all([quelle.aufnahme(kennung), quelle.titel(kennung)]);
        if (zustand.ansicht.aufnahme === kennung) { gewaehlt = a; titel = x; }
      } catch (f) {
        actions.showToast((f as Error).message, "error");
      }
    });
  });

  type Eintrag = { path: string; name: string; session_id: string; station_name: string; duration: number; playUrl: string; source: "recording" };
  const jetzt = $derived(appState.isPlaying ? ((appState.currentRecording as Eintrag | null) ?? null) : null);
  const eintrag = (a: Aufnahme, x: Titel): Eintrag => ({ path: x.pfad, name: x.titel || a.sender, session_id: a.id, station_name: a.sender, duration: x.dauer,
    playUrl: quelle.titelTon(x.id), source: "recording" });

  async function hoeren(a: Aufnahme, ab?: Titel) {
    if (a.status === "laeuft") return;
    if (appState.isRecording) { actions.showToast(t("aufnahmenAnsicht.erstBeenden"), "error"); return; }
    try {
      const reihe = a.id === gewaehlt?.id && titel.length ? titel : await quelle.titel(a.id);
      if (!reihe.length) {
        const ganz: Eintrag = { path: `sitzung:${a.id}`, name: a.sender, session_id: a.id, station_name: a.sender, duration: a.dauer,
          playUrl: schnittquelle.ton({ art: "sitzung", kennung: a.id }), source: "recording" };
        appState.recordingPlaylist = [ganz];
        void actions.playRecording(ganz);
        return;
      }
      const eintraege = reihe.map((x) => eintrag(a, x));
      const start = eintraege[ab ? reihe.findIndex((x) => x.id === ab.id) : 0] ?? eintraege[0];
      if (jetzt?.path === start.path) { actions.stop(); return; }
      appState.recordingPlaylist = eintraege;
      void actions.playRecording(start);
    } catch (f) {
      actions.showToast((f as Error).message, "error");
    }
  }

  const ordnerName = (oid: number | null) => ordnerliste.name(oid) ?? t("aufnahmenAnsicht.ohneOrdner");
  const wahl = $derived([{ wert: "", name: t("aufnahmenAnsicht.alleAufnahmen") }, ...ordnerliste.ordner.map((o) => ({ wert: String(o.id), name: o.name })),
    { wert: "ohne", name: t("aufnahmenAnsicht.ohneOrdner") }]);
</script>

<div class="tf-radio tf-aufnahmen">
  {#if gewaehlt && id}
    <div class="t-kopf-zurueck tf-a-kopf">
      <button class="rund" type="button" aria-label={t("aufnahmenAnsicht.telefon.zurueck")} title={t("aufnahmenAnsicht.telefon.zurueck")}
              onclick={() => zustand.gehen((a) => ({ ...a, aufnahme: null }))}><i class="fa-solid fa-chevron-left"></i></button>
      <div><b>{gewaehlt.sender}</b><span class="rh-still">{datum(gewaehlt.beginn)} · {t("aufnahmenAnsicht.telefon.titel", { n: gewaehlt.titelzahl })} · {zeit(gewaehlt.dauer)}</span></div>
    </div>
    <div class="t-chips">
      <button class="knopf primaer" type="button" disabled={gewaehlt.status === "laeuft"} onclick={() => void hoeren(gewaehlt!)}><i class="fa-solid fa-play"></i>{t("aufnahmenAnsicht.telefon.alles")}</button>
      <span class="rh-still">{ordnerName(gewaehlt.ordnerId)}</span>
    </div>
    <div class="tf-liste">
      {#each titel as x (x.id)}
        {@const spielt = jetzt?.path === x.pfad}
        <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
        <div class="tf-sender" class:spielt onclick={() => void hoeren(gewaehlt!, x)}>
          <span class="rh-a-nr">{String(x.nr).padStart(2, "0")}</span>
          <div><b>{x.titel}</b><div class="tf-meta"><span>{t("aufnahmenAnsicht.spalteAb")} {zeit(x.start)}</span><span>{zeit(x.dauer)}</span></div></div>
          <span class="tf-aktionen"><button class="rund" type="button" aria-label={t("aufnahmenAnsicht.abHier")} title={t("aufnahmenAnsicht.abHier")}
                  onclick={(e) => { e.stopPropagation(); void hoeren(gewaehlt!, x); }}><i class="fa-solid {spielt ? 'fa-volume-high' : 'fa-play'}"></i></button></span>
        </div>
      {/each}
    </div>
  {:else}
    <div class="t-suche tf-a-suche">
      <Suchfeld wert={ansicht.suche} gedaechtnis={verlauf} name="aufnahmen-suche" platzhalter={t("aufnahmenAnsicht.suche")} beschriftung={t("aufnahmenAnsicht.suche")}
                hilfe={t("aufnahmenAnsicht.suche")} onsuche={(s) => zustand.aendern((a) => ({ ...a, suche: s }))} />
    </div>
    <div class="t-chips">
      <span class="t-treffer" title={t("aufnahmenAnsicht.zaehlerHilfe")}><ak-segmente art="7" stellen="4" farbe="rot" text={liste.gesamt === null ? "----" : zahl(liste.gesamt)}></ak-segmente>{t("aufnahmenAnsicht.aufnahmen")}</span>
      {#each wahl as w (w.wert)}
        <button type="button" class="chip wahl" class:an={ansicht.ordner === w.wert} aria-pressed={ansicht.ordner === w.wert}
                onclick={() => zustand.aendern((a) => ({ ...a, ordner: w.wert }))}>{w.name}</button>
      {/each}
    </div>
    <div class="tf-liste">
      {#if !liste.geladen}
        <p class="tf-hinweis">{t("aufnahmenAnsicht.laedt")}</p>
      {:else if liste.fehler && !liste.aufnahmen.length}
        <p class="tf-hinweis">{liste.fehler}</p>
      {:else if !liste.aufnahmen.length}
        <p class="tf-hinweis">{ansicht.ordner || ansicht.suche ? t("aufnahmenAnsicht.keineTreffer") : t("aufnahmenAnsicht.leer")}</p>
      {:else}
        {#each liste.aufnahmen as a (a.id)}
          {@const spielt = jetzt?.session_id === a.id}
          <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
          <div class="tf-sender" class:spielt onclick={() => zustand.gehen((v) => ({ ...v, aufnahme: a.id }))}>
            <Logo uuid={a.senderUuid} name={a.sender} logo="" />
            <div><b>{a.sender}</b>
              <div class="tf-meta"><span>{datum(a.beginn)}</span><span>{ordnerName(a.ordnerId)}</span>
                {#if a.status === "laeuft"}<span class="rh-a-warn">{t("aufnahmenAnsicht.nimmtAuf")}</span>
                {:else if a.status !== "fertig"}<span class="rh-a-warn"><i class="fa-solid fa-triangle-exclamation"></i>{t(`aufnahmenAnsicht.${a.status}`)}</span>{/if}</div>
              <div class="t-titel"><i class="fa-solid fa-list"></i>{t("aufnahmenAnsicht.telefon.titel", { n: a.titelzahl })} · {zeit(a.dauer)}</div></div>
            <span class="tf-aktionen">{#if a.status !== "laeuft"}<button class="rund" type="button" aria-label={t("aufnahmenAnsicht.hoeren")} title={t("aufnahmenAnsicht.hoeren")}
                    onclick={(e) => { e.stopPropagation(); void hoeren(a); }}><i class="fa-solid {spielt ? 'fa-volume-high' : 'fa-play'}"></i></button>{/if}</span>
          </div>
        {/each}
        <Nachladen geladen={liste.aufnahmen.length} gesamt={liste.gesamt} laedt={liste.laedt} fehler={liste.fehler} onmehr={() => void liste.nachladen()}
                   einheit={t("aufnahmenAnsicht.geladen")} />
      {/if}
    </div>
  {/if}
</div>
