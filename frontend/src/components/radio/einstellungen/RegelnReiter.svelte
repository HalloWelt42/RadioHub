<script lang="ts">
  // Reiter Ausschlussregeln (Entwurf regeln.html): Bestand als Gerät (gesamt, sichtbar, durch Regeln aus, verschwunden),
  // die neue Regel mit Vorschau und die lebenden Regeln (an und aus, entfernen mit Folgenvorschau). Die neue Regel steht
  // vor der Liste: die überführten Regeln sind fast 200, die Liste lädt beim Rollen nach und schöbe sie sonst immer weiter
  // nach unten. Jede Änderung meldet das Band mit Rückgängig.
  import { onMount } from "svelte";
  import { Nachladen } from "appkern-oberflaeche";
  import { t } from "../../../lib/i18n.svelte.js";
  import { senderquelle } from "../../../lib/radio";
  import { zahl } from "../../../lib/radio/anzeige";
  import type { BandInhalt } from "../../../lib/radio/bedienung.svelte";
  import type { Bestand, Kandidat, Regel, RegelAenderung } from "../../../lib/radio/typen";
  import Band from "../Band.svelte";
  import NeueRegel from "./NeueRegel.svelte";
  import RegelZeile from "./RegelZeile.svelte";

  const SEITE = 40;
  let bestand = $state<Bestand | null>(null);
  let regeln = $state<Regel[]>([]);
  let geladen = $state(false);
  let fehler = $state("");
  let sichtbar = $state(SEITE);
  let neu = $state<string | null>(null);
  let band = $state<BandInhalt | null>(null);

  // eigene Regeln vorn, dann nach Zahl der betroffenen Sender
  const sortiert = $derived([...regeln].sort((a, b) => Number(a.herkunft !== "nutzer") - Number(b.herkunft !== "nutzer") || b.betroffen - a.betroffen));

  async function laden() {
    try {
      const u = await senderquelle.regeln();
      bestand = u.bestand;
      regeln = u.regeln;
      fehler = "";
    } catch (f) {
      fehler = (f as Error).message;
    } finally {
      geladen = true;
    }
  }
  onMount(() => { void laden(); });

  function uebernehmen(a: RegelAenderung) {
    bestand = a.bestand;
    if (a.regel) regeln = regeln.some((r) => r.id === a.regel!.id) ? regeln.map((r) => (r.id === a.regel!.id ? a.regel! : r)) : [a.regel, ...regeln];
  }

  async function schalten(r: Regel, an = !r.an, mitBand = true) {
    try {
      const a = await senderquelle.schalten(r.id, an);
      uebernehmen(a);
      if (mitBand) band = { symbol: "fa-circle-check", art: "gut", name: r.titel,
        text: an ? t("radio.einst.bandAn", { n: zahl(a.ausgeblendet) }) : t("radio.einst.bandAus", { n: zahl(a.wieder_sichtbar) }),
        rueckgaengig: () => schalten(r, !an, false) };
    } catch (f) {
      band = { symbol: "fa-triangle-exclamation", art: "fehler", text: (f as Error).message };
    }
  }

  function entfernt(r: Regel, wiederSichtbar: number) {
    regeln = regeln.filter((x) => x.id !== r.id);
    void laden();
    const entwurf = r.entwurf;
    band = { symbol: "fa-circle-check", art: "gut", name: r.titel, text: t("radio.einst.bandEntfernt", { n: zahl(wiederSichtbar) }),
      rueckgaengig: entwurf ? async () => { uebernehmen(await senderquelle.anlegen(entwurf)); } : undefined };
  }

  function angelegt(a: RegelAenderung, rueckgaengig: () => Promise<RegelAenderung | null>) {
    uebernehmen(a);
    neu = a.regel?.id ?? null;
    band = { symbol: "fa-circle-check", art: "gut", name: a.regel?.titel,
      text: t("radio.einst.bandAngelegt", { n: zahl(a.ausgeblendet), f: zahl(a.regel?.favoriten ?? 0) }),
      rueckgaengig: async () => {
        const z = await rueckgaengig();
        regeln = regeln.filter((x) => x.id !== a.regel?.id);
        if (z) bestand = z.bestand;
      } };
  }

  function einzeln(k: Kandidat) {
    void laden();
    band = { symbol: "fa-eye-slash", name: k.name, text: k.favoriten ? t("radio.bandBleibtFavorit") : t("radio.bandAusgeblendet"),
      rueckgaengig: async () => { await senderquelle.entsperren(k.schluessel); await laden(); } };
  }
</script>

<section class="rh-reiter">
  <div class="ak-geraet rh-bestand" data-bauform="inspektor">
    <span class="ak-schraube lo" style="--dreh:18deg"></span><span class="ak-schraube ro" style="--dreh:62deg"></span><span class="ak-schraube lu" style="--dreh:-20deg"></span><span class="ak-schraube ru" style="--dreh:35deg"></span>
    <div class="rh-bestand-feld"><ak-segmente art="7" stellen="6" farbe="weiss" text={bestand ? zahl(bestand.gesamt) : "------"}></ak-segmente><span class="ak-etikett">{t("radio.einst.gesamt")}</span></div>
    <div class="rh-bestand-feld"><ak-segmente art="7" stellen="6" farbe="gruen" text={bestand ? zahl(bestand.sichtbar) : "------"}></ak-segmente><span class="ak-etikett">{t("radio.einst.sichtbar")}</span></div>
    <div class="rh-bestand-feld"><ak-segmente art="7" stellen="6" farbe="bernstein" text={bestand ? zahl(bestand.ausgeblendet) : "------"}></ak-segmente><span class="ak-etikett">{t("radio.einst.durchRegelnAus")}</span></div>
    <div class="rh-bestand-feld"><ak-segmente art="7" stellen="6" farbe="rot" text={bestand ? zahl(bestand.verschwunden) : "------"}></ak-segmente><span class="ak-etikett">{t("radio.einst.verschwunden")}</span></div>
  </div>

  <div class="karte rh-karte">
    <div class="rh-karte-kopf"><h2><i class="fa-solid fa-plus"></i>{t("radio.einst.neueRegel")}</h2><span class="rh-still">{t("radio.einst.erstVorschau")}</span></div>
    <NeueRegel onangelegt={angelegt} oneinzeln={einzeln} />
  </div>
  <div class="karte rh-karte">
    <div class="rh-karte-kopf"><h2><i class="fa-solid fa-list-check"></i>{t("radio.einst.lebendeRegeln")}</h2>
      <span class="rh-still">{t("radio.einst.lebendeRegelnHilfe", { n: zahl(regeln.length) })}</span></div>
    {#if fehler}<p class="hinweis-band"><i class="fa-solid fa-triangle-exclamation"></i><span>{fehler}</span></p>{/if}
    <div class="rh-regeln">
      {#if !geladen}<p class="rh-still">{t("radio.laedt")}</p>{/if}
      {#each sortiert.slice(0, sichtbar) as r (r.id)}
        <RegelZeile regel={r} neu={neu === r.id} onschalten={(x) => schalten(x)} onentfernt={entfernt} />
      {/each}
      {#if geladen && regeln.length}
        <Nachladen geladen={Math.min(sichtbar, regeln.length)} gesamt={regeln.length} onmehr={() => (sichtbar += SEITE)} einheit={t("radio.einst.regelnEinheit")} />
      {/if}
    </div>
  </div>

</section>
<Band bind:inhalt={band} />
