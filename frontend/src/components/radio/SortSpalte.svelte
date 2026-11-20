<script lang="ts">
  // Sortierbarer Titel im stehenden Tabellenkopf (RAD-25, Nutzer 21.11.2026: "die sortierung könnte man sich samt button
  // sparen, wenn man das direkt an der table head macht"). Sieht aus wie der Spaltentitel selbst; der aktive trägt einen
  // Pfeil in seiner Richtung. Ein Klick sortiert nach der Spalte; wo die Spalte zwei Richtungen kennt, schaltet ein
  // zweiter Klick um (das entscheidet der Aufrufer über `onwahl`).
  let { titel, hilfe, aktiv, absteigend, onwahl }: {
    titel: string;
    /** Richtung in Worten, etwa "meiste zuerst" */
    hilfe: string;
    aktiv: boolean;
    absteigend: boolean;
    onwahl: () => void;
  } = $props();
</script>

<button class="rh-sortspalte" class:aktiv type="button" aria-pressed={aktiv} title="{titel} · {hilfe}" onclick={onwahl}>
  {titel}<i class="fa-solid {absteigend ? 'fa-arrow-down-long' : 'fa-arrow-up-long'}" aria-hidden="true"></i>
</button>
