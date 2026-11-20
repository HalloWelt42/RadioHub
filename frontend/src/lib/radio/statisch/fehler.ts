// Fehler der statischen Senderquelle mit dem Status, den das Backend in demselben Fall meldet (400, 404, 409), damit
// die Ansichten beide Umsetzungen gleich behandeln.

export class Quellfehler extends Error {
  constructor(text: string, public readonly status = 400) {
    super(text);
    this.name = "Quellfehler";
  }
}

export class NichtGefunden extends Quellfehler {
  constructor(text: string) {
    super(text, 404);
    this.name = "NichtGefunden";
  }
}

/** Die Webversion kann das nicht (Fähigkeit fehlt); die Ansichten rufen es dann nicht auf. */
export class NichtVerfuegbar extends Error {
  constructor(was: string) {
    super(`In der Webversion nicht verfügbar: ${was}`);
    this.name = "NichtVerfuegbar";
  }
}
