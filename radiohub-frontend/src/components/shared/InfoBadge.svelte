<script>
  /**
   * InfoBadge - Legacy-Wrapper um HiFiBadge
   * Mappt alte type-Werte auf HiFiBadge-Farben.
   */
  import HiFiBadge from '../hifi/HiFiBadge.svelte';

  let { type = 'default', label = '' } = $props();

  const colorMap = {
    downloaded: 'blue',
    played: 'green',
    resume: 'amber',
    new: 'green',
    auto: 'blue',
    default: 'muted',
  };
</script>

<HiFiBadge {label} color={colorMap[type] || 'muted'} />
