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
    segments = [],
    selectedSegmentIds = [],
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
  let dragStartX = 0;
  let dragMoved = false;
  let lastSeekTime = 0;
  const PLAYHEAD_RATIO = 0.7; // Playhead steht fest bei 70% von links (letztes Drittel)
  let trimStart = $state(false);
  let trimEnd = $state(false);
  let autoPlayEnabled = $state(true); // Auto-Play bei Klick

  // Minimap-Drag
  let isDraggingMinimapMarker = $state(false);
  let minimapDragIndex = $state(-1);
  let minimapDragMoved = false;

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

  // Bestehende Segmente kommen als `segments` Prop

  // === Lifecycle ===
  let themeObserver = null;

  onMount(() => {
    initCutter();

    // Theme-Wechsel: Renderer-Farben aktualisieren
    themeObserver = new MutationObserver(() => {
      updateRendererColors();
      drawFrame();
    });
    themeObserver.observe(document.documentElement, {
      attributes: true, attributeFilter: ['data-theme']
    });

    return () => {
      if (loader) loader.destroy();
      if (renderer) renderer.destroy();
      if (minimapRenderer) minimapRenderer.destroy();
      if (playRafId) cancelAnimationFrame(playRafId);
      if (themeObserver) themeObserver.disconnect();
    };
  });

  let playRafId = null;

  async function initCutter() {
    if (!session) return;

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

    // Playback-Position tracken per rAF, gedeckelt auf 25fps (40ms)
    // Playhead steht fest bei 30% -- Waveform scrollt darunter durch
    let wasPlaying = false;
    let lastDrawMs = 0;
    const FRAME_INTERVAL = 40; // 25fps

    function playLoop() {
      playRafId = requestAnimationFrame(playLoop);

      // Nach Seek kurz warten, damit audio.currentTime den neuen Wert hat
      if (Date.now() - lastSeekTime < 300) return;
      if (appState.currentRecording?.session_id !== session.id) return;

      const audio = document.querySelector('audio');
      if (!audio || audio.paused) {
        if (wasPlaying) { wasPlaying = false; drawFrame(); }
        return;
      }

      // 25fps Throttle
      const now = performance.now();
      if (now - lastDrawMs < FRAME_INTERVAL) return;
      lastDrawMs = now;

      wasPlaying = true;

      // Sprung unterdrücken: audio.currentTime ignorieren wenn weit weg von playPosition
      // (Browser hat noch nicht zur gewünschten Position geseekt)
      const audioTime = audio.currentTime;
      if (playPosition >= 0 && Math.abs(audioTime - playPosition) > 5) return;
      playPosition = audioTime;

      // Waveform scrollt weich mit: Playhead bleibt bei PLAYHEAD_RATIO (70%)
      const targetStart = Math.max(0,
        Math.min(playPosition - viewDuration * PLAYHEAD_RATIO, totalDuration - viewDuration)
      );
      // Lerp: sanftes Gleiten statt harter Sprung (15% pro Frame bei 25fps)
      const diff = targetStart - viewStart;
      if (Math.abs(diff) < 0.1) {
        viewStart = targetStart;
      } else {
        viewStart += diff * 0.15;
      }
      loader.ensureRange(viewStart, viewStart + viewDuration);

      drawFrame();
    }
    playRafId = requestAnimationFrame(playLoop);
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

  function updateRendererColors() {
    if (renderer && canvasEl) {
      renderer.waveColor = getComputedStyle(canvasEl).getPropertyValue('--hifi-accent').trim() || '#4a90d9';
      renderer.bgColor = getComputedStyle(canvasEl).getPropertyValue('--hifi-display-bg').trim() || '#1a1a1a';
    }
    if (minimapRenderer && minimapEl) {
      const accent = getComputedStyle(minimapEl).getPropertyValue('--hifi-accent').trim() || '#4a90d9';
      minimapRenderer.waveColor = accent + '80';
      minimapRenderer.bgColor = getComputedStyle(minimapEl).getPropertyValue('--hifi-display-bg').trim() || '#111';
    }
  }

  function setupMinimap() {
    if (!minimapEl) return;
    const minimapBg = getComputedStyle(minimapEl).getPropertyValue('--hifi-display-bg').trim() || '#111';
    const accent = getComputedStyle(minimapEl).getPropertyValue('--hifi-accent').trim() || '#ff9800';
    minimapRenderer = new WaveformRenderer(minimapEl, {
      waveColor: accent + '80',
      bgColor: minimapBg,
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
      dragStartX = x;
      dragMoved = false;
      e.preventDefault();
      return;
    }

    if (hit.type === 'waveform' || hit.type === 'timeline') {
      // Seek zur Position
      seekToTime(hit.time);
    }
  }

  function handleCanvasMouseMove(e) {
    if (!renderer) return;
    const rect = canvasEl.getBoundingClientRect();
    const x = e.clientX - rect.left;

    // Cursor anpassen: Hand bei Marker-Naehe
    if (!isDraggingMarker) {
      const y = e.clientY - rect.top;
      const hit = renderer.hitTest(x, y);
      canvasEl.style.cursor = hit.type === 'marker' ? 'grab' : 'crosshair';
      return;
    }

    // Drag: Marker nur bewegen wenn Maus sich merklich bewegt hat
    if (Math.abs(x - dragStartX) > 3) dragMoved = true;
    if (!dragMoved) return;

    canvasEl.style.cursor = 'grabbing';
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
      const idx = dragMarkerIndex;
      const moved = dragMoved;
      isDraggingMarker = false;
      dragMarkerIndex = -1;

      if (moved) {
        // Marker wurde verschoben -> sortieren
        markers = [...markers].sort((a, b) => a.time - b.time);
      } else if (idx >= 0 && idx < markers.length) {
        // Klick ohne Drag -> Play an Markerposition
        seekToTime(markers[idx].time);
      }

      canvasEl.style.cursor = 'crosshair';
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

  // Minimap: Navigation + Marker-Drag + Seek
  function handleMinimapMouseDown(e) {
    if (!minimapRenderer) return;
    const rect = minimapEl.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const hit = minimapRenderer.hitTest(x, y);

    if (hit.type === 'marker') {
      isDraggingMinimapMarker = true;
      minimapDragIndex = hit.index;
      minimapDragMoved = false;
      e.preventDefault();
      return;
    }

    // Klick: View zentrieren + Seek
    const clickTime = minimapRenderer.xToTime(x);
    viewStart = Math.max(0, Math.min(clickTime - viewDuration / 2, totalDuration - viewDuration));
    seekToTime(clickTime);
    loadAndDraw();
  }

  function handleMinimapMouseMove(e) {
    if (!minimapRenderer) return;
    const rect = minimapEl.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (isDraggingMinimapMarker) {
      minimapDragMoved = true;
      const newTime = minimapRenderer.xToTime(x);
      const snapped = Math.round(newTime * 10) / 10;
      const clamped = Math.max(0, Math.min(snapped, totalDuration));
      markers = markers.map((m, i) =>
        i === minimapDragIndex ? { ...m, time: clamped } : m
      );
      minimapEl.style.cursor = 'grabbing';
      drawFrame();
      return;
    }

    // Cursor: grab bei Marker-Nähe
    const hit = minimapRenderer.hitTest(x, y);
    minimapEl.style.cursor = hit.type === 'marker' ? 'grab' : 'pointer';
  }

  function handleMinimapMouseUp() {
    if (isDraggingMinimapMarker) {
      const moved = minimapDragMoved;
      const idx = minimapDragIndex;
      isDraggingMinimapMarker = false;
      minimapDragIndex = -1;
      if (moved) {
        markers = [...markers].sort((a, b) => a.time - b.time);
      } else if (idx >= 0 && idx < markers.length) {
        seekToTime(markers[idx].time);
      }
      minimapEl.style.cursor = 'pointer';
      drawFrame();
    }
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
  function seekToTime(timeSec, forcePlay = false) {
    const clamped = Math.max(0, Math.min(timeSec, totalDuration));
    const shouldPlay = forcePlay || autoPlayEnabled;
    lastSeekTime = Date.now();

    if (appState.currentRecording?.session_id !== session.id) {
      if (!shouldPlay) {
        playPosition = clamped;
        drawFrame();
        return;
      }
      const playUrl = api.getSessionAudioUrl(session.id);
      actions.playRecording({
        path: session.file_path || '',
        name: session.station_name || session.id,
        session_id: session.id,
        station_name: session.station_name,
        date: session.start_time,
        duration: session.duration,
        playUrl
      }, clamped);
    } else {
      const audio = document.querySelector('audio');
      if (audio) {
        audio.currentTime = clamped;
        if (shouldPlay && audio.paused) audio.play().catch(() => {});
      }
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
      const result = await api.customSplit(session.id, cutPoints, trimStart, trimEnd);
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

  // === Audio-Nachbearbeitung ===
  let isProcessing = $state(false);
  let processingStatus = $state('');
  let showConvertPanel = $state(false);
  let convertFormat = $state('mp3');
  let convertBitrate = $state(192);
  let convertMono = $state(false);

  // kbps-Stufen pro Format
  const FORMAT_BITRATES = {
    mp3: [64, 96, 128, 160, 192, 224, 256, 320],
    ogg: [64, 96, 128, 160, 192, 224, 256, 320],
    aac: [64, 96, 128, 160, 192, 256]
  };

  // Bitrate clampen wenn Format wechselt
  function onFormatChange() {
    const rates = FORMAT_BITRATES[convertFormat];
    if (!rates.includes(convertBitrate)) {
      // Nächsten passenden Wert finden
      convertBitrate = rates.reduce((prev, curr) =>
        Math.abs(curr - convertBitrate) < Math.abs(prev - convertBitrate) ? curr : prev
      );
    }
  }

  async function handleNormalize() {
    isProcessing = true;
    processingStatus = '';

    const allSelected = segments.length > 0 && selectedSegmentIds.length === segments.length;
    const partialSelection = segments.length > 0 && selectedSegmentIds.length > 0 && !allSelected;

    // Hinweis bei Einzelselektion
    if (partialSelection) {
      actions.showToast(t('cutter.normalisierungEinzelnHinweis'), 'info');
    }

    // segment_ids nur schicken wenn Teilauswahl
    const segIds = partialSelection ? selectedSegmentIds : null;

    try {
      processingStatus = t('cutterExtra.analyse');
      const response = await api.normalizeSessionSSE(session.id, -16.0, segIds);

      if (response.headers.get('content-type')?.includes('text/event-stream')) {
        await readSSEStream(response, (evt) => {
          if (evt.type === 'start') {
            const min = Math.floor(evt.estimated_seconds / 60);
            const sec = evt.estimated_seconds % 60;
            processingStatus = t('cutterExtra.normalisiere', { count: evt.segments, time: `${min}:${String(sec).padStart(2, '0')}` });
          } else if (evt.type === 'progress') {
            processingStatus = evt.message;
          } else if (evt.type === 'done') {
            actions.showToast(t('cutter.normalisierungErfolgreich'), 'success');
          } else if (evt.type === 'error') {
            actions.showToast(evt.message, 'error');
          }
        });
      } else {
        const data = await response.json();
        if (data.success) {
          actions.showToast(t('cutter.normalisierungErfolgreich'), 'success');
        } else {
          actions.showToast(t('cutter.normalisierungFehler'), 'error');
        }
      }
    } catch (e) {
      actions.showToast(t('cutter.normalisierungFehler'), 'error');
    }
    isProcessing = false;
    processingStatus = '';
  }

  // SSE-Stream lesen und Events per Callback verarbeiten
  async function readSSEStream(response, onEvent) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try { onEvent(JSON.parse(line.slice(6))); } catch {}
      }
    }
  }

  async function handleConvert() {
    isProcessing = true;
    showConvertPanel = false;
    processingStatus = '';

    const allSelected = segments.length > 0 && selectedSegmentIds.length === segments.length;
    const segIds = (segments.length > 0 && !allSelected && selectedSegmentIds.length > 0)
      ? selectedSegmentIds : null;

    try {
      const resp = await api.convertSessionSSE(
        session.id, convertFormat, convertBitrate, convertMono, segIds
      );
      const ct = resp.headers.get('content-type') || '';
      if (ct.includes('text/event-stream')) {
        await readSSEStream(resp, (evt) => {
          if (evt.type === 'progress') {
            processingStatus = evt.message;
          } else if (evt.type === 'done') {
            actions.showToast(t('cutter.konvertierungErfolgreich'), 'success');
          } else if (evt.type === 'error') {
            actions.showToast(evt.message, 'error');
          }
        });
      } else {
        const data = await resp.json();
        if (data.success) {
          actions.showToast(t('cutter.konvertierungErfolgreich'), 'success');
        }
      }
    } catch (e) {
      actions.showToast(t('cutter.konvertierungFehler'), 'error');
    }
    isProcessing = false;
    processingStatus = '';
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
      <button
        class="cutter-btn autoplay-toggle"
        class:autoplay-active={autoPlayEnabled}
        onclick={() => autoPlayEnabled = !autoPlayEnabled}
        title={t('cutterExtra.autoPlay')}
      >
        <i class="fa-solid fa-circle-play"></i>
      </button>
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
      <button
        class="cutter-btn"
        class:trim-active={trimStart}
        onclick={() => trimStart = !trimStart}
        title={t('cutter.trimAnfangTip')}
      >
        <i class="fa-solid fa-backward-step"></i> {t('cutter.trimAnfang')}
      </button>
      <button
        class="cutter-btn"
        class:trim-active={trimEnd}
        onclick={() => trimEnd = !trimEnd}
        title={t('cutter.trimEndeTip')}
      >
        <i class="fa-solid fa-forward-step"></i> {t('cutter.trimEnde')}
      </button>
      {#if markers.length > 0}
        <button class="cutter-btn cutter-btn-primary" onclick={executeCut} disabled={isCutting}>
          {#if isCutting}
            <div class="mini-spinner"></div>
          {:else}
            <i class="fa-solid fa-scissors"></i>
          {/if}
          {t('cutter.schneiden')} ({markers.length + 1 - (trimStart ? 1 : 0) - (trimEnd ? 1 : 0)} {t('cutter.teile')})
        </button>
      {/if}
      {#if metadata.length > 0 && segments.length === 0}
        <button class="cutter-btn" onclick={autoSplit} disabled={isCutting} title={t('cutter.autoSplit')}>
          <i class="fa-solid fa-wand-magic-sparkles"></i> {t('cutterExtra.auto')}
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
  <div class="cutter-minimap-wrap"
    onmousedown={handleMinimapMouseDown}
    onmousemove={handleMinimapMouseMove}
    onmouseup={handleMinimapMouseUp}
    onmouseleave={handleMinimapMouseUp}
  >
    <canvas bind:this={minimapEl} class="cutter-minimap"></canvas>
  </div>

  <!-- Werkzeuge + Analyse in einer Zeile -->
  <div class="tools-bar">
    {#if segments.length > 0}
      <span class="segment-selection-badge" class:partial={selectedSegmentIds.length < segments.length}>
        {selectedSegmentIds.length}/{segments.length} {t('cutterExtra.seg')}
      </span>
    {/if}
    <button class="cutter-btn" onclick={handleNormalize} disabled={isProcessing || (segments.length > 0 && selectedSegmentIds.length === 0)} title={t('cutter.normalisierenTip')}>
      <i class="fa-solid fa-volume-high"></i> {t('cutter.normalisieren')}
    </button>
    <button class="cutter-btn" onclick={() => showConvertPanel = !showConvertPanel} disabled={isProcessing || (segments.length > 0 && selectedSegmentIds.length === 0)} title={t('cutter.konvertierenTip')}>
      <i class="fa-solid fa-file-audio"></i> {t('cutter.konvertieren')}
    </button>
    {#if isProcessing}
      <span class="processing-indicator">
        <div class="mini-spinner"></div>
        <span>{processingStatus || t('cutter.verarbeitung')}</span>
      </span>
    {/if}
  </div>

  <!-- Konvertierungs-Panel -->
  {#if showConvertPanel}
    <div class="convert-panel">
      <div class="convert-row">
        <label class="convert-label">{t('cutterExtra.format')}</label>
        <select class="convert-select" bind:value={convertFormat} onchange={onFormatChange}>
          <option value="mp3">MP3</option>
          <option value="ogg">OGG Vorbis</option>
          <option value="aac">AAC</option>
        </select>
      </div>
      <div class="convert-row">
        <label class="convert-label">{t('cutterExtra.bitrate')}</label>
        <select class="convert-select" bind:value={convertBitrate}>
          {#each FORMAT_BITRATES[convertFormat] as kbps}
            <option value={kbps}>{kbps} kbps</option>
          {/each}
        </select>
      </div>
      <div class="convert-row">
        <label class="convert-checkbox">
          <input type="checkbox" bind:checked={convertMono} />
          {t('cutterExtra.mono')}
        </label>
      </div>
      <button class="cutter-btn cutter-btn-primary" onclick={handleConvert} disabled={isProcessing}>
        <i class="fa-solid fa-arrow-right-arrow-left"></i> {t('cutter.konvertieren')}
      </button>
    </div>
  {/if}

  <!-- Marker-Liste -->
  {#if markers.length > 0}
    <div class="marker-list">
      <span class="marker-list-label">{t('cutter.schnittpunkte')}:</span>
      {#each markers as marker, i}
        <span class="marker-chip">
          <span class="marker-index">{i + 1}</span>
          <span class="marker-time">{formatDuration(marker.time)}</span>
          <button class="marker-action" onclick={() => seekToTime(marker.time, true)} title={t('cutter.abspielen')}>
            <i class="fa-solid fa-play"></i>
          </button>
          <button class="marker-action marker-remove" onclick={() => removeMarker(i)} title={t('common.loeschen')}>
            <i class="fa-solid fa-xmark"></i>
          </button>
        </span>
      {/each}
    </div>
  {/if}

  <!-- Spacer: füllt freigewordenen Platz bis zur Sidebar-Divider-Höhe -->
  <div class="cutter-spacer"></div>
</div>

<style>
  .cutter-view {
    display: flex;
    flex-direction: column;
    gap: 0;
    height: 100%;
    padding-bottom: 40px;
    background: var(--hifi-bg-panel);
    border-radius: var(--hifi-border-radius);
    overflow: hidden;
  }

  .cutter-spacer {
    flex: 1 1 0;
    min-height: 0;
    background: var(--hifi-bg-panel);
  }

  /* Toolbar -- gleicher Stil wie .sidebar-actions */
  .cutter-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 10px;
    flex-wrap: wrap;
    gap: 4px;
  }

  .toolbar-group {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  /* Buttons -- gleicher Stil wie .action-btn in Sidebar */
  .cutter-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    height: 34px;
    padding: 0 12px;
    background: var(--hifi-bg-panel);
    border: none;
    border-radius: var(--hifi-border-radius-sm, 4px);
    box-shadow: var(--hifi-shadow-button);
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-display);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    cursor: pointer;
    transition: all 0.15s;
  }

  .cutter-btn i { font-size: 13px; }

  .cutter-btn:hover {
    color: var(--hifi-text-primary);
    box-shadow: 2px 2px 4px var(--hifi-shadow-dark),
                -2px -2px 4px var(--hifi-shadow-light);
  }
  .cutter-btn:active { box-shadow: var(--hifi-shadow-inset); }
  .cutter-btn:disabled { opacity: 0.4; cursor: default; }

  .cutter-btn-primary {
    background: var(--hifi-accent);
    color: var(--hifi-text-value);
    box-shadow: var(--hifi-shadow-button);
  }
  .cutter-btn-primary:hover { color: var(--hifi-text-value); }

  .cutter-btn.trim-active {
    box-shadow: var(--hifi-shadow-inset);
  }
  .cutter-btn.trim-active i {
    color: var(--hifi-led-red);
    filter: drop-shadow(0 0 4px rgba(255, 51, 51, 0.5));
  }

  .cutter-btn.autoplay-toggle {
    padding: 0 8px;
  }
  .cutter-btn.autoplay-active {
    box-shadow: var(--hifi-shadow-inset);
  }
  .cutter-btn.autoplay-active i {
    color: var(--hifi-accent);
    filter: drop-shadow(0 0 4px currentColor);
  }

  .zoom-label {
    font-family: var(--hifi-font-values);
    font-size: 10px;
    font-weight: 700;
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
    font-weight: 600;
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

  .info-sep { color: var(--hifi-text-secondary); opacity: 0.5; }

  .info-loading {
    display: flex;
    align-items: center;
    margin-left: auto;
  }

  /* Canvas */
  .cutter-canvas-wrap {
    position: relative;
    flex: 0 0 auto;
    height: 32vh;
    min-height: 80px;
    background: var(--hifi-display-bg);
    border-bottom: 2px solid var(--hifi-accent);
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
    height: 44px;
    background: var(--hifi-display-bg);
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
    background: var(--hifi-bg-panel);
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
    font-weight: 700;
    color: var(--hifi-accent);
  }

  .marker-index {
    font-family: var(--hifi-font-values);
    font-size: 9px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    min-width: 12px;
    text-align: center;
  }

  .marker-action {
    background: none;
    border: none;
    color: var(--hifi-text-secondary);
    cursor: pointer;
    padding: 0 2px;
    font-size: 9px;
  }
  .marker-action:hover { color: var(--hifi-accent); }
  .marker-remove:hover { color: var(--hifi-led-red); }

  /* Bestehende Segmente */
  /* Werkzeuge-Leiste */
  .tools-bar {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 12px;
    background: var(--hifi-bg-panel);
    flex-wrap: wrap;
  }

  .segment-selection-badge {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-accent);
    padding: 2px 6px;
    border: 1px solid var(--hifi-accent);
    border-radius: 3px;
    letter-spacing: 0.5px;
  }

  .segment-selection-badge.partial {
    color: var(--hifi-text-warning, #ff9800);
    border-color: var(--hifi-text-warning, #ff9800);
  }

  .tools-label {
    font-family: var(--hifi-font-display);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1px;
    color: var(--hifi-text-secondary);
    text-transform: uppercase;
  }

  .processing-indicator {
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: var(--hifi-font-display);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-accent);
  }

  /* Konvertierungs-Panel */
  .convert-panel {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    background: var(--hifi-bg-panel);
    flex-wrap: wrap;
  }

  .convert-row {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .convert-label {
    font-family: var(--hifi-font-display);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
  }

  .convert-select {
    height: 28px;
    padding: 0 8px;
    background: var(--hifi-bg-secondary);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm);
    color: var(--hifi-text-primary);
    font-family: var(--hifi-font-display);
    font-size: 10px;
    font-weight: 600;
    cursor: pointer;
  }

  .convert-checkbox {
    display: flex;
    align-items: center;
    gap: 4px;
    font-family: var(--hifi-font-display);
    font-size: 10px;
    font-weight: 600;
    color: var(--hifi-text-secondary);
    cursor: pointer;
  }

  .convert-checkbox input {
    accent-color: var(--hifi-accent);
  }

  /* Spinner */
  .mini-spinner {
    width: 12px;
    height: 12px;
    border: 2px solid var(--hifi-text-secondary);
    border-top-color: var(--hifi-accent);
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
