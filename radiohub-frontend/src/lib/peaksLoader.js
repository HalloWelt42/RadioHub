/**
 * RadioHub - Peaks Loader
 *
 * Lazy-Loading Manager fuer Waveform-Peaks.
 * Laedt 5-Minuten-Chunks vom Backend, haelt max ~30 min im Speicher.
 * Binary Transfer (Float32Array) fuer minimale Bandbreite.
 */

const CHUNK_DURATION = 300; // 5 Minuten pro Chunk
const SAMPLE_RATE = 100;   // Peaks pro Sekunde (muss mit Backend uebereinstimmen)
const PREFETCH_THRESHOLD = 30; // Prefetch wenn 30s vor Chunk-Rand

export class PeaksLoader {
  constructor(sessionId) {
    this.sessionId = sessionId;
    this.totalDuration = 0;
    this.sampleRate = SAMPLE_RATE;
    this.chunks = new Map(); // chunkIndex -> Float32Array
    this.loading = new Set(); // chunkIndex die gerade laden
    this.onLoad = null; // Callback wenn Chunk fertig
  }

  async init() {
    const res = await fetch(`/api/recording/sessions/${this.sessionId}/peaks/info`);
    if (!res.ok) throw new Error(`Peaks-Info fehlgeschlagen: ${res.status}`);
    const info = await res.json();
    this.totalDuration = info.total_duration;
    this.sampleRate = info.sample_rate || SAMPLE_RATE;
    return info;
  }

  _chunkIndex(timeSec) {
    return Math.floor(timeSec / CHUNK_DURATION);
  }

  _chunkStart(index) {
    return index * CHUNK_DURATION;
  }

  async loadChunk(chunkIndex) {
    if (this.chunks.has(chunkIndex) || this.loading.has(chunkIndex)) return;

    const start = this._chunkStart(chunkIndex);
    if (start >= this.totalDuration) return;

    this.loading.add(chunkIndex);

    try {
      const duration = Math.min(CHUNK_DURATION, this.totalDuration - start);
      const res = await fetch(
        `/api/recording/sessions/${this.sessionId}/peaks?start=${start}&duration=${duration}`
      );

      if (!res.ok) {
        console.warn(`Peaks-Chunk ${chunkIndex} fehlgeschlagen: ${res.status}`);
        return;
      }

      const buffer = await res.arrayBuffer();
      const peaks = new Float32Array(buffer);
      this.chunks.set(chunkIndex, peaks);

      if (this.onLoad) this.onLoad(chunkIndex, start, peaks);
    } finally {
      this.loading.delete(chunkIndex);
    }
  }

  async ensureRange(startSec, endSec) {
    const firstChunk = this._chunkIndex(startSec);
    const lastChunk = this._chunkIndex(Math.min(endSec, this.totalDuration - 0.01));
    const promises = [];

    for (let i = firstChunk; i <= lastChunk; i++) {
      if (!this.chunks.has(i) && !this.loading.has(i)) {
        promises.push(this.loadChunk(i));
      }
    }

    if (promises.length > 0) {
      await Promise.all(promises);
    }
  }

  prefetch(viewStart, viewEnd) {
    // Prefetch naechsten Chunk wenn nah am Rand
    const lastChunk = this._chunkIndex(viewEnd);
    const distToEnd = this._chunkStart(lastChunk + 1) - viewEnd;

    if (distToEnd < PREFETCH_THRESHOLD) {
      this.loadChunk(lastChunk + 1);
    }

    const firstChunk = this._chunkIndex(viewStart);
    const distToStart = viewStart - this._chunkStart(firstChunk);

    if (distToStart < PREFETCH_THRESHOLD && firstChunk > 0) {
      this.loadChunk(firstChunk - 1);
    }
  }

  getPeaks(startSec, endSec) {
    const startSample = Math.floor(startSec * this.sampleRate);
    const endSample = Math.ceil(endSec * this.sampleRate);
    const totalSamples = endSample - startSample;

    if (totalSamples <= 0) return new Float32Array(0);

    const result = new Float32Array(totalSamples);
    let written = 0;

    const firstChunk = this._chunkIndex(startSec);
    const lastChunk = this._chunkIndex(Math.max(0, endSec - 0.01));

    for (let ci = firstChunk; ci <= lastChunk; ci++) {
      const chunkData = this.chunks.get(ci);
      if (!chunkData) {
        // Nicht geladener Bereich: Nullen lassen
        const chunkSamples = Math.min(
          CHUNK_DURATION * this.sampleRate,
          totalSamples - written
        );
        written += chunkSamples;
        continue;
      }

      const chunkStartSample = ci * CHUNK_DURATION * this.sampleRate;
      const readStart = Math.max(0, startSample - chunkStartSample);
      const readEnd = Math.min(chunkData.length, endSample - chunkStartSample);

      if (readEnd > readStart) {
        const slice = chunkData.subarray(readStart, readEnd);
        result.set(slice, written);
        written += slice.length;
      }
    }

    return result;
  }

  isLoaded(startSec, endSec) {
    const firstChunk = this._chunkIndex(startSec);
    const lastChunk = this._chunkIndex(Math.max(0, endSec - 0.01));
    for (let i = firstChunk; i <= lastChunk; i++) {
      if (!this.chunks.has(i)) return false;
    }
    return true;
  }

  isLoading() {
    return this.loading.size > 0;
  }

  destroy() {
    this.chunks.clear();
    this.loading.clear();
    this.onLoad = null;
  }
}
