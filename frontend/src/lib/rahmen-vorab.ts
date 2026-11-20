// Statusleiste am Telefon (RAD-10, Nutzer 20.11.2026: "obere Bedienelemente nicht erreichbar"): bis unter die
// Statusleiste zeichnen (viewport-fit=cover) gilt nur für die Web-App vom Startbildschirm; dort setzt der Rahmen des
// Appkerns den sicheren Rand (env(safe-area-inset-top)). In Safari selbst läge der Kopf sonst in der Glaszone der
// Statusleiste, die Berührungen abfängt. vite.config.ts setzt die Funktion als kleines Skript an den Anfang des Kopfs
// der Startseite (vor dem ersten Zeichnen); sie ist darum in sich geschlossen.
export function rahmenVorab(): void {
  const alsApp = window.matchMedia("(display-mode: standalone)").matches || (navigator as Navigator & { standalone?: boolean }).standalone === true;
  if (alsApp) return;
  const meta = document.querySelector<HTMLMetaElement>('meta[name="viewport"]');
  if (meta) meta.content = meta.content.replace(/,\s*viewport-fit=cover/, "");
}
