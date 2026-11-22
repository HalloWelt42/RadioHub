<script lang="ts">
  // Details eines aufgeklappten Senders nach Entwurf A (steckbrief-kompakt.html, RAD-35): drei schmale Spalten.
  // Steckbrief dicht (Stream mit Kopieren und eigener Adresse, Senderinfo, Codec, Homepage, Sprachen, Ort;
  // Genres und Varianten stehen schon in der Zeile); Werbung aus den
  // Sendedaten nach Werbenden zusammengefasst (die häufigsten drei, der Rest auf Klick) mit Schalter und Werbeverdacht;
  // Einschätzung zeigt nur Gewähltes (abwählbar), alles Übrige liegt in der Tafel hinter dem Plus. Erklärungen stehen
  // als Tooltip am Info-Zeichen. Jede Änderung geht über die Senderquelle und meldet die neuen Felder an die Liste.
  import { kopieren } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { actions, appState } from "../../lib/store.svelte.js";
  import { senderquelle } from "../../lib/radio";
  import { MARKIERUNGEN, bewertungName, landName, qualitaetName, sterneVon, zahl } from "../../lib/radio/anzeige";
  import type { Kategorie, Steckbrief } from "../../lib/radio/quelle";
  import type { Bewertung, SenderEintrag } from "../../lib/radio/typen";
  import { haeufigste, nachWerbenden, sendewerbung, type Steckbrief as Werbesteckbrief } from "../../lib/radio/sendewerbung";
  import { wann, werbende } from "../../lib/radio/werbende.svelte";
  import Schalter from "./Schalter.svelte";

  let { eintrag, kategorien, spielt, onaendern, onneustart }: {
    eintrag: SenderEintrag;
    kategorien: Kategorie[];
    spielt: boolean;
    onaendern: (teil: Partial<SenderEintrag>) => void;
    /** eigene Adresse geändert: läuft der Sender, startet er mit der neuen */
    onneustart: (e: SenderEintrag) => void;
  } = $props();

  const faehig = senderquelle.faehig;
  let steckbrief = $state<Steckbrief | null>(null);
  let bearbeiten = $state(false);
  let adresse = $state("");
  let arbeitet = $state(false);

  $effect(() => {
    void eintrag.uuid;
    void eintrag.eigene_adresse;
    let aktuell = true;
    senderquelle.steckbrief(eintrag).then((s) => { if (aktuell) steckbrief = s; }).catch(() => {});
    return () => { aktuell = false; };
  });

  // Werbung aus den Sendedaten (RAD-33): bekannte Spots und der Schalter je Sender
  let werbung = $state<Werbesteckbrief | null>(null);
  $effect(() => {
    const uuid = eintrag.uuid;
    let aktuell = true;
    if (faehig.werbung) sendewerbung.steckbrief(uuid).then((w) => { if (aktuell) werbung = w; }).catch(() => {});
    return () => { aktuell = false; };
  });
  function werbungSchalten(an: boolean) {
    void tun(async () => {
      werbung = await sendewerbung.setzen(eintrag.uuid, an);
      werbende.merken(werbung);
    });
  }
  /** Marke Werbung, sobald einmal Werbung erkannt wurde (RAD-59); steht die eigene Markierung, gilt nur diese */
  const werbemarke = $derived(faehig.werbung && !!werbung?.marke && !eintrag.bewertungen.includes("werbung"));
  function werbemarkeEntfernen() {
    void tun(async () => {
      werbung = await sendewerbung.markeEntfernen(eintrag.uuid);
      werbende.merken(werbung);
    });
  }
  // Werbende, die häufigsten zuerst; lange Listen rollen in sich und zeigen höchstens die häufigsten (haeufigste)
  const gruppen = $derived(nachWerbenden(werbung?.liste ?? []));
  const mal = $derived(gruppen.reduce((n, g) => n + g.mal, 0));
  const werbendeListe = $derived(haeufigste(gruppen));
  /** ohne Namen aus den Sendedaten: eine Kennung aus Ziffern als "Spot 199326", ein Text (etwa "Kurze Werbepause") selbst */
  const werbendenName = (g: { name: string; kennung: string }) =>
    g.name || (/^\d+$/.test(g.kennung) ? t("radio.werbungOhneName", { k: g.kennung }) : g.kennung);

  // Tafel der Einschätzung: öffnet am Plus, schließt mit Escape oder einem Klick daneben
  let tafel = $state(false);
  let anker = $state<HTMLElement>();
  /** Größengruppe eines Knopfs in der Auswahltafel: lange Namen belegen zwei Zellen des Rasters (RAD-59) */
  const breit = (text: string, mitSymbol = false) => text.length + (mitSymbol ? 2 : 0) > 11;
  /** die Tafel ganz zeigen: die Liste rollt beim Öffnen so weit, dass sie nicht hinter der Kanzel verschwindet (RAD-59) */
  const ganzZeigen = (tafelEl: HTMLElement) => { requestAnimationFrame(() => tafelEl.scrollIntoView({ block: "nearest", behavior: "smooth" })); };
  function tafelAussen(e: MouseEvent) {
    if (tafel && anker && !anker.contains(e.target as Node)) tafel = false;
  }
  const spotDauer = (ms: number | null) => (ms ? `${Math.floor(ms / 60000)}:${String(Math.round((ms % 60000) / 1000)).padStart(2, "0")}` : "?");

  const sterne = $derived(Math.max(0, ...eintrag.bewertungen.map(sterneVon)));
  const strom = $derived(steckbrief ? (steckbrief.eigeneAdresse || steckbrief.adresse) : "");

  async function tun(arbeit: () => Promise<void>) {
    if (arbeitet) return;
    arbeitet = true;
    try {
      await arbeit();
    } catch (f) {
      actions.showToast((f as Error).message || t("common.fehler"), "error");
    } finally {
      arbeitet = false;
    }
  }

  async function kopiere(text: string, was: string) {
    const ok = await kopieren(text);
    actions.showToast(ok ? t("radio.kopiert", { was }) : t("radio.kopierenFehler"), ok ? "success" : "error");
  }

  function sternSetzen(n: number) {
    const neu: Bewertung = `sterne:${n}` as Bewertung;
    const an = sterne !== n;
    void tun(async () => {
      if (an) await senderquelle.bewerten(eintrag.uuid, neu, true);
      else await senderquelle.bewerten(eintrag.uuid, neu, false);
      onaendern({ bewertungen: [...eintrag.bewertungen.filter((b) => !b.startsWith("sterne:")), ...(an ? [neu] : [])] });
    });
  }

  function markieren(b: Bewertung) {
    const an = !eintrag.bewertungen.includes(b);
    void tun(async () => {
      await senderquelle.bewerten(eintrag.uuid, b, an);
      onaendern({ bewertungen: an ? [...eintrag.bewertungen, b] : eintrag.bewertungen.filter((x) => x !== b) });
      if (an && b === "werbung" && steckbrief) steckbrief = { ...steckbrief, widerspruch: false };
    });
  }

  function widersprechen() {
    const an = !steckbrief?.widerspruch;
    void tun(async () => {
      await senderquelle.werbungWidersprechen(eintrag.uuid, an);
      if (steckbrief) steckbrief = { ...steckbrief, widerspruch: an };
      if (an) onaendern({ bewertungen: eintrag.bewertungen.filter((x) => x !== "werbung") });
    });
  }

  function kategorie(id: number) {
    const an = !eintrag.kategorien.includes(id);
    void tun(async () => {
      await senderquelle.kategorieZuordnen(eintrag.uuid, id, an);
      onaendern({ kategorien: an ? [...eintrag.kategorien, id] : eintrag.kategorien.filter((k) => k !== id) });
    });
  }

  function adresseSpeichern(neu: string | null) {
    const wert = neu?.trim() || null;
    const gleichVerzeichnis = !!wert && wert === steckbrief?.adresse;
    void tun(async () => {
      await senderquelle.eigeneAdresse(eintrag.uuid, gleichVerzeichnis ? null : wert);
      bearbeiten = false;
      const teil = { eigene_adresse: gleichVerzeichnis ? null : wert };
      onaendern(teil);
      actions.showToast(teil.eigene_adresse ? t("radio.adresseGespeichert") : t("radio.adresseZurueck"), "success");
      if (spielt) onneustart({ ...eintrag, ...teil });
    });
  }
