<script lang="ts">
  // Seitenleiste der Podcasts (Entwurf podcasts.html): oben eine schlichte Wahl (alle, ungehört, heruntergeladen),
  // darunter die Abos mit der Zahl ungehörter Folgen. Ein Klick wählt genau ein Abo (Nutzer: "meist wird eh nur einer
  // gewählt"), noch einmal zurück zu allen; mit Befehls- oder Strg-Taste mehrere. Angeheftete stehen fest oben
  // (Nadel am Abo heftet an und löst). Reihenfolge per Ziehen an der Griffleiste: das gezogene Abo bleibt blass sichtbar,
  // ein gestrichelter Platzhalter mit seinem Namen steht dort, wo es landet (Nutzer 20.11.2026: "man dockt immer blind
  // an"); gezogen wird innerhalb der eigenen Gruppe (angeheftet oder übrige).
  import { t } from "../../lib/i18n.svelte.js";
  import { FOLGENWAHL, type Abo, type Folgenwahl } from "../../lib/podcasts";
  import AboBild from "./AboBild.svelte";

  let { abos, gewaehlt, wahl, offen, onwahl, onabos, onordnen, onanheften, onabonnieren, onzu }: {
    abos: Abo[];
    gewaehlt: number[];
    wahl: Folgenwahl;
    offen: boolean;
    onwahl: (w: Folgenwahl) => void;
    onabos: (ids: number[]) => void;
    onordnen: (ids: number[]) => void;
    onanheften: (id: number, an: boolean) => void;
    onabonnieren: () => void;
    onzu: () => void;
  } = $props();

  const alleUngehoert = $derived(abos.reduce((s, a) => s + a.ungehoert, 0));
  const angeheftet = $derived(abos.filter((a) => a.angeheftet));
  const uebrige = $derived(abos.filter((a) => !a.angeheftet));

  let gezogen = $state<Abo | null>(null);
  /** wohin es fällt: vor oder hinter dieses Abo */
  let ziel = $state<{ id: number; nach: boolean } | null>(null);

  function waehlen(e: MouseEvent | KeyboardEvent, id: number) {
    if (e.metaKey || e.ctrlKey) onabos(gewaehlt.includes(id) ? gewaehlt.filter((x) => x !== id) : [...gewaehlt, id]);
    else onabos(gewaehlt.length === 1 && gewaehlt[0] === id ? [] : [id]);
  }

  function ueber(e: DragEvent, a: Abo) {
    if (!gezogen || gezogen.angeheftet !== a.angeheftet) return;      // nur in der eigenen Gruppe
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
    ziel = { id: a.id, nach: e.clientY > r.top + r.height / 2 };
  }

  function ablegen(e: DragEvent) {
    e.preventDefault();
    const z = ziel, g = gezogen;
    ende();
    if (!z || !g || z.id === g.id) return;
    const ids = abos.map((a) => a.id).filter((id) => id !== g.id);
    ids.splice(ids.indexOf(z.id) + (z.nach ? 1 : 0), 0, g.id);
    onordnen(ids);
  }

  function ende() {
    gezogen = null;
    ziel = null;
  }
</script>

