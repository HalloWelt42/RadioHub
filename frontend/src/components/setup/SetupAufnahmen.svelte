<script>
  import HiFiLed from '../hifi/HiFiLed.svelte';
  import { api } from '../../lib/api.js';
  import { actions } from '../../lib/store.svelte.js';
  import { t } from '../../lib/i18n.svelte.js';

  // === STATE ===
  let folders = $state([]);
  let isLoading = $state(true);
  let editingId = $state(null);
  let formName = $state('');
  let showForm = $state(false);

  // ICY Ignore
  let ignoreItems = $state([]);
  let ignorePattern = $state('');
  let ignoreMatchType = $state('exact');

  // === INIT ===
  $effect(() => {
    loadFolders();
    loadIgnoreList();
  });

  async function loadFolders() {
    try {
      const data = await api.getRecordingFolders();
      folders = data.folders || [];
    } catch (e) {
      actions.showToast(t('toast.ladenFehler'), 'error');
    }
    isLoading = false;
  }

  // === ORDNER CRUD ===
  function startCreate() {
    editingId = null;
    formName = '';
    showForm = true;
  }

  function startEdit(folder) {
    editingId = folder.id;
    formName = folder.name;
    showForm = true;
  }

  function cancelForm() {
    showForm = false;
    editingId = null;
  }

  async function saveForm() {
    const name = formName.trim();
    if (!name) {
      actions.showToast(t('aufnahmen.ordnernameErforderlich'), 'error');
      return;
    }
    try {
      if (editingId) {
        await api.updateRecordingFolder(editingId, { name });
        actions.showToast(t('toast.ordnerUmbenannt'));
      } else {
        await api.createRecordingFolder(name);
        actions.showToast(t('toast.ordnerErstellt'));
      }
      showForm = false;
      editingId = null;
      await loadFolders();
    } catch (e) {
      actions.showToast(t('toast.speichernFehler'), 'error');
    }
  }

  async function deleteFolder(id) {
    try {
      await api.deleteRecordingFolder(id);
      folders = folders.filter(f => f.id !== id);
      actions.showToast(t('toast.ordnerGeloescht'));
      if (editingId === id) cancelForm();
    } catch (e) {
      const msg = e.message || t('toast.loeschenFehler');
      actions.showToast(msg, 'error');
    }
  }

  async function activateFolder(id) {
    try {
      await api.activateRecordingFolder(id);
      folders = folders.map(f => ({ ...f, is_active: f.id === id ? 1 : 0 }));
      actions.showToast(t('toast.ordnerAktiviert'));
    } catch (e) {
      actions.showToast(t('toast.aktivierungFehler'), 'error');
    }
  }

  async function deactivateAll() {
    try {
      await api.deactivateRecordingFolder();
      folders = folders.map(f => ({ ...f, is_active: 0 }));
      actions.showToast(t('toast.standardOrdner'));
    } catch (e) {
      actions.showToast(t('toast.deaktivierungFehler'), 'error');
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      saveForm();
    }
    if (e.key === 'Escape') {
      cancelForm();
    }
  }

  // === ICY IGNORE ===
  async function loadIgnoreList() {
    try {
      const data = await api.getIcyIgnoreList();
      ignoreItems = data.items || [];
    } catch (e) {
      console.error('Ignore-Liste laden fehlgeschlagen:', e);
    }
  }

  async function addIgnoreItem() {
    const pattern = ignorePattern.trim();
    if (!pattern) return;
    try {
      await api.addIcyIgnore(pattern, ignoreMatchType);
      ignorePattern = '';
      ignoreMatchType = 'exact';
      await loadIgnoreList();
      actions.showToast(t('recordings.titelIgnoriert'));
    } catch (e) {
      if (e.message?.includes('409')) {
        actions.showToast(t('recordings.titelIgnoriert'), 'info');
      } else {
        actions.showToast(e.message || 'Fehler', 'error');
      }
    }
  }

  async function removeIgnoreItem(id) {
    try {
      await api.removeIcyIgnore(id);
      ignoreItems = ignoreItems.filter(i => i.id !== id);
      actions.showToast(t('toast.geloescht'));
    } catch (e) {
      actions.showToast(e.message || 'Fehler', 'error');
    }
  }

  function handleIgnoreKeydown(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      addIgnoreItem();
    }
  }
</script>

