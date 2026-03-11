<script>
  /**
   * FileExplorer - Einheitlicher Datei-Explorer fuer Podcasts und Aufnahmen
   * Ordner-Baum mit Dateien, Multi-Select, ZIP-Download.
   */
  import InfoBadge from './InfoBadge.svelte';
  import HiFiLed from '../hifi/HiFiLed.svelte';
  import { formatSize, formatDate } from '../../lib/formatters.js';
  import { api } from '../../lib/api.js';

  let {
    type = 'podcast',        // 'podcast' | 'recording'
    folders = [],
    totalSize = 0,
    totalFiles = 0,
    isLoading = false,
    onplay = () => {},
    ondelete = () => {},
    onrefresh = () => {},
    oncutter = null           // Callback für Cutter (nur recording)
  } = $props();

  let expandedFolders = $state(new Set());
  let selectedFiles = $state(new Set());
  let isDownloading = $state(false);

  function toggleFolder(folderId) {
    const next = new Set(expandedFolders);
    if (next.has(folderId)) {
      next.delete(folderId);
    } else {
      next.add(folderId);
    }
    expandedFolders = next;
  }

  function toggleFile(filePath) {
    const next = new Set(selectedFiles);
    if (next.has(filePath)) {
      next.delete(filePath);
    } else {
      next.add(filePath);
    }
    selectedFiles = next;
  }

  function toggleFolderSelect(folder) {
    const paths = folder.files.map(f => f.path);
    const allSelected = paths.every(p => selectedFiles.has(p));
    const next = new Set(selectedFiles);
    if (allSelected) {
      paths.forEach(p => next.delete(p));
    } else {
      paths.forEach(p => next.add(p));
    }
    selectedFiles = next;
  }

  function isFolderSelected(folder) {
    if (!folder.files.length) return false;
    return folder.files.every(f => selectedFiles.has(f.path));
  }

  function isFolderPartial(folder) {
    if (!folder.files.length) return false;
    const some = folder.files.some(f => selectedFiles.has(f.path));
    const all = folder.files.every(f => selectedFiles.has(f.path));
    return some && !all;
  }

  function selectAll() {
    const next = new Set();
    folders.forEach(f => f.files.forEach(file => next.add(file.path)));
    selectedFiles = next;
  }

  function selectNone() {
    selectedFiles = new Set();
  }

  async function downloadZip() {
    if (selectedFiles.size === 0) return;
    isDownloading = true;
    try {
      const files = Array.from(selectedFiles);
      const response = await api.downloadFilesZip(files, true);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `radiohub_${type}_${new Date().toISOString().slice(0,10)}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('ZIP-Download fehlgeschlagen:', e);
    }
    isDownloading = false;
  }

  async function handleDelete(file) {
    ondelete(file);
  }

  let selectedSize = $derived(
    folders.reduce((sum, f) =>
      sum + f.files.filter(file => selectedFiles.has(file.path)).reduce((s, file) => s + file.size, 0)
    , 0)
  );
</script>

<div class="file-explorer">
  <div class="explorer-toolbar">
    <div class="toolbar-info">
      <span class="info-total">
        <i class="fa-solid fa-folder"></i> {folders.length}
      </span>
      <span class="info-total">
        <i class="fa-solid fa-file-audio"></i> {totalFiles}
      </span>
      <span class="info-total">
        <i class="fa-solid fa-hard-drive"></i> {formatSize(totalSize)}
      </span>
    </div>

    <div class="toolbar-actions">
      {#if selectedFiles.size > 0}
        <span class="selection-info">{selectedFiles.size} ausgewaehlt ({formatSize(selectedSize)})</span>
      {/if}
      <button class="hifi-btn hifi-btn-small" onclick={selectAll} title="Alle Dateien auswaehlen">
        <i class="fa-solid fa-check-double"></i>
      </button>
      <button class="hifi-btn hifi-btn-small" onclick={selectNone} disabled={selectedFiles.size === 0} title="Auswahl aufheben">
        <i class="fa-solid fa-xmark"></i>
      </button>
      <button
        class="hifi-btn hifi-btn-small"
        onclick={downloadZip}
        disabled={selectedFiles.size === 0 || isDownloading}
        title="Ausgewaehlte Dateien als ZIP herunterladen (mit M3U-Playlist)"
      >
        <i class="fa-solid fa-file-zipper" class:fa-spin={isDownloading}></i>
      </button>
      {#if oncutter}
        <button class="hifi-btn hifi-btn-small" onclick={oncutter} disabled={selectedFiles.size === 0} title="Ausgewählte Aufnahmen schneiden (Segmente erzeugen)">
          <i class="fa-solid fa-scissors"></i>
        </button>
      {/if}
      <button class="hifi-btn hifi-btn-small" onclick={onrefresh} disabled={isLoading} title="Dateiliste aktualisieren">
        <i class="fa-solid fa-arrows-rotate" class:fa-spin={isLoading}></i>
      </button>
    </div>
  </div>

  {#if isLoading}
    <div class="explorer-loading">
      <i class="fa-solid fa-spinner fa-spin"></i> Lade Dateien...
    </div>
  {:else if folders.length === 0}
    <div class="explorer-empty">
      <i class="fa-solid fa-folder-open"></i>
      <span>Keine Dateien vorhanden</span>
    </div>
  {:else}
    <div class="explorer-tree">
      {#each folders as folder (folder.id)}
        <div class="folder-row" class:orphaned={folder.orphaned}>
          <div class="folder-header" onclick={() => toggleFolder(folder.id)}>
            <button class="led-toggle" onclick={(e) => { e.stopPropagation(); toggleFolderSelect(folder); }} title="Alle Dateien in diesem Ordner auswählen">
              <HiFiLed color={isFolderSelected(folder) ? 'green' : isFolderPartial(folder) ? 'amber' : 'off'} size="small" title={isFolderSelected(folder) ? 'Alle Dateien ausgewählt' : isFolderPartial(folder) ? 'Teilweise ausgewählt' : 'Keine Dateien ausgewählt'} />
            </button>
            <i class="fa-solid" class:fa-folder-open={expandedFolders.has(folder.id)} class:fa-folder={!expandedFolders.has(folder.id)}></i>
            <span class="folder-name">{folder.name}</span>
            {#if folder.orphaned}
              <InfoBadge type="resume" label="Verwaist" />
            {/if}
            <span class="folder-count">{folder.file_count} Dateien</span>
            <span class="folder-size">{formatSize(folder.total_size)}</span>
            <i class="fa-solid fa-chevron-right chevron" class:expanded={expandedFolders.has(folder.id)}></i>
          </div>

          {#if expandedFolders.has(folder.id)}
            <div class="folder-files">
              {#each folder.files as file (file.path)}
                <div class="file-row" class:selected={selectedFiles.has(file.path)}>
                  <button class="led-toggle" onclick={() => toggleFile(file.path)} title="Datei für ZIP-Download auswählen">
                    <HiFiLed color={selectedFiles.has(file.path) ? 'green' : 'off'} size="small" title={selectedFiles.has(file.path) ? 'Für Download ausgewählt' : 'Nicht ausgewählt'} />
                  </button>
                  <span class="file-name" title={file.name}>{file.name}</span>
                  <span class="file-size">{formatSize(file.size)}</span>
                  <span class="file-date">{formatDate(file.modified)}</span>
                  <div class="file-actions">
                    <button class="action-btn" onclick={() => onplay(file)} title="Datei abspielen">
                      <i class="fa-solid fa-play"></i>
                    </button>
                    <button class="action-btn action-btn-danger" onclick={() => handleDelete(file)} title="Datei endgueltig loeschen">
                      <i class="fa-solid fa-trash"></i>
                    </button>
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .file-explorer {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--hifi-bg-panel);
  }

  .explorer-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    border-bottom: 1px solid var(--hifi-border-dark);
    gap: 8px;
    flex-shrink: 0;
  }

  .toolbar-info {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  .info-total {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 11px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .info-total i {
    font-size: 10px;
    color: var(--hifi-accent);
  }

  .toolbar-actions {
    display: flex;
    gap: 6px;
    align-items: center;
  }

  .selection-info {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-accent);
    white-space: nowrap;
  }

  .explorer-loading,
  .explorer-empty {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 40px 16px;
    color: var(--hifi-text-secondary);
    font-family: 'Barlow', sans-serif;
    font-size: 13px;
  }

  .explorer-empty i {
    font-size: 20px;
    opacity: 0.4;
  }

  .explorer-tree {
    flex: 1;
    overflow-y: auto;
    padding: 4px 0;
  }

  /* Ordner */
  .folder-row {
    border-bottom: 1px solid var(--hifi-border-dark);
  }

  .folder-row.orphaned {
    border-left: 2px solid var(--hifi-led-amber, #e5a00d);
  }

  .folder-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    cursor: pointer;
    transition: background 0.15s;
  }

  .folder-header:hover {
    background: var(--hifi-bg-tertiary);
  }

  .folder-header i.fa-folder,
  .folder-header i.fa-folder-open {
    color: var(--hifi-accent);
    font-size: 14px;
    width: 16px;
    text-align: center;
  }

  .folder-name {
    font-family: 'Barlow', sans-serif;
    font-size: 13px;
    font-weight: 500;
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .folder-count {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    white-space: nowrap;
    min-width: 80px;
    text-align: right;
  }

  .folder-size {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    white-space: nowrap;
    min-width: 70px;
    text-align: right;
  }

  .chevron {
    font-size: 10px;
    color: var(--hifi-text-secondary);
    transition: transform 0.2s;
    flex-shrink: 0;
  }

  .chevron.expanded {
    transform: rotate(90deg);
  }

  /* Dateien */
  .folder-files {
    background: var(--hifi-bg-secondary);
  }

  .file-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 12px 4px 40px;
    transition: background 0.1s;
  }

  .file-row:hover {
    background: var(--hifi-bg-tertiary);
  }

  .file-row.selected {
    background: rgba(51, 153, 255, 0.08);
  }

  .led-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
    flex-shrink: 0;
  }

  .file-name {
    font-family: 'Barlow', sans-serif;
    font-size: 12px;
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .file-size {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    white-space: nowrap;
    min-width: 50px;
    text-align: right;
  }

  .file-date {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    white-space: nowrap;
    min-width: 70px;
  }

  .file-actions {
    display: flex;
    gap: 4px;
    flex-shrink: 0;
    opacity: 0;
    transition: opacity 0.15s;
  }

  .file-row:hover .file-actions {
    opacity: 1;
  }

  .action-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border: none;
    background: var(--hifi-bg-tertiary);
    color: var(--hifi-text-secondary);
    cursor: pointer;
    border-radius: var(--hifi-border-radius-sm, 4px);
    box-shadow: var(--hifi-shadow-button);
    font-size: 10px;
    transition: all 0.15s;
  }

  .action-btn:hover {
    background: var(--hifi-bg-panel);
    color: var(--hifi-text-primary);
  }

  .action-btn:active {
    box-shadow: var(--hifi-shadow-inset);
  }

  .action-btn-danger {
    color: var(--hifi-led-red, #e53935);
    opacity: 0.6;
  }

  .action-btn-danger:hover {
    color: var(--hifi-led-red, #e53935);
    opacity: 1;
  }

  /* HiFi Buttons */
  .explorer-toolbar :global(.hifi-btn) {
    box-shadow: var(--hifi-shadow-button);
    border: none;
    background: var(--hifi-bg-tertiary);
  }

  .explorer-toolbar :global(.hifi-btn:hover) {
    background: var(--hifi-bg-secondary);
  }

  .explorer-toolbar :global(.hifi-btn:active) {
    box-shadow: var(--hifi-shadow-inset);
  }

  .explorer-toolbar :global(.hifi-btn:disabled) {
    opacity: 0.3;
    cursor: not-allowed;
    pointer-events: none;
  }
</style>
