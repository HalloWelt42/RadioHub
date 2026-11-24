<script lang="ts">
  // Einstellungen > Allgemein > Bedienung, Karte Fehlersuche (RAD-143): was der Messmodus mitgeschrieben hat. Je Tag eine Datei mit
  // Zahl und Größe, auf Wunsch der Bericht (Auffälliges mit Uhrzeit, Grenzen des Schnitts nach Grund), laden, alles löschen mit
  // Rückfrage, die nennt, was verschwindet.
  import { Rueckfrage } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { actions } from "../../lib/store.svelte.js";
  import { groesse, uhrzeit } from "../../lib/aufnahmen/anzeige";
  import { netz } from "../../lib/radio/netz";

  interface Datei { name: string; groesse: number; ereignisse: number; von: string; bis: string }
  interface Bericht { ereignisse: number; grenzen: Record<string, number>; auffaellig: { t: string; was: string; werte: Record<string, unknown> }[] }

  const anfrage = netz();
  const ZEIGEN = 200;
  let dateien = $state<Datei[]>([]);
  let offen = $state("");
  let bericht = $state<Bericht | null>(null);
  let fragt = $state(false);

  async function sicher(arbeit: () => Promise<void>) {
    try { await arbeit(); } catch (f) { actions.showToast((f as Error).message, "error"); }
  }
  const laden = () => sicher(async () => { dateien = (await anfrage<{ dateien: Datei[] }>("/api/messung")).dateien; });
  $effect(() => { void laden(); });

  function zeigen(name: string) {
    if (offen === name) { offen = ""; return; }
    offen = name;
    bericht = null;
    void sicher(async () => { bericht = await anfrage<Bericht>(`/api/messung/${encodeURIComponent(name)}/bericht`); });
  }
  const loeschen = () => sicher(async () => { fragt = false; await anfrage("/api/messung", { methode: "DELETE" }); await laden(); });
  const tag = (iso: string) => new Date(iso).toLocaleDateString("de-DE");
  const zahl = (n: number) => n.toLocaleString("de-DE");
  const werte = (w: Record<string, unknown>) => Object.entries(w).filter(([, v]) => typeof v !== "object" && v !== "").map(([k, v]) => `${k} ${v}`).join(", ");
</script>

<div class="rh-messung">
  {#each dateien as d (d.name)}
    <div class="rh-messung-zeile">
      <span><b>{tag(d.von)}</b> <span class="rh-zahl">{uhrzeit(d.von)} - {uhrzeit(d.bis)}</span></span>
      <span class="rh-still">{t("einstellungen.messung.umfang", { n: zahl(d.ereignisse), mb: groesse(d.groesse) })}</span>
      <span class="rh-knoepfe">
        <button class="knopf" type="button" aria-expanded={offen === d.name} onclick={() => zeigen(d.name)}><i class="fa-solid fa-list-check"></i>{t("einstellungen.messung.bericht")}</button>
        <a class="knopf" href="/api/messung/{d.name}" download><i class="fa-solid fa-download"></i>{t("einstellungen.messung.laden")}</a>
      </span>
    </div>
    {#if offen === d.name && bericht}
      <div class="rh-messung-bericht">
        {#if Object.keys(bericht.grenzen).length}<p class="rh-still">{t("einstellungen.messung.grenzen")}:
          {Object.entries(bericht.grenzen).map(([g, n]) => `${t(`einstellungen.messung.grund_${g}`)} ${n}`).join(", ")}</p>{/if}
        {#each bericht.auffaellig.slice(-ZEIGEN) as a, i (i)}
          <p><span class="rh-zahl">{uhrzeit(a.t)}</span> <b>{a.was}</b> <span class="rh-still">{werte(a.werte)}</span></p>
        {:else}<p class="rh-still">{t("einstellungen.messung.nichts")}</p>{/each}
      </div>
    {/if}
  {:else}<p class="rh-still">{t("einstellungen.messung.leer")}</p>{/each}
  {#if dateien.length}
    {#if fragt}
      <Rueckfrage frage={t("einstellungen.messung.loeschenFrage", { n: dateien.length, mb: groesse(dateien.reduce((s, d) => s + d.groesse, 0)) })}
                  knopf={t("aufnahmenAnsicht.loeschen")} onabbrechen={() => (fragt = false)} onja={() => void loeschen()} />
    {:else}<button class="knopf" type="button" onclick={() => (fragt = true)}><i class="fa-solid fa-trash-can rh-loeschen"></i>{t("einstellungen.messung.alleLoeschen")}</button>{/if}
  {/if}
</div>
