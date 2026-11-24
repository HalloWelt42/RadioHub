<script lang="ts">
  // Aufnahmen am Telefon nach dem Entwurf (mockups/radio-filter/telefon-aufnahmen.html, RAD-17): die Liste mit Suche und
  // Ordnern als Chips, eine geöffnete Aufnahme mit Angaben, Laden, Ordner, Löschen (RAD-134) und ihren Titeln. Schneiden
  // gibt es am Rechner. Dieselben Bausteine wie das Radio am Telefon; Zustand und Adresse wie am Rechner.
  import { onMount, tick, untrack } from "svelte";
  import { Nachladen } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { actions, appState } from "../../lib/store.svelte.js";
  import { appPfad } from "../../lib/router.js";
  import { zahl } from "../../lib/radio/anzeige";
  import { Suchverlauf } from "../../lib/radio/suchverlauf";
  import { aufnahmeliste as liste, aufnahmequelle as quelle, aufnahmezustand as zustand, ordnerliste, reiheAus, imGange, vorzeitig, zumAendern, zumHoeren, type Aufnahme, type Spieleintrag, type Titel } from "../../lib/aufnahmen";
  import { datum, zeit } from "../../lib/aufnahmen/anzeige";
  import AufnahmeKopf from "../aufnahmen/AufnahmeKopf.svelte";
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

  // läuft eine Aufnahme oder wird eine fein geschnitten, holt die Liste nach
  const aendertSich = $derived((!!gewaehlt && imGange(gewaehlt)) || liste.aufnahmen.some(imGange));
  $effect(() => {
    if (!aendertSich) return;
    const uhr = setInterval(() => {
      void liste.laden(zustand.abfrage());
      if (gewaehlt && imGange(gewaehlt)) void holen(gewaehlt.id);
    }, 4000);
    return () => clearInterval(uhr);
  });

  async function holen(kennung: string) {
    try {
      const [a, x] = await Promise.all([quelle.aufnahme(kennung), quelle.titel(kennung)]);
      if (zustand.ansicht.aufnahme === kennung) { gewaehlt = a; titel = x; }
    } catch (f) {
      actions.showToast((f as Error).message, "error");
    }
  }

  const id = $derived(ansicht.quelle === "aufnahmen" ? ansicht.aufnahme : null);
  $effect(() => {
    const kennung = id;
    untrack(async () => {
      if (!kennung) { gewaehlt = null; titel = []; return; }
      gewaehlt = liste.aufnahmen.find((a) => a.id === kennung) ?? gewaehlt;
      await holen(kennung);
      // "In der Liste zeigen": steht der laufende Titel in dieser Aufnahme, rollt die Liste zu ihm
      await tick();
      const pfad = (appState.currentRecording as Spieleintrag | null)?.path;
      if (pfad) listeEl?.querySelector(`[data-pfad="${CSS.escape(pfad)}"]`)?.scrollIntoView({ block: "center" });
    });
  });
  let listeEl = $state<HTMLElement>();

  const jetzt = $derived(appState.isPlaying ? ((appState.currentRecording as Spieleintrag | null) ?? null) : null);
  async function hoeren(a: Aufnahme, ab?: Titel) {
    if (!zumHoeren(a)) return;
    if (appState.isRecording) { actions.showToast(t("aufnahmenAnsicht.erstBeenden"), "error"); return; }
    try {
      const reihe = a.id === gewaehlt?.id && titel.length ? titel : await quelle.titel(a.id);
      const eintraege = reiheAus(quelle, a, reihe);
      const start = eintraege[ab ? Math.max(0, reihe.findIndex((x) => x.id === ab.id)) : 0] ?? eintraege[0];
      if (jetzt?.path === start.path) { actions.stop(); return; }
      appState.recordingPlaylist = eintraege;
      void actions.playRecording(start);
    } catch (f) {
      actions.showToast((f as Error).message, "error");
    }
  }

  async function loeschen(a: Aufnahme) {
    if (jetzt?.session_id === a.id) actions.stop();
    try {
      await quelle.loeschen(a.id);
      liste.entfernen(a.id);
      zustand.gehen((v) => ({ ...v, aufnahme: null }));
      actions.showToast(t("aufnahmenAnsicht.geloescht"), "success");
      void ordnerliste.laden().catch(() => undefined);
    } catch (f) {
      actions.showToast((f as Error).message, "error");
    }
  }
  async function verschieben(a: Aufnahme, ordnerId: number | null) {
    try {
      await quelle.verschieben(a.id, ordnerId);
      if (gewaehlt?.id === a.id) gewaehlt = { ...gewaehlt, ordnerId };
      actions.showToast(t("aufnahmenAnsicht.verschoben", { name: ordnerName(ordnerId) }), "success");
      void ordnerliste.laden().catch(() => undefined);
      void liste.laden(zustand.abfrage());
    } catch (f) {
      actions.showToast((f as Error).message, "error");
    }
  }

  const ordnerName = (oid: number | null) => ordnerliste.name(oid) ?? t("aufnahmenAnsicht.ohneOrdner");
  const wahl = $derived([{ wert: "", name: t("aufnahmenAnsicht.alleAufnahmen") }, ...ordnerliste.ordner.map((o) => ({ wert: String(o.id), name: o.name })),
    { wert: "ohne", name: t("aufnahmenAnsicht.ohneOrdner") }]);
