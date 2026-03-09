<script>
  import HiFiLed from '../hifi/HiFiLed.svelte';
  import { api } from '../../lib/api.js';
  import { actions } from '../../lib/store.svelte.js';

  // === STATE ===
  let categories = $state([]);
  let availableTags = $state([]);
  let isLoading = $state(true);
  let editingId = $state(null);

  // Form State
  let formName = $state('');
  let formTags = $state([]);
  let tagSearch = $state('');
  let showForm = $state(false);

  let filteredTags = $derived(() => {
    if (!tagSearch) return availableTags.slice(0, 30);
    const q = tagSearch.toLowerCase();
    return availableTags.filter(t => t.name.toLowerCase().includes(q)).slice(0, 30);
  });

  // === INIT ===
  $effect(() => {
    loadAll();
  });

  async function loadAll() {
    try {
      const [cats, tags] = await Promise.all([
        api.getCategories(),
        api.getAllTags(200)
      ]);
      categories = Array.isArray(cats) ? cats : (cats?.categories || []);
      availableTags = Array.isArray(tags) ? tags : (tags?.tags || []);
    } catch (e) {
      console.error('SetupKategorien: Daten laden fehlgeschlagen:', e);
    }
    isLoading = false;
  }

  // === CRUD ===
  function startCreate() {
    editingId = null;
    formName = '';
    formTags = [];
    tagSearch = '';
    showForm = true;
  }

  function startEdit(cat) {
    editingId = cat.id;
    formName = cat.name;
    formTags = cat.tags ? cat.tags.split(',').map(t => t.trim()).filter(Boolean) : [];
    tagSearch = '';
    showForm = true;
  }

  function cancelForm() {
    showForm = false;
    editingId = null;
  }

  async function saveForm() {
    if (!formName.trim() || formTags.length === 0) {
      actions.showToast('Name und mindestens ein Tag erforderlich', 'error');
      return;
    }
    try {
      const tagsStr = formTags.join(',');
      if (editingId) {
        await api.updateCategory(editingId, { name: formName.trim(), tags: tagsStr });
        actions.showToast('Kategorie aktualisiert');
      } else {
        await api.createCategory(formName.trim(), tagsStr);
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

  function toggleFormTag(tagName) {
    if (formTags.includes(tagName)) {
      formTags = formTags.filter(t => t !== tagName);
    } else {
      formTags = [...formTags, tagName];
    }
  }

  function addCustomTag() {
    const tag = tagSearch.trim().toLowerCase();
    if (tag && !formTags.includes(tag)) {
      formTags = [...formTags, tag];
    }
    tagSearch = '';
  }

  function handleTagKeydown(e) {
    if (e.key === 'Enter' && tagSearch.trim()) {
      e.preventDefault();
      addCustomTag();
    }
  }
</script>

{#if isLoading}
  <div class="hifi-flex" style="justify-content:center; padding:60px;">
    <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
  </div>
{:else}

  <!-- Header + Erstellen-Button -->
  <div class="kat-header">
    <span class="hifi-font-label">BENUTZERDEFINIERTE KATEGORIEN ({categories.length})</span>
    {#if !showForm}
      <button class="action-btn create-btn" onclick={startCreate}>
        + NEUE KATEGORIE
      </button>
    {/if}
  </div>

  <!-- Formular (Erstellen / Bearbeiten) -->
  {#if showForm}
    <div class="hifi-panel">
      <div class="hifi-panel-header">
        <span class="hifi-font-label">{editingId ? 'KATEGORIE BEARBEITEN' : 'NEUE KATEGORIE'}</span>
      </div>
      <div class="form-content">
        <!-- Name -->
        <div class="form-group">
          <span class="form-label">NAME</span>
          <input
            type="text"
            class="form-input"
            placeholder="z.B. Elektronik, News, Klassik..."
            bind:value={formName}
          />
        </div>

        <!-- Ausgewaehlte Tags -->
        <div class="form-group">
          <span class="form-label">TAGS ({formTags.length})</span>
          <div class="selected-tags">
            {#each formTags as tag}
              <button class="tag-chip selected" onclick={() => toggleFormTag(tag)}>
                {tag}
                <span class="tag-x">&times;</span>
              </button>
            {/each}
            {#if formTags.length === 0}
              <span class="tag-hint">Noch keine Tags ausgewaehlt</span>
            {/if}
          </div>
        </div>

        <!-- Tag-Suche + Auswahl -->
        <div class="form-group">
          <span class="form-label">TAGS SUCHEN / HINZUFUEGEN</span>
          <div class="tag-search-row">
            <input
              type="text"
              class="form-input"
              placeholder="Tag suchen oder eingeben..."
              bind:value={tagSearch}
              onkeydown={handleTagKeydown}
            />
            {#if tagSearch.trim()}
              <button class="mini-btn" onclick={addCustomTag}>+</button>
            {/if}
          </div>
          <div class="tag-pool">
            {#each filteredTags() as tag}
              <button
                class="tag-chip"
                class:selected={formTags.includes(tag.name)}
                onclick={() => toggleFormTag(tag.name)}
              >
                {tag.name}
                <span class="tag-count">({tag.count})</span>
              </button>
            {/each}
          </div>
        </div>

        <!-- Aktionen -->
        <div class="form-actions">
          <button class="action-btn save-btn" onclick={saveForm} disabled={!formName.trim() || formTags.length === 0}>
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
            <span class="kat-tag-count">{cat.tags ? cat.tags.split(',').length : 0} Tags</span>
          </div>
          <div class="kat-tags">
            {#each (cat.tags || '').split(',').map(t => t.trim()).filter(Boolean).slice(0, 8) as tag}
              <span class="tag-chip small">{tag}</span>
            {/each}
            {#if cat.tags && cat.tags.split(',').length > 8}
              <span class="tag-more">+{cat.tags.split(',').length - 8}</span>
            {/if}
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
      <span class="empty-hint">Kategorien gruppieren Tags fuer die Sendersuche</span>
    </div>
  {/if}

{/if}

<style>
  /* === Header === */
  .kat-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }

  /* === Shared Buttons === */
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

  /* === Form === */
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

  .tag-search-row {
    display: flex;
    gap: 4px;
  }

  .tag-search-row .form-input {
    flex: 1;
  }

  .form-actions {
    display: flex;
    gap: 8px;
    padding-top: 4px;
  }

  /* === Tags === */
  .selected-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    min-height: 28px;
    padding: 6px;
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-sm);
    box-shadow: var(--hifi-shadow-inset);
  }

  .tag-hint {
    font-family: var(--hifi-font-body);
    font-size: 11px;
    color: var(--hifi-text-secondary);
    font-style: italic;
  }

  .tag-pool {
    display: flex;
    flex-wrap: wrap;
    gap: 3px;
    max-height: 160px;
    overflow-y: auto;
    padding: 6px;
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-sm);
  }

  .tag-chip {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    padding: 3px 8px;
    background: var(--hifi-bg-secondary);
    border: 1px solid transparent;
    border-radius: var(--hifi-border-radius-sm);
    box-shadow: var(--hifi-shadow-button);
    font-family: var(--hifi-font-body);
    font-size: 11px;
    color: var(--hifi-text-primary);
    cursor: pointer;
  }

  .tag-chip:hover {
    border-color: var(--hifi-accent);
  }

  .tag-chip.selected {
    background: var(--hifi-accent);
    color: #fff;
    border-color: var(--hifi-accent);
  }

  .tag-chip.small {
    font-size: 9px;
    padding: 2px 6px;
    cursor: default;
  }

  .tag-x {
    font-size: 12px;
    line-height: 1;
  }

  .tag-count {
    font-size: 9px;
    opacity: 0.6;
  }

  .tag-more {
    font-family: var(--hifi-font-body);
    font-size: 9px;
    color: var(--hifi-text-secondary);
    padding: 2px 4px;
  }

  /* === Kategorie-Liste === */
  .kat-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .kat-row {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 10px 12px;
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
    flex: 1;
    font-family: var(--hifi-font-display);
    font-size: 13px;
    font-weight: 600;
    color: var(--hifi-text-primary);
    letter-spacing: 0.5px;
  }

  .kat-tag-count {
    font-family: var(--hifi-font-body);
    font-size: 10px;
    color: var(--hifi-text-secondary);
  }

  .kat-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 3px;
    padding-left: 20px;
  }

  .kat-actions {
    display: flex;
    gap: 6px;
    padding-left: 20px;
  }

  /* === Empty State === */
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