</script>

<svelte:window onclick={tafelAussen} onkeydown={(e) => { if (e.key === "Escape" && tafel) { e.stopPropagation(); tafel = false; } }} />

<div class="rh-detail rh-detail-dicht">
  <!-- ohne Überschriften (Nutzer 22.11.2026, RAD-59): Steckbrief, eigene Filter, Werbung sprechen für sich -->
  <section class="rh-tafel-detail" aria-label={t("radio.steckbrief")}>
    <!-- Stream zuoberst, jede Beschriftung steht immer, auch ohne Wert: die Zeilen bleiben an ihrem Platz (RAD-59) -->
    <dl class="rh-werte-dicht">
      <dt>{t("radio.stream")}{#if eintrag.eigene_adresse}<span class="rh-eigen">{t("radio.eigene")}</span>{/if}</dt>
      {#if bearbeiten}
        <dd class="rh-strom-eingabe">
          <label class="eingabe"><input bind:value={adresse} type="url" aria-label={t("radio.eigeneAdresse")}
                 onkeydown={(e) => { if (e.key === "Enter") adresseSpeichern(adresse); if (e.key === "Escape") { e.stopPropagation(); bearbeiten = false; } }} /></label>
          <button class="rund rh-mini" type="button" title={t("radio.speichern")} aria-label={t("radio.speichern")} disabled={arbeitet}
                  onclick={() => adresseSpeichern(adresse)}><i class="fa-solid fa-check"></i></button>
          <button class="rund rh-mini" type="button" title={t("radio.abbrechen")} aria-label={t("radio.abbrechen")} onclick={() => (bearbeiten = false)}>
            <i class="fa-solid fa-xmark"></i></button>
        </dd>
      {:else}
        <dd class="rh-strom-dicht"><code title={strom}>{strom || t("radio.laedt")}</code>
          {#if strom}
            <button class="rund rh-mini" type="button" title={t("radio.adresseKopieren")} aria-label={t("radio.adresseKopieren")}
                    onclick={() => kopiere(strom, t("radio.streamAdresse"))}><i class="fa-regular fa-copy"></i></button>
          {/if}
          {#if faehig.eigeneAdresse && steckbrief}
            <button class="rund rh-mini" type="button" title={t("radio.adresseBearbeiten")} aria-label={t("radio.adresseBearbeiten")}
                    onclick={() => { adresse = strom; bearbeiten = true; }}><i class="fa-solid fa-pen"></i></button>
            {#if eintrag.eigene_adresse}
              <button class="rund rh-mini" type="button" title={t("radio.adresseOriginal")} aria-label={t("radio.adresseOriginal")} disabled={arbeitet}
                      onclick={() => adresseSpeichern(null)}><i class="fa-solid fa-rotate-left"></i></button>
            {/if}
          {/if}
        </dd>
      {/if}
      <dt>{t("radio.senderinfo")}</dt>
      <dd class="rh-laeuft">{#if spielt && appState.streamTitle}<span>{appState.streamTitle}</span><button class="rund rh-mini" type="button" title={t("radio.titelKopieren")}
          aria-label={t("radio.titelKopieren")} onclick={() => kopiere(appState.streamTitle ?? "", t("radio.titel"))}><i class="fa-regular fa-copy"></i></button>{/if}</dd>
      <dt>{t("radio.codec")}</dt>
      <dd>{eintrag.codec === "unbekannt" ? t("radio.unbekannt") : eintrag.codec}{#if eintrag.kbps}{` ${zahl(eintrag.kbps)} kbit/s`}{/if}<i class="fa-solid fa-circle-info rh-info"
        title={`${eintrag.kbps_gemessen ? t("radio.gemessenKlein") : t("radio.lautVerzeichnis")} · ${t("radio.qualitaetTitel")} ${qualitaetName(eintrag.qualitaet)}`}></i></dd>
      <dt>{t("radio.homepage")}</dt>
      <dd class="rh-kurz">{#if eintrag.homepage}<a href={eintrag.homepage} target="_blank" rel="noopener noreferrer" title={eintrag.homepage}>{eintrag.homepage.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "")}</a>{/if}</dd>
      <dt>{t("radio.sprachen")}</dt>
      <dd>{eintrag.sprachen.length ? eintrag.sprachen.map((s) => s.name).join(", ") : t("radio.keineAngabe")}</dd>
      <dt>{t("radio.ort")}</dt>
      <dd>{[eintrag.bundesland, landName(eintrag.land, eintrag.land_name)].filter(Boolean).join(", ") || t("radio.keineAngabe")}</dd>
    </dl>
  </section>

  <section class="rh-tafel-detail rh-tafel-fuellt" aria-label={t("radio.eigeneBewertung")}>
    <div class="rh-einschaetzung">
      <!-- "Eigene Filter" mit dem Plus immer oben, auf der Linie der ersten Steckbriefzeile (Nutzer 22.11.2026, RAD-59) -->
      <div class="rh-einschaetzung-kopf">
      <span class="rh-still" title={t("radio.einschaetzungHinweis")}>{t("radio.eigeneFilter")}</span>
      <span class="rh-tafel-anker" bind:this={anker}>
        <button type="button" class="rund rh-mini" aria-expanded={tafel} aria-haspopup="dialog" title={t("radio.einschaetzungAendern")}
                aria-label={t("radio.einschaetzungAendern")} onclick={() => (tafel = !tafel)}><i class="fa-solid {tafel ? 'fa-xmark' : 'fa-plus'}"></i></button>
        {#if tafel}
          <div class="rh-einschaetzung-tafel" role="dialog" aria-label={t("radio.eigeneBewertung")} use:ganzZeigen>
            <div class="rh-tafel-zeile"><span class="ak-etikett">{t("radio.bewertungTitel")}</span><span class="rh-bewerten">
              {#each [1, 2, 3] as i (i)}
                <button type="button" class="rh-stern" class:an={i <= sterne} aria-label={t("radio.sterneSetzen", { n: i })} aria-pressed={i <= sterne}
                        title={bewertungName(`sterne:${i}`)} onclick={() => sternSetzen(i)}><i class="fa-solid fa-star"></i></button>
              {/each}</span></div>
            <div class="rh-tafel-zeile"><span class="ak-etikett">{t("radio.markierungenTitel")}</span><span class="rh-bewerten rh-raster">
              {#each MARKIERUNGEN as b (b)}
                {@const an = eintrag.bewertungen.includes(b)}
                <button type="button" class="chip wahl rh-chip-klein" class:an class:breit={breit(bewertungName(b), b === "werbung")} aria-pressed={an} onclick={() => markieren(b)}>
                  {#if b === "werbung"}<i class="fa-solid fa-rectangle-ad"></i>{/if}{bewertungName(b)}</button>
              {/each}
              {#if steckbrief && faehig.werbung}
                <button type="button" class="chip wahl rh-chip-klein" class:an={steckbrief.widerspruch} class:breit={breit(t("radio.keinWerbeverdacht"), true)} aria-pressed={steckbrief.widerspruch}
                        title={t("radio.keinWerbeverdachtHilfe")} onclick={widersprechen}><i class="fa-solid fa-ban"></i>{t("radio.keinWerbeverdacht")}</button>
              {/if}</span></div>
            {#if faehig.kategorien}
              <div class="rh-tafel-zeile"><span class="ak-etikett">{t("radio.kategorienTitel")}</span><span class="rh-bewerten rh-raster">
                {#each kategorien as k (k.id)}
                  {@const an = eintrag.kategorien.includes(k.id)}
                  <button type="button" class="chip wahl rh-chip-klein" class:an class:breit={breit(k.name)} aria-pressed={an} onclick={() => kategorie(k.id)}>{k.name}</button>
                {:else}
                  <span class="rh-still">{t("radio.keineKategorien")}</span>
                {/each}</span></div>
            {/if}
          </div>
        {/if}
      </span>
      </div>
      <!-- die Auswahl als Liste gleich großer Einträge, die bei vielen in sich rollt wie die Werbeliste (RAD-59) -->
      <div class="rh-einschaetzung-liste">
      {#if sterne}<span class="chip wahl an rh-chip-klein rh-gewaehlt-sterne" title={bewertungName(`sterne:${sterne}`)}>{#each { length: sterne } as _, i (i)}<i class="fa-solid fa-star"></i>{/each}</span>{/if}
      {#if werbemarke}
        <button type="button" class="chip wahl an rh-chip-klein" title={t("radio.werbemarkeHilfe")} onclick={werbemarkeEntfernen}>
          <i class="fa-solid fa-rectangle-ad"></i>{bewertungName("werbung")}<i class="fa-solid fa-xmark rh-weg"></i></button>
      {/if}
      {#each MARKIERUNGEN.filter((b) => eintrag.bewertungen.includes(b)) as b (b)}
        <button type="button" class="chip wahl an rh-chip-klein" title={t("radio.abwaehlen")} onclick={() => markieren(b)}>
          {#if b === "werbung"}<i class="fa-solid fa-rectangle-ad"></i>{/if}{bewertungName(b)}<i class="fa-solid fa-xmark rh-weg"></i></button>
      {/each}
      {#if steckbrief?.widerspruch && faehig.werbung}
        <button type="button" class="chip wahl an rh-chip-klein" title={t("radio.abwaehlen")} onclick={widersprechen}><i class="fa-solid fa-ban"></i>{t("radio.keinWerbeverdacht")}<i class="fa-solid fa-xmark rh-weg"></i></button>
      {/if}
      {#if faehig.kategorien}
        {#each kategorien.filter((k) => eintrag.kategorien.includes(k.id)) as k (k.id)}
          <button type="button" class="chip wahl an rh-chip-klein" title={t("radio.abwaehlen")} onclick={() => kategorie(k.id)}><i class="fa-solid fa-folder"></i>{k.name}<i class="fa-solid fa-xmark rh-weg"></i></button>
        {/each}
      {/if}
      </div>
    </div>
  </section>

  <!-- Werbung rechts außen, schmal und kurz (RAD-59) -->
  {#if faehig.werbung}
    <section class="rh-tafel-detail" aria-label={t("radio.werbungTitel")}>
      <!-- Kopf: links die Anzahl, rechts außen der Schalter über der Liste der Werbenden (RAD-59) -->
      <div class="rh-werbung-kopf">
        {#if werbung?.spots}<span class="rh-still" title={t("radio.werbungZahlenHilfe", { s: zahl(werbung.spots), w: zahl(gruppen.length), m: zahl(mal) })}>{t("radio.werbungZahlen", { m: zahl(mal) })}</span>{/if}
        {#if werbung}<Schalter an={werbung.ueberspringen} farbe="bernstein" text={t("radio.werbungUeberspringen")}
          hilfe={werbung.ausgenommen || werbung.ueberspringen ? t("radio.werbungUeberspringenHilfe") : t("radio.werbungUeberspringenAlleAus")}
          onwechsel={werbungSchalten} />{/if}
      </div>
      {#if gruppen.length}
        <div class="rh-werbende" class:rh-liste-rollt={werbendeListe.rollt}>
          {#each werbendeListe.zeigen as g (g.name || g.kennung)}
            {@const spots = haeufigste(g.spots)}
            <details class="rh-werbender">
              <summary><i class="fa-solid fa-chevron-right rh-pfeil"></i><b title={werbendenName(g)}>{werbendenName(g)}</b>
                <span class="rh-zahl">{t("radio.werbungMal", { n: zahl(g.mal) })}</span>
                {#if g.beimVerbinden}<i class="fa-solid fa-plug rh-verbinden" title={t("radio.werbungBeimVerbinden")}></i>{:else}<span></span>{/if}</summary>
              <ul class:rh-liste-rollt={spots.rollt}>
                {#each spots.zeigen as s (s.format + s.kennung)}
                  <li><span class="rh-zahl">{spotDauer(s.dauer_ms)}</span><span class="rh-kurz" title={s.titel}>{s.titel || s.kennung}</span><span class="rh-zahl">{t("radio.werbungMal", { n: zahl(s.anzahl) })}</span>
                    <span class="rh-still">{t(s.beim_verbinden ? "radio.werbungBeimVerbinden" : "radio.werbungImProgramm")} · {wann(s.zuletzt)}</span></li>
                {/each}
                {#if spots.weggelassen}<li class="rh-still">{t("radio.listeHaeufigste", { n: zahl(spots.zeigen.length), von: zahl(g.spots.length) })}</li>{/if}
              </ul>
            </details>
          {/each}
        </div>
        {#if werbendeListe.weggelassen}<span class="rh-still">{t("radio.listeHaeufigste", { n: zahl(werbendeListe.zeigen.length), von: zahl(gruppen.length) })}</span>{/if}
      {:else if werbung}
        <span class="rh-still">{t("radio.werbungKeineBekannt")}</span>
      {/if}
    </section>
  {/if}
</div>
