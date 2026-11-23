<script lang="ts">
  // Reiter Werbefilter (HELF-256, RAD-128): oben der Stand als Gerät, darunter die gefundenen Spots zum Anhören und
  // Entscheiden (Listen mit eigener Höhe, die beim Rollen nachladen, nie Seiten), der Lernlauf mit Zeitfenster, laufenden Sendern und letzten Nächten, zuletzt die Sender mit ihrem Grund.
  import { onMount } from "svelte";
  import { Nachladen } from "appkern-oberflaeche";
  import { t } from "../../../lib/i18n.svelte.js";
  import { zahl } from "../../../lib/radio/anzeige";
  import type { BandInhalt } from "../../../lib/radio/bedienung.svelte";
  import { wann } from "../../../lib/radio/werbende.svelte";
  import { gehoert, Stueckliste, werbefilter, type Fach, type Filterstand, type Grund, type Lernsender, type Lernstand, type Spotfund } from "../../../lib/radio/werbefilter.svelte";
  import type { Zeile as ZeileTyp } from "../../../lib/einstellungen";
  import Zeile from "../../einstellungen/Zeile.svelte";
  import Schalter from "../../bausteine/Schalter.svelte";
  import Band from "../Band.svelte";
  import Logo from "../Logo.svelte";

  const TAKT_MS = 5000, SOFORT_MIN = 60;
  const FAECHER: Fach[] = ["pruefen", "wirkt", "verworfen"];
  const GRUND: Record<Grund, string> = { gehoert: "fa-headphones", favorit: "fa-star", aehnlich: "fa-wand-magic-sparkles", bekannt: "fa-earth-europe" };

  let stand = $state<Filterstand | null>(null);
  let faecher = $state<Record<Fach, number> | null>(null);
  let gewaehlt = $state<Fach>("pruefen");
  let spielt = $state("");
  let band = $state<BandInhalt | null>(null);
  const ton = typeof Audio === "undefined" ? null : new Audio();

  const lern = $derived(stand?.lernlauf ?? null);
  const spots = new Stueckliste<Spotfund>(async (ab, anzahl) => {
    const f = gewaehlt;
    const r = await werbefilter.spots(f, ab, anzahl);
    faecher = r.faecher;
    return { eintraege: r.signaturen, gesamt: r.faecher[f] };
  }, (s) => s.id);
  const sender = new Stueckliste<Lernsender>(async (ab, anzahl) => {
    const r = await werbefilter.sender(ab, anzahl);
    return { eintraege: r.sender, gesamt: r.gesamt };
  }, (s) => s.quelle);
  const laufzeit = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

  const melden = (f: unknown) => { band = { symbol: "fa-triangle-exclamation", art: "fehler", text: (f as Error).message }; };
  const versuchen = async (tun: () => Promise<void>) => { try { await tun(); } catch (f) { melden(f); } };
  const lernSetzen = (l: Lernstand) => { if (stand) stand = { ...stand, lernlauf: l }; };

  async function laden() {
    stand = await werbefilter.stand();
    if (stand.erreichbar) await Promise.all([spots.neu(), sender.neu()]);
  }
  /** solange gehört wird: der Stand, und die Listen neu, wenn ein Sender fertig ausgewertet ist */
  async function nachsehen() {
    const fertig = () => lern?.laeufe.reduce((n, l) => n + l.sender + l.fehler, 0);
    const vorher = fertig();
    stand = await werbefilter.stand();
    if (stand.erreichbar && fertig() !== vorher) await Promise.all([spots.neu(), sender.neu()]);
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
  const urteilen = (s: Spotfund, u: "offen" | "bestaetigt" | "verworfen") => versuchen(async () => { await werbefilter.beurteilen(s.id, u); await spots.neu(); });
  const auchDort = (s: Spotfund) => versuchen(async () => {
    for (const q of s.quellen.filter((x) => x.stand === "vorschlag")) await werbefilter.quelle(s.id, q.quelle, "wirkt");
    await spots.neu();
  });
  const nurNeueSender = (s: Spotfund) => s.urteil !== "offen" || s.herkunft !== "lernlauf";

  const titel = (s: Spotfund) => s.werbender || t(`radio.werbefilter.klingt_${s.einschaetzung || "unklar"}`);
  const orte = (s: Spotfund) => !s.quellen.length ? s.quelle : s.quellen.slice(0, 2).map((q) => q.name).join(", ") + (s.quellen.length > 2 ? ` +${zahl(s.quellen.length - 2)}` : "");
  const zeitfenster = $derived<ZeileTyp>({ schluessel: "lernlauf", titel: t("radio.werbefilter.zeitfenster"), beschreibung: "", art: "zeitraum",
    geltung: "alle", wert: [lern?.von ?? "", lern?.bis ?? ""], optionen: [], schritt: 15, einheit: "", fest: false, geaendert: false, angebot: false });
</script>

<section class="rh-reiter">
  {#if stand && !stand.erreichbar}
    <p class="hinweis-band"><i class="fa-solid fa-plug-circle-xmark"></i><span>{stand.eingerichtet ? t("radio.werbefilter.fort") : t("radio.werbefilter.nichtEingerichtet")}</span></p>
  {/if}
  <div class="ak-geraet rh-bestand" data-bauform="inspektor">
    <span class="ak-schraube lo" style="--dreh:14deg"></span><span class="ak-schraube ro" style="--dreh:58deg"></span><span class="ak-schraube lu" style="--dreh:-24deg"></span><span class="ak-schraube ru" style="--dreh:39deg"></span>
    <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="weiss" text={lern ? zahl(Math.round(lern.stunden)) : "-----"}></ak-segmente><span class="ak-etikett">{t("radio.werbefilter.stundenGehoert")}</span></div>
    <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="bernstein" text={faecher ? zahl(faecher.pruefen) : "-----"}></ak-segmente><span class="ak-etikett">{t("radio.werbefilter.fach_pruefen")}</span></div>
    <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="gruen" text={faecher ? zahl(faecher.wirkt) : "-----"}></ak-segmente><span class="ak-etikett">{t("radio.werbefilter.fach_wirkt")}</span></div>
    <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="weiss" text={lern ? zahl(lern.sender) : "-----"}></ak-segmente><span class="ak-etikett">{t("radio.werbefilter.sender")}</span></div>
  </div>

  {#if lern}
    <div class="karte rh-karte">
      <div class="rh-karte-kopf"><h2><i class="fa-solid fa-rectangle-ad"></i>{t("radio.werbefilter.spots")}</h2></div>
      <div class="segment" role="group" aria-label={t("radio.werbefilter.spots")}>
        {#each FAECHER as f (f)}
          <button type="button" class:aktiv={gewaehlt === f} aria-pressed={gewaehlt === f} onclick={() => { gewaehlt = f; void spots.wechsel(); }}>{t(`radio.werbefilter.fach_${f}`)} <span class="rh-zahl">{faecher ? zahl(faecher[f]) : ""}</span></button>
        {/each}
      </div>
      <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
      <div class="rh-a-liste rh-spots rh-rollfeld" role="list" tabindex="0" aria-label={t("radio.werbefilter.spots")}>
        {#each spots.eintraege as s (s.id)}
          <div class="rh-a-zeile rh-spot" role="listitem">
            <button class="rund" type="button" title={t("radio.werbefilter.anhoeren")} aria-label="{titel(s)}: {t('radio.werbefilter.anhoeren')}" aria-pressed={spielt === s.id} onclick={() => anhoeren(s)}>
              <i class="fa-solid {spielt === s.id ? 'fa-stop' : 'fa-play'}"></i></button>
            <span class="name"><b>{titel(s)}</b>{#if s.text}<span class="rh-spot-text" title={s.text}>{s.text}</span>{/if}</span>
            <span class="grund"><i class="fa-solid fa-tower-broadcast"></i><span title={s.quellen.map((q) => `${q.name} (${q.treffer})`).join(", ")}>{orte(s)}</span></span>
            <span class="stimmen">{laufzeit(s.dauer_s)} · {t("radio.werbungMal", { n: zahl(Math.max(1, gehoert(s))) })}</span>
            <span class="rh-a-knoepfe">
              {#if gewaehlt === "pruefen"}
                {#if nurNeueSender(s)}
                  <button class="knopf" type="button" title={t("radio.werbefilter.auchDortHilfe")} onclick={() => auchDort(s)}><i class="fa-solid fa-check"></i>{t("radio.werbefilter.auchDort")}</button>
                {:else}
                  <button class="knopf" type="button" title={t("radio.werbefilter.filternHilfe")} onclick={() => urteilen(s, "bestaetigt")}><i class="fa-solid fa-check"></i>{t("radio.werbefilter.filtern")}</button>
                {/if}
                <button class="knopf" type="button" title={t("radio.werbefilter.verwerfenHilfe")} onclick={() => urteilen(s, "verworfen")}><i class="fa-solid fa-xmark"></i>{t("radio.werbefilter.verwerfen")}</button>
              {:else if gewaehlt === "wirkt"}
                <button class="knopf" type="button" title={t("radio.werbefilter.verwerfenHilfe")} onclick={() => urteilen(s, "verworfen")}><i class="fa-solid fa-xmark"></i>{t("radio.werbefilter.verwerfen")}</button>
              {:else}
                <button class="knopf" type="button" onclick={() => urteilen(s, "offen")}><i class="fa-solid fa-rotate-left"></i>{t("radio.werbefilter.zurueck")}</button>
              {/if}
            </span>
          </div>
        {:else}
          {#if spots.gesamt === 0}<p class="rh-still">{t(`radio.werbefilter.leer_${gewaehlt}`)}</p>{/if}
        {/each}
        {@render ende(spots)}
      </div>
    </div>

    <div class="karte rh-karte">
      <div class="rh-karte-kopf"><h2><i class="fa-solid fa-moon"></i>{t("radio.werbefilter.lernlauf")}</h2><span class="rh-still">{t("radio.werbefilter.lernlaufHilfe")}</span></div>
      <div class="rh-schalter-zeile"><span><b>{t("radio.werbefilter.jedeNacht")}</b>{#if lern.naechste.length}<span>{t("radio.werbefilter.naechste", { namen: lern.naechste.slice(0, 4).join(", ") })}</span>{/if}</span>
        <Schalter an={lern.an} text={lern.an ? t("einstellungen.an") : t("einstellungen.aus")} hilfe={t("radio.werbefilter.jedeNacht")} onwechsel={(an) => versuchen(async () => lernSetzen(await werbefilter.stellen({ an })))} /></div>
      <Zeile zeile={zeitfenster} onwert={(w) => { const [von, bis] = w as [string, string]; if (von && bis) void versuchen(async () => lernSetzen(await werbefilter.stellen({ von, bis }))); }} />
      <div class="rh-knoepfe">
        {#if lern.sofort_bis}
          <button class="knopf" type="button" onclick={() => versuchen(async () => lernSetzen(await werbefilter.jetzt(0)))}><i class="fa-solid fa-stop"></i>{t("radio.einst.stopp")}</button>
        {:else}
          <button class="knopf" type="button" title={t("radio.werbefilter.jetztHilfe")} onclick={() => versuchen(async () => lernSetzen(await werbefilter.jetzt(SOFORT_MIN)))}><i class="fa-solid fa-play"></i>{t("radio.werbefilter.jetzt")}</button>
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
            <dt>{wann(l.begonnen)}</dt><dd>{t("radio.werbefilter.lauf", { s: zahl(l.sender), h: zahl(Math.round(l.stunden)), n: zahl(l.neu), b: zahl(l.bekannte) })}</dd>
          {/each}
        </dl>
      {/if}
    </div>

    <div class="karte rh-karte">
      <div class="rh-karte-kopf"><h2><i class="fa-solid fa-tower-broadcast"></i>{t("radio.werbefilter.senderTitel")}</h2><span class="rh-still">{t("radio.werbefilter.senderHilfe")}</span></div>
      <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
      <div class="rh-a-liste rh-rollfeld" role="list" tabindex="0" aria-label={t("radio.werbefilter.senderTitel")}>
        {#each sender.eintraege as s (s.quelle)}
          <div class="rh-a-zeile" class:frei={s.aus} role="listitem"><Logo uuid={s.quelle} name={s.name} logo="" klein />
            <span class="name"><b>{s.name}</b><span>{s.fehler ? s.fehler : s.zuletzt ? t("radio.werbefilter.zuletzt", { wann: wann(s.zuletzt), h: zahl(Math.round(s.stunden * 10) / 10) }) : t("radio.werbefilter.nochNie")}</span></span>
            <span class="grund"><i class="fa-solid {GRUND[s.grund]}"></i><span>{t(`radio.werbefilter.grund_${s.grund}`)}</span></span>
            <span class="stimmen">{#if s.kandidaten + s.bekannte}{t("radio.werbefilter.funde", { n: zahl(s.kandidaten + s.bekannte) })}{/if}</span>
            <span class="rh-a-knoepfe"><Schalter an={!s.aus} text={t("radio.werbefilter.hoeren")} symbol="fa-headphones" onwechsel={(an) => versuchen(async () => { sender.ersetzen(await werbefilter.ausnehmen(s.quelle, !an)); })} /></span></div>
        {/each}
        {@render ende(sender)}
      </div>
    </div>
  {/if}
</section>

{#snippet ende(liste: Stueckliste<Spotfund> | Stueckliste<Lernsender>)}
  {#if liste.fehler || liste.laedt || (liste.gesamt ?? 0) > liste.eintraege.length}
    <Nachladen geladen={liste.eintraege.length} gesamt={liste.gesamt} laedt={liste.laedt} fehler={liste.fehler} onmehr={() => void liste.mehr()} />
  {/if}
{/snippet}
<Band bind:inhalt={band} />
