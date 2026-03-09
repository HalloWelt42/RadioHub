<script>
  import HiFiLed from './hifi/HiFiLed.svelte';
  import HiFiDisplay from './hifi/HiFiDisplay.svelte';
  import { api } from '../lib/api.js';
  import { appState, actions } from '../lib/store.svelte.js';
  import { formatDuration, formatSize, formatDate, formatMetaTime, formatDurationMs } from '../lib/formatters.js';

  let sessions = $state([]);
  let stats = $state({ disk_free_gb: 0, file_count: 0, used_mb: 0 });
  let isLoading = $state(false);
  let expandedSession = $state(null);
  let metadata = $state([]);
  let segments = $state([]);
  let metadataLoading = $state(false);

  // Aktiver Aufnahme-Status (wird gepollt)
  let recStatus = $state(null);
  let pollInterval = null;

  $effect(() => {
    loadData();
    startPolling();
    return () => stopPolling();
  });

  function startPolling() {
    pollInterval = setInterval(async () => {
      try {
        recStatus = await api.getRecordingStatus();
        // Live-Session aktualisieren
        if (recStatus?.recording) {
          loadSessions();
        }
      } catch (e) {}
    }, 3000);
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }

  async function loadData() {
    isLoading = true;
    await Promise.all([loadStats(), loadSessions()]);
    isLoading = false;
  }

  async function loadStats() {
    try {
      stats = await api.getRecordingsStats();
    } catch (e) {}
  }

  async function loadSessions() {
    try {
      const result = await api.getSessions();
      sessions = result.sessions || [];
    } catch (e) {}
  }

  async function toggleSession(session) {
    if (expandedSession === session.id) {
      expandedSession = null;
      metadata = [];
      segments = [];
      return;
    }

    expandedSession = session.id;
    metadata = [];
    segments = [];
    metadataLoading = true;

    try {
      // Segmente und Metadata parallel laden
      const [segResult, metaResult] = await Promise.all([
        api.getSegments(session.id).catch(() => ({ segments: [] })),
        session.meta_file_path
          ? api.getSessionMetadata(session.id).catch(() => ({ entries: [] }))
          : Promise.resolve({ entries: [] })
      ]);
      segments = segResult.segments || [];
      metadata = metaResult.entries || [];
    } catch (e) {}

    metadataLoading = false;
  }

  function playSession(session) {
    if (session.status === 'recording') return;

    // Toggle: Stop wenn diese Session schon laeuft
    if (activeSessionId === session.id) {
      actions.stop();
      return;
    }

    // Dateiname aus file_path extrahieren
    const filePath = session.file_path || '';
    const fileName = filePath.split('/').pop() || session.id;
    const playUrl = api.getPlayUrl(`radio/${fileName}`);

    // Session aufklappen wenn nicht schon offen
    if (expandedSession !== session.id) {
      toggleSession(session);
    }

    actions.playRecording({
      path: filePath,
      name: session.station_name || fileName,
      session_id: session.id,
      station_name: session.station_name,
      date: session.start_time,
      duration: session.duration,
      playUrl
    });
  }

  function playAtPosition(session, entry) {
    // Erst Session abspielen, dann zur Position springen
    playSession(session);
    // Verzoeegerter Seek -- Audio muss erst laden
    if (entry.t > 0 && session.duration > 0) {
      setTimeout(() => {
        const percent = (entry.t / 1000) / session.duration * 100;
        import('../lib/playerEngine.js').then(engine => engine.seek(percent));
      }, 500);
    }
  }

  async function deleteSession(session, e) {
    e.stopPropagation();
    if (session.status === 'recording') return;

    try {
      await api.deleteSession(session.id);
      sessions = sessions.filter(s => s.id !== session.id);
      if (expandedSession === session.id) {
        expandedSession = null;
        metadata = [];
      }
      actions.showToast('Aufnahme geloescht', 'success');
      loadStats();
    } catch (e) {
      actions.showToast('Fehler beim Loeschen', 'error');
    }
  }

  function downloadSession(session, e) {
    e.stopPropagation();
    // Segmente vorhanden -> ZIP-Paket, sonst Gesamtdatei
    const url = session.segment_count > 0
      ? api.getZipDownloadUrl(session.id)
      : api.getFullDownloadUrl(session.id);
    window.open(url, '_blank');
  }

  function playSegment(segment) {
    const playUrl = api.getSegmentPlayUrl(segment.id);
    actions.playRecording({
      path: segment.file_path,
      name: segment.title || `Segment ${segment.segment_index}`,
      session_id: segment.session_id,
      station_name: segment.title,
      duration: segment.duration_ms / 1000,
      playUrl
    });
  }

  function downloadSegment(segment, e) {
    e.stopPropagation();
    const url = api.getSegmentDownloadUrl(segment.id);
    window.open(url, '_blank');
  }

  async function deleteSegment(session, segment, e) {
    e.stopPropagation();
    try {
      await api.deleteSegment(session.id, segment.id);
      segments = segments.filter(s => s.id !== segment.id);
      // Falls keine Segmente mehr: Session aus Liste entfernen
      if (segments.length === 0) {
        sessions = sessions.filter(s => s.id !== session.id);
        expandedSession = null;
      }
      actions.showToast('Segment geloescht', 'success');
      loadStats();
    } catch (e) {
      actions.showToast('Fehler beim Loeschen', 'error');
    }
  }

  let splitting = $state(false);

  async function splitSession(session) {
    splitting = true;
    try {
      const result = await api.splitSession(session.id);
      if (result.success) {
        actions.showToast(`${result.segments} Segmente erzeugt`, 'success');
        // Segmente neu laden
        const segResult = await api.getSegments(session.id);
        segments = segResult.segments || [];
        metadata = [];
        loadStats();
        loadSessions();
      }
    } catch (e) {
      actions.showToast('Split fehlgeschlagen', 'error');
    }
    splitting = false;
  }

  // Format Helpers aus lib/formatters.js importiert

  function codecBadge(session) {
    const codec = session.codec || '';
    const ext = session.file_format || '';
    if (codec) return codec.toUpperCase();
    if (ext) return ext.replace('.', '').toUpperCase();
    return 'MP3';
  }

  // Ist diese Session gerade im Player aktiv?
  let activeSessionId = $derived(appState.currentRecording?.session_id || null);
