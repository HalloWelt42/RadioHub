<script lang="ts">
  // Seitenleiste der Podcasts (Entwurf podcasts.html): oben eine schlichte Wahl (alle, ungehört, gespeichert),
  // darunter die Abos mit der Zahl ungehörter Folgen. Ein Klick wählt genau ein Abo (Nutzer: "meist wird eh nur einer
  // gewählt"), noch einmal zurück zu allen; mit Befehls- oder Strg-Taste mehrere. Angeheftete stehen fest oben
  // (Nadel am Abo heftet an und löst). Darunter die eigenen Ordner untereinander (RAD-23), dann die losen Abos.
  // Gezogen wird an der Griffleiste: das gezogene bleibt blass sichtbar, ein gestrichelter Platzhalter mit seinem Namen
  // steht dort, wo es landet (Nutzer 20.11.2026: "man dockt immer blind an"). Ein Abo kommt per Ziehen auf einen
  // Ordnerkopf oder zwischen dessen Abos in den Ordner, per Ziehen auf "Ohne Ordner" wieder heraus; angeheftete bleiben
  // unter sich. Ordner lassen sich ebenso umsortieren.
  import { t } from "../../lib/i18n.svelte.js";
  import { angeboteneWahl, podcastquelle, type Abo, type Folgenwahl, type Ordner } from "../../lib/podcasts";
  import AboBild from "./AboBild.svelte";
  import OrdnerKopf from "./OrdnerKopf.svelte";

  let { abos, ordner, gewaehlt, wahl, offen, onwahl, onabos, onordnen, onanheften, onabonnieren, onzu,
        onordnerneu, onordneraendern, onordnerloeschen, onordnerordnen, onzuordnen }: {
    abos: Abo[];
    ordner: Ordner[];
    gewaehlt: number[];
    wahl: Folgenwahl;
    offen: boolean;
    onwahl: (w: Folgenwahl) => void;
    onabos: (ids: number[]) => void;
    onordnen: (ids: number[]) => void;
    onanheften: (id: number, an: boolean) => void;
    onabonnieren: () => void;
    onzu: () => void;
    onordnerneu: (name: string) => void;
    onordneraendern: (id: string, teil: Partial<Pick<Ordner, "name" | "offen">>) => void;
    onordnerloeschen: (id: string) => Promise<void>;
    onordnerordnen: (ids: string[]) => void;
    /** Abo in einen Ordner (null: lose) und an seine neue Stelle in der Reihenfolge aller Abos */
    onzuordnen: (aboId: number, ordnerId: string | null, ids: number[]) => void;
  } = $props();

  const alleUngehoert = $derived(abos.reduce((s, a) => s + a.ungehoert, 0));
  const angeheftet = $derived(abos.filter((a) => a.angeheftet));
  const bekannt = $derived(new Set(ordner.map((o) => o.id)));
  /** Ordner eines Abos; einer, den es nicht (mehr) gibt, zählt als lose */
  const ordnerVon = (a: Abo) => (a.ordnerId && bekannt.has(a.ordnerId) ? a.ordnerId : null);
  const imOrdner = (id: string | null) => abos.filter((a) => !a.angeheftet && ordnerVon(a) === id);
  const lose = $derived(imOrdner(null));

  type Gezogen = { art: "abo"; abo: Abo } | { art: "ordner"; ordner: Ordner };
  type Ziel = { art: "abo"; id: number; nach: boolean } | { art: "in"; ordnerId: string | null } | { art: "ordner"; id: string; nach: boolean };
  let gezogen = $state<Gezogen | null>(null);
  let ziel = $state<Ziel | null>(null);

  let neuName = $state("");
  let legtAn = $state(false);

  function waehlen(e: MouseEvent | KeyboardEvent, id: number) {
    if (e.metaKey || e.ctrlKey) onabos(gewaehlt.includes(id) ? gewaehlt.filter((x) => x !== id) : [...gewaehlt, id]);
    else onabos(gewaehlt.length === 1 && gewaehlt[0] === id ? [] : [id]);
  }

  function ziehen(e: DragEvent, was: Gezogen) {
    gezogen = was;
    e.dataTransfer?.setData("text/plain", was.art === "abo" ? String(was.abo.id) : was.ordner.id);
    if (e.dataTransfer) e.dataTransfer.effectAllowed = "move";
  }

  function erlauben(e: DragEvent) {
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
  }

  const unterhalb = (e: DragEvent) => { const r = (e.currentTarget as HTMLElement).getBoundingClientRect(); return e.clientY > r.top + r.height / 2; };

  /** über einem Abo: vor oder hinter ihm; angeheftete nur unter sich, die übrigen auch über Ordnergrenzen */
  function ueberAbo(e: DragEvent, a: Abo) {
    if (gezogen?.art !== "abo" || gezogen.abo.angeheftet !== a.angeheftet) return;
    erlauben(e);
    ziel = { art: "abo", id: a.id, nach: unterhalb(e) };
  }

  /** über einem Ordnerkopf: ein Abo kommt hinein, ein Ordner davor oder dahinter */
  function ueberOrdner(e: DragEvent, o: Ordner) {
    if (!gezogen || (gezogen.art === "abo" && gezogen.abo.angeheftet)) return;
    erlauben(e);
    ziel = gezogen.art === "abo" ? { art: "in", ordnerId: o.id } : { art: "ordner", id: o.id, nach: unterhalb(e) };
  }

  function ueberLose(e: DragEvent) {
    if (gezogen?.art !== "abo" || gezogen.abo.angeheftet) return;
    erlauben(e);
    ziel = { art: "in", ordnerId: null };
  }

  function ablegen(e: DragEvent) {
    e.preventDefault();
    const z = ziel, g = gezogen;
    ende();
    if (!z || !g) return;
    if (g.art === "ordner") {
      if (z.art !== "ordner" || z.id === g.ordner.id) return;
      const ids = ordner.map((o) => o.id).filter((id) => id !== g.ordner.id);
      ids.splice(ids.indexOf(z.id) + (z.nach ? 1 : 0), 0, g.ordner.id);
      onordnerordnen(ids);
      return;
    }
    const ids = abos.map((a) => a.id).filter((id) => id !== g.abo.id);
    if (z.art === "abo") {
      if (z.id === g.abo.id) return;
      ids.splice(ids.indexOf(z.id) + (z.nach ? 1 : 0), 0, g.abo.id);
      const zielAbo = abos.find((a) => a.id === z.id);
      const nach = zielAbo && !zielAbo.angeheftet ? ordnerVon(zielAbo) : ordnerVon(g.abo);
      if (nach === ordnerVon(g.abo)) onordnen(ids);
      else onzuordnen(g.abo.id, nach, ids);
    } else if (z.art === "in") {
      if (z.ordnerId === ordnerVon(g.abo)) return;
      ids.push(g.abo.id);                                                     // hinten im Ordner
      onzuordnen(g.abo.id, z.ordnerId, ids);
    }
  }

  function ende() {
    gezogen = null;
    ziel = null;
  }

  function anlegen() {
    const name = neuName.trim();
    legtAn = false;
    neuName = "";
    if (name) onordnerneu(name);
  }

  function fokus(el: HTMLInputElement) {
    el.focus();
  }
