<script>
  import HiFiLed from './hifi/HiFiLed.svelte';
  import HiFiDisplay from './hifi/HiFiDisplay.svelte';
  import FileExplorer from './shared/FileExplorer.svelte';
  import RecordingSidebar from './recordings/RecordingSidebar.svelte';
  import CutterView from './recordings/CutterView.svelte';
  import { api } from '../lib/api.js';
  import { tick } from 'svelte';
  import { appState, actions } from '../lib/store.svelte.js';
  import { t } from '../lib/i18n.svelte.js';
  import { formatDuration, formatSize, formatDate, formatMetaTime, formatDurationMs } from '../lib/formatters.js';

  let sessions = $state([]);
  let folders = $state([]);
  let stats = $state({ disk_free_gb: 0, file_count: 0, used_mb: 0 });
  let isLoading = $state(false);
  let selectedSession = $state(null);
  let metadata = $state([]);
  let segments = $state([]);
  let selectedSegmentIds = $state([]);
  let metadataLoading = $state(false);

  // View: aus Route abgeleitet ('details' | 'file-explorer' | 'cutter')
  let view = $derived.by(() => {
    if (appState.activeTab !== 'recordings') return 'details';
    const seg = appState.routeSegments?.[0];
    if (seg === 'files') return 'file-explorer';
    if (seg === 'cutter') return 'cutter';
    if (seg === 'search') return 'details'; // Suche bleibt in details-View
    return 'details';
  });

  function setView(v) {
    if (v === 'file-explorer') actions.navigateTo('/recorder/files');
    else if (v === 'cutter') actions.navigateTo('/recorder/cutter');
    else actions.navigateTo('/recorder');
  }

  // Sidebar
  let sidebarWidth = $state(Number(localStorage.getItem('radiohub_rec_sidebar_width')) || 280);
  let searchQuery = $state('');

  // Aktiver Aufnahme-Status (wird gepollt)
  let recStatus = $state(null);
  let pollInterval = null;

  // ICY Ignore-Liste (Set aus Pattern-Strings fuer schnellen Lookup)
  let ignoredTitles = $state(new Set());

  $effect(() => {
    loadData();
    loadIgnoredTitles();
    startPolling();
    // Deep-Link: Search-Query aus URL /recorder/search/[query]
    const segs = appState.routeSegments;
    if (segs?.[0] === 'search' && segs[1]) {
      searchQuery = decodeURIComponent(segs[1]);
    }
    return () => stopPolling();
  });

  $effect(() => {
    if (view === 'file-explorer') loadFileExplorer();
  });

  // Auto-Expand: Session des aktuell spielenden Segments öffnen + hinscrollen
  $effect(() => {
    const rec = appState.currentRecording;
    if (rec?.session_id && appState.playerMode === 'recording') {
      const session = sessions.find(s => s.id === rec.session_id);
      if (session && selectedSession?.id !== rec.session_id) {
        selectSession(session);
      }
    }
  });

  function scrollToPlayingSegment() {
    const el = document.querySelector('.segment-entry.playing');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  // === Source-Jump: Transport-Label Klick scrollt zum spielenden Segment ===
  let lastRecJumpTs = 0;
  $effect(() => {
    const req = appState.sourceJumpRequest;
    if (!req || req.type !== 'recording' || !req.id || req.ts <= lastRecJumpTs) return;
    lastRecJumpTs = req.ts;
    setTimeout(scrollToPlayingSegment, 200);
  });

  async function selectSession(session) {
    if (selectedSession?.id === session.id) return;
    selectedSession = session;
    setView('details');
    metadata = [];
    segments = [];
    selectedSegmentIds = [];
    metadataLoading = true;
    try {
      const [segResult, metaResult] = await Promise.all([
        api.getSegments(session.id).catch(() => ({ segments: [] })),
        session?.meta_file_path
          ? api.getSessionMetadata(session.id).catch(() => ({ entries: [] }))
          : Promise.resolve({ entries: [] })
      ]);
      segments = segResult.segments || [];
      selectedSegmentIds = segments.map(s => s.id);
      metadata = metaResult.entries || [];
    } catch (e) {}
    metadataLoading = false;
    await tick();
    scrollToPlayingSegment();
  }

  let wasRecording = false;

  function startPolling() {
    pollInterval = setInterval(async () => {
      try {
        if (appState.isRecording) {
          wasRecording = true;
          recStatus = { recording: true, station_name: appState.currentStation?.name, duration: appState.recordingElapsed };
          await loadSessions();
          // Aktive Session-Referenz aktualisieren damit status/segment_count live angezeigt werden
          if (selectedSession) {
            const updated = sessions.find(s => s.id === selectedSession.id);
            if (updated) selectedSession = updated;
          }
        } else if (wasRecording) {
          wasRecording = false;
          recStatus = null;
          await loadSessions();
          loadStats();
          // selectedSession aktualisieren damit status von 'recording' auf 'completed' wechselt
          if (selectedSession) {
            const updated = sessions.find(s => s.id === selectedSession.id);
            if (updated) selectedSession = updated;
          }
        } else {
          recStatus = null;
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
    await Promise.all([loadStats(), loadSessions(), loadFolders()]);
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

  async function loadFolders() {
    try {
      const result = await api.getRecordingFolders();
      folders = result.folders || [];
    } catch (e) {}
  }

  // === Ordner-Verwaltung ===
  async function createFolder(name) {
    try {
      await api.createRecordingFolder(name);
      await loadFolders();
      actions.showToast(t('toast.ordnerErstellt'), 'success');
    } catch (e) {
      actions.showToast(t('toast.speichernFehler'), 'error');
    }
  }

  async function renameFolder(id, newName) {
    try {
      await api.updateRecordingFolder(id, { name: newName });
      await loadFolders();
      actions.showToast(t('toast.ordnerUmbenannt'), 'success');
    } catch (e) {
      actions.showToast(t('toast.speichernFehler'), 'error');
    }
  }

  async function deleteFolder(id) {
    try {
      await api.deleteRecordingFolder(id);
      await loadFolders();
      actions.showToast(t('toast.ordnerGeloescht'), 'success');
    } catch (e) {
      actions.showToast(`${t('toast.loeschenFehler')}: ${e.message}`, 'error');
    }
  }

  async function activateFolder(id) {
    try {
      await api.activateRecordingFolder(id);
      await loadFolders();
    } catch (e) {}
  }

  async function deactivateFolder() {
    try {
      await api.deactivateRecordingFolder();
      await loadFolders();
    } catch (e) {}
  }

  async function moveSessionToFolder(sessionId, folderId) {
    try {
      await api.moveSession(sessionId, folderId);
      await loadSessions();
      actions.showToast(t('toast.aufnahmeVerschoben'), 'success');
    } catch (e) {
      actions.showToast(t('toast.speichernFehler'), 'error');
    }
  }

  function playSession(session) {
    if (session.status === 'recording') return;
    if (activeSessionId === session.id) {
      actions.stop();
      return;
    }

    // Segmentierte Session: erstes Segment abspielen, Playlist aufbauen
    if (session.segment_count > 0 && segments.length > 0 && segments[0].session_id === session.id) {
      playSegment(segments[0]);
      return;
    }

    const filePath = session.file_path || '';
    const fileName = filePath.split('/').pop() || session.id;
    const playUrl = api.getPlayUrl(`radio/${fileName}`);

    actions.playRecording({
      path: filePath,
      name: session.station_name || fileName,
      session_id: session.id,
      station_name: session.station_name,
      date: session.start_time,
      duration: session.duration,
      playUrl,
      source: 'recording'
    });
  }

  function playAtPosition(session, entry) {
    playSession(session);
    if (entry.t > 0 && session.duration > 0) {
      setTimeout(() => {
        const percent = (entry.t / 1000) / session.duration * 100;
        import('../lib/playerEngine.js').then(engine => engine.seek(percent));
      }, 500);
    }
  }

  async function deleteSession(session) {
    if (session.status === 'recording') return;
    try {
      // Wiedergabe stoppen falls diese Session gerade abgespielt wird
      if (appState.currentRecording?.session_id === session.id) {
        actions.stop();
      }
      await api.deleteSession(session.id);
      sessions = sessions.filter(s => s.id !== session.id);
      if (selectedSession?.id === session.id) {
        selectedSession = null;
        metadata = [];
        segments = [];
      }
      actions.showToast(t('toast.aufnahmeGeloescht'), 'success');
      loadStats();
      if (view === 'file-explorer') loadFileExplorer();
    } catch (e) {
      actions.showToast(`${t('toast.loeschenFehler')}: ${e.message}`, 'error');
    }
  }

  function downloadSession(session) {
    const url = session.segment_count > 0
      ? api.getZipDownloadUrl(session.id)
      : api.getFullDownloadUrl(session.id);
    window.open(url, '_blank');
  }

  function mapSegmentToPlaylistEntry(s) {
    return {
      path: s.file_path,
      name: s.title || `Segment ${s.segment_index}`,
      session_id: s.session_id,
      station_name: s.title,
      duration: s.duration_ms / 1000,
      playUrl: api.getSegmentPlayUrl(s.id)
    };
  }

  async function playSegment(segment) {
    const playlistSegments = selectedSegmentIds.length > 0
      ? segments.filter(s => selectedSegmentIds.includes(s.id))
      : segments;

    if (appState.playMode === 'shuffle') {
      try {
        const result = await api.getAllSegments();
        const all = result.segments || [];
        appState.recordingPlaylist = all.length > 0
          ? all.map(mapSegmentToPlaylistEntry)
          : playlistSegments.map(mapSegmentToPlaylistEntry);
      } catch (e) {
        appState.recordingPlaylist = playlistSegments.map(mapSegmentToPlaylistEntry);
      }
    } else {
      appState.recordingPlaylist = playlistSegments.map(mapSegmentToPlaylistEntry);
    }

    const playUrl = api.getSegmentPlayUrl(segment.id);
    actions.playRecording({
      path: segment.file_path,
      name: segment.title || `Segment ${segment.segment_index}`,
      session_id: segment.session_id,
      station_name: segment.title,
      duration: segment.duration_ms / 1000,
      playUrl,
      source: 'recording'
    });
  }

  function downloadSegment(segment, e) {
    e.stopPropagation();
    const url = api.getSegmentDownloadUrl(segment.id);
    window.open(url, '_blank');
  }

  async function loadIgnoredTitles() {
    try {
      const data = await api.getIcyIgnoreList();
      ignoredTitles = new Set((data.items || []).map(i => i.pattern));
    } catch (e) {
      console.error('Ignore-Liste laden fehlgeschlagen:', e);
    }
  }

  function isTitleIgnored(title) {
    if (!title) return false;
    return ignoredTitles.has(title);
  }

  async function toggleIgnore(title, e) {
    e.stopPropagation();
    if (!title) return;
    const wasIgnored = isTitleIgnored(title);
    try {
      if (wasIgnored) {
        await api.removeIcyIgnoreByPattern(title);
        const next = new Set(ignoredTitles);
        next.delete(title);
        ignoredTitles = next;
        actions.showToast(t('recordings.titelNichtMehrIgnoriert'), 'success');
      } else {
        await api.addIcyIgnore(title, 'exact');
        ignoredTitles = new Set([...ignoredTitles, title]);
        actions.showToast(t('recordings.titelIgnoriert'), 'success');
      }
    } catch (err) {
      if (!wasIgnored && err.message?.includes('409')) {
        ignoredTitles = new Set([...ignoredTitles, title]);
        actions.showToast(t('recordings.titelIgnoriert'), 'info');
      } else {
        actions.showToast(`Fehler: ${err.message}`, 'error');
      }
    }
  }

  async function deleteSegment(segment, e) {
    e.stopPropagation();
    try {
      // Wiedergabe stoppen falls dieses Segment gerade abgespielt wird
      if (appState.currentRecording?.session_id === selectedSession?.id) {
        actions.stop();
      }
      await api.deleteSegment(selectedSession.id, segment.id);
      segments = segments.filter(s => s.id !== segment.id);
      if (segments.length === 0) {
        sessions = sessions.filter(s => s.id !== selectedSession.id);
        selectedSession = null;
      }
      actions.showToast(t('toast.segmentGeloescht'), 'success');
      loadStats();
    } catch (e) {
      actions.showToast(`${t('toast.loeschenFehler')}: ${e.message}`, 'error');
    }
  }

  let splitting = $state(false);

  async function splitSession(session) {
    splitting = true;
    try {
      const result = await api.splitSession(session.id);
      if (result.success) {
        actions.showToast(t('recordings.segmenteErzeugtToast', { count: result.segments }), 'success');
        const segResult = await api.getSegments(session.id);
        segments = segResult.segments || [];
        metadata = [];
        loadStats();
        loadSessions();
      }
    } catch (e) {
      const msg = e?.message || t('recordings.splitFehler');
      actions.showToast(msg, 'error');
    }
    splitting = false;
  }

  let activeSessionId = $derived(appState.currentRecording?.session_id || null);
  let playingPath = $derived(appState.currentRecording?.path || null);

  // Gefilterte Sessions (Suchfilter)
  let filteredSessions = $derived(
    searchQuery
      ? sessions.filter(s => (s.station_name || s.id).toLowerCase().includes(searchQuery.toLowerCase()))
      : sessions
  );

  // === File Explorer ===
  let fileExplorerFolders = $state([]);
  let fileExplorerTotalSize = $state(0);
  let fileExplorerTotalFiles = $state(0);
  let fileExplorerLoading = $state(false);

  function toggleFileExplorer() {
    if (view === 'file-explorer') {
      setView('details');
    } else {
      setView('file-explorer');
      loadFileExplorer();
    }
  }

  async function loadFileExplorer() {
    fileExplorerLoading = true;
    try {
      const result = await api.getRecordingFiles();
      fileExplorerFolders = result.folders || [];
      fileExplorerTotalSize = result.total_size || 0;
      fileExplorerTotalFiles = result.total_files || 0;
    } catch (e) {
      // Netzwerkfehler ignorieren
    }
    fileExplorerLoading = false;
  }

  async function handleFileExplorerDelete(file) {
    try {
      await api.deleteFileExplorer(file.path);
      actions.showToast(t('toast.dateiGeloescht'), 'success');
      await loadFileExplorer();
      await loadSessions();
      await loadStats();
    } catch (e) {
      actions.showToast(t('toast.loeschenFehler'), 'error');
    }
  }

  async function handleDeleteOrphaned() {
    const orphaned = fileExplorerFolders.filter(f => f.orphaned);
    if (!orphaned.length) return;
    try {
      const result = await api.deleteOrphanedFolders();
      actions.showToast(`${result.count} Ordner gelöscht`, 'success');
      await loadFileExplorer();
      await loadStats();
    } catch (e) {
      actions.showToast(t('toast.loeschenFehler'), 'error');
    }
  }

  function handleFileExplorerPlay(file, selectedList) {
    const playlist = selectedList && selectedList.length > 0 ? selectedList : [file];
    appState.recordingPlaylist = playlist.map(f => ({
      path: f.path,
      name: f.name,
      playUrl: api.getPlayUrl(f.path.replace(/^.*\/recordings\//, '')),
      source: 'file'
    }));

    actions.playRecording({
      path: file.path,
      name: file.name,
      playUrl: api.getPlayUrl(file.path.replace(/^.*\/recordings\//, '')),
      source: 'file'
    });
  }

  function handleCutter() {
    if (selectedSession && selectedSession.status !== 'recording') {
      setView('cutter');
    } else {
      actions.showToast(t('recordings.bitteAufnahmeAuswaehlen'), 'info');
    }
  }

  function handleCutterClose() {
    setView('details');
  }

  async function handleCutterSplit() {
    // Nach Schnitt: Segmente + Sessions neu laden, zurück zur Detail-Ansicht
    await Promise.all([loadSessions(), loadStats()]);
    if (selectedSession) {
      const segResult = await api.getSegments(selectedSession.id).catch(() => ({ segments: [] }));
      segments = segResult.segments || [];
      selectedSegmentIds = segments.map(s => s.id);
    }
    setView('details');
  }

  function handleSegmentSelectionChange(ids) {
    selectedSegmentIds = ids;
  }

  function handleSidebarResize(newWidth) {
    sidebarWidth = newWidth;
    localStorage.setItem('radiohub_rec_sidebar_width', String(newWidth));
  }

  function handleSearch(query) {
    searchQuery = query;
    if (query && query.length >= 2) {
      actions.navigateTo('/recorder/search/' + encodeURIComponent(query), { replace: true });
    } else if (!query) {
      actions.navigateTo('/recorder', { replace: true });
    }
  }
</script>

<div class="recordings-tab">
  <RecordingSidebar
    sessions={filteredSessions}
    {stats}
    {folders}
    {segments}
    {selectedSegmentIds}
    selectedSessionId={selectedSession?.id || null}
    {activeSessionId}
    isRecording={appState.isRecording}
    width={sidebarWidth}
    fileExplorerActive={view === 'file-explorer'}
    {searchQuery}
    isRefreshing={isLoading}
    onselectsession={selectSession}
    onrefresh={loadData}
    onfileexplorer={toggleFileExplorer}
    oncutter={handleCutter}
    onsearch={handleSearch}
    onresize={handleSidebarResize}
    oncreatefolder={createFolder}
    onrenamefolder={renameFolder}
    ondeletefolder={deleteFolder}
    onactivatefolder={activateFolder}
    ondeactivatefolder={deactivateFolder}
    onmovesession={moveSessionToFolder}
    onsegmentselectionchange={handleSegmentSelectionChange}
  />

  <div class="recording-content">
    {#if view === 'cutter' && selectedSession}
      <CutterView
        session={selectedSession}
        {metadata}
        {segments}
        {selectedSegmentIds}
        onclose={handleCutterClose}
        onsplit={handleCutterSplit}
      />
    {:else if view === 'file-explorer'}
      <FileExplorer
        type="recording"
        folders={fileExplorerFolders}
        totalSize={fileExplorerTotalSize}
        totalFiles={fileExplorerTotalFiles}
        isLoading={fileExplorerLoading}
        activeSessionPath={selectedSession?.file_path || null}
        playingFilePath={appState.playerMode === 'recording' && appState.currentRecording?.source === 'file' ? appState.currentRecording.path : null}
        onplay={handleFileExplorerPlay}
        ondelete={handleFileExplorerDelete}
        onrefresh={loadFileExplorer}
        ondeleteorphaned={handleDeleteOrphaned}
        oncutter={handleCutter}
      />
    {:else if selectedSession}
      {@const session = selectedSession}
      {@const isActive = session.status === 'recording'}
      {@const isStalled = session.status === 'stalled'}
      {@const isPlaying = activeSessionId === session.id}

      <!-- Session Detail Header -->
      <div class="detail-header">
        <div class="detail-info">
          <HiFiLed
            color={isActive ? 'red' : isStalled ? 'amber' : isPlaying ? 'green' : 'blue'}
            size="small"
            blink={isActive}
            pulse={isPlaying}
          />
          <span class="detail-name">{session.station_name || session.id}</span>
          {#if isStalled}
            <span class="stalled-tag">{t('recordings.abgebrochen')}</span>
          {/if}
          <span class="detail-date">{formatDate(session.start_time)}</span>
        </div>
        <div class="detail-meta">
          <span class="meta-val">{session.segment_count > 0 ? session.segment_count : '--'} Seg.</span>
          <span class="meta-val">{isActive ? formatDuration(appState.recordingElapsed) : formatDuration(session.duration)}</span>
          <span class="meta-val">{session.file_size ? formatSize(session.file_size) : '--'}</span>
          <span class="meta-val">{session.bitrate || (session.duration > 0 ? Math.round((session.file_size * 8) / (session.duration * 1000)) : '--')} kbps</span>
        </div>
        <div class="detail-actions">
          {#if !isActive}
            <button class="action-btn play-btn" class:playing={isPlaying} onclick={() => playSession(session)} title={isPlaying ? t('recordings.stoppen') : t('recordings.abspielen')}>
              <i class="fa-solid {isPlaying ? 'fa-stop' : 'fa-play'}"></i>
            </button>
            {#if folders.length > 0}
              <div class="move-dropdown">
                <button class="action-btn" title={t('recordings.inOrdnerVerschieben')}>
                  <i class="fa-solid fa-folder-open"></i>
                </button>
                <div class="move-menu">
                  {#if session.folder_id}
                    <button class="move-item" onclick={() => moveSessionToFolder(session.id, null)}>
                      <i class="fa-solid fa-arrow-up"></i> {t('recordings.rootKeinOrdner')}
                    </button>
                  {/if}
                  {#each folders as folder}
                    {#if folder.id !== session.folder_id}
                      <button class="move-item" onclick={() => moveSessionToFolder(session.id, folder.id)}>
                        <i class="fa-solid fa-folder"></i> {folder.name}
                      </button>
                    {/if}
                  {/each}
                </div>
              </div>
            {/if}
            <button class="action-btn" onclick={() => downloadSession(session)} title={t('recordings.herunterladen')}>
              <i class="fa-solid fa-download"></i>
            </button>
            <button class="action-btn delete-btn" onclick={() => deleteSession(session)} title={t('recordings.aufnahmeLoeschen')}>
              <i class="fa-solid fa-trash-can"></i>
            </button>
          {:else}
            <button class="action-btn rec-btn" onclick={() => actions.stopRecording()} title={t('recordings.aufnahmeStoppen')}>
              <i class="fa-solid fa-stop"></i>
            </button>
          {/if}
        </div>
      </div>

      <!-- Session Detail Body -->
      <div class="detail-body">
        {#if isActive}
          {#if appState.devMode && appState.recordingEvents.some(e => e.type === 'gap_start')}
            {@const gaps = appState.recordingEvents.filter(e => e.type === 'gap_start')}
            {@const hasOpenGap = appState.recordingEvents.filter(e => e.type === 'gap_start').length > appState.recordingEvents.filter(e => e.type === 'gap_end').length}
            <div class="gap-banner" class:active={hasOpenGap}>
              <i class="fa-solid fa-triangle-exclamation"></i>
              {#if hasOpenGap}
                Dropout erkannt -- kein Datenstrom!
              {:else}
                {gaps.length} Dropout(s) erkannt
              {/if}
            </div>
          {/if}
          {#if appState.recordingIcyEntries.length > 0}
            <div class="meta-list">
              <div class="meta-header">{t('recordings.erkannteTitle')} ({appState.recordingIcyEntries.length})</div>
              {#each appState.recordingIcyEntries as entry}
                <div class="meta-entry live-entry" class:sperrtext={entry.ignored}>
                  <span class="meta-time">[{formatMetaTime(entry.t)}]</span>
                  <span class="meta-title">
                    {entry.title}
                    {#if entry.ignored}
                      <span class="sperrtext-badge" title="Sperrtext: {entry.raw_title}">SPERR</span>
                    {/if}
                  </span>
                </div>
              {/each}
            </div>
          {:else}
            <div class="meta-empty">{t('recordings.nochKeineTitelwechsel')}</div>
          {/if}
        {:else if metadataLoading}
          <div class="meta-loading">{t('recordings.ladeMetadaten')}</div>
        {:else if segments.length > 0}
          <div class="meta-list">
            <div class="meta-header">{t('recordings.segmente')} ({segments.length} {t('recordings.tracks')})</div>
            {#each segments as seg}
              <div class="segment-entry" class:playing={playingPath === seg.file_path} role="button" tabindex="0" onclick={() => playSegment(seg)} onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); playSegment(seg); } }}>
                <span class="meta-time">[{formatMetaTime(seg.start_ms)}]</span>
                <span class="meta-title">{seg.title}</span>
                <span class="segment-duration">{formatDurationMs(seg.duration_ms)}</span>
                <span class="segment-size">{formatSize(seg.file_size)}</span>
                <!-- svelte-ignore a11y_click_events_have_key_events -->
                <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
                <div class="segment-actions" role="group" onclick={(e) => e.stopPropagation()}>
                  <button class="action-btn" onclick={(e) => downloadSegment(seg, e)} title={t('recordings.herunterladen')}>
                    <i class="fa-solid fa-download"></i>
                  </button>
                  <button class="action-btn delete-btn" onclick={(e) => deleteSegment(seg, e)} title={t('recordings.segmentLoeschen')}>
                    <i class="fa-solid fa-trash-can"></i>
                  </button>
                  <button class="action-btn ignore-btn" class:ignored={isTitleIgnored(seg.title)} onclick={(e) => toggleIgnore(seg.title, e)} title={isTitleIgnored(seg.title) ? t('recordings.titelNichtMehrIgnorieren') : t('recordings.titelIgnorieren')}>
                    <i class="fa-solid" class:fa-eye-slash={isTitleIgnored(seg.title)} class:fa-eye={!isTitleIgnored(seg.title)}></i>
                  </button>
                </div>
              </div>
            {/each}
          </div>
        {:else if metadata.length > 0}
          <div class="meta-list">
            <div class="meta-header-row">
              <span class="meta-header">{t('recordings.tracklist')} ({metadata.length} {t('recordings.titel')})</span>
              <button
                class="split-btn"
                onclick={() => splitSession(session)}
                disabled={splitting}
                title="Tracks in einzelne Dateien schneiden"
              >
                <i class="fa-solid {splitting ? 'fa-spinner fa-spin' : 'fa-scissors'}"></i>
                {splitting ? t('recordings.schneide') : t('recordings.segmenteErzeugen')}
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
          <div class="meta-empty">{t('recordings.keineIcyMetadaten')}</div>
        {/if}
      </div>
    {:else}
      <!-- Welcome -->
      <div class="welcome-state">
        <i class="fa-solid fa-microphone welcome-icon"></i>
        <HiFiDisplay size="medium">{t('recordings.aufnahmen')}</HiFiDisplay>
        <p class="welcome-hint">{t('recordings.aufnahmeAuswaehlen')}</p>
      </div>
    {/if}
  </div>
</div>

<style>
  .recordings-tab {
    display: flex;
    height: 100%;
    gap: 1px;
    background: var(--hifi-border-dark);
    overflow: hidden;
  }

  .recording-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    overflow: hidden;
    background: var(--hifi-bg-secondary);
  }

  /* Welcome */
  .welcome-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 12px;
    color: var(--hifi-text-secondary);
  }

  .welcome-icon {
    font-size: 40px;
    opacity: 0.15;
  }

  .welcome-hint {
    font-family: 'Barlow', sans-serif;
    font-size: 12px;
    color: var(--hifi-text-secondary);
    opacity: 0.5;
  }

  /* Detail Header */
  .detail-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 16px;
    background: var(--hifi-bg-panel);
    border-bottom: 1px solid var(--hifi-border-dark);
    flex-shrink: 0;
  }

  .detail-info {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
    min-width: 0;
  }

  .detail-name {
    font-family: 'Barlow', sans-serif;
    font-size: 14px;
    font-weight: 600;
    color: var(--hifi-text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .stalled-tag {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 9px;
    font-weight: 700;
    padding: 1px 6px;
    border-radius: 3px;
    background: rgba(255, 170, 0, 0.15);
    color: var(--hifi-led-amber, #ffaa00);
    letter-spacing: 0.5px;
    flex-shrink: 0;
  }

  .detail-date {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    flex-shrink: 0;
  }

  .detail-meta {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
  }

  .meta-val {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    white-space: nowrap;
  }

  .detail-actions {
    display: flex;
    gap: 4px;
    flex-shrink: 0;
  }

  /* Detail Body */
  .detail-body {
    flex: 1;
    overflow-y: auto;
    padding: 12px 16px;
  }

  /* Actions */
  .action-btn {
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--hifi-bg-tertiary);
    border: none;
    border-radius: var(--hifi-border-radius-sm, 4px);
    cursor: pointer;
    color: var(--hifi-text-secondary);
    font-size: 11px;
    transition: background 0.15s, color 0.15s;
    box-shadow: var(--hifi-shadow-button);
  }

  .action-btn:hover {
    background: var(--hifi-bg-panel);
    color: var(--hifi-text-primary);
  }

  .action-btn:active {
    box-shadow: var(--hifi-shadow-inset);
  }

  .action-btn.play-btn:hover {
    color: var(--hifi-display-text);
  }

  .action-btn.play-btn.playing {
    background: rgba(40, 180, 40, 0.15);
    color: var(--hifi-text-green, #4caf50);
  }

  .action-btn.delete-btn {
    color: var(--hifi-led-red);
    opacity: 0.6;
  }

  .action-btn.delete-btn:hover {
    color: var(--hifi-led-red);
    opacity: 1;
  }

  .action-btn.ignore-btn {
    color: var(--hifi-text-secondary);
    opacity: 0.4;
  }

  .action-btn.ignore-btn:hover {
    color: var(--hifi-text-primary);
    opacity: 0.8;
  }

  .action-btn.ignore-btn.ignored {
    color: var(--hifi-led-red);
    opacity: 0.9;
  }

  .action-btn.ignore-btn.ignored:hover {
    color: var(--hifi-led-red);
    opacity: 1;
  }

  .action-btn.ignore-btn.mini {
    font-size: 0.7em;
    padding: 0 4px;
    margin-left: auto;
  }

  .action-btn.rec-btn {
    background: rgba(180, 40, 40, 0.15);
    color: var(--hifi-led-red);
  }

  /* Metadata */
  .meta-loading, .meta-empty {
    font-family: 'Barlow', sans-serif;
    font-size: 12px;
    color: var(--hifi-text-secondary);
    padding: 20px 0;
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
    font-family: 'Barlow', sans-serif;
    font-size: 9px;
    font-weight: 600;
    color: var(--hifi-text-secondary);
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 4px;
  }

  .split-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 3px 8px;
    background: var(--hifi-bg-tertiary);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm, 4px);
    color: var(--hifi-display-text);
    font-family: 'Barlow', sans-serif;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.5px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    box-shadow: var(--hifi-shadow-button);
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
    background: var(--hifi-bg-tertiary);
  }

  .meta-entry.sperrtext {
    opacity: 0.5;
  }

  .gap-banner {
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
    background: var(--hifi-bg-tertiary);
    color: var(--hifi-yellow, #f39c12);
    margin-bottom: 6px;
  }

  .gap-banner.active {
    background: var(--hifi-red, #c0392b);
    color: #fff;
    animation: gap-pulse 1s ease-in-out infinite alternate;
  }

  @keyframes gap-pulse {
    from { opacity: 0.7; }
    to { opacity: 1; }
  }

  .sperrtext-badge {
    font-size: 9px;
    font-weight: 700;
    padding: 1px 4px;
    border-radius: 3px;
    background: var(--hifi-red, #c0392b);
    color: #fff;
    margin-left: 4px;
    vertical-align: middle;
  }

  .meta-time {
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    font-weight: 700;
    color: var(--hifi-display-text);
    flex-shrink: 0;
    min-width: 40px;
  }

  .meta-title {
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    color: var(--hifi-text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* Segment Entries */
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
    background: var(--hifi-bg-tertiary);
  }

  .segment-entry.playing {
    background: rgba(40, 180, 40, 0.08);
  }

  .segment-entry .meta-time {
    font-family: 'Barlow', sans-serif;
    padding-left: 8px;
    min-width: unset;
  }

  .segment-entry .meta-title {
    padding: 0 8px;
    font-size: 12px;
    font-weight: 600;
  }

  .segment-duration {
    font-family: 'Barlow', sans-serif;
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    text-align: right;
    padding-right: 8px;
  }

  .segment-size {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
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

  /* Move Dropdown */
  .move-dropdown {
    position: relative;
  }

  .move-menu {
    display: none;
    position: absolute;
    top: 100%;
    right: 0;
    min-width: 160px;
    background: var(--hifi-bg-panel);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm, 4px);
    box-shadow: 4px 4px 12px rgba(0, 0, 0, 0.3);
    z-index: var(--hifi-z-dropdown, 1000);
    padding: 4px 0;
  }

  .move-dropdown:hover .move-menu {
    display: block;
  }

  .move-item {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 6px 12px;
    background: none;
    border: none;
    color: var(--hifi-text-primary);
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    cursor: pointer;
    text-align: left;
  }

  .move-item:hover {
    background: var(--hifi-row-hover);
  }

  .move-item i {
    font-size: 10px;
    color: var(--hifi-text-secondary);
    width: 14px;
    text-align: center;
  }
</style>
