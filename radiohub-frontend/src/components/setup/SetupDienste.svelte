<script>
  /**
   * SetupDienste - Externe Dienste und Datenquellen
   * Zeigt alle externen Endpunkte mit Richtung, Kategorie, Status.
   * Erlaubt URL-Änderungen für konfigurierbare Dienste.
   */
  import HiFiLed from '../hifi/HiFiLed.svelte';
  import { api } from '../../lib/api.js';
  import { actions } from '../../lib/store.svelte.js';

  let services = $state([]);
  let isLoading = $state(true);
  let editingService = $state(null);
  let editValue = $state('');
  let isSaving = $state(false);

  $effect(() => {
    loadServices();
  });

  async function loadServices() {
    isLoading = true;
    try {
      const result = await api.getServices();
      services = result.services || [];
    } catch (e) {
      // Netzwerkfehler ignorieren
    }
    isLoading = false;
  }

  function startEdit(svc) {
    editingService = svc.id;
    if (Array.isArray(svc.urls)) {
      editValue = svc.urls.join('\n');
    } else {
      editValue = svc.urls || '';
    }
  }

  function cancelEdit() {
    editingService = null;
    editValue = '';
  }

  async function saveService(svc) {
    if (!editValue.trim()) return;
    isSaving = true;
    try {
      let value;
      if (svc.url_type === 'multi') {
        value = editValue.split('\n').map(u => u.trim()).filter(u => u.length > 0);
      } else {
        value = editValue.trim();
      }
      await api.updateServiceUrl(svc.id, value);
      actions.showToast('Endpunkt aktualisiert', 'success');
      cancelEdit();
      await loadServices();
    } catch (e) {
      actions.showToast('Speichern fehlgeschlagen', 'error');
    }
    isSaving = false;
  }

  async function resetService(svc) {
    isSaving = true;
    try {
      await api.resetServiceUrl(svc.id);
      actions.showToast('Standard wiederhergestellt', 'success');
      cancelEdit();
      await loadServices();
    } catch (e) {
      actions.showToast('Zurücksetzen fehlgeschlagen', 'error');
    }
    isSaving = false;
  }

  function directionLabel(dir) {
    switch (dir) {
      case 'eingehend': return 'EINGEHEND';
      case 'ausgehend': return 'AUSGEHEND';
      case 'lokal': return 'LOKAL';
      default: return dir?.toUpperCase() || '';
    }
  }

  function directionColor(dir) {
    switch (dir) {
      case 'eingehend': return 'green';
      case 'lokal': return 'amber';
      default: return 'blue';
    }
  }

  function categoryLabel(cat) {
    switch (cat) {
      case 'radio': return 'RADIO';
      case 'podcast': return 'PODCAST';
      default: return cat?.toUpperCase() || '';
    }
  }

  function formatUrls(svc) {
    if (!svc.urls) return null;
    if (Array.isArray(svc.urls)) return svc.urls;
    return [svc.urls];
  }
</script>

