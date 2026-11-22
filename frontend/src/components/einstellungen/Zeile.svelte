<script lang="ts">
  // Eine Einstellung als Zeile (Entwurf mockups/radio-filter/einstellungen.html, RAD-11): links Name, Geltung und ein
  // Satz, rechts das Bedienteil aus der HiFi-Vorlage; Adressen und Listen nehmen die volle Breite. Geänderte Werte für
  // alle Geräte tragen einen Punkt, bis sie gespeichert sind. Fest gesetzte (vom Ausrollen) und auf diesem Gerät
  // gesperrte stehen ausgegraut mit Grund da. "Vorgabe" fragt vorher und nennt, was verloren geht.
  import { Auswahl, Rueckfrage } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import Schalter from "../bausteine/Schalter.svelte";
  import { server, type Wahlwert, type Zeile } from "../../lib/einstellungen";

  let { zeile, onwert }: { zeile: Zeile; onwert: (wert: unknown) => void } = $props();

  const gesperrt = $derived(zeile.fest || !!zeile.sperrgrund);
  const breit = $derived(zeile.art === "text" || zeile.art === "liste");
  const vorgabeMoeglich = $derived(zeile.geltung === "alle" && breit && zeile.vorgabe !== undefined
    && JSON.stringify(zeile.vorgabe) !== JSON.stringify(zeile.wert) && !gesperrt);

  // ----- Schieber: der Wert kommt auch von außen (Verwerfen), dann ohne Meldung nachziehen -----
  let schieber = $state<HTMLElement & { wert?: number }>();
  $effect(() => {
    const w = zeile.wert as number;
    if (schieber && schieber.wert !== w) schieber.wert = w;
  });

  // ----- Auswahl aus dem System (etwa die Zeit-Stimme): erst beim Zeigen geholt -----
  let angebot = $state<Wahlwert[] | null>(null);
  let angebotStand = $state("");
  $effect(() => {
    if (!zeile.angebot || angebot) return;
    server.angebot(zeile.schluessel).then((a) => { angebot = a.optionen; angebotStand = a.stand; })
      .catch((f: Error) => { angebot = []; angebotStand = f.message; });
  });
  const optionen = $derived(zeile.angebot ? angebot ?? [] : zeile.optionen);

  // ----- Text und Liste -----
  let neu = $state("");
  function textUebernehmen(e: Event) {
    const wert = (e.currentTarget as HTMLInputElement).value.trim();
    if (wert !== zeile.wert) onwert(wert);
  }
  function listeHinzu() {
    const w = neu.trim();
    if (!w) return;
    const liste = (zeile.wert as string[]) ?? [];
    if (!liste.includes(w)) onwert([...liste, w]);
    neu = "";
  }

  // ----- Uhrzeit: eigenes Feld (die native Eingabe ist amerikanisch), Stunde und Minute als Auswahl -----
  const STUNDEN = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, "0"));
  const minuten = $derived(Array.from({ length: 60 / (zeile.schritt || 15) }, (_, i) => String(i * (zeile.schritt || 15)).padStart(2, "0")));
  const leerWahl = $derived({ wert: "", titel: "--", hinweis: t("einstellungen.ohneZeit") });
  function uhrzeitSetzen(alt: string, teil: "h" | "m", wert: string): string {
    if (!wert) return "";
    const [h, m] = alt ? alt.split(":") : ["00", "00"];
    return teil === "h" ? `${wert}:${m}` : `${h}:${wert}`;
  }

  // ----- Stufe: geordnete Werte mit kleiner und größer -----
  const stufe = $derived(zeile.optionen.findIndex((o) => o.wert === zeile.wert));

  let fragtVorgabe = $state(false);
  const vorgabeText = $derived(Array.isArray(zeile.wert) ? (zeile.wert as string[]).join(", ") : String(zeile.wert ?? ""));
</script>