{#if isLoading}
  <div class="hifi-flex" style="justify-content:center; padding:60px;">
    <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
  </div>
{:else}
  <div class="aufnahmen-grid">
    <!-- Ordner-Verwaltung -->
    <div class="hifi-panel">
      <div class="hifi-panel-header">
        <span class="hifi-font-label">{t('aufnahmen.ordner')} ({folders.length})</span>
        {#if !showForm}
          <button class="action-btn create-btn" onclick={startCreate}>
            {t('aufnahmen.neuerOrdner')}
          </button>
        {/if}
      </div>

      <div class="folder-content">
        <!-- Formular -->
        {#if showForm}
          <div class="folder-form">
            <div class="form-group">
              <span class="form-label">{t('aufnahmen.ordnername')}</span>
              <input
                type="text"
                class="form-input"
                placeholder="z.B. Jazz, Nachrichten..."
                bind:value={formName}
                onkeydown={handleKeydown}
              />
            </div>
            <div class="form-actions">
              <button class="action-btn save-btn" onclick={saveForm} disabled={!formName.trim()}>
                {t('common.speichern')}
              </button>
              <button class="action-btn cancel-btn" onclick={cancelForm}>
                {t('common.abbrechen')}
              </button>
            </div>
          </div>
        {/if}

        <!-- Aktiver Ordner Hinweis -->
        {#if folders.some(f => f.is_active)}
          <div class="active-hint">
            <HiFiLed color="green" size="small" />
            <span>{t('aufnahmen.neueAufnahmenIn')} <strong>{folders.find(f => f.is_active)?.name}</strong></span>
            <button class="mini-btn" onclick={deactivateAll}>{t('aufnahmen.root')}</button>
          </div>
        {:else}
          <div class="active-hint">
            <HiFiLed color="amber" size="small" />
            <span>{t('aufnahmen.standardOrdner')}</span>
          </div>
        {/if}

        <!-- Ordner-Liste -->
        {#if folders.length > 0}
          <div class="folder-list">
            {#each folders as folder (folder.id)}
              <div class="folder-row" class:editing={editingId === folder.id} class:is-active={folder.is_active}>
                <div class="folder-info">
                  <HiFiLed color={folder.is_active ? 'green' : 'off'} size="small" />
                  <span class="folder-name">{folder.name}</span>
                  <span class="folder-count">{folder.session_count || 0} {t('aufnahmen.aufnahmen')}</span>
                </div>
                <div class="folder-actions">
                  {#if !folder.is_active}
                    <button class="mini-btn" onclick={() => activateFolder(folder.id)}>{t('aufnahmen.aktivieren')}</button>
                  {/if}
                  <button class="mini-btn" onclick={() => startEdit(folder)}>{t('common.bearbeiten')}</button>
                  <button class="mini-btn delete-btn" onclick={() => deleteFolder(folder.id)}>{t('common.loeschen')}</button>
                </div>
              </div>
            {/each}
          </div>
        {:else if !showForm}
          <div class="empty-state">
            <span class="hifi-font-label">{t('aufnahmen.nochKeineOrdner')}</span>
            <span class="empty-hint">{t('aufnahmen.ordnerHint')}</span>
          </div>
        {/if}
      </div>
    </div>

    <!-- ICY Ignore-Liste -->
    <div class="hifi-panel">
      <div class="hifi-panel-header">
        <span class="hifi-font-label">{t('aufnahmen.ignorierteIcyTitel')} ({ignoreItems.length})</span>
      </div>

      <div class="folder-content">
        <div class="active-hint">
          <span>{t('aufnahmen.ignoreHint')}</span>
        </div>

        <!-- Hinzufügen-Formular -->
        <div class="ignore-add-form">
          <input
            type="text"
            class="form-input ignore-input"
            placeholder={t('aufnahmen.musterHinzufuegen')}
            bind:value={ignorePattern}
            onkeydown={handleIgnoreKeydown}
          />
          <select class="form-input ignore-select" bind:value={ignoreMatchType}>
            <option value="exact">{t('aufnahmen.exact')}</option>
            <option value="contains">{t('aufnahmen.contains')}</option>
          </select>
          <button class="action-btn create-btn" onclick={addIgnoreItem} disabled={!ignorePattern.trim()}>
            {t('aufnahmen.hinzufuegen')}
          </button>
        </div>

        <!-- Liste -->
        {#if ignoreItems.length > 0}
          <div class="ignore-list">
            <div class="ignore-header-row">
              <span class="ignore-col-pattern">{t('aufnahmen.muster')}</span>
              <span class="ignore-col-type">{t('aufnahmen.typ')}</span>
              <span class="ignore-col-source">{t('aufnahmen.quelle')}</span>
              <span class="ignore-col-actions"></span>
            </div>
            {#each ignoreItems as item (item.id)}
              <div class="ignore-row">
                <span class="ignore-col-pattern ignore-pattern-text">{item.pattern}</span>
                <span class="ignore-col-type">{item.match_type === 'contains' ? t('aufnahmen.contains') : t('aufnahmen.exact')}</span>
                <span class="ignore-col-source">{item.source === 'builtin' ? t('aufnahmen.builtin') : t('aufnahmen.user')}</span>
                <span class="ignore-col-actions">
                  <button class="mini-btn delete-btn" onclick={() => removeIgnoreItem(item.id)}>{t('common.loeschen')}</button>
                </span>
              </div>
            {/each}
          </div>
        {:else}
          <div class="empty-state">
            <span class="hifi-font-label">{t('aufnahmen.nochKeineIgnore')}</span>
            <span class="empty-hint">{t('aufnahmen.ignoreListeHint')}</span>
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .aufnahmen-grid {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .folder-content {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .active-hint {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-sm);
    font-family: var(--hifi-font-body);
    font-size: 11px;
    color: var(--hifi-text-secondary);
  }

  .active-hint strong {
    color: var(--hifi-accent);
  }

  /* === Ordner-Liste === */
  .folder-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .folder-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    background: var(--hifi-bg-panel);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm);
  }

  .folder-row.editing {
    border-color: var(--hifi-accent);
  }

  .folder-row.is-active {
    border-color: rgba(76, 175, 80, 0.3);
  }

  .folder-info {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .folder-name {
    font-family: var(--hifi-font-display);
    font-size: 13px;
    font-weight: 600;
    color: var(--hifi-text-primary);
    letter-spacing: 0.5px;
  }

  .folder-count {
    font-family: var(--hifi-font-body);
    font-size: 10px;
    color: var(--hifi-text-secondary);
  }

  .folder-actions {
    display: flex;
    gap: 6px;
  }

  /* === Formular === */
  .folder-form {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-sm);
    border: 1px solid var(--hifi-border-dark);
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .form-label {
    font-family: var(--hifi-font-display);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: var(--hifi-text-secondary);
    text-transform: uppercase;
  }

  .form-input {
    padding: 8px 10px;
    font-family: var(--hifi-font-values);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: var(--hifi-text-primary);
    background: var(--hifi-bg-tertiary);
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    outline: none;
    box-shadow: var(--hifi-shadow-inset);
  }

  .form-input:focus {
    box-shadow: var(--hifi-shadow-inset), 0 0 0 1px rgba(255,255,255,0.15);
  }

  .form-input::placeholder {
    color: var(--hifi-text-secondary);
  }

  .form-actions {
    display: flex;
    gap: 8px;
  }

  /* === Buttons === */
  .action-btn {
    padding: 8px 16px;
    font-family: var(--hifi-font-display);
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.5px;
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    box-shadow: var(--hifi-shadow-button);
    cursor: pointer;
    text-transform: uppercase;
  }

  .action-btn:disabled { opacity: 0.4; cursor: default; }

  .create-btn {
    background: var(--hifi-accent);
    color: #fff;
    font-size: 10px;
    padding: 6px 14px;
  }

  .save-btn {
    background: var(--hifi-accent);
    color: #fff;
  }

  .cancel-btn {
    background: var(--hifi-bg-tertiary);
    color: var(--hifi-text-secondary);
  }

  .mini-btn {
    padding: 3px 9px;
    background: var(--hifi-bg-tertiary);
    border: none;
    box-shadow: var(--hifi-shadow-button);
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-body);
    font-size: 10px;
    cursor: pointer;
    border-radius: var(--hifi-border-radius-sm);
  }

  .mini-btn:hover { color: var(--hifi-text-primary); }
  .delete-btn { color: var(--hifi-led-red); }
  .delete-btn:hover { color: var(--hifi-led-red); }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 40px;
    color: var(--hifi-text-muted);
  }

  .empty-hint {
    font-family: var(--hifi-font-body);
    font-size: 11px;
    color: var(--hifi-text-secondary);
  }

  /* === ICY Ignore === */
  .ignore-add-form {
    display: flex;
    gap: 6px;
    align-items: center;
  }

  .ignore-input {
    flex: 1;
  }

  .ignore-select {
    width: 100px;
    padding: 8px 6px;
    appearance: auto;
  }

  .ignore-list {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .ignore-header-row {
    display: flex;
    align-items: center;
    padding: 4px 12px;
    font-family: var(--hifi-font-display);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: var(--hifi-text-secondary);
    text-transform: uppercase;
  }

  .ignore-row {
    display: flex;
    align-items: center;
    padding: 6px 12px;
    background: var(--hifi-bg-panel);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm);
  }

  .ignore-col-pattern { flex: 1; min-width: 0; }
  .ignore-col-type { width: 70px; text-align: center; }
  .ignore-col-source { width: 70px; text-align: center; }
  .ignore-col-actions { width: 60px; text-align: right; }

  .ignore-pattern-text {
    font-family: var(--hifi-font-values);
    font-size: 11px;
    color: var(--hifi-text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .ignore-row .ignore-col-type,
  .ignore-row .ignore-col-source {
    font-family: var(--hifi-font-body);
    font-size: 10px;
    color: var(--hifi-text-secondary);
  }
</style>
