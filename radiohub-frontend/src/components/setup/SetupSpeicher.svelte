<script>
  /**
   * SetupSpeicher - Storage-Zone-Konfiguration
   * Zeigt alle Zonen mit Pfad, Speicherplatz, Status.
   * Erlaubt Pfad-Aenderungen fuer jede Zone.
   */
  import HiFiLed from '../hifi/HiFiLed.svelte';
  import { api } from '../../lib/api.js';
  import { actions } from '../../lib/store.svelte.js';

  let zones = $state({});
  let isLoading = $state(true);
  let editingZone = $state(null);
  let editPath = $state('');
  let validationResult = $state(null);
  let isValidating = $state(false);
  let isSaving = $state(false);

  $effect(() => {
    loadZones();
  });

  async function loadZones() {
    isLoading = true;
    try {
      const result = await api.getStorageZones();
      zones = result.zones || {};
    } catch (e) {
      // Netzwerkfehler ignorieren
    }
    isLoading = false;
  }

  function startEdit(zoneName) {
    editingZone = zoneName;
    editPath = zones[zoneName]?.path || '';
    validationResult = null;
  }

  function cancelEdit() {
    editingZone = null;
    editPath = '';
    validationResult = null;
  }

  async function validatePath() {
    if (!editPath.trim()) return;
    isValidating = true;
    try {
      validationResult = await api.validateStoragePath(editPath.trim());
    } catch (e) {
      validationResult = { error: 'Validierung fehlgeschlagen' };
    }
    isValidating = false;
  }

  async function saveZone() {
    if (!editingZone || !editPath.trim()) return;
    isSaving = true;
    try {
      await api.updateStorageZone(editingZone, editPath.trim());
      actions.showToast('Speicherpfad aktualisiert', 'success');
      cancelEdit();
      await loadZones();
    } catch (e) {
      actions.showToast('Speichern fehlgeschlagen', 'error');
    }
    isSaving = false;
  }

  function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(i > 1 ? 1 : 0) + ' ' + units[i];
  }

  function usagePercent(used, total) {
    if (!total || total === 0) return 0;
    return Math.min(100, (used / total) * 100);
  }
</script>

