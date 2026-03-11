<script>
  /**
   * RecordingSidebar - Linkes Panel im Recorder-Tab
   * Session-Liste mit Ordner-Gruppen, Stats, Action-Buttons, Resize.
   */
  import HiFiLed from '../hifi/HiFiLed.svelte';
  import { formatDuration, formatSize, formatDate } from '../../lib/formatters.js';
  import { appState } from '../../lib/store.svelte.js';
  import { tick } from 'svelte';
  import * as sfx from '../../lib/uiSounds.js';

  let {
    sessions = [],
    stats = {},
    folders = [],
    selectedSessionId = null,
    activeSessionId = null,
    isRecording = false,
    width = 280,
    fileExplorerActive = false,
    searchQuery = '',
    onselectsession = () => {},
    onrefresh = () => {},
    onfileexplorer = () => {},
    oncutter = () => {},
    onsearch = () => {},
    onresize = () => {},
    oncreatefolder = () => {},
    onrenamefolder = () => {},
    ondeletefolder = () => {},
    onactivatefolder = () => {},
    ondeactivatefolder = () => {},
    onmovesession = () => {}
  } = $props();

  let showSearch = $state(false);
  let localQuery = $state('');
  let showNewFolder = $state(false);
  let newFolderName = $state('');
  let renamingFolderId = $state(null);
  let renameFolderName = $state('');

  // Zugeklappte Ordner (persistiert)
  let collapsedFolders = $state(
    JSON.parse(localStorage.getItem('radiohub_collapsed_folders') || '{}')
  );

  function toggleFolder(folderId) {
    collapsedFolders = { ...collapsedFolders, [folderId]: !collapsedFolders[folderId] };
    localStorage.setItem('radiohub_collapsed_folders', JSON.stringify(collapsedFolders));
  }

  // Sessions gruppieren
  let rootSessions = $derived(sessions.filter(s => !s.folder_id));
  let folderSessions = $derived((folderId) => sessions.filter(s => s.folder_id === folderId));

  function handleSearch() {
    onsearch(localQuery);
  }

  function handleSearchKey(e) {
    if (e.key === 'Enter') handleSearch();
    if (e.key === 'Escape') { showSearch = false; localQuery = ''; onsearch(''); }
  }

  function handleNewFolderKey(e) {
    if (e.key === 'Enter' && newFolderName.trim()) {
      oncreatefolder(newFolderName.trim());
      newFolderName = '';
      showNewFolder = false;
    }
    if (e.key === 'Escape') { showNewFolder = false; newFolderName = ''; }
  }

  function startRenaming(folder) {
    renamingFolderId = folder.id;
    renameFolderName = folder.name;
  }

  function handleRenameKey(e) {
    if (e.key === 'Enter' && renameFolderName.trim()) {
      onrenamefolder(renamingFolderId, renameFolderName.trim());
      renamingFolderId = null;
    }
    if (e.key === 'Escape') { renamingFolderId = null; }
  }

  // Spielende Session in Sicht scrollen
  $effect(() => {
    if (activeSessionId) {
      tick().then(() => {
        const el = document.querySelector(`.session-item[data-session-id="${activeSessionId}"]`);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      });
    }
  });

  // === Resize Handle ===
  let isDragging = $state(false);
  let startX = 0;
  let startWidth = 0;

  function handleResizeStart(e) {
    e.preventDefault();
    isDragging = true;
    startX = e.clientX;
    startWidth = width;
    document.addEventListener('mousemove', handleResizeMove);
    document.addEventListener('mouseup', handleResizeEnd);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }

  function handleResizeMove(e) {
    if (!isDragging) return;
    const delta = e.clientX - startX;
    const newWidth = Math.min(Math.max(startWidth + delta, 200), 500);
    onresize(newWidth);
  }

  function handleResizeEnd() {
    isDragging = false;
    document.removeEventListener('mousemove', handleResizeMove);
    document.removeEventListener('mouseup', handleResizeEnd);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }

  function codecBadge(session) {
    const codec = session.codec || '';
    const ext = session.file_format || '';
    if (codec) return codec.toUpperCase();
    if (ext) return ext.replace('.', '').toUpperCase();
    return 'MP3';
  }
</script>

