<script lang="ts">
  // Einstellungen (Entwurf mockups/radio-filter/einstellungen.html, RAD-11): links die Bereiche, oben Pfad und Reiter,
  // darunter das Rollfeld mit Karten. Was wo steht, sagt allein die Liste BEREICHE: Karten nennen ihre Felder (Server
  // oder "geraet:<name>"), Sonderteile ihren Baustein. Was eine Ausgabe nicht hat (Basic ohne Server, Reiter je nach
  // Senderquelle), fällt aus der Liste, nie als toter Regler. Adresse: /einstellungen/<bereich>/<reiter>; frühere
  // Bereiche und Reiter führen zum neuen Ort. Werte für alle Geräte warten in der Leiste Speichern.
  import { onMount, type Component } from "svelte";
  import { t } from "../../lib/i18n.svelte.js";
  import { actions, appState } from "../../lib/store.svelte.js";
  import { senderquelle } from "../../lib/radio";
  import { server } from "../../lib/einstellungen";
  import RegelnReiter from "../radio/einstellungen/RegelnReiter.svelte";
  import AusgeblendetReiter from "../radio/einstellungen/AusgeblendetReiter.svelte";
  import LaenderReiter from "../radio/einstellungen/LaenderReiter.svelte";
  import WerbungReiter from "../radio/einstellungen/WerbungReiter.svelte";
  import AbgleichReiter from "../radio/einstellungen/AbgleichReiter.svelte";
  import DateiReiter from "../radio/einstellungen/DateiReiter.svelte";
  import AblageTeil from "./AblageTeil.svelte";
  import AufnahmeordnerTeil from "./AufnahmeordnerTeil.svelte";
  import BausteineTeil from "./BausteineTeil.svelte";
  import Felder from "./Felder.svelte";
  import Karte from "./Karte.svelte";
  import KategorienTeil from "./KategorienTeil.svelte";
  import MusterTeil from "./MusterTeil.svelte";
  import OrtTeil from "./OrtTeil.svelte";
  import TastaturTeil from "./TastaturTeil.svelte";
  import UeberTeil from "./UeberTeil.svelte";

  let { bereichszahl }: { bereichszahl: number } = $props();

  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- Bausteine mit eigenen Props (etwa die Tastatur)
  type Teil = Component<any>;
  interface Kartenbaustein { karte: string; symbol: string; hinweis?: string; felder: string[]; teil?: Teil }
  type Baustein = Kartenbaustein | { teil: Teil; karte?: undefined };
  interface Reiter { id: string; symbol: string; titel: string; bausteine: Baustein[] }
  interface Bereich { id: string; symbol: string; reiter: Reiter[] }

  const S = server.amServer;
  const faehig = senderquelle.faehig;
  const r = (id: string, symbol: string, bausteine: Baustein[], titel = t(`einstellungen.reiter.${id}`)): Reiter => ({ id, symbol, titel, bausteine });
  const radio = (id: string, symbol: string, bausteine: Baustein[]) => r(id, symbol, bausteine, t(`radio.einst.reiter.${id}`));

  const BEREICHE: Bereich[] = $derived([
    { id: "allgemein", symbol: "fa-gear", reiter: [
      ...(S ? [r("bedienung", "fa-hand-pointer", [
        { karte: "sprache", symbol: "fa-language", felder: ["language"] },
        { karte: "fehlersuche", symbol: "fa-stethoscope", felder: ["geraet:entwickleransicht"] }])]
        : [r("bedienung", "fa-hand-pointer", [{ karte: "spracheGeraet", symbol: "fa-language", felder: ["geraet:sprache"] }])]),
      r("tastatur", "fa-keyboard", [{ teil: TastaturTeil }]),
      r("ueber", "fa-circle-info", [{ teil: UeberTeil }]),
    ] },
    { id: "darstellung", symbol: "fa-circle-half-stroke", reiter: [r("darstellung", "", [
      { karte: "aussehen", symbol: "fa-palette", hinweis: "aussehen", felder: ["geraet:vorlage", "geraet:thema", "geraet:schrift"] },
      { karte: "bildschirm", symbol: "fa-mobile-screen", felder: ["geraet:wachHalten"] }], t("einstellungen.bereich.darstellung"))] },
    { id: "radio", symbol: "fa-radio", reiter: [
      radio("regeln", "fa-filter-circle-xmark", [{ teil: RegelnReiter }]),
      radio("ausgeblendet", "fa-eye-slash", [{ teil: AusgeblendetReiter }]),
      radio("laender", "fa-earth-europe", [{ teil: LaenderReiter }]),
      ...(faehig.werbung ? [radio("werbung", "fa-rectangle-ad", [{ teil: WerbungReiter }])] : []),
      ...(faehig.abgleich ? [radio("abgleich", "fa-arrows-rotate", [{ teil: AbgleichReiter },
        { karte: "abgleich", symbol: "fa-moon", hinweis: "abgleich", felder: ["abgleich_uhrzeit"] }])] : []),
      ...(faehig.kategorien ? [radio("kategorien", "fa-folder", [{ teil: KategorienTeil }])] : []),
      ...(faehig.datei ? [radio("datei", "fa-box-archive", [{ teil: DateiReiter }])] : []),
    ] },
    ...(S ? [
      { id: "wiedergabe", symbol: "fa-clock-rotate-left", reiter: [r("zeitversatz", "", [
        { karte: "zeitversatz", symbol: "fa-clock-rotate-left", hinweis: "zeitversatz",
          felder: ["hls_min_bitrate", "hls_max_bitrate", "hls_sample_rate", "hls_puffer_minuten"] }],
        t("einstellungen.bereich.wiedergabe"))] },
      { id: "aufnahmen", symbol: "fa-circle-dot", reiter: [
        r("ordner", "fa-folder-tree", [{ teil: AufnahmeordnerTeil }]),
        r("titel", "fa-ban", [{ teil: MusterTeil }]),
        r("technik", "fa-sliders", [{ karte: "aufnahme", symbol: "fa-circle-dot", felder: ["recording_bitrate", "recording_debug_log"] }]),
      ] },
      { id: "podcasts", symbol: "fa-podcast", reiter: [r("abruf", "", [
        { karte: "abruf", symbol: "fa-rotate", felder: ["podcast_auto_refresh", "podcast_refresh_interval"] }], t("einstellungen.bereich.podcasts"))] },
    ] : []),
    { id: "wecker", symbol: "fa-bell", reiter: [
      r("zeitansage", "fa-comment-dots", [
        { karte: "zeitansage", symbol: "fa-comment-dots", hinweis: "zeitansage",
          felder: ["geraet:zeitansage", "geraet:zeitansageAbstand", "geraet:zeitansageZeitraum", "geraet:zeitansageWann", "geraet:zeitansageNachts"] },
        ...(S ? [{ karte: "stimme", symbol: "fa-microphone-lines", felder: ["zeitstimme", "zeitstimme_tempo"], teil: BausteineTeil }] : [])]),
      r("ort", "fa-location-dot", [{ teil: OrtTeil }]),
    ] },
    ...(S ? [
      { id: "ablage", symbol: "fa-hard-drive", reiter: [r("ablage", "", [{ teil: AblageTeil },
        { karte: "kellerwolke", symbol: "fa-cloud", felder: ["kellerwolke_wurzel", "kellerwolke_geduld_s"] }], t("einstellungen.bereich.ablage"))] },
      { id: "dienste", symbol: "fa-plug", reiter: [r("dienste", "", [
        { karte: "verzeichnisse", symbol: "fa-book-atlas", felder: ["service_radio_browser_servers", "service_itunes_search_url", "service_fyyd_search_url"] },
        { karte: "helfer", symbol: "fa-house-signal", felder: ["ortssuche_adresse", "vertonung_adresse"] },
        { karte: "zugang", symbol: "fa-shield-halved", felder: ["erlaubte_urspruenge"] }], t("einstellungen.bereich.dienste"))] },
    ] : []),
  ]);

  // frühere Adressen: Bereiche und Reiter, die umgezogen sind
  const FRUEHER: Record<string, string> = { podcast: "podcasts", speicher: "ablage" };
  const FRUEHER_REITER: Record<string, string> = { filter: "regeln", sender: "werbung", einstellungen: "bedienung" };

  const segmente = $derived((appState.routeSegments as string[]) ?? []);
  const bereich = $derived(BEREICHE.find((b) => b.id === (FRUEHER[segmente[0]] ?? segmente[0])) ?? BEREICHE[0]);
  const reiter = $derived(bereich.reiter.find((x) => x.id === (FRUEHER_REITER[segmente[1]] ?? segmente[1])) ?? bereich.reiter[0]);
  const reiterSichtbar = $derived(bereich.reiter.length > 1);

  // Adresse richtigstellen (fehlender, früherer oder in dieser Ausgabe fehlender Bereich oder Reiter)
  $effect(() => {
    if (appState.activeTab !== "settings") return;
    const soll = `/einstellungen/${bereich.id}${reiterSichtbar ? `/${reiter.id}` : ""}`;
    if (segmente[0] !== bereich.id || (reiterSichtbar ? segmente[1] !== reiter.id : segmente.length > 1)) actions.navigateTo(soll, { replace: true });
  });

  onMount(() => { void server.laden(); });

  const wartend = $derived(server.wartend());
  let speichert = $state(false);

  async function speichern() {
    speichert = true;
    try {
      await server.speichern();
      actions.showToast(S ? t("einstellungen.leiste.gespeichert") : t("einstellungen.leiste.gespeichertHier"), "success");
    } catch (f) {
      actions.showToast((f as Error).message, "error");
    } finally {
      speichert = false;
    }
  }

  const gehe = (b: Bereich, x?: Reiter) => actions.navigateTo(`/einstellungen/${b.id}${x && b.reiter.length > 1 ? `/${x.id}` : ""}`);
