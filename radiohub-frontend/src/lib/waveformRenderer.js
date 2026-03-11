/**
 * RadioHub - Waveform Renderer
 *
 * Canvas-basierter Waveform-Renderer fuer den Cutter.
 * Zeichnet Peaks, ICY-Titel-Farbstreifen, Marker, Playback-Linie.
 * Kein Framework -- reines JS fuer maximale Performance.
 */

// Titel-Farb-Palette (HiFi-passend, Alpha 0.15 beim Zeichnen)
const TITLE_COLORS = [
  '#4fc3f7', '#81c784', '#ffb74d', '#e57373',
  '#ba68c8', '#4dd0e1', '#aed581', '#ff8a65',
  '#9575cd', '#f06292'
];

function hashTitle(title) {
  let hash = 0;
  for (let i = 0; i < title.length; i++) {
    hash = ((hash << 5) - hash + title.charCodeAt(i)) | 0;
  }
  return Math.abs(hash);
}

export class WaveformRenderer {
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.dpr = window.devicePixelRatio || 1;

    // Konfiguration
    this.waveColor = options.waveColor || '#ff9800';
    this.bgColor = options.bgColor || '#1a1a1a';
    this.playheadColor = options.playheadColor || '#f44336';
    this.markerColor = options.markerColor || '#ffeb3b';
    this.selectionColor = options.selectionColor || 'rgba(255, 152, 0, 0.15)';
    this.timelineHeight = options.timelineHeight || 22;
    this.markerHitRadius = 8; // px fuer Marker-Klick-Erkennung

    // Daten
    this.peaks = new Float32Array(0);
    this.peaksStart = 0; // Start-Zeit der geladenen Peaks
    this.sampleRate = 100;
    this.viewStart = 0;
    this.viewDuration = 300;
    this.totalDuration = 0;
    this.markers = [];
    this.playPosition = -1;
    this.titleRegions = [];
    this.selection = null; // { start, end }

