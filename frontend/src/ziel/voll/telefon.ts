// Bauziel volle App: Wecker, Ort und Zeitansage über das eigene Backend.
import { BackendWeckerablage, BackendZeitbausteine } from "../../lib/telefon/weckerablage-backend";
import type { Weckerablage, Zeitbausteine } from "../../lib/telefon/weckerablage";

export const weckerablage: Weckerablage = new BackendWeckerablage();
export const zeitbausteine: Zeitbausteine = new BackendZeitbausteine();