</script>

<div class="rh-einst">
  <nav class="rh-einst-nav" aria-label={t("einstellungen.einstellungen")}>
    {#each BEREICHE as b (b.id)}
      <a href="/einstellungen/{b.id}" class:aktiv={b === bereich} aria-current={b === bereich ? "page" : undefined}
         onclick={(e) => { e.preventDefault(); gehe(b); }}><i class="fa-solid {b.symbol}"></i>{t(`einstellungen.bereich.${b.id}`)}</a>
    {/each}
  </nav>
  <div class="rh-einst-haupt">
    <div class="rh-einst-kopf">
      <div class="rh-pfad"><span>{t("einstellungen.einstellungen")}</span><i class="fa-solid fa-chevron-right"></i><span>{t(`einstellungen.bereich.${bereich.id}`)}</span></div>
      {#if reiterSichtbar}
        <div class="reiterleiste" role="tablist" aria-label={t(`einstellungen.bereich.${bereich.id}`)}>
          {#each bereich.reiter as x (x.id)}
            <button type="button" role="tab" class:aktiv={x === reiter} aria-selected={x === reiter} onclick={() => gehe(bereich, x)}>
              {#if x.symbol}<i class="fa-solid {x.symbol}"></i>{/if}{x.titel}</button>
          {/each}
        </div>
      {/if}
    </div>
    <div class="rh-einst-rollt">
      {#if S && server.serverstand.fehler}
        <p class="hinweis-band rh-einst-fehler"><i class="fa-solid fa-triangle-exclamation"></i><span>{t("einstellungen.ladeFehler", { grund: server.serverstand.fehler })}</span>
          <button class="knopf" type="button" onclick={() => void server.laden()}><i class="fa-solid fa-rotate"></i>{t("einstellungen.nochmal")}</button></p>
      {/if}
      <section class="rh-reiter" data-reiter={reiter.id}>
        {#each reiter.bausteine as b, i (`${reiter.id}${i}`)}
          {#if b.karte}
            <Karte titel={t(`einstellungen.karte.${b.karte}`)} symbol={b.symbol} hinweis={b.hinweis ? t(`einstellungen.hinweis.${b.hinweis}`) : ""}>
              <Felder felder={b.felder} />
              {#if b.teil}<b.teil />{/if}
            </Karte>
          {:else}
            {#if b.teil === TastaturTeil}<TastaturTeil bereiche={bereichszahl} />{:else}<b.teil />{/if}
          {/if}
        {/each}
      </section>
    </div>
    {#if wartend.length}
      <div class="rh-speichern" role="status">
        <span class="rh-geaendert-punkt" aria-hidden="true"></span>
        <span><b>{wartend.length === 1 ? t("einstellungen.leiste.aenderung") : t("einstellungen.leiste.aenderungen", { n: wartend.length })}</b>
          {S ? t("einstellungen.leiste.fuerAlle") : t("einstellungen.leiste.warten")}: {wartend.join(", ")}</span>
        <button class="knopf" type="button" disabled={speichert} onclick={() => server.verwerfen()}><i class="fa-solid fa-rotate-left"></i>{t("einstellungen.leiste.verwerfen")}</button>
        <button class="knopf primaer" type="button" disabled={speichert} onclick={() => void speichern()}>
          <i class="fa-solid {speichert ? 'fa-spinner fa-spin' : 'fa-floppy-disk'}"></i>{t("einstellungen.leiste.speichern")}</button>
      </div>
    {/if}
  </div>
</div>
