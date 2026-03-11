<script>
  /**
   * CutterView - Grafischer Waveform-Editor fuer Aufnahmen.
   * Canvas-basiert, Lazy-Loading, Marker-System, ICY-Titel-Farben.
   */
  import { onMount } from 'svelte';
  import { appState, actions } from '../../lib/store.svelte.js';
  import { api } from '../../lib/api.js';
  import { PeaksLoader } from '../../lib/peaksLoader.js';
  import { WaveformRenderer } from '../../lib/waveformRenderer.js';
  import { formatDuration } from '../../lib/formatters.js';
  import { t } from '../../lib/i18n.svelte.js';

  let {
    session,
    metadata = [],
    onclose = () => {},
    onsplit = () => {}
  } = $props();

  // === State ===
  let canvasEl = $state(null);
  let minimapEl = $state(null);
  let containerEl = $state(null);
  let renderer = null;
  let minimapRenderer = null;
  let loader = null;

  let totalDuration = $state(0);
  let viewStart = $state(0);
  let viewDuration = $state(300); // 5 min sichtbar
  let markers = $state([]);
  let playPosition = $state(-1);
  let isLoadingPeaks = $state(true);
  let isCutting = $state(false);
  let isDraggingMarker = $state(false);
  let dragMarkerIndex = $state(-1);

  // Zoom-Stufen (Sekunden sichtbar)
  const ZOOM_LEVELS = [15, 30, 60, 120, 300, 600, 1800, 3600];
  let zoomIndex = $state(4); // Start: 300s = 5 min

  // Titel-Regionen aus Metadata
  let titleRegions = $derived.by(() => {
    if (!metadata || metadata.length === 0) return [];
    const regions = [];
    for (let i = 0; i < metadata.length; i++) {
      const entry = metadata[i];
      const startSec = (entry.t || 0) / 1000;
      const endSec = i + 1 < metadata.length
        ? (metadata[i + 1].t || 0) / 1000
        : totalDuration;
      if (entry.title && endSec > startSec) {
        regions.push({ start: startSec, end: endSec, title: entry.title });
      }
    }
    return regions;
  });

  // Bestehende Segmente
  let existingSegments = $state([]);

  // === Lifecycle ===
  onMount(() => {
    initCutter();
    return () => {
      if (loader) loader.destroy();
      if (renderer) renderer.destroy();
      if (minimapRenderer) minimapRenderer.destroy();
      if (playPosInterval) clearInterval(playPosInterval);
    };
  });

  let playPosInterval = null;

  async function initCutter() {
    if (!session) return;

    // Bestehende Segmente laden
    try {
      const result = await api.getSegments(session.id);
      existingSegments = result.segments || [];
    } catch (e) {}

    // Peaks-Loader initialisieren
    loader = new PeaksLoader(session.id);

    try {
      const info = await loader.init();
      totalDuration = info.total_duration || session.duration || 0;

      // Initiale Ansicht
      viewDuration = Math.min(ZOOM_LEVELS[zoomIndex], totalDuration);

      // Erste Peaks laden
      await loader.ensureRange(0, viewDuration);
      isLoadingPeaks = false;

      // Renderer aufbauen
      setupRenderer();
      setupMinimap();
      drawFrame();
    } catch (e) {
      console.error('Cutter init Fehler:', e);
      isLoadingPeaks = false;
      actions.showToast(t('toast.ladenFehler'), 'error');
    }

    // Playback-Position tracken
    playPosInterval = setInterval(() => {
      if (appState.currentRecording?.session_id === session.id) {
        const audio = document.querySelector('audio');
        if (audio && !audio.paused) {
          playPosition = audio.currentTime;
          drawFrame();
        }
      }
    }, 100);
  }

  function setupRenderer() {
    if (!canvasEl) return;
    renderer = new WaveformRenderer(canvasEl, {
      waveColor: getComputedStyle(canvasEl).getPropertyValue('--hifi-accent').trim() || '#ff9800',
      bgColor: getComputedStyle(canvasEl).getPropertyValue('--hifi-display-bg').trim() || '#1a1a1a'
    });
    renderer.resize();
    renderer.totalDuration = totalDuration;
  }

  function setupMinimap() {
    if (!minimapEl) return;
    minimapRenderer = new WaveformRenderer(minimapEl, {
      waveColor: 'rgba(255, 152, 0, 0.5)',
      bgColor: '#111',
      timelineHeight: 0
    });
    minimapRenderer.resize();
    minimapRenderer.totalDuration = totalDuration;
  }

  function drawFrame() {
    if (!renderer || !loader) return;

    const peaks = loader.getPeaks(viewStart, viewStart + viewDuration);
    renderer.setPeaks(peaks, viewStart, loader.sampleRate);
    renderer.setView(viewStart, viewDuration);
    renderer.setMarkers(markers);
    renderer.setPlayPosition(playPosition);
    renderer.setTitleRegions(titleRegions);
    renderer.render();

    // Minimap
    if (minimapRenderer) {
      const allPeaks = loader.getPeaks(0, totalDuration);
      minimapRenderer.setPeaks(allPeaks, 0, loader.sampleRate);
      minimapRenderer.setView(0, totalDuration);
      minimapRenderer.setTitleRegions(titleRegions);
      minimapRenderer.setMarkers(markers);
      minimapRenderer.setPlayPosition(playPosition);
      minimapRenderer.render();

      // Viewport-Indikator auf Minimap zeichnen
      const mmCtx = minimapEl.getContext('2d');
      const x1 = (viewStart / totalDuration) * minimapEl.width / (window.devicePixelRatio || 1);
      const x2 = ((viewStart + viewDuration) / totalDuration) * minimapEl.width / (window.devicePixelRatio || 1);
      mmCtx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
      mmCtx.lineWidth = 1;
      mmCtx.strokeRect(x1, 0, x2 - x1, minimapEl.height / (window.devicePixelRatio || 1));
    }

    // Prefetch
    loader.prefetch(viewStart, viewStart + viewDuration);
  }

  // === Zoom ===
  function zoomIn() {
    if (zoomIndex > 0) {
      const centerTime = viewStart + viewDuration / 2;
      zoomIndex--;
      viewDuration = Math.min(ZOOM_LEVELS[zoomIndex], totalDuration);
      viewStart = Math.max(0, Math.min(centerTime - viewDuration / 2, totalDuration - viewDuration));
      loadAndDraw();
    }
  }

  function zoomOut() {
    if (zoomIndex < ZOOM_LEVELS.length - 1) {
      const centerTime = viewStart + viewDuration / 2;
      zoomIndex++;
      viewDuration = Math.min(ZOOM_LEVELS[zoomIndex], totalDuration);
      viewStart = Math.max(0, Math.min(centerTime - viewDuration / 2, totalDuration - viewDuration));
      loadAndDraw();
    }
  }

  function fitAll() {
    viewStart = 0;
    viewDuration = totalDuration;
    // Passenden Zoom-Index finden
    zoomIndex = ZOOM_LEVELS.findIndex(z => z >= totalDuration);
    if (zoomIndex === -1) zoomIndex = ZOOM_LEVELS.length - 1;
    loadAndDraw();
  }

  async function loadAndDraw() {
    const loading = !loader.isLoaded(viewStart, viewStart + viewDuration);
    if (loading) isLoadingPeaks = true;
    await loader.ensureRange(viewStart, viewStart + viewDuration);
    isLoadingPeaks = false;
    drawFrame();
  }

  // === Canvas Events ===
  function handleCanvasMouseDown(e) {
    if (!renderer) return;
    const rect = canvasEl.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const hit = renderer.hitTest(x, y);

    if (hit.type === 'marker') {
      isDraggingMarker = true;
      dragMarkerIndex = hit.index;
      e.preventDefault();
      return;
    }

    if (hit.type === 'waveform' || hit.type === 'timeline') {
      // Seek zur Position
      seekToTime(hit.time);
    }
  }

  function handleCanvasMouseMove(e) {
    if (!isDraggingMarker || !renderer) return;
    const rect = canvasEl.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const newTime = renderer.xToTime(x);

    // Snap auf 100ms
    const snapped = Math.round(newTime * 10) / 10;
    const clamped = Math.max(0, Math.min(snapped, totalDuration));

    markers = markers.map((m, i) =>
      i === dragMarkerIndex ? { ...m, time: clamped } : m
    );
    drawFrame();
  }

  function handleCanvasMouseUp() {
    if (isDraggingMarker) {
      isDraggingMarker = false;
      dragMarkerIndex = -1;
      // Marker sortieren
      markers = [...markers].sort((a, b) => a.time - b.time);
      drawFrame();
    }
  }

  function handleCanvasDblClick(e) {
    if (!renderer) return;
    const rect = canvasEl.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const time = renderer.xToTime(x);
    addMarkerAt(time);
  }

  function handleWheel(e) {
    e.preventDefault();
    if (e.ctrlKey || e.metaKey) {
      // Zoom
      if (e.deltaY < 0) zoomIn();
      else zoomOut();
    } else {
      // Scroll
      const scrollAmount = viewDuration * 0.15 * Math.sign(e.deltaY);
      viewStart = Math.max(0, Math.min(viewStart + scrollAmount, totalDuration - viewDuration));
      loadAndDraw();
    }
  }

  // Minimap-Klick: Navigation
  function handleMinimapClick(e) {
    if (!minimapEl) return;
    const rect = minimapEl.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const clickTime = (x / rect.width) * totalDuration;
    viewStart = Math.max(0, Math.min(clickTime - viewDuration / 2, totalDuration - viewDuration));
    loadAndDraw();
  }

  // === Marker ===
  function addMarker() {
    const centerTime = viewStart + viewDuration / 2;
    addMarkerAt(centerTime);
  }

  function addMarkerAt(time) {
    const snapped = Math.round(time * 10) / 10;
    const clamped = Math.max(0, Math.min(snapped, totalDuration));
    markers = [...markers, { time: clamped, label: `M${markers.length + 1}` }]
      .sort((a, b) => a.time - b.time);
    drawFrame();
  }

  function removeMarker(index) {
    markers = markers.filter((_, i) => i !== index);
    drawFrame();
  }

  function clearMarkers() {
    markers = [];
    drawFrame();
  }

  // === Playback ===
  function seekToTime(timeSec) {
    const clamped = Math.max(0, Math.min(timeSec, totalDuration));

    // Falls Session nicht spielt, starten
    if (appState.currentRecording?.session_id !== session.id) {
      // Session abspielen
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
        playUrl
      });

      setTimeout(() => {
        const audio = document.querySelector('audio');
        if (audio) audio.currentTime = clamped;
      }, 500);
    } else {
      const audio = document.querySelector('audio');
      if (audio) audio.currentTime = clamped;
    }

    playPosition = clamped;
    drawFrame();
  }

  // === Schnitt ===
  async function executeCut() {
    if (markers.length === 0) {
      actions.showToast(t('cutter.keineMarker'), 'info');
      return;
    }

    isCutting = true;
    try {
      const cutPoints = markers.map(m => m.time);
      const result = await api.customSplit(session.id, cutPoints);
      if (result.success) {
        actions.showToast(
          t('cutter.schnittErfolgreich', { count: result.segments }),
          'success'
        );
        markers = [];
        onsplit();
      }
    } catch (e) {
      actions.showToast(t('cutter.schnittFehler'), 'error');
    }
    isCutting = false;
  }

  // Auto-Split (bestehende Funktion via ICY-Metadata)
  async function autoSplit() {
    if (!session.meta_file_path) {
      actions.showToast(t('cutter.keineMetadaten'), 'info');
      return;
    }
    isCutting = true;
    try {
      const result = await api.splitSession(session.id);
      if (result.success) {
        actions.showToast(
          t('recordings.segmenteErzeugtToast', { count: result.segments }),
          'success'
        );
        onsplit();
      }
    } catch (e) {
      actions.showToast(t('recordings.splitFehler'), 'error');
    }
    isCutting = false;
  }

  // Marker aus ICY-Metadata uebernehmen
  function markersFromMetadata() {
    if (!metadata || metadata.length === 0) {
      actions.showToast(t('cutter.keineMetadaten'), 'info');
      return;
    }
    const newMarkers = metadata.map((entry, i) => ({
      time: (entry.t || 0) / 1000,
      label: entry.title || `M${i + 1}`
    })).filter(m => m.time > 0 && m.time < totalDuration);
    markers = newMarkers.sort((a, b) => a.time - b.time);
    drawFrame();
  }

  // ResizeObserver
  $effect(() => {
    if (!containerEl) return;
    const ro = new ResizeObserver(() => {
      if (renderer) { renderer.resize(); drawFrame(); }
      if (minimapRenderer) { minimapRenderer.resize(); drawFrame(); }
    });
    ro.observe(containerEl);
    return () => ro.disconnect();
  });