</script>

{#snippet platzhalter(titel: string, zeigen: boolean)}
  {#if zeigen}
    <div class="rh-abo-platz" aria-hidden="true" ondragover={(e) => e.preventDefault()} ondrop={ablegen}><i class="fa-solid fa-arrow-right-to-bracket"></i>{titel}</div>
  {/if}
{/snippet}

{#snippet zeile(a: Abo)}
  {@const an = gewaehlt.includes(a.id)}
  {@const hier = gezogen?.art === "abo" && ziel?.art === "abo" && ziel.id === a.id && gezogen.abo.id !== a.id}
  {@render platzhalter(gezogen?.art === "abo" ? gezogen.abo.titel : "", hier && ziel?.art === "abo" && !ziel.nach)}
  <div class="rh-facette rh-abo" class:an class:gezogen={gezogen?.art === "abo" && gezogen.abo.id === a.id} title={a.autor} role="button" tabindex="0" aria-pressed={an}
       onclick={(e) => waehlen(e, a.id)} onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); waehlen(e, a.id); } }}
       ondragover={(e) => ueberAbo(e, a)} ondrop={ablegen}>
    <span class="rh-griff" draggable="true" title={t("podcastAnsicht.ziehenHilfe")} aria-hidden="true"
          ondragstart={(e) => ziehen(e, { art: "abo", abo: a })} ondragend={ende}><i class="fa-solid fa-grip-vertical"></i></span>
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
  {@render platzhalter(gezogen?.art === "abo" ? gezogen.abo.titel : "", hier && ziel?.art === "abo" && ziel.nach)}
{/snippet}

