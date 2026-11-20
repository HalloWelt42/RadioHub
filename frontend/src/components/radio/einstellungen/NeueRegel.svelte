<script lang="ts">
  // Neue Regel (Entwurf regeln.html): Art wählen, tippen oder einstellen; die Vorschau zeigt vorher, was ausgeblendet
  // würde (Anzahl, davon Favoriten, Beispiele). Erst "Regel anlegen" ändert etwas (Entscheidung 4, 31); danach meldet der
  // Elternteil die Änderung mit Rückgängig. Sprache, Genre, Tag und Bewertung nehmen mehrere Werte in eine Regel, beim
  // Tippen gilt der beste Treffer. Einzelsender legen eine Einzelsperre an (wie das Auge in der Liste).
  import { untrack } from "svelte";
  import type { Schieber, Wahl } from "appkern-oberflaeche/instrumente";
  import { t } from "../../../lib/i18n.svelte.js";
  import { senderquelle } from "../../../lib/radio";
  import { REGEL_SYMBOL, zahl } from "../../../lib/radio/anzeige";
  import { Regelablauf } from "../../../lib/radio/regelablauf.svelte";
  import type { Bewertung, Kandidat, KandidatenArt, RegelAenderung, RegelArt, RegelEntwurf, WerbeStufe } from "../../../lib/radio/typen";

  let { onangelegt, oneinzeln }: {
    /** neue Regel angelegt; Rückgängig entfernt sie wieder */
    onangelegt: (a: RegelAenderung, rueckgaengig: () => Promise<RegelAenderung | null>) => void;
    /** Einzelsender gesperrt */
    oneinzeln: (k: Kandidat) => void;
  } = $props();

  type Art = Exclude<RegelArt, "altsperren">;
  const ARTEN: Art[] = ["sprache", "genre", "tag", "stimmen", "werbung", "bewertung", "einzeln"];
  const MIT_LISTE: Art[] = ["sprache", "genre", "tag", "bewertung", "einzeln"];
  const STIMMEN = [1, 3, 5, 10, 25, 50, 100];
  const WERBUNG: WerbeStufe[] = ["eigene", "hoch", "mittel", "verdacht"];

  const ablauf = new Regelablauf(senderquelle);
  let art = $state<Art>("sprache");
  let suche = $state("");
  let treffer = $state<Kandidat[]>([]);
  let gewaehlt = $state<Kandidat[]>([]);
  let stimmen = $state(1);
  let werbung = $state<WerbeStufe>("hoch");
  let arbeitet = $state(false);
  let schieber = $state<Schieber>();
  let wahl = $state<Wahl>();

  const stimmenRaster = $derived(STIMMEN.map((n) => t("radio.einst.unter", { n })).join("|"));
  const werbeOptionen = $derived(WERBUNG.map((w) => t(`radio.einst.werbeStufe.${w}`)));
  /** gilt: die gewählten Werte, ohne Wahl der beste Treffer der Suche */
  const wirksam = $derived(gewaehlt.length ? gewaehlt : treffer.length && suche.trim() ? [treffer[0]] : []);

  function artWaehlen(a: Art) {
    art = a;
    suche = "";
    treffer = [];
    gewaehlt = [];
    if (a === "bewertung") void kandidatenHolen();
  }

  // Treffer zur Suche (kurz entprellt, eine ältere Antwort gilt nicht)
  let lauf = 0;
  let uhr: ReturnType<typeof setTimeout> | undefined;
  async function kandidatenHolen() {
    const meiner = ++lauf;
    const k = await senderquelle.kandidaten(art as KandidatenArt, suche.trim(), 8).catch(() => []);
    if (meiner === lauf) treffer = k;
  }
  function getippt() {
    clearTimeout(uhr);
    if (!suche.trim() && art !== "bewertung") { treffer = []; lauf++; return; }
    uhr = setTimeout(kandidatenHolen, 200);
  }

  function umschalten(k: Kandidat) {
    if (art === "einzeln") { gewaehlt = gewaehlt[0]?.schluessel === k.schluessel ? [] : [k]; return; }
    gewaehlt = gewaehlt.some((g) => g.schluessel === k.schluessel) ? gewaehlt.filter((g) => g.schluessel !== k.schluessel) : [...gewaehlt, k];
  }

  function entwurf(): RegelEntwurf | null {
    const werte = wirksam.map((k) => k.schluessel);
    switch (art) {
      case "sprache": return werte.length ? { art, schluessel: werte, eintraege: [] } : null;
      case "genre": return werte.length ? { art, genres: werte } : null;
      case "tag": return werte.length ? { art, tags: werte } : null;
      case "bewertung": return werte.length ? { art, bewertungen: werte as Bewertung[] } : null;
      case "stimmen": return { art, mindeststimmen: stimmen };
      case "werbung": return { art, stufe: werbung };
      default: return null;
    }
  }

  // jede Änderung der Eingabe: neue Vorschau
  $effect(() => {
    void art; void wirksam; void stimmen; void werbung;
    untrack(() => ablauf.setzen(entwurf()));
  });

  async function anlegen() {
    arbeitet = true;
    try {
      if (art === "einzeln") {
        const k = wirksam[0];
        if (!k) return;
        await senderquelle.sperren(k.schluessel);
        oneinzeln(k);
      } else {
        const a = await ablauf.anlegen();
        onangelegt(a, () => ablauf.rueckgaengig());
      }
      artWaehlen(art);
    } catch (f) {
      ablauf.fehler = (f as Error).message;
    } finally {
      arbeitet = false;
    }
  }

  const einzel = $derived(art === "einzeln" ? wirksam[0] ?? null : null);
  const v = $derived(ablauf.vorschau);
  const bereit = $derived(art === "einzeln" ? !!einzel : ablauf.bereit);
  const zahlText = $derived(art === "einzeln" ? (einzel ? "1" : "-----") : v ? zahl(v.neu_ausgeblendet) : "-----");
  const favoriten = $derived(art === "einzeln" ? (einzel?.favoriten ?? 0) : (v?.favoriten ?? 0));
