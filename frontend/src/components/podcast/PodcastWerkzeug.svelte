<script lang="ts">
  // Werkzeugleiste der Podcasts (Entwurf podcasts.html), dieselben Bausteine wie beim Radio: Knopf Abos (unter 1100
  // Pixeln), Zählwerk der Folgen, Suche mit eigenem Verlauf, Sortierung, Aktualisieren; darunter die aktiven Filter als
  // Chips und der Hinweis auf die nächste automatische Aktualisierung.
  import { Auswahl } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import * as sfx from "../../lib/uiSounds.js";
  import { zahl } from "../../lib/radio/anzeige";
  import { Suchverlauf } from "../../lib/radio/suchverlauf";
  import { PODCASTSORTIERUNG, type Abo, type Aktualisierungsstand, type Podcastansicht, type Podcastsortierung } from "../../lib/podcasts";
  import Suchfeld from "../radio/Suchfeld.svelte";

  const verlauf = new Suchverlauf("radiohub_podcast_suche");

  let { ansicht, abos, gesamt, ungehoert, stand, laedt, leisteOffen, onaendern, onleiste, onaktualisieren, oneinstellungen }: {
    ansicht: Podcastansicht;
    abos: Abo[];
    gesamt: number | null;
    ungehoert: number;
    stand: Aktualisierungsstand | null;
    laedt: boolean;
    leisteOffen: boolean;
    onaendern: (arbeit: (a: Podcastansicht) => Podcastansicht) => void;
    onleiste: () => void;
    onaktualisieren: () => void;
    oneinstellungen: () => void;
  } = $props();

  const sorten = $derived(PODCASTSORTIERUNG.map((s) => ({ wert: s, titel: t(`podcastAnsicht.sort_${s}`), hinweis: ` · ${t(`podcastAnsicht.sortHinweis_${s}`)}` })));
  const name = (id: number) => abos.find((a) => a.id === id)?.titel ?? String(id);

  type Chip = { art: "abo" | "wahl" | "suche"; wert: string; text: string };
  const chips = $derived<Chip[]>([
    ...ansicht.abos.map((id) => ({ art: "abo" as const, wert: String(id), text: name(id) })),
    ...(ansicht.wahl !== "alle" ? [{ art: "wahl" as const, wert: ansicht.wahl, text: t(`podcastAnsicht.wahl_${ansicht.wahl}`) }] : []),
    ...(ansicht.suche ? [{ art: "suche" as const, wert: ansicht.suche, text: ansicht.suche }] : []),
  ]);

  function ohne(c: Chip) {
    onaendern((a) => c.art === "abo" ? { ...a, abos: a.abos.filter((x) => String(x) !== c.wert), offen: null }
      : c.art === "wahl" ? { ...a, wahl: "alle" } : { ...a, suche: "" });
  }

  /** "2 h 14 min" bis zur nächsten automatischen Aktualisierung */
  let jetzt = $state(Date.now());
  $effect(() => {
    const uhr = setInterval(() => (jetzt = Date.now()), 30_000);
    return () => clearInterval(uhr);
  });
  const bis = $derived.by(() => {
    if (!stand?.naechste) return null;
    const min = Math.max(0, Math.round((new Date(stand.naechste).getTime() - jetzt) / 60_000));
    return min >= 60 ? `${Math.floor(min / 60)} h ${min % 60} min` : `${min} min`;
  });
</script>

<div class="rh-werkzeug">
  <div class="rh-werkzeug-zeile">
    <button class="knopf rh-filter-auf" type="button" aria-expanded={leisteOffen} aria-controls="rh-podcast-leiste" onclick={onleiste}>
      <i class="fa-solid fa-sliders"></i>{t("podcastAnsicht.abosKnopf")}{#if chips.length}<span class="pille">{chips.length}</span>{/if}</button>
    <div class="rh-zaehler" title={t("podcastAnsicht.folgenHilfe")}>
      <ak-segmente art="7" stellen="5" farbe="gruen" text={gesamt === null ? "-----" : zahl(gesamt)}></ak-segmente>
      <span class="ak-etikett">{t("podcastAnsicht.folgen")}</span>
      <span class="rh-breit">{t("podcastAnsicht.ungehoertZahl", { n: zahl(ungehoert) })}</span>
    </div>
    <Suchfeld wert={ansicht.suche} gedaechtnis={verlauf} name="folgen-suche" platzhalter={t("podcastAnsicht.sucheHilfe")}
              beschriftung={t("podcastAnsicht.sucheHilfe")} hilfe={t("podcastAnsicht.sucheHilfe")}
              onsuche={(s) => onaendern((a) => ({ ...a, suche: s, offen: null }))} />
    <span class="rh-sortierung">
      <Auswahl wert={ansicht.sortierung} optionen={sorten} symbol="fa-arrow-down-wide-short" titel={t("podcastAnsicht.sortierungTitel")}
               onwahl={(s: Podcastsortierung) => onaendern((a) => ({ ...a, sortierung: s }))} />
    </span>
    <button class="knopf" type="button" title={t("podcastAnsicht.aktualisierenHilfe")} aria-label={t("podcastAnsicht.aktualisieren")} disabled={laedt}
            onclick={() => { onaktualisieren(); sfx.click(); }}>
      <i class="fa-solid fa-rotate" class:fa-spin={laedt}></i><span class="rh-breit">{t("podcastAnsicht.aktualisieren")}</span></button>
  </div>
  <div class="rh-werkzeug-zeile">
    <div class="rh-aktiv-chips" aria-label={t("podcastAnsicht.aktiveFilter")}>
      {#each chips as c (`${c.art}:${c.wert}`)}
        <span class="chip">{t(`podcastAnsicht.chip_${c.art}`)}: <b>{c.text}</b><button type="button" aria-label={t("podcastAnsicht.filterEntfernen")}
              title={t("podcastAnsicht.entfernen")} onclick={() => ohne(c)}><i class="fa-solid fa-xmark"></i></button></span>
      {:else}
        <span class="rh-leer-chips">{t("podcastAnsicht.keineFilter")}</span>
      {/each}
    </div>
    {#if stand}
      <p class="rh-hinweis" title={t("podcastAnsicht.automatischHilfe")}>
        <ak-led farbe={stand.automatisch ? "gruen" : "bernstein"} zustand="an" groesse="klein"></ak-led>
        <span>{#if stand.automatisch && bis}{t("podcastAnsicht.naechsteIn", { zeit: "" })}<b>{bis}</b>{:else}{t("podcastAnsicht.automatischAus")}{/if}</span>
        <a href="/einstellungen/podcast" onclick={(e) => { e.preventDefault(); oneinstellungen(); }}>{t("podcastAnsicht.abstandAendern")}<i class="fa-solid fa-arrow-right"></i></a>
      </p>
    {/if}
  </div>
</div>
