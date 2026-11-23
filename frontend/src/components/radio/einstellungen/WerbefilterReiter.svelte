<script lang="ts">
  // Reiter Werbefilter (HELF-256, RAD-128): oben der Stand als Gerät, darunter die gefundenen Spots zum Anhören und
  // Entscheiden, der Lernlauf mit Zeitfenster, laufenden Sendern und letzten Nächten, zuletzt die Sender mit ihrem Grund.
  import { onMount } from "svelte";
  import { t } from "../../../lib/i18n.svelte.js";
  import { zahl } from "../../../lib/radio/anzeige";
  import type { BandInhalt } from "../../../lib/radio/bedienung.svelte";
  import { wann } from "../../../lib/radio/werbende.svelte";
  import { fach, geordnet, gehoert, werbefilter, type Fach, type Filterstand, type Grund, type Lernsender, type Lernstand, type Spotfund } from "../../../lib/radio/werbefilter";
  import type { Zeile as ZeileTyp } from "../../../lib/einstellungen";
  import Zeile from "../../einstellungen/Zeile.svelte";
  import Schalter from "../../bausteine/Schalter.svelte";
  import Band from "../Band.svelte";
  import Logo from "../Logo.svelte";

  const TAKT_MS = 5000, JE_SEITE = 12, SOFORT_MIN = 60;
  const FAECHER: Fach[] = ["pruefen", "wirkt", "verworfen"];
  const GRUND: Record<Grund, string> = { gehoert: "fa-headphones", favorit: "fa-star", aehnlich: "fa-wand-magic-sparkles", bekannt: "fa-earth-europe" };

  let stand = $state<Filterstand | null>(null);
  let spots = $state<Spotfund[]>([]);
  let sender = $state<Lernsender[]>([]);
  let gewaehlt = $state<Fach>("pruefen");
  let spotseite = $state(0);
  let senderseite = $state(0);
  let spielt = $state("");
  let band = $state<BandInhalt | null>(null);
  const ton = typeof Audio === "undefined" ? null : new Audio();

  const lern = $derived(stand?.lernlauf ?? null);
  const inFach = $derived(geordnet(spots, gewaehlt));
  const anzahl = (f: Fach) => spots.filter((s) => fach(s) === f).length;
  const dabei = $derived(sender.filter((s) => s.dabei));
  const teil = <T,>(liste: T[], seite: number) => liste.slice(seite * JE_SEITE, (seite + 1) * JE_SEITE);
  const seiten = (liste: unknown[]) => Math.max(1, Math.ceil(liste.length / JE_SEITE));
  const laufzeit = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

  const melden = (f: unknown) => { band = { symbol: "fa-triangle-exclamation", art: "fehler", text: (f as Error).message }; };
  const versuchen = async (tun: () => Promise<void>) => { try { await tun(); } catch (f) { melden(f); } };
  const lernSetzen = (l: Lernstand) => { if (stand) stand = { ...stand, lernlauf: l }; };

  async function laden() {
    stand = await werbefilter.stand();
    if (stand.erreichbar) [spots, sender] = await Promise.all([werbefilter.spots(), werbefilter.sender()]);
  }
  /** solange gehört wird: der Stand, und die Listen neu, wenn ein Sender fertig ausgewertet ist */
  async function nachsehen() {
    const fertig = () => lern?.laeufe.reduce((n, l) => n + l.sender + l.fehler, 0);
    const vorher = fertig();
    stand = await werbefilter.stand();
    if (stand.erreichbar && fertig() !== vorher) [spots, sender] = await Promise.all([werbefilter.spots(), werbefilter.sender()]);
  }
  onMount(() => {
    void versuchen(laden);
    const uhr = setInterval(() => { if (!document.hidden && lern?.laeuft) void nachsehen().catch(() => undefined); }, TAKT_MS);
    if (ton) ton.onended = ton.onerror = () => (spielt = "");
    return () => { clearInterval(uhr); ton?.pause(); };
  });

  function anhoeren(s: Spotfund) {
    if (!ton) return;
    if (spielt === s.id) { ton.pause(); spielt = ""; return; }
    ton.src = werbefilter.tonadresse(s.id);
    spielt = s.id;
    void ton.play().catch(() => (spielt = ""));
  }
  const ersetzen = (neu: Spotfund) => { spots = spots.map((s) => (s.id === neu.id ? neu : s)); };
  const urteilen = (s: Spotfund, u: "offen" | "bestaetigt" | "verworfen") => versuchen(async () => ersetzen(await werbefilter.beurteilen(s.id, u)));
  const auchDort = (s: Spotfund) => versuchen(async () => {
    for (const q of s.quellen.filter((x) => x.stand === "vorschlag")) ersetzen(await werbefilter.quelle(s.id, q.quelle, "wirkt"));
  });
  const nurNeueSender = (s: Spotfund) => s.urteil !== "offen" || s.herkunft !== "lernlauf";

  const titel = (s: Spotfund) => s.werbender || t(`radio.filter.klingt_${s.einschaetzung || "unklar"}`);
  const orte = (s: Spotfund) => s.quellen.slice(0, 2).map((q) => q.name).join(", ") + (s.quellen.length > 2 ? ` +${zahl(s.quellen.length - 2)}` : "");
  const zeitfenster = $derived<ZeileTyp>({ schluessel: "lernlauf", titel: t("radio.filter.zeitfenster"), beschreibung: "", art: "zeitraum",
    geltung: "alle", wert: [lern?.von ?? "", lern?.bis ?? ""], optionen: [], schritt: 15, einheit: "", fest: false, geaendert: false, angebot: false });
