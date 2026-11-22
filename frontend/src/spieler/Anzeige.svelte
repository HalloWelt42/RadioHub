<script lang="ts">
  // Modul Anzeige: das Glas zeigt nur an (Nutzer 17.11.2026: keine Bedienelemente im Glas). Oben die Statuszeile als
  // kleine Punktmatrix ohne Leuchte (Nutzer 20.11.2026: "der teil sollte auch matrix sein nur kleiner", "miniLED passt
  // nicht dazu"): was geschieht, Codec und Bitrate, rechts bündig der Hinweis (Wechsel gesperrt während der Aufnahme,
  // sonst die Bitrate des Zeitversatzes, gewählt in der Steuerung). Darunter die große Punktmatrix mit dem Sender und
  // die Titelzeile, ebenfalls kleine Punktmatrix (Nutzer 20.11.2026: "muss auch matrixanzeige sein"), die immer steht
  // und ohne Titel dunkel bleibt. Alle Matrizen haben so viele Stellen, wie ihre Breite trägt, füllen ihr Glas
  // (rasterbreite.ts) und laufen, wenn der Text länger ist; die große führt zur Quelle.
  import { t } from "../lib/i18n.svelte.js";
  import * as sfx from "../lib/uiSounds.js";
  import { zurQuelle } from "./aktionen";
  import type { Anzeige } from "./kanzel";
  import { rasterStellen, statuszeile, STATUS_JE_SCHRIFT, ZEICHEN_JE_SCHRIFT } from "./rasterbreite";

  let { anzeige, hinweis, aufnahme }: {
    anzeige: Anzeige;
    /** Leuchtschrift rechts in der Statuszeile (Bitrate des Zeitversatzes), oder keine */
    hinweis: string | null;
    /** eine Aufnahme läuft (Sprung zum aufnehmenden Sender) */
    aufnahme: boolean;
  } = $props();

  let stellen = $state(16);
  let statusStellen = $state(40);
  let titelStellen = $state(40);
  const statusLinks = $derived([anzeige.art, anzeige.format].filter(Boolean).join("  "));
  const statusRechts = $derived(hinweis);
  const status = $derived(statuszeile(statusLinks, statusRechts, statusStellen));
  const quelleHilfe = $derived(aufnahme ? t("player.zumSender") : t("player.zurQuelle"));
</script>

<section class="rh-modul rh-m-anzeige" aria-label={t("kanzel.anzeige")}><span class="ak-etikett">{t("kanzel.anzeige")}</span>
  <div class="ak-glas rh-display" data-ton={anzeige.ton}>
    <div class="rh-display-zeile"
      use:rasterStellen={{ jeSchrift: STATUS_JE_SCHRIFT, melden: (n) => (statusStellen = n) }}>
      {#key statusStellen}<ak-segmente art="punkt" stellen={statusStellen} lauf="200" farbe="gruen" text={status}></ak-segmente>{/key}
    </div>
    <button class="rh-display-quelle" type="button" disabled={!anzeige.sender} title={anzeige.sender ? quelleHilfe : undefined}
      aria-label={anzeige.sender ? `${anzeige.sender}: ${quelleHilfe}` : t("kanzel.senderHilfe")}
      onclick={() => { zurQuelle(); sfx.click(); }} use:rasterStellen={{ jeSchrift: ZEICHEN_JE_SCHRIFT, melden: (n) => (stellen = n) }}>
      <!-- der Appkern liest die Stellen beim Einhängen: neue Stellenzahl, neue Anzeige (nur wenn sich die Breite ändert) -->
      {#key stellen}<ak-segmente art="punkt" {stellen} lauf="280" farbe="gruen" text={anzeige.sender}></ak-segmente>{/key}
    </button>
    <div class="rh-display-zeile rh-display-titel" title={anzeige.titel ?? undefined}
      use:rasterStellen={{ jeSchrift: STATUS_JE_SCHRIFT, melden: (n) => (titelStellen = n) }}>
      {#key titelStellen}<ak-segmente art="punkt" stellen={titelStellen} lauf="200" farbe="gruen" text={anzeige.titel ?? ""}></ak-segmente>{/key}
    </div>
  </div>
</section>
