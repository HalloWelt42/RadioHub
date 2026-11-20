<script lang="ts">
  // Gestaltung A "Matrixanzeige": der ganze Bildschirm ein Punktfeld mit groben Punkten (Nutzer 20.11.2026: "größere
  // Pixel"). Punktgrafik hat nie Rahmen: Tastenflächen sind unsichtbar, nur ihre Schrift leuchtet. Lange Sendernamen
  // laufen durch. Die Tasten der ruhigen Ansicht erscheinen nach Antippen in der unteren Zeile.
  import type { Gestaltungsprops } from "./typen";
  import Punktfeld, { type Ebene } from "./Punktfeld.svelte";
  import { breite, fuerMatrix } from "../../../lib/telefon/punktmatrix.js";
  let p: Gestaltungsprops = $props();
  const b = $derived(p.bild);
  const S = 120, Z = 48;
  const gross = fuerMatrix;

  interface Feld { x: number; b: number; y: number; text: string; farbe: string; tun: () => void; name: string }
  const felder = $derived.by((): Feld[] => {
    if (b.lage === "klingelt") return [
      { x: 0, b: 40, y: 37, text: `~ ${gross(p.t("minutenKurz", { n: b.schlummerMinuten }))}`, farbe: "--akzent", tun: p.tun.schlummern, name: p.t("schlummern") },
      { x: 42, b: 36, y: 37, text: gross(p.t("aus")), farbe: "--an", tun: p.tun.aus, name: p.t("aus") },
      { x: 80, b: 40, y: 37, text: b.quelle === "radio" ? gross(b.quelleName) : gross(p.t("ton")), farbe: "--an",
        tun: () => p.tun.quelle(b.quelle === "radio" ? "weckton" : "radio"), name: b.quelle === "radio" ? p.t("weckton") : b.quelleName },
    ];
    if (b.lage === "schlummert") return [{ x: S - 30, b: 30, y: 41, text: gross(p.t("aus")), farbe: "--akzent", tun: p.tun.aus, name: p.t("weckerAus") }];
    if (b.tastenSichtbar) return [
      { x: 26, b: 30, y: 41, text: b.spielt ? "|" : ">", farbe: "--an", tun: p.tun.umschalten, name: b.spielt ? p.t("pause") : p.t("abspielen") },
      { x: 58, b: 30, y: 41, text: gross(p.t("zeitKurz")), farbe: b.ansage.an ? "--akzent" : "--an", tun: p.tun.ansage, name: p.t("zeitansage") },
      { x: 90, b: 30, y: 41, text: b.nachtWahl === "aus" ? "*" : ")", farbe: b.nachtWahl === "aus" ? "--an" : "--akzent", tun: p.tun.nacht, name: p.t("nacht") },
    ];
    return [];
  });

  const ebenen = $derived.by((): Ebene[] => {
    const e: Ebene[] = [];
    if (b.lage === "klingelt") {
      e.push({ text: `@ ${b.klingelZeit ?? ""}   ${b.senderKurz}`, y: 0, mitte: true, farbe: "--akzent" });
      e.push({ text: b.zeit, y: 9, mass: 3, mitte: true, farbe: "--an" });
    } else {
      e.push({ text: b.datum, x: 0, y: 0, farbe: "--an" });
      const w = b.lage === "schlummert" ? `~ ${b.schlummerBis}` : b.naechster ? `@ ${gross(b.naechster)}` : "";
      e.push({ text: w, x: S - breite(w), y: 0, farbe: "--akzent" });
      e.push({ text: b.zeit, y: 10, mass: 4, mitte: true, farbe: "--an" });
      const sender = (felder.length ? b.senderKurz : gross(b.sender || "-")) + (b.verbindung === "verbindet" ? " ..." : b.verbindung === "gestoert" ? " !" : "");
      const sonne = !felder.length && b.sonne ? `*${b.sonne.auf} )${b.sonne.unter}` : "";
      const fenster = (felder.length ? felder[0].x : S - (sonne ? breite(sonne) : 0)) - 4;
      e.push({ text: sender, x: 0, y: 41, farbe: "--an", lauf: true, fenster });
      if (sonne) e.push({ text: sonne, x: S - breite(sonne), y: 41, farbe: "--an" });
    }
    for (const f of felder) e.push({ text: f.text, x: f.x + Math.round((f.b - breite(f.text)) / 2), y: f.y, farbe: f.farbe });
    return e;
  });
  const anteil = (n: number, von: number) => `${(n / von) * 100}%`;
</script>

<div class="wa-matrixfeld uhr-box" class:zucken={b.zucken}>
  <Punktfeld spalten={S} zeilen={Z} {ebenen} glanz={b.modus !== "hell"} modus={b.modus} />
  {#each felder as f (f.x)}
    <button type="button" class="wa-feld" style:left={anteil(f.x, S)} style:width={anteil(f.b, S)} style:top={anteil(f.y - 4, Z)} style:bottom="0"
      onclick={f.tun} aria-label={f.name}></button>
  {/each}
</div>
