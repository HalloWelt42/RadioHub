// Anzeige für Aufnahmen und Schnitt (RAD-17): Zeiten, Dauer, Größe, Datum, rein rechnend.

/** 3:12, 25:37, 1:02:03 */
export function zeit(sekunden: number): string {
  const s = Math.max(0, Math.round(sekunden));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60;
  return h ? `${h}:${String(m).padStart(2, "0")}:${String(x).padStart(2, "0")}` : `${m}:${String(x).padStart(2, "0")}`;
}

/** 26 min, 1 h 12 min */
export function dauer(sekunden: number): string {
  if (sekunden >= 3600) return `${Math.floor(sekunden / 3600)} h ${Math.round((sekunden % 3600) / 60)} min`;
  return `${Math.max(1, Math.round(sekunden / 60))} min`;
}

/** 48 MB, 1,3 MB, 2,1 GB */
export function groesse(bytes: number): string {
  const mb = bytes / 1024 / 1024;
  if (mb >= 1024) return `${(mb / 1024).toLocaleString("de-DE", { maximumFractionDigits: 1 })} GB`;
  return `${mb.toLocaleString("de-DE", { maximumFractionDigits: mb < 10 ? 1 : 0 })} MB`;
}

/** 21. Nov., 20:14 */
export function datum(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${d.toLocaleDateString("de-DE", { day: "numeric", month: "short" })}, ${d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })}`;
}

/** Uhrzeit 22:41:07 */
export function uhrzeit(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleTimeString("de-DE");
}

/** Endung einer Datei als Format: MP3, FLAC */
export const format = (name: string) => (name.includes(".") ? name.split(".").pop()!.toUpperCase() : "");