</script>

<div class="recordings-tab">
  <!-- Stats Bar -->
  <div class="stats-bar">
    <div class="stat-item">
      <span class="stat-value">{stats.file_count}</span>
      <span class="stat-label">DATEIEN</span>
    </div>
    <div class="stat-item">
      <span class="stat-value">{stats.used_mb?.toFixed(1) || '0'}</span>
      <span class="stat-label">MB BELEGT</span>
    </div>
    <div class="stat-item">
      <span class="stat-value">{stats.disk_free_gb?.toFixed(1) || '0'}</span>
      <span class="stat-label">GB FREI</span>
    </div>

    {#if recStatus?.recording}
      <div class="stat-item stat-active">
        <HiFiLed color="red" size="small" blink={true} />
        <span class="stat-value">{recStatus.station_name || 'Aufnahme'}</span>
        <span class="stat-label">{formatDuration(recStatus.duration)}</span>
      </div>
    {/if}

    <div class="stat-spacer"></div>
    <button class="hifi-btn hifi-btn-small" onclick={loadData} title="Aktualisieren">
      <i class="fa-solid fa-arrows-rotate"></i>
    </button>
  </div>

  <!-- Session-Liste -->
  <div class="session-list">
    {#if isLoading}
      <div class="empty-state">
        <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
      </div>
    {:else if sessions.length === 0}
      <div class="empty-state">
        <HiFiDisplay size="medium">KEINE AUFNAHMEN</HiFiDisplay>
        <p class="empty-hint">Starte eine Aufnahme ueber den REC-Button im Player</p>
      </div>
    {:else}
      {#each sessions as session (session.id)}
        {@const isActive = session.status === 'recording'}
        {@const isPlaying = activeSessionId === session.id}
        {@const isExpanded = expandedSession === session.id}

        <div class="session-card" class:active={isActive} class:playing={isPlaying}>
          <!-- Session-Header (klickbar) -->
          <button class="session-header" onclick={() => toggleSession(session)}>
            <div class="session-led">
              <HiFiLed
                color={isActive ? 'red' : isPlaying ? 'green' : 'off'}
                size="small"
                blink={isActive}
              />
            </div>

            <div class="session-info">
              <span class="session-name">{session.station_name || session.id}</span>
              <span class="session-date">{formatDate(session.start_time)}</span>
            </div>

            <div class="session-meta">
              {#if session.segment_count > 0}
                <span class="session-tracks">{session.segment_count}</span>
              {/if}
              <span class="session-duration">{isActive ? formatDuration(recStatus?.duration || 0) : formatDuration(session.duration)}</span>
              <span class="session-size">{formatSize(session.file_size)}</span>
              {#if session.bitrate}
                <span class="session-bitrate">{session.bitrate} kbps</span>
              {/if}
              <span class="session-codec">{codecBadge(session)}</span>
            </div>

            <div class="session-actions">
              {#if !isActive}
                <button class="action-btn play-btn" class:playing={isPlaying} onclick={(e) => { e.stopPropagation(); playSession(session); }} title={isPlaying ? 'Stoppen' : 'Abspielen'}>
                  <i class="fa-solid {isPlaying ? 'fa-stop' : 'fa-play'}"></i>
                </button>
                <button class="action-btn" onclick={(e) => downloadSession(session, e)} title="Herunterladen">
                  <i class="fa-solid fa-download"></i>
                </button>
                <button class="action-btn delete-btn" onclick={(e) => deleteSession(session, e)} title="Loeschen">
                  <i class="fa-solid fa-trash-can"></i>
                </button>
              {:else}
                <button class="action-btn rec-btn" onclick={(e) => { e.stopPropagation(); actions.stopRecording(); }} title="Aufnahme stoppen">
                  <i class="fa-solid fa-stop"></i>
                </button>
              {/if}
            </div>

            <div class="session-expand">
              <i class="fa-solid {isExpanded ? 'fa-chevron-up' : 'fa-chevron-down'}"></i>
            </div>
          </button>

          <!-- Expandierter Detail-Bereich -->
          {#if isExpanded}
            <div class="session-detail">
              {#if metadataLoading}
                <div class="meta-loading">Lade Metadaten...</div>
              {:else if segments.length > 0}
                <!-- Segmente: Atomare Tracks mit Play/Download/Delete -->
                <div class="meta-list">
                  <div class="meta-header">SEGMENTE ({segments.length} Tracks)</div>
                  {#each segments as seg}
                    <div class="segment-entry" role="button" tabindex="0" onclick={() => playSegment(seg)}>
                      <span class="meta-time">[{formatMetaTime(seg.start_ms)}]</span>
                      <span class="meta-title">{seg.title}</span>
                      <span class="segment-duration">{formatDurationMs(seg.duration_ms)}</span>
                      <span class="segment-size">{formatSize(seg.file_size)}</span>
                      <div class="segment-actions" onclick={(e) => e.stopPropagation()}>
                        <button class="action-btn" onclick={(e) => downloadSegment(seg, e)} title="Herunterladen">
                          <i class="fa-solid fa-download"></i>
                        </button>
                        <button class="action-btn delete-btn" onclick={(e) => deleteSegment(session, seg, e)} title="Loeschen">
                          <i class="fa-solid fa-trash-can"></i>
                        </button>
                      </div>
                    </div>
                  {/each}
                </div>
              {:else if metadata.length > 0}
                <!-- Fallback: Nur Metadata ohne Segmente (Legacy) -->
                <div class="meta-list">
                  <div class="meta-header-row">
                    <span class="meta-header">TRACKLIST ({metadata.length} Titel)</span>
                    <button
                      class="split-btn"
                      onclick={() => splitSession(session)}
                      disabled={splitting}
                      title="Tracks in einzelne Dateien schneiden"
                    >
                      <i class="fa-solid {splitting ? 'fa-spinner fa-spin' : 'fa-scissors'}"></i>
                      {splitting ? 'SCHNEIDE...' : 'SEGMENTE ERZEUGEN'}
                    </button>
                  </div>
                  {#each metadata as entry, i}
                    <button class="meta-entry" onclick={() => playAtPosition(session, entry)}>
                      <span class="meta-time">[{formatMetaTime(entry.t)}]</span>
                      <span class="meta-title">{entry.title}</span>
                    </button>
                  {/each}
                </div>
              {:else}
                <div class="meta-empty">Keine ICY-Metadaten vorhanden</div>
              {/if}
            </div>
          {/if}
        </div>
      {/each}
    {/if}
  </div>
</div>

<style>
  .recordings-tab {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  /* Stats Bar */
  .stats-bar {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 10px 16px;
    background: var(--hifi-bg-secondary);
    border-bottom: 1px solid var(--hifi-border-dark);
    flex-shrink: 0;
  }

  .stat-item {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .stat-value {
    font-family: var(--hifi-font-body);
    font-size: 12px;
    font-weight: 600;
    color: var(--hifi-display-text);
  }

  .stat-label {
    font-family: var(--hifi-font-body);
    font-size: 9px;
    color: var(--hifi-text-secondary);
    letter-spacing: 0.5px;
  }

  .stat-active {
    gap: 6px;
    padding: 4px 10px;
    background: rgba(180, 40, 40, 0.1);
    border-radius: var(--hifi-border-radius-sm);
  }

  .stat-active .stat-value {
    color: var(--hifi-led-red);
  }

  .stat-spacer {
    flex: 1;
  }

  /* Session List */
  .session-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px 12px;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    gap: 12px;
  }

  .empty-hint {
    font-family: var(--hifi-font-labels);
    font-size: 12px;
    color: var(--hifi-text-secondary);
    text-align: center;
  }

  /* Session Card */
  .session-card {
    background: var(--hifi-bg-secondary);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm);
    margin-bottom: 4px;
    overflow: hidden;
  }

  .session-card.active {
    border-color: rgba(180, 40, 40, 0.3);
    background: rgba(180, 40, 40, 0.05);
  }

  .session-card.playing {
    border-color: rgba(40, 180, 40, 0.3);
    background: rgba(40, 180, 40, 0.03);
  }

  /* Session Header */
  .session-header {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 8px 12px;
    background: none;
    border: none;
    cursor: pointer;
    text-align: left;
    color: inherit;
    font: inherit;
  }

  .session-header:hover {
    background: var(--hifi-bg-tertiary);
  }

  .session-led {
    flex-shrink: 0;
  }

  .session-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .session-name {
    font-family: var(--hifi-font-body);
    font-size: 13px;
    font-weight: 500;
    color: var(--hifi-text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .session-date {
    font-family: var(--hifi-font-body);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
  }

  .session-meta {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }

  .session-tracks {
    font-family: var(--hifi-font-display);
    font-size: 12px;
    font-weight: 700;
    color: var(--hifi-display-amber);
    min-width: 20px;
    text-align: right;
  }

  .session-duration {
    font-family: var(--hifi-font-body);
    font-size: 12px;
    font-weight: 600;
    color: var(--hifi-display-text);
    min-width: 48px;
    text-align: right;
  }

  .session-size {
    font-family: var(--hifi-font-body);
    font-size: 11px;
    color: var(--hifi-text-secondary);
    min-width: 60px;
    text-align: right;
  }

  .session-bitrate {
    font-family: var(--hifi-font-values);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    min-width: 50px;
    text-align: right;
  }

  .session-codec {
    font-family: var(--hifi-font-body);
    font-size: 9px;
    font-weight: 700;
    color: var(--hifi-display-blue);
    background: rgba(100, 180, 255, 0.08);
    padding: 2px 6px;
    border-radius: 3px;
    letter-spacing: 0.5px;
  }

  /* Actions */
  .session-actions {
    display: flex;
    gap: 4px;
    flex-shrink: 0;
  }

  .action-btn {
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--hifi-bg-tertiary);
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    cursor: pointer;
    color: var(--hifi-text-secondary);
    font-size: 11px;
    transition: background 0.15s, color 0.15s;
  }

  .action-btn:hover {
    background: var(--hifi-bg-panel);
    color: var(--hifi-text-primary);
  }

  .action-btn.play-btn:hover {
    color: var(--hifi-display-text);
  }

  .action-btn.play-btn.playing {
    background: rgba(40, 180, 40, 0.15);
    color: var(--hifi-led-green, #4caf50);
  }

  .action-btn.play-btn.playing:hover {
    background: rgba(40, 180, 40, 0.25);
  }

  .action-btn.delete-btn:hover {
    color: var(--hifi-led-red);
  }

  .action-btn.rec-btn {
    background: rgba(180, 40, 40, 0.15);
    color: var(--hifi-led-red);
  }

  .action-btn.rec-btn:hover {
    background: rgba(180, 40, 40, 0.25);
  }

  .session-expand {
    flex-shrink: 0;
    width: 20px;
    text-align: center;
    color: var(--hifi-text-secondary);
    font-size: 10px;
  }

  /* Detail (Metadata) */
  .session-detail {
    border-top: 1px solid var(--hifi-border-dark);
    padding: 8px 12px;
    background: var(--hifi-bg-panel);
  }

  .meta-loading, .meta-empty {
    font-family: var(--hifi-font-labels);
    font-size: 11px;
    color: var(--hifi-text-secondary);
    padding: 8px 0;
    text-align: center;
  }

  .meta-list {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .meta-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4px;
  }

  .meta-header {
    font-family: var(--hifi-font-body);
    font-size: 9px;
    font-weight: 600;
    color: var(--hifi-text-secondary);
    letter-spacing: 1px;
    text-transform: uppercase;
  }

  .split-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 3px 8px;
    background: var(--hifi-bg-tertiary);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm);
    color: var(--hifi-display-text);
    font-family: var(--hifi-font-body);
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.5px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }

  .split-btn:hover:not(:disabled) {
    background: var(--hifi-bg-panel);
    color: var(--hifi-accent);
  }

  .split-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .meta-entry {
    display: flex;
    gap: 8px;
    padding: 4px 8px;
    background: none;
    border: none;
    cursor: pointer;
    text-align: left;
    border-radius: 3px;
    color: inherit;
    font: inherit;
  }

  .meta-entry:hover {
    background: var(--hifi-bg-secondary);
  }

  .meta-time {
    font-family: var(--hifi-font-body);
    font-size: 11px;
    font-weight: 500;
    color: var(--hifi-display-text);
    flex-shrink: 0;
    min-width: 40px;
  }

  .meta-title {
    font-family: var(--hifi-font-body);
    font-size: 11px;
    color: var(--hifi-text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* Segment Entries - tabellarisches Grid */
  .segment-entry {
    display: grid;
    grid-template-columns: 80px 1fr 42px 56px auto;
    align-items: center;
    gap: 0;
    border-radius: 3px;
    padding: 3px 0;
    cursor: pointer;
  }

  .segment-entry:hover {
    background: var(--hifi-bg-secondary);
  }

  .segment-entry .meta-time {
    padding-left: 8px;
    min-width: unset;
  }

  .segment-entry .meta-title {
    padding: 0 8px;
    font-size: 12px;
    font-weight: 600;
  }

  .segment-duration {
    font-family: var(--hifi-font-body);
    font-size: 10px;
    font-weight: 600;
    color: var(--hifi-text-secondary);
    text-align: right;
    padding-right: 8px;
  }

  .segment-size {
    font-family: var(--hifi-font-body);
    font-size: 10px;
    color: var(--hifi-text-secondary);
    text-align: right;
    padding-right: 8px;
  }

  .segment-actions {
    display: flex;
    gap: 2px;
    padding-right: 4px;
  }

  .segment-actions .action-btn {
    width: 24px;
    height: 24px;
    font-size: 10px;
  }
</style>
