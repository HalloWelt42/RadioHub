<script lang="ts">
  // Reiter Werbeerkennung (bisher Einstellungen > Radio > Sender): Stand als Gerät, Prüfung aller noch nicht geprüften
  // sichtbaren Sender mit Fortschritt und Stopp, Verdächtige einzeln oder alle entscheiden, Einstellungen der Erkennung.
  // "Ausblenden" ist eine eigene Werbeentscheidung (blendet aus, Entscheidung 32), "Keine Werbung" nimmt den Verdacht zurück.
  // Dazu Werbung in den Sendedaten (RAD-33): überspringen für alle Sender und die Sender, die Werbung ankündigen, je mit
  // ihrem Schalter.
  import { onMount } from "svelte";
  import type { Schieber } from "appkern-oberflaeche/instrumente";
  import { t } from "../../../lib/i18n.svelte.js";
  import { werbeerkennung } from "../../../lib/radio";
  import { zahl } from "../../../lib/radio/anzeige";
  import type { BandInhalt } from "../../../lib/radio/bedienung.svelte";
  import type { ScanStand, Verdaechtiger, WerbeEinstellungen, WerbeStand } from "../../../lib/radio/werbeerkennung";
  import Band from "../Band.svelte";
  import Schalter from "../Schalter.svelte";
  import { haeufigste, sendewerbung } from "../../../lib/radio/sendewerbung";
  import { wann, werbende } from "../../../lib/radio/werbende.svelte";

  const RUNDE = 50;
  const SCHWELLEN = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1];
  let stand = $state<WerbeStand | null>(null);
  let verdaechtige = $state<Verdaechtiger[] | null>(null);
  let einst = $state<WerbeEinstellungen | null>(null);
  let scan = $state<ScanStand | null>(null);
  let abbruch: AbortController | null = null;
  let arbeitet = $state(false);
  let band = $state<BandInhalt | null>(null);
  let schwelle = $state<Schieber>();

  async function standLaden() {
    stand = await werbeerkennung.stand().catch(() => null);
    if (einst) verdaechtige = await werbeerkennung.verdaechtige(einst.schwelle).catch(() => []);
  }
  // Werbung in den Sendedaten: Einstellung für alle, Liste der werbenden Sender (aufgeklappt)
  let alleAn = $state<boolean | null>(null);
  let listeOffen = $state(false);
  const werbendeListe = $derived([...werbende.sender.values()]);
  // in der Liste die häufigsten zuerst; lange Listen rollen in sich und zeigen höchstens die häufigsten
  const gezeigt = $derived(haeufigste([...werbendeListe].sort((a, b) => b.spots - a.spots || (b.zuletzt ?? "").localeCompare(a.zuletzt ?? ""))));
  const spotsZusammen = $derived(werbendeListe.reduce((n, s) => n + s.spots, 0));
  const ausgenommen = $derived(werbendeListe.filter((s) => s.ausgenommen).length);
  async function alleSchalten(an: boolean) {
    try {
      await sendewerbung.alleSetzen(an);
      alleAn = an;
      await werbende.laden(true);
    } catch (f) {
      band = { symbol: "fa-triangle-exclamation", art: "fehler", text: (f as Error).message };
    }
  }
  async function senderSchalten(uuid: string, an: boolean) {
    try {
      werbende.merken(await sendewerbung.setzen(uuid, an));
    } catch (f) {
      band = { symbol: "fa-triangle-exclamation", art: "fehler", text: (f as Error).message };
    }
  }

  onMount(() => {
    void sendewerbung.alle().then((an) => (alleAn = an)).catch(() => (alleAn = null));
    void werbende.laden(true);
    void werbeerkennung.einstellungen().then((e) => { einst = e; return standLaden(); });
    return () => abbruch?.abort();
  });

  async function pruefen() {
    abbruch = new AbortController();
    let geprueft = 0, neu = 0;
    try {
      for (;;) {
        scan = { geprueft: 0, gesamt: RUNDE, aktuell: "" };
        const r = await werbeerkennung.runde(RUNDE, (s) => (scan = { ...s, geprueft: geprueft + s.geprueft, gesamt: geprueft + (stand?.remaining ?? s.gesamt) }), abbruch.signal);
        geprueft += r.geprueft;
        neu += r.neuVerdaechtig;
        if (stand) stand = { ...stand, remaining: r.uebrig };
        if (!r.uebrig || !r.geprueft || abbruch.signal.aborted) break;
      }
    } catch (f) {
      if ((f as Error).name !== "AbortError") band = { symbol: "fa-triangle-exclamation", art: "fehler", text: (f as Error).message };
    } finally {
      scan = null;
      abbruch = null;
      band ??= { symbol: "fa-circle-check", art: "gut", text: t("radio.einst.scanFertig", { n: zahl(geprueft), v: zahl(neu) }) };
      await standLaden();
    }
  }

  async function entscheiden(liste: Verdaechtiger[], aktion: "block" | "allow") {
    arbeitet = true;
    let n = 0;
    for (const v of liste) {
      try { await werbeerkennung.entscheiden(v.uuid, aktion); n++; } catch { /* nächster */ }
    }
    arbeitet = false;
    band = { symbol: aktion === "block" ? "fa-eye-slash" : "fa-circle-check", art: "gut",
             text: aktion === "block" ? t("radio.einst.werbungGesperrt", { n }) : t("radio.einst.werbungErlaubt", { n }) };
    await standLaden();
  }

  async function aendern(teil: Partial<WerbeEinstellungen>) {
    if (!einst) return;
    einst = { ...einst, ...teil };
    await werbeerkennung.speichern(einst).catch((f: Error) => (band = { symbol: "fa-triangle-exclamation", art: "fehler", text: f.message }));
    if ("schwelle" in teil) verdaechtige = await werbeerkennung.verdaechtige(einst.schwelle).catch(() => []);
  }

  const art = (a: "url_check" | "header_check") => !!einst?.arten.includes(a);
  function artUmschalten(a: "url_check" | "header_check") {
    if (!einst) return;
    void aendern({ arten: art(a) ? einst.arten.filter((x) => x !== a) : [...einst.arten, a] });
  }