</script>

<div class="cutter-view" bind:this={containerEl}>
  <!-- Toolbar -->
  <div class="cutter-toolbar">
    <div class="toolbar-group">
      <button class="cutter-btn" onclick={zoomIn} title={t('cutter.zoomRein')} disabled={zoomIndex <= 0}>
        <i class="fa-solid fa-magnifying-glass-plus"></i>
      </button>
      <button class="cutter-btn" onclick={zoomOut} title={t('cutter.zoomRaus')} disabled={zoomIndex >= ZOOM_LEVELS.length - 1}>
        <i class="fa-solid fa-magnifying-glass-minus"></i>
      </button>
      <button class="cutter-btn" onclick={fitAll} title={t('cutter.allesAnzeigen')}>
        <i class="fa-solid fa-arrows-left-right-to-line"></i>
      </button>
      <span class="zoom-label">{formatDuration(viewDuration)}</span>
    </div>

    <div class="toolbar-group">
      <button class="cutter-btn" onclick={addMarker} title={t('cutter.markerSetzen')}>
        <i class="fa-solid fa-map-pin"></i> {t('cutter.marker')}
      </button>
      {#if metadata.length > 0}
        <button class="cutter-btn" onclick={markersFromMetadata} title={t('cutter.markerAusMetadata')}>
          <i class="fa-solid fa-tags"></i> ICY
        </button>
      {/if}
      {#if markers.length > 0}
        <button class="cutter-btn" onclick={clearMarkers} title={t('cutter.alleMarkerEntfernen')}>
          <i class="fa-solid fa-xmark"></i> ({markers.length})
        </button>
      {/if}
    </div>

    <div class="toolbar-group">
      {#if markers.length > 0}
        <button class="cutter-btn cutter-btn-primary" onclick={executeCut} disabled={isCutting}>
          {#if isCutting}
            <div class="mini-spinner"></div>
          {:else}
            <i class="fa-solid fa-scissors"></i>
          {/if}
          {t('cutter.schneiden')} ({markers.length + 1} {t('cutter.teile')})
        </button>
      {/if}
      {#if metadata.length > 0 && existingSegments.length === 0}
        <button class="cutter-btn" onclick={autoSplit} disabled={isCutting} title={t('cutter.autoSplit')}>
          <i class="fa-solid fa-wand-magic-sparkles"></i> Auto
        </button>
      {/if}
      <button class="cutter-btn" onclick={onclose}>
        <i class="fa-solid fa-xmark"></i> {t('common.schliessen')}
      </button>
    </div>
  </div>

  <!-- Info-Leiste -->
  <div class="cutter-info">
    <span class="info-station">{session.station_name || session.id}</span>
    <span class="info-sep">--</span>
    <span class="info-date">{session.start_time ? new Date(session.start_time).toLocaleString('de-DE') : ''}</span>
    <span class="info-sep">--</span>
    <span class="info-duration">{formatDuration(totalDuration)}</span>
    <span class="info-sep">--</span>
    <span class="info-codec">{(session.codec || 'mp3').toUpperCase()} {session.bitrate ? session.bitrate + ' kbps' : ''}</span>
    {#if isLoadingPeaks}
      <span class="info-loading"><div class="mini-spinner"></div></span>
    {/if}
  </div>

  <!-- Waveform Canvas -->
  <div class="cutter-canvas-wrap">
    {#if isLoadingPeaks && !renderer}
      <div class="canvas-loading">
        <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
        <span>{t('cutter.ladePeaks')}</span>
      </div>
    {/if}
    <canvas
      bind:this={canvasEl}
      class="cutter-canvas"
      onmousedown={handleCanvasMouseDown}
      onmousemove={handleCanvasMouseMove}
      onmouseup={handleCanvasMouseUp}
      onmouseleave={handleCanvasMouseUp}
      ondblclick={handleCanvasDblClick}
      onwheel={handleWheel}
    ></canvas>
  </div>

  <!-- Minimap -->
  <div class="cutter-minimap-wrap" onclick={handleMinimapClick}>
    <canvas bind:this={minimapEl} class="cutter-minimap"></canvas>
  </div>

  <!-- Marker-Liste -->
  {#if markers.length > 0}
    <div class="marker-list">
      <span class="marker-list-label">{t('cutter.schnittpunkte')}:</span>
      {#each markers as marker, i}
        <span class="marker-chip">
          <span class="marker-time">{formatDuration(marker.time)}</span>
          <button class="marker-remove" onclick={() => removeMarker(i)} title={t('common.loeschen')}>
            <i class="fa-solid fa-xmark"></i>
          </button>
        </span>
      {/each}
    </div>
  {/if}

  <!-- Bestehende Segmente -->
  {#if existingSegments.length > 0}
    <div class="existing-segments">
      <span class="segments-label">{t('cutter.bestehendeSegmente')} ({existingSegments.length})</span>
      <div class="segment-chips">
        {#each existingSegments as seg}
          <span class="segment-chip">
            <span class="seg-index">{seg.segment_index + 1}</span>
            <span class="seg-title">{seg.title || `Teil ${seg.segment_index + 1}`}</span>
            <span class="seg-duration">{formatDuration((seg.duration_ms || 0) / 1000)}</span>
          </span>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .cutter-view {
    display: flex;
    flex-direction: column;
    gap: 0;
    height: 100%;
    background: var(--hifi-bg-panel);
    border-radius: var(--hifi-border-radius);
    overflow: hidden;
  }

  /* Toolbar */
  .cutter-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    background: var(--hifi-bg-tertiary);
    border-bottom: 1px solid var(--hifi-border-dark);
    flex-wrap: wrap;
    gap: 8px;
  }

  .toolbar-group {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .cutter-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 5px 10px;
    background: var(--hifi-bg-panel);
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    box-shadow: var(--hifi-shadow-button);
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-display);
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    cursor: pointer;
  }

  .cutter-btn:hover { color: var(--hifi-text-primary); }
  .cutter-btn:disabled { opacity: 0.4; cursor: default; }

  .cutter-btn-primary {
    background: var(--hifi-accent);
    color: #fff;
  }
  .cutter-btn-primary:hover { color: #fff; }

  .zoom-label {
    font-family: var(--hifi-font-values);
    font-size: 10px;
    color: var(--hifi-text-secondary);
    padding: 0 6px;
  }

  /* Info-Leiste */
  .cutter-info {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    font-family: var(--hifi-font-body);
    font-size: 11px;
    color: var(--hifi-text-secondary);
    background: var(--hifi-bg-panel);
    border-bottom: 1px solid var(--hifi-border-dark);
    flex-wrap: wrap;
  }

  .info-station {
    font-family: var(--hifi-font-display);
    font-weight: 600;
    color: var(--hifi-accent);
  }

  .info-sep { color: var(--hifi-text-muted); }

  .info-loading {
    display: flex;
    align-items: center;
    margin-left: auto;
  }

  /* Canvas */
  .cutter-canvas-wrap {
    position: relative;
    flex: 1;
    min-height: 150px;
    background: var(--hifi-display-bg, #1a1a1a);
  }

  .cutter-canvas {
    width: 100%;
    height: 100%;
    display: block;
    cursor: crosshair;
  }

  .canvas-loading {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-body);
    font-size: 12px;
    z-index: 2;
  }

  /* Minimap */
  .cutter-minimap-wrap {
    height: 36px;
    background: #111;
    border-top: 1px solid var(--hifi-border-dark);
    cursor: pointer;
  }

  .cutter-minimap {
    width: 100%;
    height: 100%;
    display: block;
  }

  /* Marker-Liste */
  .marker-list {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: var(--hifi-bg-tertiary);
    border-top: 1px solid var(--hifi-border-dark);
    flex-wrap: wrap;
  }

  .marker-list-label {
    font-family: var(--hifi-font-display);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1px;
    color: var(--hifi-text-secondary);
    text-transform: uppercase;
  }

  .marker-chip {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 2px 6px;
    background: var(--hifi-bg-panel);
    border-radius: var(--hifi-border-radius-sm);
    box-shadow: var(--hifi-shadow-button);
  }

  .marker-time {
    font-family: var(--hifi-font-values);
    font-size: 10px;
    color: var(--hifi-accent);
  }

  .marker-remove {
    background: none;
    border: none;
    color: var(--hifi-text-muted);
    cursor: pointer;
    padding: 0 2px;
    font-size: 9px;
  }
  .marker-remove:hover { color: var(--hifi-led-red); }

  /* Bestehende Segmente */
  .existing-segments {
    padding: 8px 12px;
    background: var(--hifi-bg-tertiary);
    border-top: 1px solid var(--hifi-border-dark);
  }

  .segments-label {
    font-family: var(--hifi-font-display);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1px;
    color: var(--hifi-text-secondary);
    text-transform: uppercase;
  }

  .segment-chips {
    display: flex;
    gap: 6px;
    margin-top: 6px;
    flex-wrap: wrap;
  }

  .segment-chip {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    background: var(--hifi-bg-panel);
    border-radius: var(--hifi-border-radius-sm);
    box-shadow: var(--hifi-shadow-button);
    font-size: 10px;
  }

  .seg-index {
    font-family: var(--hifi-font-values);
    font-weight: 700;
    color: var(--hifi-accent);
    min-width: 14px;
    text-align: center;
  }

  .seg-title {
    font-family: var(--hifi-font-body);
    color: var(--hifi-text-primary);
    max-width: 150px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .seg-duration {
    font-family: var(--hifi-font-values);
    color: var(--hifi-text-secondary);
    font-size: 9px;
  }

  /* Spinner */
  .mini-spinner {
    width: 12px;
    height: 12px;
    border: 2px solid var(--hifi-text-muted);
    border-top-color: var(--hifi-accent);
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
