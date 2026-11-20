// Wecker, Ort und Zeitansage der vollen App gegen das eigene Backend (/api/wecker, /api/zeitansage).
import { api } from "../api.js";
import type { Bausteinstand, Fundort, Ort, Wecker, WeckerEntwurf, Weckerablage, WeckSender, Zeitbausteine } from "./weckerablage";

interface Favorit { uuid: string; name: string; url?: string; url_resolved?: string; favicon?: string }

export class BackendWeckerablage implements Weckerablage {
  readonly faehig = { ortssuche: true, podcast: true };

  async liste(): Promise<Wecker[]> {
    return (await api.getWecker()).wecker ?? [];
  }

  speichern(w: WeckerEntwurf): Promise<Wecker> {
    return api.saveWecker(w);
  }

  async loeschen(id: Wecker["id"]): Promise<void> {
    await api.deleteWecker(id);
  }

  ort(): Promise<Ort> {
    return api.getOrt();
  }

  ortSetzen(o: Ort): Promise<Ort> {
    return api.saveOrt(o);
  }

  async orteSuchen(q: string): Promise<Fundort[]> {
    return (await api.searchOrte(q)).orte ?? [];
  }

  async sender(): Promise<WeckSender[]> {
    const favoriten: Favorit[] = await api.getFavoritesAll();
    return favoriten.map((f) => ({ uuid: f.uuid, name: f.name, url: f.url ?? "", url_resolved: f.url_resolved ?? "", favicon: f.favicon ?? "" }));
  }
}

export class BackendZeitbausteine implements Zeitbausteine {
  readonly faehig = { erzeugen: true };

  stand(): Promise<Bausteinstand> {
    return api.fetch("/api/zeitansage");
  }

  adresse(stimme: string, name: string): string {
    return `/api/zeitansage/ton/${name}?stimme=${encodeURIComponent(stimme)}`;
  }

  async erzeugen(): Promise<void> {
    await api.fetch("/api/zeitansage/erzeugen", { method: "POST" });
  }
}