</script>

<section class="rh-reiter">
  {#if alleAn !== null}
    <div class="karte rh-karte">
      <div class="rh-karte-kopf"><h2><i class="fa-solid fa-rectangle-ad"></i>{t("radio.einst.sendedaten")}</h2></div>
      <p class="hinweis-band"><i class="fa-solid fa-circle-info"></i><span>{t("radio.einst.sendedatenHinweis")}</span></p>
      <div class="rh-schalter-zeile"><span><b>{t("radio.einst.werbungUeberspringen")}</b><span>{t("radio.einst.werbungUeberspringenHilfe")}</span></span>
        <button class="schalter" class:an={alleAn} type="button" aria-pressed={alleAn} aria-label={t("radio.einst.werbungUeberspringen")} onclick={() => alleSchalten(!alleAn)}></button></div>
      <div class="rh-schalter-zeile"><span><b>{t("radio.einst.senderMitWerbung")}</b>
          <span>{werbendeListe.length ? t(ausgenommen ? "radio.einst.senderMitWerbungZahlAus" : "radio.einst.senderMitWerbungZahl", { n: zahl(werbendeListe.length), s: zahl(spotsZusammen), a: zahl(ausgenommen) }) : t("radio.einst.senderMitWerbungKeine")}</span></span>
        {#if werbendeListe.length}<button class="knopf" type="button" aria-expanded={listeOffen} onclick={() => (listeOffen = !listeOffen)}>
          <i class="fa-solid {listeOffen ? 'fa-chevron-up' : 'fa-list'}"></i>{t("radio.einst.liste")}</button>{/if}</div>
      {#if listeOffen}
        <div class="rh-a-liste" class:rh-liste-rollt={gezeigt.rollt} role="list">
          {#each gezeigt.zeigen as s (s.uuid)}
            <div class="rh-a-zeile" role="listitem">
              <span class="name"><b>{s.name || s.uuid}</b></span>
              <span class="grund"><i class="fa-solid fa-rectangle-ad"></i><span>{t("radio.einst.spotsZuletzt", { n: zahl(s.spots), wann: wann(s.zuletzt) })}</span></span>
              <span class="stimmen"></span>
              <span class="rh-a-knoepfe"><Schalter an={!s.ausgenommen} farbe="bernstein" text={t("radio.werbungUeberspringen")} hilfe={t("radio.werbungUeberspringenHilfe")}
                onwechsel={(an) => senderSchalten(s.uuid, an)} /></span>
            </div>
          {/each}
        </div>
        {#if gezeigt.weggelassen}<p class="rh-still">{t("radio.listeHaeufigste", { n: zahl(gezeigt.zeigen.length), von: zahl(werbendeListe.length) })}</p>{/if}
      {/if}
    </div>
  {/if}
  <div class="ak-geraet rh-bestand" data-bauform="inspektor">
    <span class="ak-schraube lo" style="--dreh:14deg"></span><span class="ak-schraube ro" style="--dreh:58deg"></span><span class="ak-schraube lu" style="--dreh:-24deg"></span><span class="ak-schraube ru" style="--dreh:39deg"></span>
    <div class="rh-bestand-feld"><ak-segmente art="7" stellen="6" farbe="weiss" text={stand ? zahl(stand.total_checked) : "------"}></ak-segmente><span class="ak-etikett">{t("radio.einst.geprueft")}</span></div>
    <div class="rh-bestand-feld"><ak-segmente art="7" stellen="6" farbe="gruen" text={stand ? zahl(stand.clean) : "------"}></ak-segmente><span class="ak-etikett">{t("radio.einst.sauber")}</span></div>
    <div class="rh-bestand-feld"><ak-segmente art="7" stellen="6" farbe="bernstein" text={stand ? zahl(stand.suspect + stand.confirmed_ad) : "------"}></ak-segmente><span class="ak-etikett">{t("radio.einst.verdaechtig")}</span></div>
    <div class="rh-bestand-feld"><ak-segmente art="7" stellen="6" farbe="rot" text={stand ? zahl(stand.manual_blocked + stand.auto_blocked) : "------"}></ak-segmente><span class="ak-etikett">{t("radio.einst.werbungAus")}</span></div>
  </div>

  <div class="karte rh-karte">
    <div class="rh-karte-kopf"><h2><i class="fa-solid fa-magnifying-glass-chart"></i>{t("radio.einst.pruefung")}</h2>
      <span class="rh-still">{t("radio.einst.pruefungHilfe")}</span></div>
    <div class="rh-knoepfe">
      {#if scan}
        <button class="knopf" type="button" onclick={() => abbruch?.abort()}><i class="fa-solid fa-stop"></i>{t("radio.einst.stopp")}</button>
      {:else}
        <button class="knopf primaer" type="button" disabled={!einst?.an || !stand?.remaining} onclick={pruefen}><i class="fa-solid fa-play"></i>{t("radio.einst.allePruefen")}</button>
      {/if}
      {#if stand}<span class="rh-still">{t("radio.einst.nochNicht", { n: zahl(stand.remaining) })}</span>{/if}
    </div>
    {#if scan}
      <div class="rh-auftrag" aria-live="polite">
        <div class="balken"><span style="width:{scan.gesamt ? Math.min(100, (scan.geprueft / scan.gesamt) * 100) : 0}%"></span></div>
        <div class="rh-auftrag-zeile"><span>{scan.aktuell}</span><span class="rh-zahl">{zahl(scan.geprueft)} / {zahl(scan.gesamt)}</span></div>
      </div>
    {/if}
  </div>

  <div class="karte rh-karte">
    <div class="rh-karte-kopf"><h2><i class="fa-solid fa-triangle-exclamation"></i>{t("radio.einst.verdaechtige")}</h2>
      <span class="rh-still">{verdaechtige ? t("radio.einst.nVerdaechtige", { n: zahl(verdaechtige.length) }) : t("radio.laedt")}</span></div>
    {#if verdaechtige?.length}
      <div class="rh-knoepfe">
        <button class="knopf" type="button" disabled={arbeitet} onclick={() => entscheiden(verdaechtige ?? [], "block")}><i class="fa-solid fa-eye-slash"></i>{t("radio.einst.alleAusblenden")}</button>
        <button class="knopf" type="button" disabled={arbeitet} onclick={() => entscheiden(verdaechtige ?? [], "allow")}><i class="fa-solid fa-check"></i>{t("radio.einst.alleKeineWerbung")}</button>
      </div>
      <div class="rh-a-liste" role="list" style="margin-top:12px">
        {#each verdaechtige.slice(0, 100) as v (v.uuid)}
          <div class="rh-a-zeile" role="listitem">
            <span class="name"><b>{v.name}</b></span>
            <span class="grund"><i class="fa-solid fa-rectangle-ad"></i><span>{t("radio.einst.verdachtProzent", { n: Math.round(v.confidence * 100) })}</span></span>
            <span class="stimmen"></span>
            <span class="rh-a-knoepfe">
              <button class="knopf" type="button" disabled={arbeitet} onclick={() => entscheiden([v], "block")}>{t("radio.einst.ausblenden")}</button>
              <button class="knopf" type="button" disabled={arbeitet} onclick={() => entscheiden([v], "allow")}>{t("radio.einst.keineWerbung")}</button>
            </span>
          </div>
        {/each}
      </div>
      {#if verdaechtige.length > 100}<p class="rh-still">{t("radio.einst.ersteHundert", { n: zahl(verdaechtige.length) })}</p>{/if}
    {/if}
  </div>

  {#if einst}
    <div class="karte rh-karte">
      <div class="rh-karte-kopf"><h2><i class="fa-solid fa-sliders"></i>{t("radio.einst.erkennung")}</h2></div>
      <div class="rh-schalter-zeile"><span><b>{t("radio.einst.werbeerkennung")}</b><span>{t("radio.einst.werbeerkennungHilfe")}</span></span>
        <button class="schalter" class:an={einst.an} type="button" aria-pressed={einst.an} aria-label={t("radio.einst.werbeerkennung")} onclick={() => aendern({ an: !einst?.an })}></button></div>
      {#if einst.an}
        <div class="rh-schalter-zeile"><span><b>{t("radio.einst.adresspruefung")}</b><span>{t("radio.einst.adresspruefungHilfe")}</span></span>
          <button class="schalter" class:an={art("url_check")} type="button" aria-pressed={art("url_check")} aria-label={t("radio.einst.adresspruefung")} onclick={() => artUmschalten("url_check")}></button></div>
        <div class="rh-schalter-zeile"><span><b>{t("radio.einst.serverpruefung")}</b><span>{t("radio.einst.serverpruefungHilfe")}</span></span>
          <button class="schalter" class:an={art("header_check")} type="button" aria-pressed={art("header_check")} aria-label={t("radio.einst.serverpruefung")} onclick={() => artUmschalten("header_check")}></button></div>
        <div class="rh-schalter-zeile"><span><b>{t("radio.einst.schwelle")}</b><span>{t("radio.einst.schwelleHilfe")}</span></span><span></span>
          <ak-schieber bind:this={schwelle} art="leuchte" leuchte="bernstein" name={t("radio.einst.schwelle")} hilfe={t("radio.einst.schwelleHilfe")}
                       raster={SCHWELLEN.map((s) => `${Math.round(s * 100)} %`).join("|")} wert={Math.max(0, SCHWELLEN.findIndex((s) => s >= einst!.schwelle - 0.001))}
                       oninput={() => aendern({ schwelle: SCHWELLEN[schwelle?.wert ?? 4] ?? 0.8 })}></ak-schieber></div>
      {/if}
    </div>
  {/if}
</section>
<Band bind:inhalt={band} />