<aside class="rh-filter rh-podcast-leiste" class:offen id="rh-podcast-leiste" aria-label={t("podcastAnsicht.abosUndFilter")}>
  <div class="rh-filter-oben rh-folgen-wahl">
    <div class="segment" role="group" aria-label={t("podcastAnsicht.welcheFolgen")}>
      {#each angeboteneWahl(podcastquelle.faehig.speichern) as w (w)}
        <button type="button" class:aktiv={wahl === w} aria-pressed={wahl === w} title={w === "gespeichert" ? t("podcastAnsicht.gespeichertHilfe") : undefined}
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
        {#if abos.length}<button type="button" title={t("podcastAnsicht.ordnerAnlegenHilfe")} onclick={() => (legtAn = true)}>{t("podcastAnsicht.ordnerAnlegen")}</button>{/if}
        <a href="/podcasts?verzeichnis=1" title={t("podcastAnsicht.abonnierenHilfe")} onclick={(e) => { e.preventDefault(); onabonnieren(); }}>{t("podcastAnsicht.abonnieren")}</a></div>
      {#if abos.length}
        <div class="rh-facetten rh-abos">
          <button class="rh-facette rh-alle-abos" class:an={!gewaehlt.length} type="button" aria-pressed={!gewaehlt.length} onclick={() => onabos([])}>
            <span class="rh-abo-name">{t("podcastAnsicht.alleAbos")}</span><span class="rh-zahl" title={t("podcastAnsicht.ungehoert")}>{alleUngehoert || ""}</span>
          </button>
          {#if legtAn}
            <span class="rh-ordner-eingabe rh-ordner-neu">
              <i class="fa-solid fa-folder-plus" aria-hidden="true"></i>
              <input type="text" bind:value={neuName} maxlength="80" placeholder={t("podcastAnsicht.ordnerName")} aria-label={t("podcastAnsicht.ordnerName")} use:fokus
                     onkeydown={(e) => { if (e.key === "Enter") anlegen(); if (e.key === "Escape") { legtAn = false; neuName = ""; } }} onblur={anlegen} />
            </span>
          {/if}
          {#each ordner as o (o.id)}
            {@const inhalt = imOrdner(o.id)}
            {@const ordnerHier = gezogen?.art === "ordner" && ziel?.art === "ordner" && ziel.id === o.id && gezogen.ordner.id !== o.id}
            {@render platzhalter(gezogen?.art === "ordner" ? gezogen.ordner.name : "", ordnerHier && ziel?.art === "ordner" && !ziel.nach)}
            <div class="rh-ordner-block" class:gezogen={gezogen?.art === "ordner" && gezogen.ordner.id === o.id}>
              <OrdnerKopf ordner={o} abos={inhalt} ziel={ziel?.art === "in" && ziel.ordnerId === o.id}
                          ongriff={(e) => ziehen(e, { art: "ordner", ordner: o })} onende={ende}
                          onueber={(e) => ueberOrdner(e, o)} onablegen={ablegen}
                          onumbenennen={(name) => onordneraendern(o.id, { name })} onklappen={() => onordneraendern(o.id, { offen: !o.offen })}
                          onloeschen={() => onordnerloeschen(o.id)} />
              {#if o.offen}
                <div class="rh-ordner-inhalt">
                  {#each inhalt as a (a.id)}{@render zeile(a)}{:else}<p class="rh-still rh-ordner-leer">{t("podcastAnsicht.ordnerLeer")}</p>{/each}
                </div>
              {/if}
            </div>
            {@render platzhalter(gezogen?.art === "ordner" ? gezogen.ordner.name : "", ordnerHier && ziel?.art === "ordner" && ziel.nach)}
          {/each}
          {#if ordner.length}
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="rh-ohne-ordner" class:ziel={ziel?.art === "in" && ziel.ordnerId === null} ondragover={ueberLose} ondrop={ablegen}>
              {t("podcastAnsicht.ohneOrdner")}</div>
          {/if}
          {#each lose as a (a.id)}{@render zeile(a)}{/each}
        </div>
        <p class="rh-still rh-abos-hinweis"><i class="fa-solid fa-grip-vertical"></i>{t(ordner.length ? "podcastAnsicht.ordnerHinweis" : "podcastAnsicht.ordnenHinweis")}</p>
      {:else}
        <p class="rh-leer-facette">{t("podcastAnsicht.keineAbos")}</p>
      {/if}
    </section>
  </div>
</aside>
