<script lang="ts">
  // Reiter Ausgeblendete Sender (Entwurf regeln.html): seitenweise, durchsuchbar, nach Grund filterbar, je Sender der
  // Grund; Freigeben macht ihn als Ausnahme wieder sichtbar (mit Rückgängig, oder "Wieder aus" in der Zeile).
  import { onMount } from "svelte";
  import { Auswahl } from "appkern-oberflaeche";
  import { t } from "../../../lib/i18n.svelte.js";
  import { senderquelle } from "../../../lib/radio";
  import { REGEL_SYMBOL, zahl } from "../../../lib/radio/anzeige";
  import type { BandInhalt } from "../../../lib/radio/bedienung.svelte";
  import type { AusgeblendeterSender, AusgeblendetSeite } from "../../../lib/radio/typen";
  import Band from "../Band.svelte";
  import Logo from "../Logo.svelte";

  const JE_SEITE = 25;
  let suche = $state("");
  let regel = $state<string>("");
  let seite = $state(0);
  let daten = $state<AusgeblendetSeite | null>(null);
  let fehler = $state("");
  let frei = $state<string[]>([]);
  let band = $state<BandInhalt | null>(null);
  let gruende = $state<{ wert: string; titel: string; hinweis?: string }[]>([]);

  let lauf = 0;
  let abbruch: AbortController | null = null;
  async function laden() {
    const meiner = ++lauf;
    abbruch?.abort();
    abbruch = new AbortController();
    try {
      const d = await senderquelle.ausgeblendet({ suche: suche.trim(), regel: regel || null, seite, anzahl: JE_SEITE }, abbruch.signal);
      if (meiner !== lauf) return;
      daten = d;
      fehler = "";
      // Gründe für die Auswahl aus der ersten Antwort ohne Filter (alle Regeln mit ausgeblendeten Sendern)
      if (!regel && !suche.trim()) {
        gruende = [{ wert: "", titel: t("radio.einst.alleGruende") },
          ...d.gruende.map((g) => ({ wert: g.regel, titel: g.titel, hinweis: ` · ${zahl(g.anzahl)}` }))];
      }
    } catch (f) {
      if (meiner === lauf && (f as Error).name !== "AbortError") fehler = (f as Error).message;
    }
  }
  onMount(() => { void laden(); });

  let uhr: ReturnType<typeof setTimeout> | undefined;
  function getippt() {
    clearTimeout(uhr);
    uhr = setTimeout(() => { seite = 0; void laden(); }, 250);
  }

  async function freigeben(a: AusgeblendeterSender) {
    try {
      await senderquelle.freigeben(a.uuid);
      frei = [...frei, a.uuid];
      band = { symbol: "fa-eye", art: "gut", name: a.name, text: t("radio.einst.bandFrei"), rueckgaengig: () => zuruecknehmen(a) };
    } catch (f) {
      band = { symbol: "fa-triangle-exclamation", art: "fehler", text: (f as Error).message };
    }
  }

  async function zuruecknehmen(a: AusgeblendeterSender) {
    await senderquelle.freigabeZuruecknehmen(a.uuid);
    frei = frei.filter((u) => u !== a.uuid);
  }

  function blaettern(schritt: number) {
    seite = Math.max(0, Math.min((daten?.seiten ?? 1) - 1, seite + schritt));
    void laden();
  }
</script>

<section class="rh-reiter">
  <div class="karte rh-karte">
    <div class="rh-karte-kopf"><h2><i class="fa-solid fa-eye-slash"></i>{t("radio.einst.reiter.ausgeblendet")}</h2>
      <span class="rh-still"><b class="rh-zahl">{daten ? zahl(daten.gesamt) : "-"}</b> {t("radio.einst.jeSenderGrund")}</span></div>
    <div class="rh-a-werkzeug">
      <label class="suche" role="search"><i class="fa-solid fa-magnifying-glass"></i>
        <input bind:value={suche} type="search" name="ausgeblendet-suche" placeholder={t("radio.einst.ausgeblendeteDurchsuchen")}
               aria-label={t("radio.einst.ausgeblendeteDurchsuchen")} autocomplete="off" oninput={getippt} /></label>
      {#if gruende.length}
        <Auswahl bind:wert={regel} optionen={gruende} symbol="fa-filter" titel={t("radio.einst.grund")} onwahl={() => { seite = 0; void laden(); }} />
      {/if}
    </div>
    {#if fehler}<p class="hinweis-band"><i class="fa-solid fa-triangle-exclamation"></i><span>{fehler}</span></p>{/if}
    <div class="rh-a-liste" role="list">
      {#if !daten}
        <p class="rh-still">{t("radio.laedt")}</p>
      {:else}
        {#each daten.eintraege as a (a.uuid)}
          {@const istFrei = frei.includes(a.uuid)}
          <div class="rh-a-zeile" class:frei={istFrei} role="listitem">
            <Logo uuid={a.uuid} name={a.name} logo={a.logo} klein />
            <span class="name"><b>{a.name}</b>{#if a.land}<span><span class="rh-kennung">{a.land}</span></span>{/if}</span>
            <span class="grund"><i class="fa-solid {REGEL_SYMBOL[a.gruende[0]?.art ?? 'einzeln']}"></i><span>{a.gruende.map((g) => g.titel).join("; ")}</span></span>
            <span class="stimmen">{zahl(a.stimmen)}</span>
            {#if istFrei}
              <button class="knopf" type="button" onclick={() => zuruecknehmen(a)}><i class="fa-solid fa-rotate-left"></i>{t("radio.einst.wiederAus")}</button>
            {:else}
              <button class="knopf" type="button" onclick={() => freigeben(a)}><i class="fa-solid fa-eye"></i>{t("radio.einst.freigeben")}</button>
            {/if}
          </div>
        {:else}
          <div class="rh-ohne-treffer"><i class="fa-solid fa-magnifying-glass"></i><b>{t("radio.einst.keinAusgeblendeter")}</b></div>
        {/each}
      {/if}
    </div>
    {#if daten && daten.seiten > 1}
      <div class="seitenzeile rh-seiten">
        <button class="knopf" type="button" disabled={seite === 0} onclick={() => blaettern(-1)}><i class="fa-solid fa-chevron-left"></i>{t("radio.einst.zurueck")}</button>
        <span class="rh-zahl">{t("radio.einst.seiteVon", { n: zahl(seite + 1), m: zahl(daten.seiten) })}</span>
        <button class="knopf" type="button" disabled={seite >= daten.seiten - 1} onclick={() => blaettern(1)}>{t("radio.einst.weiter")}<i class="fa-solid fa-chevron-right"></i></button>
      </div>
    {/if}
  </div>
</section>
<Band bind:inhalt={band} />