{#snippet sessionItem(session)}
  {@const isSelected = selectedSessionId === session.id}
  {@const isPlaying = activeSessionId === session.id}
  {@const isActive = session.status === 'recording'}
  <button
    class="session-item"
    class:selected={isSelected}
    class:playing={isPlaying}
    class:active={isActive}
    data-session-id={session.id}
    onclick={() => { onselectsession(session); sfx.click(); }}
  >
    <HiFiLed
      color={isActive ? (appState.recordingType === 'hls-rec' ? 'amber' : 'red') : isPlaying ? 'green' : isSelected ? 'blue' : 'off'}
      size="small"
      blink={isActive}
      pulse={isPlaying}
      title={isActive ? (appState.recordingType === 'hls-rec' ? 'HLS-Buffer-Aufnahme läuft' : 'Aufnahme läuft') : isPlaying ? 'Wird abgespielt' : isSelected ? 'Ausgewählt' : 'Inaktiv'}
    />
    <div class="session-info">
      <div class="session-name">{session.station_name || session.id}</div>
      <div class="session-meta">
        {formatDate(session.start_time)}
        {#if session.segment_count > 0}
          -- {session.segment_count} Seg.
        {/if}
      </div>
    </div>
    <div class="session-right">
      <span class="session-duration">{isActive ? formatDuration(appState.recordingElapsed) : formatDuration(session.duration)}</span>
      <span class="session-codec">{codecBadge(session)}</span>
    </div>
  </button>
{/snippet}

<aside class="recording-sidebar" style="width: {width}px; min-width: {width}px;">
  <!-- Action Row -->
  <div class="sidebar-actions">
    <button
      class="action-btn"
      class:active={showSearch}
      onclick={() => { showSearch = !showSearch; if (!showSearch) { localQuery = ''; onsearch(''); } sfx.click(); }}
      title={showSearch ? 'Suche schließen' : 'Aufnahmen durchsuchen'}
    >
      <i class="fa-solid {showSearch ? 'fa-xmark' : 'fa-magnifying-glass'}"></i>
    </button>
    <button
      class="action-btn"
      onclick={() => { oncutter(); sfx.click(); }}
      title="Aufnahmen schneiden (Segmente erzeugen)"
    >
      <i class="fa-solid fa-scissors"></i>
    </button>
    <button
      class="action-btn"
      class:active={fileExplorerActive}
      onclick={() => { onfileexplorer(); sfx.click(); }}
      title={fileExplorerActive ? 'Datei-Explorer schließen' : 'Datei-Explorer öffnen'}
    >
      <i class="fa-solid fa-folder-tree"></i>
    </button>
    <button
      class="action-btn"
      class:active={showNewFolder}
      onclick={() => { showNewFolder = !showNewFolder; if (!showNewFolder) newFolderName = ''; sfx.click(); }}
      title={showNewFolder ? 'Abbrechen' : 'Neuen Ordner erstellen'}
    >
      <i class="fa-solid {showNewFolder ? 'fa-xmark' : 'fa-folder-plus'}"></i>
    </button>
    <button
      class="action-btn"
      onclick={() => { onrefresh(); sfx.click(); }}
      title="Session-Liste aktualisieren"
    >
      <i class="fa-solid fa-arrows-rotate"></i>
    </button>
  </div>

  <div class="sidebar-divider"></div>

  {#if showNewFolder}
    <div class="search-box">
      <input
        type="text"
        class="search-input"
        placeholder="Neuer Ordnername..."
        bind:value={newFolderName}
        onkeydown={handleNewFolderKey}
      />
    </div>
    <div class="sidebar-divider"></div>
  {/if}

  {#if showSearch}
    <div class="search-box">
      <input
        type="text"
        class="search-input"
        placeholder="Sendername..."
        bind:value={localQuery}
        oninput={handleSearch}
        onkeydown={handleSearchKey}
      />
    </div>
    <div class="sidebar-divider"></div>
  {/if}

  <!-- Session-Liste mit Ordner-Gruppen -->
  <div class="section-scrollable">
    <div class="section-header">
      <span class="section-label">AUFNAHMEN</span>
      <span class="section-count">{sessions.length}</span>
    </div>

    {#if sessions.length === 0 && folders.length === 0}
      <div class="empty-hint">Keine Aufnahmen vorhanden</div>
    {:else}
      <div class="session-list">
        <!-- Ordner-Gruppen -->
        {#each folders as folder (folder.id)}
          {@const fSessions = sessions.filter(s => s.folder_id === folder.id)}
          {@const isCollapsed = collapsedFolders[folder.id]}
          <div class="folder-group">
            <div
              class="folder-header"
              role="button"
              tabindex="0"
              onclick={() => { toggleFolder(folder.id); sfx.click(); }}
            >
              <i class="fa-solid {isCollapsed ? 'fa-chevron-right' : 'fa-chevron-down'} folder-chevron"></i>
              <HiFiLed
                color={folder.is_active ? 'green' : 'off'}
                size="small"
                title={folder.is_active ? 'Aktiver Aufnahmeordner' : 'Inaktiver Ordner'}
              />
              {#if renamingFolderId === folder.id}
                <input
                  type="text"
                  class="folder-rename-input"
                  bind:value={renameFolderName}
                  onkeydown={handleRenameKey}
                  onclick={(e) => e.stopPropagation()}
                />
              {:else}
                <span class="folder-name">{folder.name}</span>
              {/if}
              <span class="folder-count">{fSessions.length}</span>
              <div class="folder-actions" onclick={(e) => e.stopPropagation()}>
                <button
                  class="folder-action-btn"
                  onclick={() => { folder.is_active ? ondeactivatefolder() : onactivatefolder(folder.id); sfx.click(); }}
                  title={folder.is_active ? 'Aufnahmeordner deaktivieren' : 'Als Aufnahmeordner aktivieren'}
                >
                  <i class="fa-solid {folder.is_active ? 'fa-circle-check' : 'fa-circle'}"></i>
                </button>
                <button
                  class="folder-action-btn"
                  onclick={() => { startRenaming(folder); sfx.click(); }}
                  title="Ordner umbenennen"
                >
                  <i class="fa-solid fa-pen"></i>
                </button>
                <button
                  class="folder-action-btn delete"
                  onclick={() => { ondeletefolder(folder.id); sfx.click(); }}
                  title="Ordner löschen (nur wenn leer)"
                >
                  <i class="fa-solid fa-trash-can"></i>
                </button>
              </div>
            </div>
            {#if !isCollapsed}
              {#if fSessions.length === 0}
                <div class="empty-hint folder-empty">Leer</div>
              {:else}
                {#each fSessions as session (session.id)}
                  {@render sessionItem(session)}
                {/each}
              {/if}
            {/if}
          </div>
        {/each}

        <!-- Unzugeordnete Sessions (Root) -->
        {#if rootSessions.length > 0}
          {#if folders.length > 0}
            <div class="root-separator">
              <span class="section-label">UNZUGEORDNET</span>
              <span class="section-count">{rootSessions.length}</span>
            </div>
          {/if}
          {#each rootSessions as session (session.id)}
            {@render sessionItem(session)}
          {/each}
        {/if}
      </div>
    {/if}
  </div>

  <div class="sidebar-divider"></div>

  <!-- Stats -->
  <div class="section-fixed">
    <div class="stats-row">
      <div class="stat-item">
        <HiFiLed color="blue" size="small" title="Anzahl Aufnahme-Dateien" />
        <span class="stat-label">{stats.file_count || 0}</span>
        <span class="stat-unit">Dateien</span>
      </div>
      <div class="stat-item">
        <HiFiLed color="amber" size="small" title="Belegter Speicherplatz" />
        <span class="stat-label">{stats.used_mb?.toFixed(0) || '0'}</span>
        <span class="stat-unit">MB</span>
      </div>
      <div class="stat-item">
        <HiFiLed color="green" size="small" title="Freier Speicherplatz" />
        <span class="stat-label">{stats.disk_free_gb?.toFixed(1) || '0'}</span>
        <span class="stat-unit">GB frei</span>
      </div>
    </div>
  </div>

  <!-- Resize Handle -->
  <div
    class="resize-handle"
    class:active={isDragging}
    onmousedown={handleResizeStart}
    title="Breite anpassen"
  ></div>
</aside>

<style>
  .recording-sidebar {
    position: relative;
    display: flex;
    flex-direction: column;
    background: var(--hifi-bg-panel);
    overflow: hidden;
    flex-shrink: 0;
  }

  .resize-handle {
    position: absolute;
    top: 0;
    right: -3px;
    width: 6px;
    height: 100%;
    cursor: col-resize;
    z-index: 20;
    transition: background 0.15s;
  }

  .resize-handle:hover,
  .resize-handle.active {
    background: var(--hifi-accent);
    opacity: 0.5;
  }

  .sidebar-actions {
    display: flex;
    gap: 4px;
    padding: 10px 10px;
  }

  .action-btn {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 34px;
    padding: 0;
    background: var(--hifi-bg-panel);
    border: none;
    border-radius: var(--hifi-border-radius-sm, 4px);
    color: var(--hifi-text-secondary);
    cursor: pointer;
    font-size: 12px;
    transition: all 0.15s;
    box-shadow: var(--hifi-shadow-button);
  }

  .action-btn:hover {
    color: var(--hifi-text-primary);
    box-shadow: 2px 2px 4px var(--hifi-shadow-dark),
                -2px -2px 4px var(--hifi-shadow-light);
  }

  .action-btn:active {
    box-shadow: var(--hifi-shadow-inset);
  }

  .action-btn.active {
    color: var(--hifi-accent);
    box-shadow: var(--hifi-shadow-inset);
  }

  .sidebar-divider {
    height: 1px;
    background: var(--hifi-border-dark);
  }

  .search-box {
    padding: 6px 10px;
  }

  .search-input {
    width: 100%;
    background: var(--hifi-bg-secondary);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm, 4px);
    color: var(--hifi-text-primary);
    font-family: 'Barlow', sans-serif;
    font-size: 12px;
    padding: 6px 8px;
    outline: none;
  }

  .search-input:focus {
    border-color: var(--hifi-accent);
  }

  .section-header {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px 4px;
  }

  .section-label {
    font-family: 'Barlow', sans-serif;
    font-size: 10px;
    font-weight: 400;
    letter-spacing: 1px;
    color: var(--hifi-text-secondary);
  }

  .section-count {
    margin-left: auto;
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-accent);
  }

  .section-scrollable {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
  }

  .section-fixed {
    flex-shrink: 0;
  }

  .empty-hint {
    padding: 12px 10px;
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    color: var(--hifi-text-secondary);
    opacity: 0.6;
    text-align: center;
  }

  .folder-empty {
    padding: 4px 10px 4px 32px;
    font-size: 10px;
  }

  .session-list {
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding: 0 4px 4px;
  }

  /* Ordner-Gruppen */
  .folder-group {
    margin-bottom: 2px;
  }

  .folder-header {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 100%;
    padding: 5px 6px;
    background: var(--hifi-bg-secondary);
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.15s;
    text-align: left;
  }

  .folder-header:hover {
    background: var(--hifi-row-hover);
  }

  .folder-chevron {
    font-size: 8px;
    color: var(--hifi-text-secondary);
    width: 10px;
    text-align: center;
  }

  .folder-name {
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    font-weight: 600;
    color: var(--hifi-text-primary);
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .folder-rename-input {
    flex: 1;
    background: var(--hifi-bg-primary);
    border: 1px solid var(--hifi-accent);
    border-radius: 3px;
    color: var(--hifi-text-primary);
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    padding: 1px 4px;
    outline: none;
  }

  .folder-count {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 9px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    opacity: 0.6;
  }

  .folder-actions {
    display: flex;
    gap: 2px;
    opacity: 0;
    transition: opacity 0.15s;
  }

  .folder-header:hover .folder-actions {
    opacity: 1;
  }

  .folder-action-btn {
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    border-radius: 3px;
    color: var(--hifi-text-secondary);
    cursor: pointer;
    font-size: 9px;
    transition: color 0.15s, background 0.15s;
  }

  .folder-action-btn:hover {
    color: var(--hifi-text-primary);
    background: var(--hifi-bg-tertiary);
  }

  .folder-action-btn.delete {
    color: var(--hifi-led-red);
    opacity: 0.6;
  }

  .folder-action-btn.delete:hover {
    opacity: 1;
  }

  .root-separator {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 6px 4px;
  }

  /* Session Items */
  .session-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 6px;
    background: none;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.15s;
    text-align: left;
    width: 100%;
  }

  .session-item:hover {
    background: var(--hifi-row-hover);
  }

  .session-item.selected {
    background: rgba(51, 153, 255, 0.08);
  }

  .session-item.playing {
    background: rgba(76, 175, 80, 0.08);
    border-left: 2px solid rgba(76, 175, 80, 0.5);
  }

  .session-item.active {
    background: rgba(255, 50, 50, 0.08);
    border-left: 2px solid rgba(255, 50, 50, 0.5);
  }

  .session-info {
    flex: 1;
    min-width: 0;
    overflow: hidden;
  }

  .session-name {
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    font-weight: 500;
    color: var(--hifi-text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .session-meta {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 9px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    opacity: 0.6;
    margin-top: 1px;
    white-space: nowrap;
  }

  .session-right {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 1px;
    flex-shrink: 0;
  }

  .session-duration {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
  }

  .session-codec {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 8px;
    font-weight: 700;
    padding: 1px 4px;
    border-radius: 2px;
    background: rgba(51, 153, 255, 0.15);
    color: var(--hifi-accent);
  }

  /* Stats */
  .stats-row {
    display: flex;
    gap: 4px;
    padding: 8px 10px;
  }

  .stat-item {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 6px;
    background: var(--hifi-bg-secondary);
    border-radius: var(--hifi-border-radius-sm, 4px);
  }

  .stat-label {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-text-primary);
  }

  .stat-unit {
    font-family: 'Barlow', sans-serif;
    font-size: 9px;
    color: var(--hifi-text-secondary);
    opacity: 0.6;
  }
</style>