    this._rafId = null;
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = rect.width * this.dpr;
    this.canvas.height = rect.height * this.dpr;
    this.ctx.scale(this.dpr, this.dpr);
    this.width = rect.width;
    this.height = rect.height;
  }

  setPeaks(peaks, startSec, sampleRate) {
    this.peaks = peaks;
    this.peaksStart = startSec;
    this.sampleRate = sampleRate;
  }

  setView(startSec, durationSec) {
    this.viewStart = startSec;
    this.viewDuration = durationSec;
  }

  setMarkers(markers) {
    this.markers = markers;
  }

  setPlayPosition(sec) {
    this.playPosition = sec;
  }

  setTitleRegions(regions) {
    this.titleRegions = regions;
  }

  setSelection(sel) {
    this.selection = sel;
  }

  timeToX(timeSec) {
    return ((timeSec - this.viewStart) / this.viewDuration) * this.width;
  }

  xToTime(x) {
    return this.viewStart + (x / this.width) * this.viewDuration;
  }

  render() {
    const { ctx, width, height } = this;
    if (!width || !height) return;

    const waveTop = this.timelineHeight;
    const waveHeight = height - waveTop;

    // Hintergrund
    ctx.fillStyle = this.bgColor;
    ctx.fillRect(0, 0, width, height);

    // Titel-Farbstreifen
    this._drawTitleRegions(ctx, waveTop, waveHeight);

    // Selection
    if (this.selection) {
      const x1 = this.timeToX(this.selection.start);
      const x2 = this.timeToX(this.selection.end);
      ctx.fillStyle = this.selectionColor;
      ctx.fillRect(x1, waveTop, x2 - x1, waveHeight);
    }

    // Waveform
    this._drawWaveform(ctx, waveTop, waveHeight);

    // Timeline (Minuten-Markierungen)
    this._drawTimeline(ctx);

    // Marker
    this._drawMarkers(ctx, waveTop, waveHeight);

    // Playhead
    if (this.playPosition >= this.viewStart &&
        this.playPosition <= this.viewStart + this.viewDuration) {
      const x = this.timeToX(this.playPosition);
      ctx.strokeStyle = this.playheadColor;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(x, waveTop);
      ctx.lineTo(x, height);
      ctx.stroke();
    }

    // Zentral-Linie
    const centerY = waveTop + waveHeight / 2;
    ctx.strokeStyle = 'rgba(255,255,255,0.08)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, centerY);
    ctx.lineTo(width, centerY);
    ctx.stroke();
  }

  _drawWaveform(ctx, top, height) {
    if (this.peaks.length === 0) return;

    const centerY = top + height / 2;
    const halfH = height / 2 * 0.9; // 90% der halben Hoehe nutzen

    const viewStartSample = Math.floor((this.viewStart - this.peaksStart) * this.sampleRate);
    const viewEndSample = viewStartSample + Math.floor(this.viewDuration * this.sampleRate);
    const samplesInView = viewEndSample - viewStartSample;

    if (samplesInView <= 0) return;

    // Wie viele Peaks pro Pixel?
    const samplesPerPx = samplesInView / this.width;

    ctx.fillStyle = this.waveColor;

    if (samplesPerPx <= 1) {
      // Weniger Samples als Pixel: Jedes Sample einzeln zeichnen
      for (let i = Math.max(0, viewStartSample); i < Math.min(this.peaks.length, viewEndSample); i++) {
        const x = ((i - viewStartSample) / samplesInView) * this.width;
        const val = Math.abs(this.peaks[i]);
        const barH = val * halfH;
        ctx.fillRect(x, centerY - barH, Math.max(1, this.width / samplesInView), barH * 2);
      }
    } else {
      // Mehr Samples als Pixel: Aggregieren (max pro Pixel)
      for (let px = 0; px < this.width; px++) {
        const sStart = viewStartSample + Math.floor(px * samplesPerPx);
        const sEnd = Math.min(
          viewStartSample + Math.floor((px + 1) * samplesPerPx),
          this.peaks.length
        );

        let maxVal = 0;
        for (let i = Math.max(0, sStart); i < sEnd; i++) {
          const v = Math.abs(this.peaks[i]);
          if (v > maxVal) maxVal = v;
        }

        if (maxVal > 0.001) {
          const barH = maxVal * halfH;
          ctx.fillRect(px, centerY - barH, 1, barH * 2);
        }
      }
    }
  }

  _drawTimeline(ctx) {
    const h = this.timelineHeight;
    ctx.fillStyle = 'rgba(0,0,0,0.5)';
    ctx.fillRect(0, 0, this.width, h);

    // Intervall bestimmen (automatisch anpassen an Zoom)
    let interval;
    if (this.viewDuration <= 30) interval = 5;
    else if (this.viewDuration <= 120) interval = 15;
    else if (this.viewDuration <= 600) interval = 60;
    else if (this.viewDuration <= 1800) interval = 300;
    else interval = 600;

    const firstTick = Math.ceil(this.viewStart / interval) * interval;

    ctx.fillStyle = 'rgba(255,255,255,0.6)';
    ctx.font = '10px Barlow, sans-serif';
    ctx.textAlign = 'center';

    for (let t = firstTick; t <= this.viewStart + this.viewDuration; t += interval) {
      const x = this.timeToX(t);
      if (x < 0 || x > this.width) continue;

      // Tick-Linie
      ctx.strokeStyle = 'rgba(255,255,255,0.2)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, h - 4);
      ctx.lineTo(x, h);
      ctx.stroke();

      // Label
      const min = Math.floor(t / 60);
      const sec = Math.floor(t % 60);
      const label = sec === 0 ? `${min}m` : `${min}:${String(sec).padStart(2, '0')}`;
      ctx.fillText(label, x, h - 6);
    }
  }

  _drawTitleRegions(ctx, top, height) {
    for (const region of this.titleRegions) {
      const x1 = this.timeToX(region.start);
      const x2 = this.timeToX(region.end);
      if (x2 < 0 || x1 > this.width) continue;

      const colorIdx = hashTitle(region.title) % TITLE_COLORS.length;
      ctx.fillStyle = TITLE_COLORS[colorIdx] + '26'; // ~15% alpha
      ctx.fillRect(
        Math.max(0, x1), top,
        Math.min(x2, this.width) - Math.max(0, x1), height
      );
    }
  }

  _drawMarkers(ctx, top, height) {
    for (let i = 0; i < this.markers.length; i++) {
      const marker = this.markers[i];
      const x = this.timeToX(marker.time);
      if (x < -20 || x > this.width + 20) continue;

      const color = marker.color || this.markerColor;

      // Vertikale gestrichelte Linie
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      ctx.moveTo(x, top);
      ctx.lineTo(x, top + height);
      ctx.stroke();
      ctx.setLineDash([]);

      // Dreieck-Griff oben
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.moveTo(x - 6, top);
      ctx.lineTo(x + 6, top);
      ctx.lineTo(x, top + 10);
      ctx.closePath();
      ctx.fill();

      // Index-Label
      ctx.fillStyle = '#000';
      ctx.font = 'bold 8px Barlow, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(String(i + 1), x, top + 8);
    }
  }

  hitTest(canvasX, canvasY) {
    // Marker pruefen
    for (let i = 0; i < this.markers.length; i++) {
      const mx = this.timeToX(this.markers[i].time);
      if (Math.abs(canvasX - mx) < this.markerHitRadius && canvasY < this.timelineHeight + 15) {
        return { type: 'marker', index: i, marker: this.markers[i] };
      }
    }

    // Waveform-Bereich
    if (canvasY > this.timelineHeight) {
      return { type: 'waveform', time: this.xToTime(canvasX) };
    }

    // Timeline-Bereich
    return { type: 'timeline', time: this.xToTime(canvasX) };
  }

  destroy() {
    if (this._rafId) {
      cancelAnimationFrame(this._rafId);
      this._rafId = null;
    }
  }
}
