// Bauziel Webversion (RAD-11): ohne Server; es gibt nur Einstellungen dieses Geräts und die eigenen Daten im Browser.
// Unter Über nur die Texte, die für die Basic stimmen (RAD-36): Lizenz, Datenschutz und Nutzungsbedingungen; die
// technischen Informationen beschreiben den Zeitversatz des Servers, den die Basic nicht hat.
// Der Datenschutz ist ein eigener Text (basic-datenschutz.md): die Basic verbindet den Browser direkt mit fremden Servern.
// hinweise: was das Fenster Datenschutz und Herkunft zeigt (Knopf oben, RAD-120, RAD-123).
export const EINSTELLUNGEN = { server: false, ueber: ["lizenz", "recht"], recht: ["basic-datenschutz.md", "agb.md"],
  hinweise: ["basic-herkunft.md", "basic-datenschutz.md"] } as const;
