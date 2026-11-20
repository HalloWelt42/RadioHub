// Schnittstellen von Wecker und Zeitansage am Telefon (RAD-15): was Weckerliste, Weckansicht und Einstellungen über
// Wecker, Ort und die Bausteine der Zeitansage wissen und ändern. Die volle App setzt sie gegen das Backend um
// (weckerablage-backend.ts), Basic im Speicher des Browsers und mit den Bausteinen aus dem Repo
// (weckerablage-browser.ts); eingebunden über das Bauziel ($ziel/telefon). Was eine Umsetzung nicht kann, meldet sie
// in `faehig`; die Ansichten zeigen dann den Teil nicht.

export interface WeckSender {
  uuid: string;
  name: string;
  url: string;
  url_resolved: string;
  favicon: string;
}

export interface Wecker {
  /** Zahl im Backend, Kennung (UUID) im Browser */
  id: number | string;
  aktiv: boolean;
  /** "HH:MM" */
  zeit: string;
  /** 1 = Montag bis 7 = Sonntag */
  tage: number[];
  quelle: "sender" | "podcast";
  sender: WeckSender | null;
  podcast_id: number | null;
  lautstaerke: number;
  anstieg_s: number;
  schlummern_min: number;
  weckton: string;
}

export type WeckerEntwurf = Omit<Wecker, "id"> & { id?: Wecker["id"] };

export interface Ort {
  name: string;
  breite: number | null;
  laenge: number | null;
}

export interface Fundort {
  name: string;
  art: string;
  breite: number;
  laenge: number;
}

export interface Weckerablage {
  readonly faehig: {
    /** Orte nach Namen suchen (sonst nur Standort und Eingabe) */
    ortssuche: boolean;
    /** mit der neuesten Folge eines Abos wecken */
    podcast: boolean;
  };
  liste(): Promise<Wecker[]>;
  speichern(w: WeckerEntwurf): Promise<Wecker>;
  loeschen(id: Wecker["id"]): Promise<void>;
  ort(): Promise<Ort>;
  ortSetzen(o: Ort): Promise<Ort>;
  orteSuchen(q: string): Promise<Fundort[]>;
  /** die Sender, mit denen geweckt werden kann (die Favoriten), abspielbar */
  sender(): Promise<WeckSender[]>;
}

export interface Bausteinstand {
  /** Stimme der Bausteine (`katalog:<Name>` oder Kennung einer privaten Stimme) */
  stimme: string;
  bausteine: string[];
  fehlend: string[];
  erzeugung?: { laeuft: boolean; meldung: string };
}

export interface Zeitbausteine {
  readonly faehig: {
    /** fehlende Bausteine sprechen lassen */
    erzeugen: boolean;
  };
  stand(): Promise<Bausteinstand>;
  /** Adresse eines Bausteins (MP3) der Stimme */
  adresse(stimme: string, name: string): string;
  erzeugen(): Promise<void>;
}