<div class="hifi-panel">
  <div class="hifi-panel-header">
    <span class="hifi-font-label">SPEICHER-ZONEN</span>
    <button class="hifi-btn hifi-btn-small refresh-btn" onclick={loadZones} title="Aktualisieren">
      <i class="fa-solid fa-arrows-rotate" class:fa-spin={isLoading}></i>
    </button>
  </div>

  {#if isLoading && Object.keys(zones).length === 0}
    <div class="loading-state">
      <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
    </div>
  {:else}
    <div class="zones-grid">
      {#each Object.entries(zones) as [name, zone]}
        {@const isEditing = editingZone === name}
        {@const usagePct = usagePercent(zone.used_bytes, zone.total_bytes)}
        {@const freePct = 100 - usagePercent(zone.used_bytes + (zone.free_bytes > 0 ? zone.total_bytes - zone.free_bytes - zone.used_bytes : 0), zone.total_bytes)}

        <div class="zone-card" class:editing={isEditing}>
          <div class="zone-header">
            <div class="zone-icon">
              <i class="fa-solid {zone.icon}"></i>
            </div>
            <div class="zone-title">
              <span class="zone-label">{zone.label}</span>
              <span class="zone-desc">{zone.description}</span>
            </div>
            <div class="zone-status">
              <HiFiLed color={zone.writable ? 'green' : 'red'} size="small" />
              <span class="zone-rec">{zone.recommended}</span>
            </div>
          </div>

          {#if !isEditing}
            <div class="zone-path-row">
              <code class="zone-path">{zone.path}</code>
              <button class="hifi-btn hifi-btn-small edit-btn" onclick={() => startEdit(name)} title="Pfad aendern">
                <i class="fa-solid fa-pen"></i>
              </button>
            </div>
          {:else}
            <div class="zone-edit">
              <div class="edit-input-row">
                <input
                  type="text"
                  class="hifi-input"
                  bind:value={editPath}
                  placeholder="Absoluter Pfad..."
                  onkeydown={(e) => { if (e.key === 'Enter') validatePath(); if (e.key === 'Escape') cancelEdit(); }}
                />
                <button class="hifi-btn hifi-btn-small" onclick={validatePath} disabled={isValidating || !editPath.trim()}>
                  {isValidating ? '...' : 'Pruefen'}
                </button>
              </div>

              {#if validationResult}
                <div class="validation-result" class:valid={validationResult.writable} class:invalid={!validationResult.writable || validationResult.error}>
                  {#if validationResult.error}
                    <i class="fa-solid fa-xmark"></i> {validationResult.error}
                  {:else if validationResult.writable}
                    <i class="fa-solid fa-check"></i>
                    Beschreibbar - {formatBytes(validationResult.free_bytes)} frei
                    {#if validationResult.created}
                      (Verzeichnis wurde erstellt)
                    {/if}
                  {:else}
                    <i class="fa-solid fa-xmark"></i> Pfad nicht beschreibbar
                  {/if}
                </div>
              {/if}

              <div class="edit-actions">
                <button class="hifi-btn hifi-btn-small" onclick={cancelEdit}>Abbrechen</button>
                <button
                  class="hifi-btn hifi-btn-small hifi-btn-primary"
                  onclick={saveZone}
                  disabled={isSaving || !validationResult?.writable}
                >
                  {isSaving ? 'Speichert...' : 'Speichern'}
                </button>
              </div>
            </div>
          {/if}

          <div class="zone-stats">
            <div class="stat-bar">
              <div class="stat-fill" style="width: {usagePct}%"></div>
            </div>
            <div class="stat-row">
              <span class="stat-value">{formatBytes(zone.used_bytes)}</span>
              <span class="stat-label">belegt</span>
              <span class="stat-sep">|</span>
              <span class="stat-value">{formatBytes(zone.free_bytes)}</span>
              <span class="stat-label">frei</span>
              <span class="stat-sep">|</span>
              <span class="stat-value">{zone.file_count}</span>
              <span class="stat-label">{zone.file_count === 1 ? 'Datei' : 'Dateien'}</span>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}

  <div class="zone-hint">
    <i class="fa-solid fa-circle-info"></i>
    Pfad-Aenderungen verschieben keine Daten. Bestehende Dateien bleiben am alten Speicherort erhalten.
  </div>
</div>

<style>
  .loading-state {
    display: flex;
    justify-content: center;
    padding: 40px;
  }

  .zones-grid {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 8px;
  }

  .zone-card {
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-sm, 4px);
    padding: 12px 16px;
    transition: background 0.15s;
  }

  .zone-card:hover {
    background: var(--hifi-bg-secondary);
  }

  .zone-card.editing {
    background: var(--hifi-bg-secondary);
    outline: 1px solid var(--hifi-accent);
  }

  .zone-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
  }

  .zone-icon {
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

  .zone-title {
    flex: 1;
    min-width: 0;
  }

  .zone-label {
    display: block;
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: var(--hifi-text-primary);
  }

  .zone-desc {
    display: block;
    font-family: 'Barlow', sans-serif;
    font-size: 10px;
    color: var(--hifi-text-secondary);
    margin-top: 1px;
  }

  .zone-status {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }

  .zone-rec {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 9px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    letter-spacing: 0.5px;
  }

  .zone-path-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }

  .zone-path {
    flex: 1;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 11px;
    color: var(--hifi-text-secondary);
    background: var(--hifi-bg-panel);
    padding: 4px 8px;
    border-radius: 3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .edit-btn {
    opacity: 0;
    transition: opacity 0.15s;
  }

  .zone-card:hover .edit-btn {
    opacity: 1;
  }

  .zone-edit {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 8px;
  }

  .edit-input-row {
    display: flex;
    gap: 8px;
  }

  .edit-input-row .hifi-input {
    flex: 1;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 11px;
  }

  .validation-result {
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    padding: 6px 10px;
    border-radius: 3px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .validation-result.valid {
    background: rgba(51, 204, 51, 0.1);
    color: var(--hifi-text-green, #33cc33);
  }

  .validation-result.invalid {
    background: rgba(255, 68, 68, 0.1);
    color: var(--hifi-text-red, #ff4444);
  }

  .edit-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }

  .zone-stats {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .stat-bar {
    height: 3px;
    background: var(--hifi-bg-panel);
    border-radius: 2px;
    overflow: hidden;
  }

  .stat-fill {
    height: 100%;
    background: var(--hifi-accent, #3399ff);
    border-radius: 2px;
    transition: width 0.3s ease;
    min-width: 1px;
  }

  .stat-row {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .stat-value {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-text-primary);
  }

  .stat-label {
    font-family: 'Barlow', sans-serif;
    font-size: 10px;
    color: var(--hifi-text-secondary);
  }

  .stat-sep {
    color: var(--hifi-border-dark);
    font-size: 10px;
    margin: 0 2px;
  }

  .zone-hint {
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
