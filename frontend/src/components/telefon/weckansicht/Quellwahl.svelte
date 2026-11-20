<script lang="ts">
  // Beim Klingeln jederzeit zwischen Radio (oder Podcast) und Weckton wechseln (Nutzer 20.11.2026); gleiche Höhe wie die
  // Tasten daneben, die gewählte Fläche reicht bis an den Rand. Aussehen über die Klasse der Gestaltung.
  import type { Gestaltungsprops } from "./typen";
  let { bild, tun, t }: Gestaltungsprops = $props();
</script>

<div class="wa-quelle" role="radiogroup" aria-label={t("weckquelle")}>
  <button type="button" role="radio" aria-checked={bild.quelle === "radio"} class:an={bild.quelle === "radio"} onclick={() => tun.quelle("radio")}>
    <i class="fa-solid fa-radio"></i>{bild.quelleName}</button>
  <button type="button" role="radio" aria-checked={bild.quelle === "weckton"} class:an={bild.quelle === "weckton"} onclick={() => tun.quelle("weckton")}>
    <i class="fa-solid fa-bell"></i>{t("weckton")}</button>
</div>
