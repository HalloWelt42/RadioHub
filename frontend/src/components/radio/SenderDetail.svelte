<script lang="ts">
  // Details eines aufgeklappten Senders (Entwurf rechner.html, ohne Titelverlauf und ähnliche Sender, die noch nicht
  // gehen): Steckbrief mit Homepage, Stream-Adresse (kopieren, eigene setzen und zurücksetzen), Codec, Sprachen, Genres,
  // Ort, Prüfung, Varianten, Titelangaben im Strom, Werbestatus und Grund der Sichtbarkeit; eigene Bewertung (Sterne,
  // Markierungen, kein Werbeverdacht) und eigene Kategorien. Jede Änderung geht über die Senderquelle und meldet die
  // neuen Felder an die Liste.
  import { kopieren } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { actions, appState } from "../../lib/store.svelte.js";
  import { senderquelle } from "../../lib/radio";
  import { MARKIERUNGEN, bewertungName, landName, qualitaetName, sterneVon, zahl } from "../../lib/radio/anzeige";
  import type { Kategorie, Steckbrief, TitelGuete } from "../../lib/radio/quelle";
  import type { Bewertung, SenderEintrag } from "../../lib/radio/typen";

  let { eintrag, kategorien, spielt, onaendern, onvarianten, onneustart }: {
    eintrag: SenderEintrag;
    kategorien: Kategorie[];
    spielt: boolean;
    onaendern: (teil: Partial<SenderEintrag>) => void;
    onvarianten: () => void;
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

  function titelGuete(g: TitelGuete) {
    const neu = steckbrief?.titelGuete === g ? null : g;
    void tun(async () => {
      await senderquelle.titelBewerten(eintrag.uuid, neu);
      if (steckbrief) steckbrief = { ...steckbrief, titelGuete: neu };
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

  function werbeText(): string {
    const w = eintrag.werbung;
    if (w.entscheidung === "gesperrt") return t("radio.werbung.gesperrt");
    if (w.entscheidung === "erlaubt") return t("radio.werbung.erlaubt");
    return t(`radio.werbung.${w.stufe}`);
  }
</script>

<div class="rh-detail">
  <section class="rh-tafel-detail"><h4><i class="fa-solid fa-circle-info"></i>{t("radio.steckbrief")}</h4>
    <dl class="rh-werte">
      {#if spielt && appState.streamTitle}
        <dt>{t("radio.laeuft")}</dt>
        <dd class="rh-laeuft"><span>{appState.streamTitle}</span><button class="rund" type="button" title={t("radio.titelKopieren")}
            aria-label={t("radio.titelKopieren")} onclick={() => kopiere(appState.streamTitle ?? "", t("radio.titel"))}><i class="fa-regular fa-copy"></i></button></dd>
      {/if}
      {#if eintrag.homepage}
        <dt>{t("radio.homepage")}</dt>
        <dd><a href={eintrag.homepage} target="_blank" rel="noopener noreferrer">{eintrag.homepage.replace(/^https?:\/\//, "").replace(/\/$/, "")}</a></dd>
      {/if}
      <dt>{t("radio.stream")}{#if eintrag.eigene_adresse}<span class="rh-eigen">{t("radio.eigene")}</span>{/if}</dt>
      {#if bearbeiten}
        <dd class="rh-strom-eingabe">
          <label class="eingabe"><input bind:value={adresse} type="url" aria-label={t("radio.eigeneAdresse")}
                 onkeydown={(e) => { if (e.key === "Enter") adresseSpeichern(adresse); if (e.key === "Escape") { e.stopPropagation(); bearbeiten = false; } }} /></label>
          <button class="rund" type="button" title={t("radio.speichern")} aria-label={t("radio.speichern")} disabled={arbeitet}
                  onclick={() => adresseSpeichern(adresse)}><i class="fa-solid fa-check"></i></button>
          <button class="rund" type="button" title={t("radio.abbrechen")} aria-label={t("radio.abbrechen")} onclick={() => (bearbeiten = false)}>
            <i class="fa-solid fa-xmark"></i></button>
        </dd>
      {:else}
        <dd class="rh-strom"><code>{strom || t("radio.laedt")}</code>
          {#if strom}
            <button class="rund" type="button" title={t("radio.adresseKopieren")} aria-label={t("radio.adresseKopieren")}
                    onclick={() => kopiere(strom, t("radio.streamAdresse"))}><i class="fa-regular fa-copy"></i></button>
          {/if}
          {#if faehig.eigeneAdresse && steckbrief}
            <button class="rund" type="button" title={t("radio.adresseBearbeiten")} aria-label={t("radio.adresseBearbeiten")}
                    onclick={() => { adresse = strom; bearbeiten = true; }}><i class="fa-solid fa-pen"></i></button>
            {#if eintrag.eigene_adresse}
              <button class="rund" type="button" title={t("radio.adresseOriginal")} aria-label={t("radio.adresseOriginal")} disabled={arbeitet}
                      onclick={() => adresseSpeichern(null)}><i class="fa-solid fa-rotate-left"></i></button>
            {/if}
          {/if}
        </dd>
      {/if}
      <dt>{t("radio.codec")}</dt>
      <dd>{eintrag.codec === "unbekannt" ? t("radio.unbekannt") : eintrag.codec}{#if eintrag.kbps} {zahl(eintrag.kbps)} kbit/s{/if},
        {eintrag.kbps_gemessen ? t("radio.gemessenKlein") : t("radio.lautVerzeichnis")} · {t("radio.qualitaetTitel")} {qualitaetName(eintrag.qualitaet)}</dd>
      <dt>{t("radio.sprachen")}</dt>
      <dd>{eintrag.sprachen.length ? eintrag.sprachen.map((s) => s.name).join(", ") : t("radio.keineAngabe")}</dd>
      {#if eintrag.genres.length}
        <dt>{t("radio.genres")}</dt><dd>{eintrag.genres.join(", ")}</dd>
      {/if}
      <dt>{t("radio.ort")}</dt>
      <dd>{[eintrag.bundesland, landName(eintrag.land, eintrag.land_name)].filter(Boolean).join(", ") || t("radio.keineAngabe")}</dd>
      <dt>{t("radio.geprueft")}</dt>
      <dd>{eintrag.verschwunden ? t("radio.verschwunden") : eintrag.erreichbar ? t("radio.erreichbar") : t("radio.nichtErreichbar")}</dd>
      {#if eintrag.varianten > 1}
        <dt>{t("radio.variantenTitel")}</dt>
        <dd><button class="knopf still" type="button" onclick={onvarianten}><i class="fa-solid fa-layer-group"></i>{t("radio.variantenZahl", { n: eintrag.varianten })}</button></dd>
      {/if}
      {#if faehig.titelBewerten && steckbrief?.titel}
        <dt>{t("radio.titelImStrom")}</dt>
        <dd><span class="rh-titelguete">
          <button type="button" class="chip wahl" class:an={steckbrief.titelGuete === "genau"} aria-pressed={steckbrief.titelGuete === "genau"}
                  title={t("radio.titelGenauHilfe")} onclick={() => titelGuete("genau")}>{t("radio.titelGenau")}</button>
          <button type="button" class="chip wahl" class:an={steckbrief.titelGuete === "ungenau"} aria-pressed={steckbrief.titelGuete === "ungenau"}
                  title={t("radio.titelUngenauHilfe")} onclick={() => titelGuete("ungenau")}>{t("radio.titelUngenau")}</button>
        </span></dd>
      {/if}
      <dt>{t("radio.werbungTitel")}</dt><dd>{werbeText()}</dd>
      {#if eintrag.ausnahme.length}
        <dt>{t("radio.sichtbarkeit")}</dt>
        <dd class="rh-ausnahme"><i class="fa-solid fa-star"></i>{t("radio.ausnahme", { gruende: eintrag.ausnahme.map((g) => g.titel).join("; ") })}</dd>
      {/if}
    </dl>
  </section>
  <section class="rh-tafel-detail"><h4><i class="fa-solid fa-star"></i>{t("radio.eigeneBewertung")}</h4>
    <div class="rh-bewerten">
      {#each [1, 2, 3] as i (i)}
        <button type="button" class="rh-stern" class:an={i <= sterne} aria-label={t("radio.sterneSetzen", { n: i })} aria-pressed={i <= sterne}
                title={bewertungName(`sterne:${i}`)} onclick={() => sternSetzen(i)}><i class="fa-solid fa-star"></i></button>
      {/each}
      {#each MARKIERUNGEN as b (b)}
        {@const an = eintrag.bewertungen.includes(b)}
        <button type="button" class="chip wahl" class:an aria-pressed={an} onclick={() => markieren(b)}>
          {#if b === "werbung"}<i class="fa-solid fa-rectangle-ad"></i>{/if}{bewertungName(b)}</button>
      {/each}
      {#if steckbrief}
        <button type="button" class="chip wahl" class:an={steckbrief.widerspruch} aria-pressed={steckbrief.widerspruch}
                title={t("radio.keinWerbeverdachtHilfe")} onclick={widersprechen}><i class="fa-solid fa-ban"></i>{t("radio.keinWerbeverdacht")}</button>
      {/if}
    </div>
    {#if faehig.kategorien}
      <h4><i class="fa-solid fa-folder"></i>{t("radio.eigeneKategorien")}</h4>
      <div class="rh-bewerten">
        {#each kategorien as k (k.id)}
          {@const an = eintrag.kategorien.includes(k.id)}
          <button type="button" class="chip wahl" class:an aria-pressed={an} onclick={() => kategorie(k.id)}>{k.name}</button>
        {:else}
          <span class="rh-still">{t("radio.keineKategorien")}</span>
        {/each}
      </div>
    {/if}
  </section>
</div>