<div class="hifi-panel">
  <div class="hifi-panel-header">
    <span class="hifi-font-label">EXTERNE DIENSTE</span>
    <button class="hifi-btn hifi-btn-small refresh-btn" onclick={loadServices} title="Aktualisieren">
      <i class="fa-solid fa-arrows-rotate" class:fa-spin={isLoading}></i>
    </button>
  </div>

  {#if isLoading && services.length === 0}
    <div class="loading-state">
      <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
    </div>
  {:else}
    <div class="services-grid">
      {#each services as svc}
        {@const isEditing = editingService === svc.id}
        {@const urls = formatUrls(svc)}

        <div class="service-card" class:editing={isEditing}>
          <div class="service-header">
            <div class="service-icon">
              <i class={svc.icon}></i>
            </div>
            <div class="service-title">
              <span class="service-label">{svc.name}</span>
              <span class="service-desc">{svc.description}</span>
            </div>
            <div class="service-badges">
              <span class="badge badge-category">{categoryLabel(svc.category)}</span>
              <span class="badge badge-direction">
                <HiFiLed color={directionColor(svc.direction)} size="small" />
                {directionLabel(svc.direction)}
              </span>
            </div>
          </div>

          {#if !isEditing}
            <div class="service-urls">
              {#if urls}
                {#each urls as url}
                  <code class="service-url">{url}</code>
                {/each}
              {:else if svc.note}
                <span class="service-note">
                  <i class="fa-solid fa-circle-info"></i>
                  {svc.note}
                </span>
              {/if}
              {#if svc.configurable}
                <button class="hifi-btn hifi-btn-small edit-btn" onclick={() => startEdit(svc)} title="Endpunkt ändern">
                  <i class="fa-solid fa-pen"></i>
                </button>
              {/if}
            </div>
          {:else}
            <div class="service-edit">
              {#if svc.url_type === 'multi'}
                <textarea
                  class="hifi-input edit-textarea"
                  bind:value={editValue}
                  placeholder="Eine URL pro Zeile..."
                  rows="3"
                  onkeydown={(e) => { if (e.key === 'Escape') cancelEdit(); }}
                ></textarea>
              {:else}
                <input
                  type="text"
                  class="hifi-input"
                  bind:value={editValue}
                  placeholder="URL eingeben..."
                  onkeydown={(e) => { if (e.key === 'Enter') saveService(svc); if (e.key === 'Escape') cancelEdit(); }}
                />
              {/if}
              <div class="edit-actions">
                <button class="hifi-btn hifi-btn-small" onclick={cancelEdit}>Abbrechen</button>
                <button class="hifi-btn hifi-btn-small" onclick={() => resetService(svc)} disabled={isSaving}>
                  Standard
                </button>
                <button
                  class="hifi-btn hifi-btn-small hifi-btn-primary"
                  onclick={() => saveService(svc)}
                  disabled={isSaving || !editValue.trim()}
                >
                  {isSaving ? 'Speichert...' : 'Speichern'}
                </button>
              </div>
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}

  <div class="dienste-hint">
    <i class="fa-solid fa-circle-info"></i>
    Zeigt alle externen Datenquellen. Konfigurierbare Dienste können bei Bedarf auf eigene Instanzen umgestellt werden.
  </div>
</div>

<style>
  .loading-state {
    display: flex;
    justify-content: center;
    padding: 40px;
  }

  .services-grid {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 8px;
  }

  .service-card {
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-sm, 4px);
    padding: 12px 16px;
    transition: background 0.15s;
  }

  .service-card:hover {
    background: var(--hifi-bg-secondary);
  }

  .service-card.editing {
    background: var(--hifi-bg-secondary);
    outline: 1px solid var(--hifi-accent);
  }

  .service-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
  }

  .service-icon {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--hifi-bg-panel);
    border-radius: var(--hifi-border-radius-sm, 4px);
    color: var(--hifi-accent);
    font-size: 14px;
    flex-shrink: 0;
  }

  .service-title {
    flex: 1;
    min-width: 0;
  }

  .service-label {
    display: block;
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: var(--hifi-text-primary);
  }

  .service-desc {
    display: block;
    font-family: 'Barlow', sans-serif;
    font-size: 10px;
    color: var(--hifi-text-secondary);
    margin-top: 1px;
  }

  .service-badges {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .badge {
    display: flex;
    align-items: center;
    gap: 4px;
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.5px;
    padding: 3px 8px;
    border-radius: 3px;
    white-space: nowrap;
  }

  .badge-category {
    background: rgba(51, 153, 255, 0.1);
    color: var(--hifi-accent, #3399ff);
  }

  .badge-direction {
    color: var(--hifi-text-secondary);
  }

  .service-urls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    position: relative;
  }

  .service-url {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 11px;
    color: var(--hifi-text-secondary);
    background: var(--hifi-bg-panel);
    padding: 3px 8px;
    border-radius: 3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
  }

  .service-note {
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    color: var(--hifi-text-secondary);
    opacity: 0.7;
    font-style: italic;
  }

  .edit-btn {
    opacity: 0;
    transition: opacity 0.15s;
    margin-left: auto;
  }

  .service-card:hover .edit-btn {
    opacity: 1;
  }

  .service-edit {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .service-edit .hifi-input {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 11px;
    width: 100%;
    box-sizing: border-box;
  }

  .edit-textarea {
    resize: vertical;
    min-height: 60px;
    line-height: 1.6;
  }

  .edit-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }

  .dienste-hint {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    color: var(--hifi-text-secondary);
    opacity: 0.6;
    border-top: 1px solid var(--hifi-border-dark);
  }

  .refresh-btn {
    margin-left: auto;
  }

  .hifi-panel-header {
    display: flex;
    align-items: center;
  }
</style>
