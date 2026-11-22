<script lang="ts">
  // Flagge einer Sprache für den Sprachknopf im Kopf (RAD-71): klein, leicht gerundet, mit dunklem Rand. Die Farben gehören
  // zur Flagge und sind fest. Englisch zeigt die Flagge des Vereinigten Königreichs.
  let { sprache }: { sprache: string } = $props();
  const id = $props.id();
</script>

<svg class="rh-flagge" viewBox="0 0 60 36" preserveAspectRatio="none" aria-hidden="true">
  {#if sprache === "de"}
    <rect width="60" height="12" fill="#000000" />
    <rect y="12" width="60" height="12" fill="#dd0000" />
    <rect y="24" width="60" height="12" fill="#ffce00" />
  {:else if sprache === "en"}
    <clipPath id="{id}-diagonal"><path d="M30,18 h30 v18 z v18 h-30 z h-30 v-18 z v-18 h30 z" /></clipPath>
    <rect width="60" height="36" fill="#012169" />
    <path d="M0,0 L60,36 M60,0 L0,36" stroke="#ffffff" stroke-width="7" />
    <path d="M0,0 L60,36 M60,0 L0,36" stroke="#c8102e" stroke-width="4" clip-path="url(#{id}-diagonal)" />
    <path d="M30,0 v36 M0,18 h60" stroke="#ffffff" stroke-width="12" />
    <path d="M30,0 v36 M0,18 h60" stroke="#c8102e" stroke-width="7" />
  {:else}
    <rect width="60" height="36" fill="currentColor" opacity=".3" />
  {/if}
</svg>
