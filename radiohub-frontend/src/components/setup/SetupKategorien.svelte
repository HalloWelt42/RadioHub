<script>
  import HiFiLed from '../hifi/HiFiLed.svelte';
  import { api } from '../../lib/api.js';
  import { actions } from '../../lib/store.svelte.js';

  // === STATE ===
  let categories = $state([]);
  let isLoading = $state(true);
  let editingId = $state(null);
  let formName = $state('');
  let showForm = $state(false);

  // === INIT ===
  $effect(() => {
    loadAll();
  });

  async function loadAll() {
    try {
      const cats = await api.getCategories();
      categories = Array.isArray(cats) ? cats : (cats?.categories || []);
    } catch (e) {
      console.error('SetupKategorien: Laden fehlgeschlagen:', e);
    }
    isLoading = false;
  }

  // === CRUD ===
  function startCreate() {
    editingId = null;
    formName = '';
    showForm = true;
  }

  function startEdit(cat) {
    editingId = cat.id;
    formName = cat.name;
    showForm = true;
  }

  function cancelForm() {
    showForm = false;
    editingId = null;
  }

  async function saveForm() {
    const name = formName.trim();
    if (!name) {
      actions.showToast('Name erforderlich', 'error');
      return;
    }
    try {
      if (editingId) {
        await api.updateCategory(editingId, { name });
        actions.showToast('Kategorie aktualisiert');
      } else {
        await api.createCategory(name);
        actions.showToast('Kategorie erstellt');
      }
      showForm = false;
      editingId = null;
      const cats = await api.getCategories();
      categories = Array.isArray(cats) ? cats : (cats?.categories || []);
    } catch (e) {
      console.error('SetupKategorien: Speichern fehlgeschlagen:', e);
      actions.showToast('Speichern fehlgeschlagen', 'error');
    }
  }

  async function deleteCategory(id) {
    try {
      await api.deleteCategory(id);
      categories = categories.filter(c => c.id !== id);
      actions.showToast('Kategorie geloescht');
      if (editingId === id) cancelForm();
    } catch (e) {
      console.error('SetupKategorien: Loeschen fehlgeschlagen:', e);
      actions.showToast('Loeschen fehlgeschlagen', 'error');
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
</script>

{#if isLoading}
  <div class="hifi-flex" style="justify-content:center; padding:60px;">
    <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
  </div>
{:else}

  <!-- Header -->
  <div class="kat-header">
    <span class="hifi-font-label">KATEGORIEN ({categories.length})</span>
    {#if !showForm}
      <button class="action-btn create-btn" onclick={startCreate}>
        + NEUE KATEGORIE
      </button>
    {/if}
  </div>

  <!-- Formular -->
  {#if showForm}
    <div class="hifi-panel">
      <div class="hifi-panel-header">
        <span class="hifi-font-label">{editingId ? 'KATEGORIE BEARBEITEN' : 'NEUE KATEGORIE'}</span>
      </div>
      <div class="form-content">
        <div class="form-group">
          <span class="form-label">NAME</span>
          <input
            type="text"
            class="form-input"
            placeholder="z.B. Rock, Jazz, Nachrichten..."
            bind:value={formName}
            onkeydown={handleKeydown}
          />
        </div>
        <div class="form-actions">
          <button class="action-btn save-btn" onclick={saveForm} disabled={!formName.trim()}>
            SPEICHERN
          </button>
          <button class="action-btn cancel-btn" onclick={cancelForm}>
            ABBRECHEN
          </button>
        </div>
      </div>
    </div>
  {/if}

  <!-- Kategorie-Liste -->
  {#if categories.length > 0}
    <div class="kat-list">
      {#each categories as cat (cat.id)}
        <div class="kat-row" class:editing={editingId === cat.id}>
          <div class="kat-info">
            <HiFiLed color="green" size="small" />
            <span class="kat-name">{cat.name}</span>
          </div>
          <div class="kat-actions">
            <button class="mini-btn" onclick={() => startEdit(cat)}>BEARBEITEN</button>
            <button class="mini-btn delete-btn" onclick={() => deleteCategory(cat.id)}>LOESCHEN</button>
          </div>
        </div>
      {/each}
    </div>
  {:else if !showForm}
    <div class="empty-state">
      <span class="hifi-font-label">Noch keine Kategorien erstellt</span>
      <span class="empty-hint">Kategorien filtern Sender in der Seitenleiste</span>
    </div>
  {/if}

{/if}

<style>
  .kat-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }

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

  .form-content {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
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
    font-family: var(--hifi-font-body);
    font-size: 12px;
    color: var(--hifi-text-primary);
    background: var(--hifi-bg-tertiary);
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    outline: none;
    box-shadow: var(--hifi-shadow-inset);
  }

  .form-input:focus {
    box-shadow: var(--hifi-shadow-inset), 0 0 0 2px var(--hifi-accent);
  }

  .form-input::placeholder {
    color: var(--hifi-text-secondary);
  }

  .form-actions {
    display: flex;
    gap: 8px;
    padding-top: 4px;
  }

  .kat-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .kat-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    background: var(--hifi-bg-panel);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm);
  }

  .kat-row.editing {
    border-color: var(--hifi-accent);
  }

  .kat-info {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .kat-name {
    font-family: var(--hifi-font-display);
    font-size: 13px;
    font-weight: 600;
    color: var(--hifi-text-primary);
    letter-spacing: 0.5px;
  }

  .kat-actions {
    display: flex;
    gap: 6px;
  }

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
</style>
