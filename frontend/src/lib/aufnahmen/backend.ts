// Aufnahmen gegen das Backend der vollen App (RAD-17): Sitzungen, Stücke, Ordner, Sperrliste, Kellerwolke.
import type { Aufnahmefaehigkeiten, Aufnahmequelle } from "./quelle";
import type { Aufnahme, Aufnahmeabfrage, Aufnahmeordner, Aufnahmeseite, Aufnahmestatus, Titel, Wolkenebene } from "./typen";

export interface Anfrager {
  fetch(pfad: string, optionen?: RequestInit): Promise<any>;
  baseUrl: string;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- Rohdaten des Backends
type Roh = Record<string, any>;

const STATUS: Record<string, Aufnahmestatus> = { recording: "laeuft", completed: "fertig", stalled: "abgebrochen", interrupted: "unterbrochen" };

function luecken(roh: unknown): number {
  try {
    const q = typeof roh === "string" ? JSON.parse(roh) : roh;
    return Number(q?.gaps ?? q?.luecken ?? (Array.isArray(q?.events) ? q.events.filter((e: Roh) => e.type === "gap").length : 0)) || 0;
  } catch {
    return 0;
  }
}

export function aufnahmeAus(r: Roh): Aufnahme {
  return {
    id: String(r.id), sender: String(r.station_name ?? ""), senderUuid: String(r.station_uuid ?? ""), beginn: String(r.start_time ?? ""), dauer: Number(r.duration) || 0,
    groesse: Number(r.file_size) || 0, codec: String(r.codec ?? r.file_format ?? "").replace(/^\./, "").toUpperCase(),
    bitrate: r.bitrate ? Number(r.bitrate) : null, art: r.rec_type === "hls-rec" ? "puffer" : "direkt",
    ordnerId: r.folder_id ?? null, titelzahl: Number(r.segment_count) || 0, status: STATUS[r.status] ?? "fertig",
    luecken: luecken(r.quality_json),
  };
}

export function titelAus(r: Roh): Titel {
  return {
    id: Number(r.id), nr: (Number(r.segment_index) || 0) + 1, titel: String(r.title ?? ""), start: (Number(r.start_ms) || 0) / 1000,
    dauer: (Number(r.duration_ms) || 0) / 1000, groesse: Number(r.file_size) || 0, pfad: String(r.file_path ?? ""),
  };
}

export class BackendAufnahmequelle implements Aufnahmequelle {
  readonly faehig: Aufnahmefaehigkeiten = { schnitt: true, wolke: true, verwalten: true };

  constructor(private readonly api: Anfrager) {}

  async aufnahmen(a: Aufnahmeabfrage, ab: number, anzahl: number): Promise<Aufnahmeseite> {
    const q = new URLSearchParams({ limit: String(anzahl), ab: String(ab), sort: a.sort, absteigend: String(a.absteigend) });
    if (a.suche.trim()) q.set("suche", a.suche.trim());
    if (a.ordner) q.set("ordner", a.ordner);
    const r = await this.api.fetch(`/api/recording/sessions?${q}`);
    return { aufnahmen: (r.sessions ?? []).map(aufnahmeAus), gesamt: Number(r.gesamt ?? r.count) || 0 };
  }

  async aufnahme(id: string): Promise<Aufnahme> {
    return aufnahmeAus(await this.api.fetch(`/api/recording/sessions/${encodeURIComponent(id)}`));
  }

  async titel(id: string): Promise<Titel[]> {
    const r = await this.api.fetch(`/api/recording/sessions/${encodeURIComponent(id)}/segments`);
    return (r.segments ?? r ?? []).map(titelAus);
  }

  async titelwechsel(id: string): Promise<number> {
    const r = await this.api.fetch(`/api/schnitt/info?art=sitzung&kennung=${encodeURIComponent(id)}`);
    return (r.titelwechsel ?? []).length;
  }

  async loeschen(id: string): Promise<void> {
    await this.api.fetch(`/api/recording/sessions/${encodeURIComponent(id)}`, { method: "DELETE" });
  }

  async titelLoeschen(id: string, titelId: number): Promise<void> {
    await this.api.fetch(`/api/recording/sessions/${encodeURIComponent(id)}/segments/${titelId}`, { method: "DELETE" });
  }

  async nachTitelnTeilen(id: string): Promise<number> {
    const r = await this.api.fetch(`/api/recording/sessions/${encodeURIComponent(id)}/split`, { method: "POST" });
    return Number(r.segments ?? r.count) || 0;
  }

  async verschieben(id: string, ordnerId: number | null): Promise<void> {
    await this.api.fetch(`/api/recording/folders/move-session/${encodeURIComponent(id)}`, { method: "PUT", body: JSON.stringify({ folder_id: ordnerId }) });
  }

  async ordner(): Promise<Aufnahmeordner[]> {
    const r = await this.api.fetch("/api/recording/folders");
    return (r.folders ?? []).map((o: Roh) => ({ id: Number(o.id), name: String(o.name), ziel: !!o.is_active, anzahl: Number(o.session_count) || 0 }));
  }

  async ordnerAnlegen(name: string): Promise<void> {
    await this.api.fetch("/api/recording/folders", { method: "POST", body: JSON.stringify({ name }) });
  }

  async ordnerUmbenennen(id: number, name: string): Promise<void> {
    await this.api.fetch(`/api/recording/folders/${id}`, { method: "PUT", body: JSON.stringify({ name }) });
  }

  async ordnerLoeschen(id: number): Promise<void> {
    await this.api.fetch(`/api/recording/folders/${id}`, { method: "DELETE" });
  }

  async zielSetzen(id: number | null): Promise<void> {
    await this.api.fetch(id === null ? "/api/recording/folders/deactivate" : `/api/recording/folders/${id}/activate`, { method: "PUT" });
  }

  async gesperrt(): Promise<Set<string>> {
    const r = await this.api.fetch("/api/recording/icy-ignore");
    return new Set((r.items ?? []).filter((i: Roh) => i.match_type === "exact").map((i: Roh) => String(i.pattern)));
  }

  async sperren(titel: string, an: boolean): Promise<void> {
    await this.api.fetch(an ? "/api/recording/icy-ignore" : "/api/recording/icy-ignore/remove-by-pattern",
      { method: "POST", body: JSON.stringify(an ? { pattern: titel, match_type: "exact" } : { pattern: titel }) });
  }

  titelTon(titelId: number): string {
    return `${this.api.baseUrl}/api/recording/segments/${titelId}/play`;
  }

  titelDatei(titelId: number): string {
    return `${this.api.baseUrl}/api/recording/segments/${titelId}/download`;
  }

  alsZip(id: string): string {
    return `${this.api.baseUrl}/api/recording/sessions/${encodeURIComponent(id)}/download-zip`;
  }

  alsEineDatei(id: string): string {
    return `${this.api.baseUrl}/api/recording/sessions/${encodeURIComponent(id)}/download-full`;
  }

  async wolke(pfad: string, ab = 0): Promise<Wolkenebene> {
    return await this.api.fetch(`/api/wolke/ebene?${new URLSearchParams({ pfad, ab: String(ab) })}`);
  }

  wolkeTon(pfad: string, herunterladen = false): string {
    return `${this.api.baseUrl}/api/wolke/ton?${new URLSearchParams({ pfad, ...(herunterladen ? { herunterladen: "true" } : {}) })}`;
  }
}