</script>

<div class="rh-neu">
  <div class="rh-neu-eingabe">
    <div class="segment rh-arten" role="group" aria-label={t("radio.einst.artDerRegel")}>
      {#each ARTEN as a (a)}
        <button type="button" class:aktiv={art === a} aria-pressed={art === a} onclick={() => artWaehlen(a)}><i class="fa-solid {REGEL_SYMBOL[a]}"></i>{t(`radio.einst.art.${a}`)}</button>
      {/each}
    </div>
    <div>
      {#if art === "stimmen"}
        <ak-schieber bind:this={schieber} art="leuchte" leuchte="bernstein" name={t("radio.einst.ausblendenBeiStimmen")} hilfe={t("radio.einst.stimmenHilfe")}
                     raster={stimmenRaster} wert={STIMMEN.indexOf(stimmen)} oninput={() => (stimmen = STIMMEN[schieber?.wert ?? 0] ?? 1)}></ak-schieber>
        <p class="rh-neu-feld-hilfe">{t("radio.einst.hilfe.stimmen")}</p>
      {:else if art === "werbung"}
        <ak-wahl bind:this={wahl} name={t("radio.einst.werbeverdachtAb")} hilfe={t("radio.einst.werbungHilfe")} optionen={werbeOptionen.join("|")}
                 wert={werbeOptionen[WERBUNG.indexOf(werbung)]} farbe="bernstein"
                 oninput={() => (werbung = WERBUNG[Math.max(0, werbeOptionen.indexOf(wahl?.wert ?? ""))])}></ak-wahl>
        <p class="rh-neu-feld-hilfe">{t("radio.einst.hilfe.werbung")}</p>
      {:else}
        {#if art !== "bewertung"}
          <label class="suche" role="search"><i class="fa-solid fa-magnifying-glass"></i>
            <input bind:value={suche} type="search" name="regel-suche" placeholder={t(`radio.einst.platzhalter.${art}`)} aria-label={t(`radio.einst.platzhalter.${art}`)}
                   autocomplete="off" oninput={getippt} /></label>
        {/if}
        {#if gewaehlt.length && art !== "einzeln"}
          <div class="rh-gewaehlt" aria-label={t("radio.einst.gewaehlt")}>
            {#each gewaehlt as g (g.schluessel)}
              <span class="chip"><b>{g.name}</b><button type="button" aria-label={t("radio.entfernen")} title={t("radio.entfernen")} onclick={() => umschalten(g)}><i class="fa-solid fa-xmark"></i></button></span>
            {/each}
          </div>
        {/if}
        <div class="rh-treffer">
          {#each treffer as k (k.schluessel)}
            <button type="button" class:aktiv={wirksam.some((w) => w.schluessel === k.schluessel)} onclick={() => umschalten(k)}>
              <b>{k.name}{#if k.code}{" "}<span class="rh-kennung">{k.code}</span>{/if}</b><span class="rh-zahl">{t("radio.einst.nSender", { n: zahl(k.anzahl) })}</span>
              <span class="fav" class:null={!k.favoriten}>{#if k.favoriten}<i class="fa-solid fa-star"></i>{" "}{/if}{t("radio.einst.nFavoriten", { n: k.favoriten })}</span></button>
          {:else}
            {#if suche.trim() || art === "bewertung"}<p class="rh-neu-feld-hilfe">{t("radio.einst.keinEintrag")}</p>{/if}
          {/each}
        </div>
        <p class="rh-neu-feld-hilfe">{t(`radio.einst.hilfe.${art}`)}</p>
      {/if}
    </div>
  </div>

  <div class="ak-geraet rh-vorschau" data-bauform="inspektor" aria-live="polite">
    <span class="ak-schraube lo" style="--dreh:30deg"></span><span class="ak-schraube ro" style="--dreh:-12deg"></span>
    <div class="ak-geraet-kopf"><b>{t("radio.einst.vorschau")}</b>
      {#key `${bereit}${favoriten}${v?.gleiche_regel}`}
        <ak-led farbe={v?.gleiche_regel || favoriten ? "bernstein" : bereit ? "gruen" : "gelb"} zustand={bereit || v?.gleiche_regel ? "an" : "aus"}
                text={v?.gleiche_regel ? t("radio.einst.gibtEs") : favoriten ? t("radio.einst.pruefen") : t("radio.einst.bereit")} hilfe={t("radio.einst.vorschau")}></ak-led>
      {/key}
    </div>
    <div class="rh-vorschau-zahl"><ak-segmente art="7" stellen="6" farbe="bernstein" text={zahlText}></ak-segmente>
      <span>
        {#if art === "einzeln" && einzel}{t("radio.einst.wuerdeAusgeblendet")} <b>{einzel.name}</b>
        {:else if v}{t("radio.einst.wuerdenAusgeblendet")} <b>{v.titel}</b>{#if v.betroffen !== v.neu_ausgeblendet}{t("radio.einst.schonAus", { n: zahl(v.betroffen - v.neu_ausgeblendet), gesamt: zahl(v.betroffen) })}{/if}
        {:else if ablauf.laedt}{t("radio.laedt")}
        {:else}{t("radio.einst.vorschauLeer")}{/if}
      </span></div>
    {#if v?.gleiche_regel}
      <div class="rh-vorschau-fav"><ak-led farbe="bernstein" zustand="an" groesse="klein"></ak-led><span>{t("radio.einst.gleicheRegel")}</span></div>
    {:else if bereit}
      <div class="rh-vorschau-fav">
        {#if favoriten}
          <ak-led farbe="bernstein" zustand="atmet" groesse="klein"></ak-led><span><b>{t("radio.einst.nFavoriten", { n: favoriten })}</b> {t("radio.einst.favoritenBetroffen")}{#if v?.favoriten_namen.length}{` (${v.favoriten_namen.slice(0, 4).map((n) => n.trim()).join(", ")})`}{/if}</span>
        {:else}
          <ak-led farbe="gruen" zustand="an" groesse="klein"></ak-led><span>{t("radio.einst.davon")} <b>{t("radio.einst.nFavoriten", { n: 0 })}</b></span>
        {/if}
      </div>
    {/if}
    {#if v && v.beispiele.length > 1 && art !== "einzeln"}
      <div class="rh-vorschau-beispiele"><span>{t("radio.einst.beispieleAus", { n: zahl(v.betroffen) })}</span>
        {#each v.beispiele.slice(0, 3) as b (b.uuid)}<span><b>{b.name.trim()}</b> · {t("radio.einst.nStimmen", { n: zahl(b.stimmen) })}</span>{/each}</div>
    {/if}
    {#if ablauf.fehler}<div class="rh-vorschau-beispiele">{ablauf.fehler}</div>{/if}
    <div class="rh-vorschau-knoepfe">
      <button class="knopf primaer" type="button" disabled={!bereit || arbeitet} onclick={anlegen}><i class="fa-solid fa-check"></i>{t("radio.einst.anlegen")}</button>
      <button class="knopf" type="button" disabled={!bereit && !gewaehlt.length && !suche} onclick={() => artWaehlen(art)}>{t("radio.einst.verwerfen")}</button>
    </div>
  </div>
</div>
