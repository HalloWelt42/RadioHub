/**
 * RadioHub - Shared Formatters v0.1.0
 *
 * Zentrale Format-Funktionen für Zeit, Größe, Datum, Zahlen.
 * Alle Komponenten importieren hieraus statt eigene zu definieren.
 */

// === Zeit-Formatierung ===

/**
 * Formatiert Sekunden als HH:MM:SS (immer mit Stunden).
 * Für Transport-Timer, Aufnahme-Anzeigen.
 */
export function formatTime(seconds) {
  if (!seconds || !isFinite(seconds)) return '00:00:00';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

/**
 * Formatiert Sekunden kompakt: H:MM:SS oder M:SS (ohne führende Null-Stunden).
 * Für Seekbar-Labels, kurze Zeitangaben.
 */
export function formatTimeShort(seconds) {
  if (!seconds || !isFinite(seconds)) return '0:00';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }
  return `${m}:${s.toString().padStart(2, '0')}`;
}

/**
 * Formatiert Sekunden als Dauer (kompakt wie formatTimeShort, aber '--:--' bei invalid).
 * Für Aufnahme-Dauern, Session-Längen.
 */
export function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '--:--';
  return formatTimeShort(seconds);
}

/**
 * Formatiert Sekunden als Dauer-Text: "1h 23m" oder "45 min".
 * Für Podcast-Episoden, längere Dauern.
 */
export function formatDurationHuman(seconds) {
  if (!seconds) return '';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) {
    return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }
  return `${m}:${String(s).padStart(2, '0')}`;
}

/**
 * Formatiert Millisekunden als M:SS.HH (mit Hundertstel).
 * Für ICY-Metadata Zeitstempel, Segment-Positionen.
 */
export function formatMetaTime(ms) {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  const hundredths = Math.floor((ms % 1000) / 10);
  return `${m}:${s.toString().padStart(2, '0')}.${hundredths.toString().padStart(2, '0')}`;
}

/**
 * Formatiert Millisekunden als Dauer (delegiert an formatTimeShort).
 */
export function formatDurationMs(ms) {
  if (!ms || ms <= 0) return '--:--';
  return formatTimeShort(ms / 1000);
}

/**
 * Formatiert Sekunden als Gesamtdauer: HHH:MM:SS (ohne Padding der Stunden).
 * Für Gesamtspieldauer von Podcasts.
 */
export function formatTotalDuration(seconds) {
  if (!seconds || seconds <= 0) return '0:00:00';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

// === Größen-Formatierung ===

/**
 * Formatiert Bytes als KB/MB/GB.
 */
export function formatSize(bytes) {
  if (!bytes || bytes <= 0) return '--';
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`;
}

// === Datum-Formatierung ===

/**
 * Formatiert ISO-Datumstring als "DD.MM.YY HH:MM".
 */
export function formatDate(isoString) {
  if (!isoString) return '--';
  const d = new Date(isoString);
  if (isNaN(d.getTime())) return '--';
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

// === Zahlen-Formatierung ===

/**
 * 1000er-Trenner (de-DE Locale): 12345 -> "12.345".
 */
export function formatNumber(num) {
  return num?.toLocaleString('de-DE') ?? '-';
}

/**
 * k-Format: 1234 -> "1,2k", 12345 -> "12,3k", 999 -> "999".
 */
export function formatK(num) {
  if (num == null) return '-';
  if (num < 1000) return String(num);
  const k = num / 1000;
  return k >= 100 ? Math.round(k) + 'k' : k.toFixed(1).replace('.', ',') + 'k';
}
