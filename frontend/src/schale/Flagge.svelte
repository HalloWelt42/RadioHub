<script lang="ts">
  // Flagge einer Sprache für die Sprachwahl (RAD-71, RAD-99): klein, leicht gerundet, mit dunklem Rand, für alle 20
  // Sprachen vereinfacht gezeichnet (ohne Wappen und feine Einzelheiten, die in dieser Größe nicht lesbar wären). Die
  // Farben gehören zur Flagge und sind fest. Englisch zeigt das Vereinigte Königreich, Norwegisch Bokmål Norwegen.
  let { sprache }: { sprache: string } = $props();
  const id = $props.id();

  /** waagrechte Streifen von oben nach unten */
  const WAAGRECHT: Record<string, string[]> = {
    de: ["#000000", "#dd0000", "#ffce00"], nl: ["#ae1c28", "#ffffff", "#21468b"], ru: ["#ffffff", "#0039a6", "#d52b1e"],
    hu: ["#cd2a3e", "#ffffff", "#436f4d"], pl: ["#ffffff", "#dc143c"], sk: ["#ffffff", "#0b4ea2", "#ee1c25"],
  };
  /** senkrechte Streifen von links nach rechts */
  const SENKRECHT: Record<string, string[]> = {
    fr: ["#0055a4", "#ffffff", "#ef4135"], it: ["#009246", "#ffffff", "#ce2b37"], ro: ["#002b7f", "#fcd116", "#ce1126"],
  };
  /** nordisches Kreuz: Grund, Kreuz, inneres Kreuz (Norwegen) */
  const KREUZ: Record<string, [string, string, string?]> = {
    da: ["#c8102e", "#ffffff"], sv: ["#006aa7", "#fecc00"], fi: ["#ffffff", "#002f6c"], no: ["#ba0c2f", "#ffffff", "#00205b"],
  };
</script>

<svg class="rh-flagge" viewBox="0 0 60 36" preserveAspectRatio="none" aria-hidden="true">
  {#if WAAGRECHT[sprache]}
    {@const farben = WAAGRECHT[sprache]}
    {#each farben as farbe, i (i)}<rect y={(36 / farben.length) * i} width="60" height={36 / farben.length} fill={farbe} />{/each}
    {#if sprache === "sk"}
      <!-- Wappen vereinfacht: rotes Schild mit weißem Doppelkreuz, damit sie nicht wie Russland aussieht -->
      <path d="M13,8 h16 v12 q0,8 -8,11 q-8,-3 -8,-11 z" fill="#ee1c25" stroke="#ffffff" stroke-width="1.5" />
      <path d="M21,11 v16 M17,15 h8 M16,19 h10" stroke="#ffffff" stroke-width="2" />
    {/if}
  {:else if SENKRECHT[sprache]}
    {#each SENKRECHT[sprache] as farbe, i (i)}<rect x={20 * i} width="20" height="36" fill={farbe} />{/each}
  {:else if KREUZ[sprache]}
    {@const [grund, kreuz, innen] = KREUZ[sprache]}
    <rect width="60" height="36" fill={grund} />
    <path d="M22,0 v36 M0,18 h60" stroke={kreuz} stroke-width="8" />
    {#if innen}<path d="M22,0 v36 M0,18 h60" stroke={innen} stroke-width="4" />{/if}
  {:else if sprache === "en"}
    <clipPath id="{id}-diagonal"><path d="M30,18 h30 v18 z v18 h-30 z h-30 v-18 z v-18 h30 z" /></clipPath>
    <rect width="60" height="36" fill="#012169" />
    <path d="M0,0 L60,36 M60,0 L0,36" stroke="#ffffff" stroke-width="7" />
    <path d="M0,0 L60,36 M60,0 L0,36" stroke="#c8102e" stroke-width="4" clip-path="url(#{id}-diagonal)" />
    <path d="M30,0 v36 M0,18 h60" stroke="#ffffff" stroke-width="12" />
    <path d="M30,0 v36 M0,18 h60" stroke="#c8102e" stroke-width="7" />
  {:else if sprache === "es"}
    <rect width="60" height="36" fill="#aa151b" /><rect y="9" width="60" height="18" fill="#f1bf00" />
  {:else if sprache === "pt"}
    <rect width="60" height="36" fill="#da291c" /><rect width="24" height="36" fill="#046a38" />
    <circle cx="24" cy="18" r="7" fill="#ffe900" /><circle cx="24" cy="18" r="4" fill="#da291c" stroke="#ffffff" stroke-width="1" />
  {:else if sprache === "cs"}
    <rect width="60" height="18" fill="#ffffff" /><rect y="18" width="60" height="18" fill="#d7141a" />
    <path d="M0,0 L30,18 L0,36 z" fill="#11457e" />
  {:else if sprache === "tr"}
    <rect width="60" height="36" fill="#e30a17" />
    <circle cx="22" cy="18" r="9" fill="#ffffff" /><circle cx="24.5" cy="18" r="7.2" fill="#e30a17" />
    <path d="M33,18 l7.6,-2.5 l-4.7,6.5 v-8 l4.7,6.5 z" fill="#ffffff" />
  {:else if sprache === "ja"}
    <rect width="60" height="36" fill="#ffffff" /><circle cx="30" cy="18" r="10.8" fill="#bc002d" />
  {:else if sprache === "zh"}
    <rect width="60" height="36" fill="#ee1c25" />
    <path d="M10,4.5 l2,6 h6.3 l-5.1,3.7 l2,6 l-5.2,-3.7 l-5.2,3.7 l2,-6 l-5.1,-3.7 h6.3 z" fill="#ffff00" />
    {#each [[21, 3.5], [24, 7.5], [24, 12.5], [21, 16]] as [x, y] (`${x},${y}`)}<circle cx={x} cy={y} r="1.4" fill="#ffff00" />{/each}
  {:else}
    <rect width="60" height="36" fill="currentColor" opacity=".3" />
  {/if}
</svg>