{#snippet uhrzeit(wert: string, beiWahl: (w: string) => void, wort: string)}
  {@const [h, m] = wert ? wert.split(":") : ["", ""]}
  <span class="rh-uhr">
    <Auswahl wert={h} optionen={[leerWahl, ...STUNDEN.map((x) => ({ wert: x, titel: x }))]} titel="{wort} {t('einstellungen.stunde')}"
             onwahl={(w: string) => beiWahl(uhrzeitSetzen(wert, "h", w))} />
    <b>:</b>
    <Auswahl wert={m} optionen={[leerWahl, ...minuten.map((x) => ({ wert: x, titel: x }))]} titel="{wort} {t('einstellungen.minute')}"
             onwahl={(w: string) => beiWahl(uhrzeitSetzen(wert, "m", w))} />
  </span>
{/snippet}

<div class="rh-e-zeile" class:breit class:fest={gesperrt} data-zeile={zeile.schluessel}>
  <div class="rh-e-beschreibung">
    <div class="rh-e-name">
      {#if zeile.geaendert}<span class="rh-geaendert-punkt" title={t("einstellungen.geaendert")}></span>{/if}
      <b>{zeile.titel}</b>
      {#if zeile.fest}
        <span class="rh-geltung fest" title={t("einstellungen.geltung.festHilfe")}><i class="fa-solid fa-lock"></i>{t("einstellungen.geltung.fest")}</span>
      {:else if zeile.geltung === "alle"}
        <span class="rh-geltung alle" title={t("einstellungen.geltung.alleHilfe")}><i class="fa-solid fa-house"></i>{t("einstellungen.geltung.alle")}</span>
      {:else}
        <span class="rh-geltung geraet" title={t("einstellungen.geltung.geraetHilfe")}><i class="fa-solid fa-display"></i>{t("einstellungen.geltung.geraet")}</span>
      {/if}
    </div>
    <p>{zeile.beschreibung}{#if zeile.sperrgrund} <span class="rh-e-pruefung">{zeile.sperrgrund}</span>{/if}</p>
  </div>
  <div class="rh-e-wert">
    {#if zeile.art === "schalter"}
      <Schalter an={!!zeile.wert} text={zeile.wert ? t("einstellungen.an") : t("einstellungen.aus")} hilfe={zeile.titel} onwechsel={onwert} />
    {:else if zeile.art === "zahl"}
      <ak-schieber bind:this={schieber} art="balken" leuchte="gruen" segmente="8" name={zeile.titel} min={zeile.kleinste} max={zeile.groesste}
                   schritt={zeile.schritt ?? 1} einheit={zeile.einheit} wert={zeile.wert as number} gesperrt={gesperrt || undefined}
                   oninput={() => { const w = schieber?.wert; if (typeof w === "number" && w !== zeile.wert) onwert(w); }}></ak-schieber>
    {:else if zeile.art === "wahl" || zeile.art === "mehrfach"}
      <div class="segment" role="group" aria-label={zeile.titel}>
        {#each zeile.optionen as o (o.wert)}
          {@const an = zeile.art === "mehrfach" ? ((zeile.wert as string[]) ?? []).includes(o.wert) : String(zeile.wert) === o.wert}
          <button type="button" class:aktiv={an} aria-pressed={an} disabled={gesperrt} title={o.hinweis}
                  onclick={() => {
                    if (zeile.art !== "mehrfach") return onwert(o.wert);
                    const liste = (zeile.wert as string[]) ?? [];
                    onwert(an ? liste.filter((x) => x !== o.wert) : [...liste, o.wert]);
                  }}>{#if o.symbol}<i class="fa-solid {o.symbol}"></i>{/if}{o.titel}</button>
        {/each}
      </div>
    {:else if zeile.art === "auswahl"}
      {#if zeile.angebot && angebot === null}
        <span class="rh-still"><i class="fa-solid fa-spinner fa-spin"></i> {t("einstellungen.angebotLaedt")}</span>
      {:else}
        <Auswahl wert={String(zeile.wert ?? "")} optionen={optionen.map((o) => ({ wert: o.wert, titel: o.titel, hinweis: o.hinweis }))}
                 titel={zeile.titel} onwahl={(w: string) => onwert(w)} />
        {#if angebotStand && !optionen.length}<span class="rh-still">{angebotStand}</span>{/if}
      {/if}
    {:else if zeile.art === "uhrzeit"}
      {@render uhrzeit(String(zeile.wert ?? ""), (w) => onwert(w), "")}
    {:else if zeile.art === "zeitraum"}
      {@const [von, bis] = (zeile.wert as [string, string]) ?? ["", ""]}
      <span class="rh-zeitraum">
        {@render uhrzeit(von, (w) => onwert([w, bis]), t("einstellungen.geraet.zeitansageZeitraum"))}
        <span>{t("einstellungen.bis")}</span>
        {@render uhrzeit(bis, (w) => onwert([von, w]), t("einstellungen.bis"))}
      </span>
    {:else if zeile.art === "stufe"}
      <div class="rh-schrift-wahl">
        <button class="knopf" type="button" aria-label={t("einstellungen.kleiner")} title={t("einstellungen.kleiner")} disabled={stufe <= 0}
                onclick={() => onwert(zeile.optionen[stufe - 1].wert)}><i class="fa-solid fa-minus"></i></button>
        <output aria-live="polite">{zeile.optionen[stufe]?.titel ?? ""}</output>
        <button class="knopf" type="button" aria-label={t("einstellungen.groesser")} title={t("einstellungen.groesser")}
                disabled={stufe < 0 || stufe >= zeile.optionen.length - 1} onclick={() => onwert(zeile.optionen[stufe + 1].wert)}><i class="fa-solid fa-plus"></i></button>
      </div>
    {:else if zeile.art === "text"}
      <span class="rh-e-text-wert">
        <label class="suche rh-e-eingabe"><i class="fa-solid fa-link"></i>
          <input type="text" value={String(zeile.wert ?? "")} spellcheck="false" aria-label={zeile.titel} disabled={gesperrt}
                 onchange={textUebernehmen} onkeydown={(e) => { if (e.key === "Enter") (e.currentTarget as HTMLInputElement).blur(); }} /></label>
        {#if vorgabeMoeglich}<button class="knopf still" type="button" title={t("einstellungen.vorgabeHilfe")} onclick={() => (fragtVorgabe = true)}>
          <i class="fa-solid fa-rotate-left"></i>{t("einstellungen.vorgabe")}</button>{/if}
      </span>
    {:else if zeile.art === "liste"}
      <div class="rh-e-liste">
        {#each (zeile.wert as string[]) ?? [] as eintrag, i (eintrag)}
          <span class="rh-e-listeneintrag"><span>{eintrag}</span>
            {#if !gesperrt}<button class="rund" type="button" aria-label="{eintrag}: {t('einstellungen.entfernen')}" title={t("einstellungen.entfernen")}
                    onclick={() => onwert(((zeile.wert as string[]) ?? []).filter((_, j) => j !== i))}><i class="fa-solid fa-xmark"></i></button>{/if}</span>
        {:else}
          <span class="rh-still">{t("einstellungen.leer")}</span>
        {/each}
        {#if !gesperrt}
          <span class="rh-e-neu">
            <label class="suche rh-e-eingabe"><i class="fa-solid fa-plus"></i>
              <input type="text" bind:value={neu} spellcheck="false" placeholder={t("einstellungen.adresseHinzu")} aria-label="{zeile.titel}: {t('einstellungen.adresseHinzu')}"
                     onkeydown={(e) => { if (e.key === "Enter") listeHinzu(); }} onblur={listeHinzu} /></label>
            {#if vorgabeMoeglich}<button class="knopf still" type="button" title={t("einstellungen.vorgabeHilfe")} onclick={() => (fragtVorgabe = true)}>
              <i class="fa-solid fa-rotate-left"></i>{t("einstellungen.vorgabe")}</button>{/if}
          </span>
        {/if}
      </div>
    {/if}
    {#if fragtVorgabe}
      <Rueckfrage frage={t("einstellungen.vorgabeFrage", { titel: zeile.titel, wert: vorgabeText })} knopf={t("einstellungen.aufVorgabe")}
                  onabbrechen={() => (fragtVorgabe = false)} onja={() => { fragtVorgabe = false; onwert(zeile.vorgabe); }} />
    {/if}
  </div>
</div>