{#snippet platzhalter(a: Abo, nach: boolean)}
  {#if gezogen && ziel?.id === a.id && ziel.nach === nach && gezogen.id !== a.id}
    <div class="rh-abo-platz" aria-hidden="true" ondragover={(e) => e.preventDefault()} ondrop={ablegen}><i class="fa-solid fa-arrow-right-to-bracket"></i>{gezogen.titel}</div>
  {/if}
{/snippet}

{#snippet zeile(a: Abo)}
  {@const an = gewaehlt.includes(a.id)}
  {@render platzhalter(a, false)}
  <div class="rh-facette rh-abo" class:an class:gezogen={gezogen?.id === a.id} title={a.autor} role="button" tabindex="0" aria-pressed={an}
       onclick={(e) => waehlen(e, a.id)} onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); waehlen(e, a.id); } }}
       ondragover={(e) => ueber(e, a)} ondrop={ablegen}>
    <span class="rh-griff" draggable="true" title={t("podcastAnsicht.ziehenHilfe")} aria-hidden="true"
          ondragstart={(e) => { gezogen = a; e.dataTransfer?.setData("text/plain", String(a.id)); if (e.dataTransfer) e.dataTransfer.effectAllowed = "move"; }}
          ondragend={ende}><i class="fa-solid fa-grip-vertical"></i></span>
    <ak-led farbe="gelb" zustand={an ? "an" : "aus"} groesse="klein"></ak-led>
    <AboBild abo={a} klein />
    <span class="rh-abo-name">{a.titel}{#if a.autoLaden} <i class="fa-solid fa-cloud-arrow-down rh-auto" title={t("podcastAnsicht.autoHilfe")}></i>{/if}</span>
    <span class="rh-abo-ende">
      <span class="rh-zahl" title={t("podcastAnsicht.ungehoert")}>{a.ungehoert || ""}</span>
      <button class="rh-nadel" class:an={a.angeheftet} type="button" aria-pressed={a.angeheftet}
              aria-label="{a.angeheftet ? t('podcastAnsicht.loesen') : t('podcastAnsicht.anheften')}: {a.titel}"
              title={a.angeheftet ? t("podcastAnsicht.loesenHilfe") : t("podcastAnsicht.anheftenHilfe")}
              onclick={(e) => { e.stopPropagation(); onanheften(a.id, !a.angeheftet); }}><i class="fa-solid fa-thumbtack"></i></button>
    </span>
  </div>
  {@render platzhalter(a, true)}
{/snippet}

<aside class="rh-filter rh-podcast-leiste" class:offen id="rh-podcast-leiste" aria-label={t("podcastAnsicht.abosUndFilter")}>
  <div class="rh-filter-oben rh-folgen-wahl">
    <div class="segment" role="group" aria-label={t("podcastAnsicht.welcheFolgen")}>
      {#each FOLGENWAHL as w (w)}
        <button type="button" class:aktiv={wahl === w} aria-pressed={wahl === w} title={w === "heruntergeladen" ? t("podcastAnsicht.heruntergeladenHilfe") : undefined}
                onclick={() => onwahl(w)}>{t(`podcastAnsicht.wahl_${w}`)}</button>
      {/each}
    </div>
    <button class="rh-kopf-taste rh-filter-zu" type="button" aria-label={t("radio.schliessen")} title={t("radio.schliessen")} onclick={onzu}>
      <i class="fa-solid fa-xmark"></i></button>
  </div>
  <div class="rh-filter-rollt">
    {#if angeheftet.length}
      <section class="rh-gruppe">
        <div class="rh-gruppe-kopf"><h3>{t("podcastAnsicht.angeheftet")}</h3></div>
        <div class="rh-facetten rh-abos">{#each angeheftet as a (a.id)}{@render zeile(a)}{/each}</div>
      </section>
    {/if}
    <section class="rh-gruppe">
      <div class="rh-gruppe-kopf"><h3>{t("podcastAnsicht.abos")}</h3>
        <a href="/podcasts?verzeichnis=1" title={t("podcastAnsicht.abonnierenHilfe")} onclick={(e) => { e.preventDefault(); onabonnieren(); }}>{t("podcastAnsicht.abonnieren")}</a></div>
      {#if abos.length}
        <div class="rh-facetten rh-abos">
          <button class="rh-facette rh-alle-abos" class:an={!gewaehlt.length} type="button" aria-pressed={!gewaehlt.length} onclick={() => onabos([])}>
            <ak-led farbe="gelb" zustand={gewaehlt.length ? "aus" : "an"} groesse="klein"></ak-led>
            <span class="rh-abo-name">{t("podcastAnsicht.alleAbos")}</span><span class="rh-zahl" title={t("podcastAnsicht.ungehoert")}>{alleUngehoert || ""}</span>
          </button>
          {#each uebrige as a (a.id)}{@render zeile(a)}{/each}
        </div>
        <p class="rh-still rh-abos-hinweis"><i class="fa-solid fa-grip-vertical"></i>{t("podcastAnsicht.ordnenHinweis")}</p>
      {:else}
        <p class="rh-leer-facette">{t("podcastAnsicht.keineAbos")}</p>
      {/if}
    </section>
  </div>
</aside>