</script>

<div class="tf-radio tf-aufnahmen" bind:this={listeEl}>
  {#if gewaehlt && id}
    <div class="t-kopf-zurueck tf-a-kopf">
      <button class="rund" type="button" aria-label={t("aufnahmenAnsicht.telefon.zurueck")} title={t("aufnahmenAnsicht.telefon.zurueck")}
              onclick={() => zustand.gehen((a) => ({ ...a, aufnahme: null }))}><i class="fa-solid fa-chevron-left"></i></button>
      <div><b>{gewaehlt.sender}</b></div>
    </div>
    <div class="tf-liste">
      <div class="tf-a-detail">
        <AufnahmeKopf aufnahme={gewaehlt} ordner={ordnerliste.ordner} titelwechsel={0} zip={quelle.alsZip(gewaehlt.id)} eineDatei={quelle.alsEineDatei(gewaehlt.id)}
                      kannSchneiden={false} kannVerwalten={quelle.faehig.verwalten && zumAendern(gewaehlt)} onhoeren={() => void hoeren(gewaehlt!)}
                      onschneiden={() => undefined} onteilen={async () => undefined} onverschieben={(o) => verschieben(gewaehlt!, o)} onloeschen={() => loeschen(gewaehlt!)} />
      </div>
      {#each titel as x (x.id)}
        {@const spielt = jetzt?.path === x.pfad}
        <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
        <div class="tf-sender" class:spielt data-pfad={x.pfad} onclick={() => void hoeren(gewaehlt!, x)}>
          <span class="rh-a-nr">{String(x.nr).padStart(2, "0")}</span>
          <div><b>{x.titel}</b><div class="tf-meta"><span>{t("aufnahmenAnsicht.spalteAb")} {zeit(x.start)}</span><span>{zeit(x.dauer)}</span></div></div>
          <span class="tf-aktionen">
            <a class="rund" href={quelle.titelDatei(x.id)} download aria-label={t("aufnahmenAnsicht.laden")} title={t("aufnahmenAnsicht.laden")} onclick={(e) => e.stopPropagation()}><i class="fa-solid fa-download"></i></a>
            <button class="rund" type="button" aria-label={t("aufnahmenAnsicht.abHier")} title={t("aufnahmenAnsicht.abHier")}
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
                {:else if a.status === "schneidet"}<span class="rh-a-arbeit"><i class="fa-solid fa-spinner fa-spin"></i>{t("aufnahmenAnsicht.schneidet")}{#if a.arbeit}{" "}{a.arbeit.fertig}/{a.arbeit.gesamt}{/if}</span>
                {:else if vorzeitig(a)}<span class="rh-a-warn"><i class="fa-solid fa-triangle-exclamation"></i>{t(`aufnahmenAnsicht.${a.status}`)}</span>{/if}</div>
              <div class="t-titel"><i class="fa-solid fa-list"></i>{t("aufnahmenAnsicht.telefon.titel", { n: a.titelzahl })} · {zeit(a.dauer)}</div></div>
            <span class="tf-aktionen">{#if zumHoeren(a)}<button class="rund" type="button" aria-label={t("aufnahmenAnsicht.hoeren")} title={t("aufnahmenAnsicht.hoeren")}
                    onclick={(e) => { e.stopPropagation(); void hoeren(a); }}><i class="fa-solid {spielt ? 'fa-volume-high' : 'fa-play'}"></i></button>{/if}</span>
          </div>
        {/each}
        <Nachladen geladen={liste.aufnahmen.length} gesamt={liste.gesamt} laedt={liste.laedt} fehler={liste.fehler} onmehr={() => void liste.nachladen()}
                   einheit={t("aufnahmenAnsicht.geladen")} />
      {/if}
    </div>
  {/if}
</div>
