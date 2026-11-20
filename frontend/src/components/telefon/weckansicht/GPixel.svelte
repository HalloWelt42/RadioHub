<script lang="ts">
  // Gestaltung I "RGB-Pixel": ganz grobes Raster aus 44 x 23 Leuchtquadraten mit kleiner 3x5-Schrift (Nutzer 20.11.2026:
  // "ganz grobe Matrix"), Regenbogen über den Ziffern ohne Lauflicht, kleine Pixelbilder. Ein RGB-Feld ist immer dunkel
  // (kein Hellmodus) und hat nie Rahmen: Tastenflächen sind unsichtbar, nur ihre Schrift leuchtet.
  import type { Gestaltungsprops } from "./typen";
  import Punktfeld, { type Ebene, type Bild } from "./Punktfeld.svelte";
  import { breite } from "../../../lib/telefon/punktmatrix.js";
  let p: Gestaltungsprops = $props();
  const b = $derived(p.bild);
  const S = 44, Z = 23;
  const SONNE = [".y.y.", "..y..", "yyyyy", "..y..", ".y.y."];
  const MOND = [".mm..", "mm...", "mm...", "mm...", ".mm.."];
  const WOLKE = [".ww..", "wwwww", ".www."];
  const GLOCKE = ["..g..", ".ggg.", ".ggg.", "ggggg", "..g.."];
  const NOTE = [".nn", ".n.", ".n.", "nn.", "nn."];
  const BETT = ["b....", "b....", "bbbbb", "b...b"];
  const hsl = (h: number, s: number, l: number) => `hsl(${((h % 360) + 360) % 360} ${s}% ${l}%)`;
  const nacht = $derived(b.modus === "nacht");
  const bunt = $derived((x: number, y: number) => (nacht ? hsl(2 + y * 1.2, 85, 46) : hsl(x * 8 + y * 6, 95, 58)));
  const farben = $derived({ y: nacht ? "#9a1a0c" : "#ffd21f", m: nacht ? "#c3241d" : "#cfd8ff", w: nacht ? "#300404" : "#6b7690",
    g: nacht ? "#ff3a28" : "#ffb21f", n: nacht ? "#ff3a28" : "#2ef0c8", b: nacht ? "#ff3a28" : "#a78bfa" });
  const klein = (t: string) => breite(t, 1, "klein");
  const kurz = $derived(b.senderKurz.replace(/[^A-Z0-9 ]/g, "").slice(0, 6) || "-");

  interface Feld { x: number; b: number; text: string; tun: () => void; name: string }
  const felder = $derived.by((): Feld[] => {
    if (b.lage === "klingelt") return [
      { x: 0, b: 14, text: "ZZZ", tun: p.tun.schlummern, name: p.t("schlummern") },
      { x: 15, b: 14, text: "AUS", tun: p.tun.aus, name: p.t("aus") },
      { x: 30, b: 14, text: b.quelle === "radio" ? "RAD" : "TON", tun: () => p.tun.quelle(b.quelle === "radio" ? "weckton" : "radio"), name: b.quelle === "radio" ? p.t("weckton") : b.quelleName },
    ];
    if (b.lage === "schlummert") return [{ x: S - 15, b: 15, text: "AUS", tun: p.tun.aus, name: p.t("weckerAus") }];
    if (b.tastenSichtbar) return [
      { x: 20, b: 8, text: b.spielt ? "II" : ">", tun: p.tun.umschalten, name: b.spielt ? p.t("pause") : p.t("abspielen") },
      { x: 29, b: 7, text: "Z", tun: p.tun.ansage, name: p.t("zeitansage") },
      { x: 37, b: 7, text: "N", tun: p.tun.nacht, name: p.t("nacht") },
    ];
    return [];
  });
  const ebenen = $derived.by((): Ebene[] => {
    const e: Ebene[] = [];
    const k = (text: string, x: number, y: number, farbe: Ebene["farbe"]) => e.push({ text, x, y, farbe, schrift: "klein" });
    if (b.lage === "klingelt") {
      k(b.klingelZeit ?? "", Math.round((S - klein(b.klingelZeit ?? "")) / 2), 0, farben.g);
      e.push({ text: b.zeit, y: 6, mass: 2, mitte: true, farbe: bunt, schrift: "klein" });
    } else {
      const w = b.lage === "schlummert" ? b.schlummerBis ?? "" : b.naechster?.slice(-5) ?? "";
      if (w) k(w, S - klein(w), 0, farben.g);
      e.push({ text: b.zeit, y: 6, mass: 2, mitte: true, farbe: bunt, schrift: "klein" });
      if (!felder.length) k(kurz, 4, 17, farben.n);
      if (b.lage !== "schlummert" && !felder.length && b.sonne) k(b.sonne.auf, S - klein(b.sonne.auf), 17, farben.y);
    }
    for (const f of felder) k(f.text, f.x + Math.round((f.b - klein(f.text)) / 2), 17, bunt);
    return e;
  });
  const bilder = $derived.by((): Bild[] => {
    const l: Bild[] = [];
    if (b.lage === "klingelt") l.push({ x: 0, y: 0, pixel: GLOCKE, farben }, { x: S - 5, y: 0, pixel: GLOCKE, farben });
    else {
      l.push({ x: 0, y: 0, pixel: nacht ? MOND : SONNE, farben }, { x: 6, y: 1, pixel: WOLKE, farben });
      const w = b.lage === "schlummert" ? b.schlummerBis ?? "" : b.naechster?.slice(-5) ?? "";
      if (w) l.push({ x: S - klein(w) - 7, y: b.lage === "schlummert" ? 1 : 0, pixel: b.lage === "schlummert" ? BETT : GLOCKE, farben });
      if (!felder.length) l.push({ x: 0, y: 17, pixel: NOTE, farben });
    }
    return l;
  });
  const anteil = (n: number, von: number) => `${(n / von) * 100}%`;
</script>

<div class="wa-matrixfeld pixelfeld uhr-box" class:zucken={b.zucken}>
  <Punktfeld spalten={S} zeilen={Z} {ebenen} {bilder} aus="#0d0d14" form="quadrat" modus={b.modus} />
  {#each felder as f (f.x)}
    <button type="button" class="wa-feld" style:left={anteil(f.x, S)} style:width={anteil(f.b, S)} style:top={anteil(15, Z)} style:bottom="0" onclick={f.tun} aria-label={f.name}></button>
  {/each}
</div>
