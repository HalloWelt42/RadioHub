<script>
  // Einstieg der Oberfläche (RAD-6): erst die Anmeldung, dann die App. Endet die Sitzung (der Server weist sie ab),
  // zeigt sie wieder die Anmeldung.
  import App from '../App.svelte';
  import Anmeldung from './Anmeldung.svelte';
  import { actions } from '../lib/store.svelte.js';
  import { sitzung, starten } from '../lib/sitzung.svelte.js';

  actions.initTheme();
  void starten();
</script>

{#if sitzung.angemeldet}
  <App />
{:else if sitzung.geladen}
  <Anmeldung />
{/if}