</script>

<section class="rh-reiter">
  {#if stand && !stand.erreichbar}
    <p class="hinweis-band"><i class="fa-solid fa-plug-circle-xmark"></i><span>{stand.eingerichtet ? t("radio.filter.fort") : t("radio.filter.nichtEingerichtet")}</span></p>
  {/if}
  <div class="ak-geraet rh-bestand" data-bauform="inspektor">
    <span class="ak-schraube lo" style="--dreh:14deg"></span><span class="ak-schraube ro" style="--dreh:58deg"></span><span class="ak-schraube lu" style="--dreh:-24deg"></span><span class="ak-schraube ru" style="--dreh:39deg"></span>
    <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="weiss" text={lern ? zahl(Math.round(lern.stunden)) : "-----"}></ak-segmente><span class="ak-etikett">{t("radio.filter.stundenGehoert")}</span></div>
    <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="bernstein" text={stand?.filter ? zahl(anzahl("pruefen")) : "-----"}></ak-segmente><span class="ak-etikett">{t("radio.filter.fach_pruefen")}</span></div>
    <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="gruen" text={stand?.filter ? zahl(anzahl("wirkt")) : "-----"}></ak-segmente><span class="ak-etikett">{t("radio.filter.fach_wirkt")}</span></div>
    <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="weiss" text={lern ? zahl(lern.sender) : "-----"}></ak-segmente><span class="ak-etikett">{t("radio.filter.sender")}</span></div>
  </div>

  {#if lern}
    <div class="karte rh-karte">
      <div class="rh-karte-kopf"><h2><i class="fa-solid fa-rectangle-ad"></i>{t("radio.filter.spots")}</h2></div>
      <div class="segment" role="group" aria-label={t("radio.filter.spots")}>
        {#each FAECHER as f (f)}
          <button type="button" class:aktiv={gewaehlt === f} aria-pressed={gewaehlt === f} onclick={() => { gewaehlt = f; spotseite = 0; }}>{t(`radio.filter.fach_${f}`)} <span class="rh-zahl">{zahl(anzahl(f))}</span></button>
        {/each}
      </div>
      <div class="rh-a-liste rh-spots" role="list">
        {#each teil(inFach, spotseite) as s (s.id)}
          <div class="rh-a-zeile rh-spot" role="listitem">
            <button class="rund" type="button" title={t("radio.filter.anhoeren")} aria-label="{titel(s)}: {t('radio.filter.anhoeren')}" aria-pressed={spielt === s.id} onclick={() => anhoeren(s)}>
              <i class="fa-solid {spielt === s.id ? 'fa-stop' : 'fa-play'}"></i></button>
            <span class="name"><b>{titel(s)}</b>{#if s.text}<span class="rh-spot-text" title={s.text}>{s.text}</span>{/if}</span>
            <span class="grund"><i class="fa-solid fa-tower-broadcast"></i><span title={s.quellen.map((q) => `${q.name} (${q.treffer})`).join(", ")}>{orte(s)}</span></span>
            <span class="stimmen">{laufzeit(s.dauer_s)} · {t("radio.werbungMal", { n: zahl(Math.max(1, gehoert(s))) })}</span>
            <span class="rh-a-knoepfe">
              {#if gewaehlt === "pruefen"}
                {#if nurNeueSender(s)}
                  <button class="knopf" type="button" title={t("radio.filter.auchDortHilfe")} onclick={() => auchDort(s)}><i class="fa-solid fa-check"></i>{t("radio.filter.auchDort")}</button>
                {:else}
                  <button class="knopf" type="button" title={t("radio.filter.filternHilfe")} onclick={() => urteilen(s, "bestaetigt")}><i class="fa-solid fa-check"></i>{t("radio.filter.filtern")}</button>
                {/if}
                <button class="knopf" type="button" title={t("radio.filter.verwerfenHilfe")} onclick={() => urteilen(s, "verworfen")}><i class="fa-solid fa-xmark"></i>{t("radio.filter.verwerfen")}</button>
              {:else if gewaehlt === "wirkt"}
                <button class="knopf" type="button" title={t("radio.filter.verwerfenHilfe")} onclick={() => urteilen(s, "verworfen")}><i class="fa-solid fa-xmark"></i>{t("radio.filter.verwerfen")}</button>
              {:else}
                <button class="knopf" type="button" onclick={() => urteilen(s, "offen")}><i class="fa-solid fa-rotate-left"></i>{t("radio.filter.zurueck")}</button>
              {/if}
            </span>
          </div>
        {:else}
          <p class="rh-still">{t(`radio.filter.leer_${gewaehlt}`)}</p>
        {/each}
      </div>
      {@render blaettern(inFach, spotseite, (n) => (spotseite = n))}
    </div>

    <div class="karte rh-karte">
      <div class="rh-karte-kopf"><h2><i class="fa-solid fa-moon"></i>{t("radio.filter.lernlauf")}</h2><span class="rh-still">{t("radio.filter.lernlaufHilfe")}</span></div>
      <div class="rh-schalter-zeile"><span><b>{t("radio.filter.jedeNacht")}</b>{#if lern.naechste.length}<span>{t("radio.filter.naechste", { namen: lern.naechste.slice(0, 4).join(", ") })}</span>{/if}</span>
        <Schalter an={lern.an} text={lern.an ? t("einstellungen.an") : t("einstellungen.aus")} hilfe={t("radio.filter.jedeNacht")} onwechsel={(an) => versuchen(async () => lernSetzen(await werbefilter.stellen({ an })))} /></div>
      <Zeile zeile={zeitfenster} onwert={(w) => { const [von, bis] = w as [string, string]; if (von && bis) void versuchen(async () => lernSetzen(await werbefilter.stellen({ von, bis }))); }} />
      <div class="rh-knoepfe">
        {#if lern.sofort_bis}
          <button class="knopf" type="button" onclick={() => versuchen(async () => lernSetzen(await werbefilter.jetzt(0)))}><i class="fa-solid fa-stop"></i>{t("radio.einst.stopp")}</button>
        {:else}
          <button class="knopf" type="button" title={t("radio.filter.jetztHilfe")} onclick={() => versuchen(async () => lernSetzen(await werbefilter.jetzt(SOFORT_MIN)))}><i class="fa-solid fa-play"></i>{t("radio.filter.jetzt")}</button>
        {/if}
      </div>
      {#if lern.laufend.length}
        <div class="rh-a-liste rh-laufend" role="list">
          {#each lern.laufend as l (l.quelle)}
            <div class="rh-a-zeile" role="listitem"><Logo uuid={l.quelle} name={l.name} logo="" klein />
              <span class="name"><b>{l.name}</b></span><span class="grund"><i class="fa-solid fa-music"></i><span>{l.titel || l.schritt}</span></span>
              <span class="stimmen">{laufzeit(l.sekunden)}</span></div>
          {/each}
        </div>
      {/if}
      {#if lern.laeufe.length}
        <dl class="rh-werte">
          {#each lern.laeufe.slice(0, 5) as l (l.id)}
            <dt>{wann(l.begonnen)}</dt><dd>{t("radio.filter.lauf", { s: zahl(l.sender), h: zahl(Math.round(l.stunden)), n: zahl(l.neu), b: zahl(l.bekannte) })}</dd>
          {/each}
        </dl>
      {/if}
    </div>

    <div class="karte rh-karte">
      <div class="rh-karte-kopf"><h2><i class="fa-solid fa-tower-broadcast"></i>{t("radio.filter.senderTitel")}</h2><span class="rh-still">{t("radio.filter.senderHilfe")}</span></div>
      <div class="rh-a-liste" role="list">
        {#each teil(dabei, senderseite) as s (s.quelle)}
          <div class="rh-a-zeile" class:frei={s.aus} role="listitem"><Logo uuid={s.quelle} name={s.name} logo="" klein />
            <span class="name"><b>{s.name}</b><span>{s.fehler ? s.fehler : s.zuletzt ? t("radio.filter.zuletzt", { wann: wann(s.zuletzt), h: zahl(Math.round(s.stunden * 10) / 10) }) : t("radio.filter.nochNie")}</span></span>
            <span class="grund"><i class="fa-solid {GRUND[s.grund]}"></i><span>{t(`radio.filter.grund_${s.grund}`)}</span></span>
            <span class="stimmen">{#if s.kandidaten + s.bekannte}{t("radio.filter.funde", { n: zahl(s.kandidaten + s.bekannte) })}{/if}</span>
            <span class="rh-a-knoepfe"><Schalter an={!s.aus} text={t("radio.filter.hoeren")} symbol="fa-headphones" onwechsel={(an) => versuchen(async () => { sender = await werbefilter.ausnehmen(s.quelle, !an); })} /></span></div>
        {/each}
      </div>
      {@render blaettern(dabei, senderseite, (n) => (senderseite = n))}
    </div>
  {/if}
</section>

{#snippet blaettern(liste: unknown[], seite: number, setzen: (n: number) => void)}
  {#if seiten(liste) > 1}
    <div class="seitenzeile rh-seiten">
      <button class="knopf" type="button" disabled={seite === 0} onclick={() => setzen(seite - 1)}><i class="fa-solid fa-chevron-left"></i>{t("radio.einst.zurueck")}</button>
      <span class="rh-zahl">{t("radio.einst.seiteVon", { n: zahl(seite + 1), m: zahl(seiten(liste)) })}</span>
      <button class="knopf" type="button" disabled={seite >= seiten(liste) - 1} onclick={() => setzen(seite + 1)}>{t("radio.einst.weiter")}<i class="fa-solid fa-chevron-right"></i></button>
    </div>
  {/if}
{/snippet}
<Band bind:inhalt={band} />
