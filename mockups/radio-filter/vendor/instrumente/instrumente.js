// Entwurf RAD-3 (RadioHub, Radio mit Filterung): Kopie aus hifi-regler/appkern/instrumente.js, Stand hifi-regler 9a7c0fe vom 09.11.2026.
// Laut Plan RAD-1 (Entscheidung 7) wandert die Vorlage HiFi samt Instrumenten in den Appkern; dann kommt diese Datei von
// dort. Im Entwurf unverändert lassen, eigene Regeln stehen in radio-marken.css und radio-bausteine.css.
// Regler des Appkerns: Drehregler, Schieber, Taster, Kippschalter, Wahltasten und Leuchten als eigene
// Elemente im Licht-DOM (ohne Schattenbaum, damit Marken und Vorlagen greifen). In der App werden daraus Svelte-Bausteine;
// die Teilung bleibt: eine Wahrheit für Werte (Wert: Bereich, Schritt, Kurve, Vorgabe, Einheit, Raster) und eine für
// Eingaben (bedienen: Ziehen, Mausrad, Tasten, Doppelklick, Doppeltipp, Feinschritt, Werteingabe). Die Elemente
// unterscheiden sich nur in der Darstellung.
//
// Beschriftung: die üblichen (meist englischen) Fachbegriffe der Tontechnik; die deutsche Erklärung steht im Attribut
// "hilfe" und erscheint im Hover.
//
// Bedienung aller Regler:
//   Ziehen hoch und runter (Schieber: entlang der Bahn), Mausrad, Pfeiltasten, Bild auf und ab (zehnmal), Pos1 und Ende;
//   Umschalttaste hält: ein Zehntel (fein); Doppelklick oder Doppeltipp: Vorgabe; Entf: Vorgabe; Klick auf den Wert oder
//   Eingabetaste: Wert eintippen. Jede Eingabe meldet sich als Ereignis "ak-eingabe" am Dokument (für Anzeigen der Seite).

(() => {
  "use strict";

  const FEIN = 0.1;            // Umschalttaste: ein Zehntel
  const ZIEH_PX = 240;         // Ziehen: so viele Pixel für den ganzen Bereich
  const RAD_JE_PX = 0.0002;    // Mausrad: Anteil je Pixel Drehung (eine Raste von 100 Pixel = 2 Prozent)
  const RAD_RASTE_PX = 60;     // Mausrad bei Rastern: so viel Drehung für eine Raste
  const DOPPEL_MS = 330;       // Doppeltipp: höchstens so lange und
  const DOPPEL_PX = 14;        //   so weit auseinander
  const ROLLPAUSE_MS = 450;    // so lange nach dem Rollen der Seite dreht das Rad keinen Regler (kein Kapern beim Rollen)

  // ─── Zahlen und Einheiten ───
  const zahl = (x, stellen) => x.toLocaleString("de-DE", { minimumFractionDigits: stellen, maximumFractionDigits: stellen });
  const stellenFuer = (schritt) => (schritt >= 1 ? 0 : Math.min(3, Math.round(-Math.log10(schritt))));
  const EINHEITEN = {
    "%": (w, s) => `${zahl(w, s)} %`,
    dB: (w, s) => `${w > 0 ? "+" : ""}${zahl(w, s)} dB`,
    Hz: (w) => (w >= 1000 ? `${zahl(w / 1000, w >= 10000 ? 1 : 2)} kHz` : `${zahl(w, w < 10 ? 2 : w < 100 ? 1 : 0)} Hz`),
    ms: (w) => (w >= 1000 ? `${zahl(w / 1000, 2)} s` : `${zahl(w, w < 10 ? 1 : 0)} ms`),
    Cent: (w, s) => `${w > 0 ? "+" : ""}${zahl(w, s)} Cent`,
    x: (w, s) => `${zahl(w, s)} ×`,
    "": (w, s) => zahl(w, s),
  };

  // ─── Wertmodell ───
  class Wert {
    constructor(o) {
      Object.assign(this, { min: 0, max: 100, schritt: 1, kurve: "lin", einheit: "", raster: null, bipolar: false }, o);
      if (this.raster) Object.assign(this, { min: 0, max: this.raster.length - 1, schritt: 1 });
      if (this.vorgabe === undefined || Number.isNaN(this.vorgabe)) this.vorgabe = this.bipolar ? (this.min + this.max) / 2 : this.min;
      this.wert = this.klemmen(o.wert ?? this.vorgabe);
    }
    klemmen(w) {
      w = Math.min(this.max, Math.max(this.min, w));
      if (this.schritt) w = this.min + Math.round((w - this.min) / this.schritt) * this.schritt;
      return +w.toFixed(6);
    }
    zuAnteil(w) {
      if (this.kurve === "log") return Math.log(w / this.min) / Math.log(this.max / this.min);
      return (w - this.min) / (this.max - this.min);
    }
    ausAnteil(a) {
      a = Math.min(1, Math.max(0, a));
      return this.kurve === "log" ? this.min * Math.pow(this.max / this.min, a) : this.min + a * (this.max - this.min);
    }
    get anteil() { return this.zuAnteil(this.wert); }
    get text() {
      if (this.raster) return this.raster[this.wert];
      const f = EINHEITEN[this.einheit] ?? ((w, s) => `${zahl(w, s)} ${this.einheit}`);
      return f(this.wert, stellenFuer(this.schritt));
    }
    /** Schritt der Tasten als Anteil: ein Raster, sonst ein Prozent des Bereichs, nie feiner als der Schritt */
    tastenAnteil(fein) {
      if (this.raster) return 1 / this.max;
      const minimal = this.kurve === "log" ? 0.001 : this.schritt / (this.max - this.min);
      return Math.max(minimal, fein ? 0.001 : 0.01);
    }
    /** Eingetippten Text lesen: "1,2 k" = 1200, "-3 dB" = -3, bei Rastern auch der Name */
    lesen(text) {
      const t = text.trim().toLowerCase();
      if (this.raster) {
        const i = this.raster.findIndex((r) => r.toLowerCase().startsWith(t));
        if (i >= 0) return i;
      }
      const m = t.replace(",", ".").match(/^([+-]?\d*\.?\d+)\s*(k)?/);
      if (!m) return null;
      let w = parseFloat(m[1]) * (m[2] ? 1000 : 1);
      if (this.einheit === "ms" && /\ds\b|\d\s*s$/.test(t) && !t.includes("ms")) w *= 1000;
      return this.raster ? Math.round(w) - 1 : w;
    }
  }

  // ─── Eingaben: eine Stelle für alle Regler ───
  let zuletztGerollt = 0;
  document.addEventListener("scroll", () => { zuletztGerollt = performance.now(); }, { capture: true, passive: true });

  function melden(el, art, fein) {
    el.dispatchEvent(new CustomEvent("input", { bubbles: true }));
    document.dispatchEvent(new CustomEvent("ak-eingabe", { detail: { name: el.getAttribute("name") || "", text: el.modell?.text ?? "", art, fein } }));
  }

  /**
   * Bedienung eines Reglers. ziel: { el, modell, setzen(anteil), griff (Element für Ziehen), bahn (Element für Lage, nur
   * Schieber), richtung ("senkrecht" | "waagrecht"), wertFeld (Element für die Werteingabe) }
   */
  function bedienen(ziel) {
    const { el, modell } = ziel;
    let zieht = null, letzterTipp = null, radRest = 0;
    const gesperrt = () => el.getAttribute("aria-disabled") === "true";
    const setzenAnteil = (a, art, fein) => { const vorher = modell.wert; modell.wert = modell.klemmen(modell.ausAnteil(a)); ziel.zeigen(); if (modell.wert !== vorher) melden(el, art, fein); };
    const vorgabe = (art) => { modell.wert = modell.klemmen(modell.vorgabe); ziel.zeigen(); melden(el, art, false); };

    // Ziehen: relativ (Drehregler, Griff) oder absolut (Klick auf die Bahn, danach relativ weiter)
    ziel.griff.addEventListener("pointerdown", (e) => {
      if (gesperrt() || e.button > 0 || e.target.closest(".ak-eingabe")) return;
      if (ziel.wertFeld && e.target === ziel.wertFeld) return;      // Klick auf den Wert öffnet die Eingabe
      e.preventDefault();
      el.focus({ preventScroll: true });
      // Doppeltipp und Doppelklick: Vorgabe (eigene Erkennung, weil dblclick bei Fingern unzuverlässig kommt)
      const jetzt = performance.now();
      if (letzterTipp && jetzt - letzterTipp.t < DOPPEL_MS && Math.hypot(e.clientX - letzterTipp.x, e.clientY - letzterTipp.y) < DOPPEL_PX) {
        letzterTipp = null; vorgabe(e.pointerType === "touch" ? "Doppeltipp" : "Doppelklick"); return;
      }
      letzterTipp = { t: jetzt, x: e.clientX, y: e.clientY };
      let roh = modell.anteil;
      if (ziel.bahn && !e.target.closest(".ak-schieber-griff")) {
        const r = ziel.bahn.getBoundingClientRect(), g = ziel.griffMass ?? 0;
        roh = ziel.richtung === "senkrecht" ? 1 - (e.clientY - r.top - g / 2) / (r.height - g) : (e.clientX - r.left - g / 2) / (r.width - g);
        roh = Math.min(1, Math.max(0, roh));
        setzenAnteil(roh, "Klick auf die Bahn", false);
      }
      zieht = { id: e.pointerId, x: e.clientX, y: e.clientY, roh };
      el.setPointerCapture?.(e.pointerId);
      el.classList.add("zieht");
    });
    el.addEventListener("pointermove", (e) => {
      if (!zieht || e.pointerId !== zieht.id) return;
      const dx = e.clientX - zieht.x, dy = e.clientY - zieht.y;
      zieht.x = e.clientX; zieht.y = e.clientY;
      const laenge = ziel.bahn ? (ziel.richtung === "senkrecht" ? ziel.bahn.clientHeight : ziel.bahn.clientWidth) : ZIEH_PX;
      const weg = ziel.bahn ? (ziel.richtung === "senkrecht" ? -dy : dx) : -dy + dx;
      zieht.roh = Math.min(1, Math.max(0, zieht.roh + (weg / Math.max(60, laenge)) * (e.shiftKey ? FEIN : 1)));
      setzenAnteil(zieht.roh, "Ziehen", e.shiftKey);
    });
    const ende = (e) => {
      if (!zieht || e.pointerId !== zieht.id) return;
      zieht = null; el.classList.remove("zieht");
      el.dispatchEvent(new CustomEvent("change", { bubbles: true }));
    };
    el.addEventListener("pointerup", ende);
    el.addEventListener("pointercancel", ende);

    // Mausrad: nur wenn die Seite nicht gerade rollt; Umschalttaste fein (macOS schickt dann deltaX)
    el.addEventListener("wheel", (e) => {
      if (gesperrt() || performance.now() - zuletztGerollt < ROLLPAUSE_MS) return;
      e.preventDefault();
      const delta = (e.deltaY || e.deltaX) * (e.deltaMode === 1 ? 33 : 1);
      if (modell.raster) {
        radRest += delta;
        if (Math.abs(radRest) < RAD_RASTE_PX) return;
        const n = Math.sign(radRest); radRest = 0;
        setzenAnteil(modell.anteil - n * modell.tastenAnteil(false), "Mausrad", false);
        return;
      }
      setzenAnteil(modell.anteil - delta * RAD_JE_PX * (e.shiftKey ? FEIN : 1), "Mausrad", e.shiftKey);
    }, { passive: false });

    // Tasten
    el.addEventListener("keydown", (e) => {
      if (gesperrt() || e.target.closest(".ak-eingabe")) return;
      const s = modell.tastenAnteil(e.shiftKey);
      const a = modell.anteil;
      const tasten = {
        ArrowUp: a + s, ArrowRight: a + s, ArrowDown: a - s, ArrowLeft: a - s,
        PageUp: a + (modell.raster ? s : 0.1), PageDown: a - (modell.raster ? s : 0.1), Home: 0, End: 1,
      };
      if (e.key in tasten) { e.preventDefault(); setzenAnteil(tasten[e.key], `Taste ${TASTENNAME[e.key]}`, e.shiftKey); return; }
      if (e.key === "Delete" || e.key === "Backspace") { e.preventDefault(); vorgabe("Taste Entf"); return; }
      if (e.key === "Enter" && ziel.wertFeld) { e.preventDefault(); eintippen(ziel); }
    });
    el.addEventListener("dblclick", (e) => e.preventDefault());
    ziel.wertFeld?.addEventListener("click", () => { if (!gesperrt()) eintippen(ziel); });
  }
  const TASTENNAME = { ArrowUp: "hoch", ArrowRight: "rechts", ArrowDown: "runter", ArrowLeft: "links", PageUp: "Bild auf", PageDown: "Bild ab", Home: "Pos1", End: "Ende" };

  // Wert eintippen: ein Eingabefeld an der Stelle des Werts, Eingabetaste übernimmt, Escape bricht ab
  function eintippen(ziel) {
    const { el, modell, wertFeld } = ziel;
    if (el.querySelector(".ak-eingabe")) return;
    const feld = document.createElement("input");
    feld.className = "ak-eingabe";
    feld.value = modell.text;
    feld.setAttribute("aria-label", `${el.getAttribute("name") || "Wert"} eintippen`);
    feld.inputMode = modell.raster ? "text" : "decimal";
    wertFeld.hidden = true;
    wertFeld.after(feld);
    feld.focus(); feld.select();
    let fertig = false;
    const schliessen = (uebernehmen) => {
      if (fertig) return; fertig = true;
      if (uebernehmen) {
        const w = modell.lesen(feld.value);
        if (w !== null && !Number.isNaN(w)) { modell.wert = modell.klemmen(w); melden(el, "Eingetippt", false); }
      }
      feld.remove(); wertFeld.hidden = false; ziel.zeigen(); el.focus({ preventScroll: true });
    };
    feld.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); schliessen(true); }
      if (e.key === "Escape") { e.preventDefault(); schliessen(false); }
      e.stopPropagation();
    });
    feld.addEventListener("blur", () => schliessen(true));
  }

  // ─── Geometrie der Skala (Koordinaten -50 bis 50, Winkel im Uhrzeigersinn ab oben) ───
  const punkt = (r, w) => [r * Math.sin((w * Math.PI) / 180), -r * Math.cos((w * Math.PI) / 180)];
  const bogen = (r, von, bis) => {
    const [x1, y1] = punkt(r, von), [x2, y2] = punkt(r, bis);
    return `M${x1.toFixed(2)} ${y1.toFixed(2)}A${r} ${r} 0 ${bis - von > 180 ? 1 : 0} 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`;
  };
  const striche = (n, innen, aussen, innenKlein) =>
    Array.from({ length: n }, (_, i) => {
      const w = -135 + (i * 270) / (n - 1);
      const r1 = innenKlein && i % 2 ? innenKlein : innen;
      const [x1, y1] = punkt(r1, w), [x2, y2] = punkt(aussen, w);
      return `M${x1.toFixed(2)} ${y1.toFixed(2)}L${x2.toFixed(2)} ${y2.toFixed(2)}`;
    }).join("");
  const R_BOGEN = 43, R_MOD = 40.2;

  const attr = (el, n, vorgabe) => (el.hasAttribute(n) ? el.getAttribute(n) : vorgabe);
  /** Erklärung im Hover: die Beschriftung bleibt der übliche Fachbegriff, "hilfe" erklärt ihn (Titel und für Vorleser) */
  const hilfe = (el, ziel = el) => {
    if (!el.hasAttribute("hilfe")) return;
    el.title = el.getAttribute("hilfe");
    ziel.setAttribute("aria-description", el.getAttribute("hilfe"));
  };
  const num = (el, n, vorgabe) => (el.hasAttribute(n) ? parseFloat(el.getAttribute(n)) : vorgabe);
  const modellAus = (el) => new Wert({
    min: num(el, "min", 0), max: num(el, "max", 100), schritt: num(el, "schritt", 1), wert: num(el, "wert", undefined),
    vorgabe: num(el, "vorgabe", undefined), kurve: attr(el, "kurve", "lin"), einheit: attr(el, "einheit", ""),
    raster: el.hasAttribute("raster") ? el.getAttribute("raster").split("|") : null, bipolar: el.hasAttribute("bipolar"),
  });

  // ─── Grundlage der Regler ───
  class Regler extends HTMLElement {
    connectedCallback() {
      if (this.modell) return;
      this.modell = modellAus(this);
      this.mod = num(this, "mod", 0);
      this.tabIndex = this.hasAttribute("gesperrt") ? -1 : 0;
      this.setAttribute("role", "slider");
      this.setAttribute("aria-label", attr(this, "name", "Regler"));
      if (this.hasAttribute("gesperrt")) this.setAttribute("aria-disabled", "true");
      if (this.hasAttribute("farbe")) this.style.setProperty("--kappe-farbe", this.getAttribute("farbe"));
      if (this.hasAttribute("leuchte")) this.style.setProperty("--ak-wert", `var(--led-${this.getAttribute("leuchte")})`);
      if (this.hasAttribute("zeiger")) this.style.setProperty("--zeiger-farbe", `var(--led-${this.getAttribute("zeiger")})`);
      this.bauen();
      hilfe(this);
      bedienen(this.ziel());
      this.zeigen();
    }
    get wert() { return this.modell.wert; }
    set wert(w) { this.modell.wert = this.modell.klemmen(w); this.zeigen(); }
    get anteil() { return this.modell.anteil; }
    set anteil(a) { this.modell.wert = this.modell.klemmen(this.modell.ausAnteil(a)); this.zeigen(); }
    zeigenGemeinsam() {
      const m = this.modell;
      this.setAttribute("aria-valuemin", m.min);
      this.setAttribute("aria-valuemax", m.max);
      this.setAttribute("aria-valuenow", m.wert);
      this.setAttribute("aria-valuetext", m.text);
      if (this.wertFeld.textContent !== m.text) this.wertFeld.textContent = m.text;
      this.style.setProperty("--a", m.anteil.toFixed(4));
    }
  }

  class Drehregler extends Regler {
    bauen() {
      const m = this.modell;
      const raster = m.raster;
      const spanne = raster ? Math.min(270, 36 * (raster.length - 1)) : 270;
      this.winkelVon = -spanne / 2; this.spanne = spanne;
      const kranz = this.getAttribute("kappe") === "ring"
        ? `<g class="kranz">${Array.from({ length: 15 }, (_, i) => { const [x, y] = punkt(44, -135 + i * (270 / 14)); return `<circle cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="2.6"/>`; }).join("")}</g>` : "";
      const rasten = raster ? `<g class="rasten">${raster.map((_, i) => { const [x, y] = punkt(46, this.winkelVon + (i * spanne) / (raster.length - 1)); return `<circle cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="1.9"/>`; }).join("")}</g>` : "";
      const namen = raster ? raster.map((r, i) => { const [x, y] = punkt(64, this.winkelVon + (i * spanne) / (raster.length - 1)); return `<span class="ak-dreh-rastname" style="left:${50 + x}%;top:${50 + y}%">${r}</span>`; }).join("") : "";
      const grenzen = attr(this, "grenzen", "");
      this.innerHTML = `<div class="ak-dreh-koerper">
          <svg class="ak-dreh-skala" viewBox="-50 -50 100 100" aria-hidden="true">
            ${raster ? "" : `<path class="striche s11" d="${striche(11, 46.5, 49.5)}"/><path class="striche s21" d="${striche(21, 46, 49.8, 47.6)}"/>
            <path class="bahn" d="${bogen(R_BOGEN, -135, 135)}"/><path class="schein" pathLength="100" d="${bogen(R_BOGEN, -135, 135)}"/>
            <path class="wert" pathLength="100" d="${bogen(R_BOGEN, -135, 135)}"/>${this.mod ? `<path class="mod" pathLength="100" d="${bogen(R_MOD, -135, 135)}"/>` : ""}`}
            ${kranz}${rasten}
          </svg>
          <div class="ak-dreh-kappe"><div class="ak-dreh-deckel"></div><div class="ak-dreh-zeiger"></div></div>${namen}
        </div>
        <span class="ak-dreh-name">${attr(this, "name", "")}</span><span class="ak-dreh-wert" title="Klicken zum Eintippen"></span>
        ${grenzen ? `<span class="ak-dreh-grenzen">${grenzen.split("|").map((g) => `<span>${g}</span>`).join("")}</span>` : ""}`;
      this.wertFeld = this.querySelector(".ak-dreh-wert");
      this.bogenWert = this.querySelector(".ak-dreh-skala .wert");
      this.bogenSchein = this.querySelector(".ak-dreh-skala .schein");
      this.bogenMod = this.querySelector(".ak-dreh-skala .mod");
      this.punkte = [...this.querySelectorAll(".kranz circle")];
      this.rastnamen = [...this.querySelectorAll(".ak-dreh-rastname")];
    }
    ziel() { return { el: this, modell: this.modell, griff: this, wertFeld: this.wertFeld, zeigen: () => this.zeigen() }; }
    zeigen() {
      this.zeigenGemeinsam();
      const m = this.modell, a = m.anteil;
      this.style.setProperty("--winkel", `${(this.winkelVon + a * this.spanne).toFixed(2)}deg`);
      if (this.bogenWert) {
        const null_ = m.bipolar ? m.zuAnteil(m.vorgabe) : 0;
        const von = Math.min(a, null_) * 100, laenge = Math.abs(a - null_) * 100;
        for (const p of [this.bogenWert, this.bogenSchein]) {
          p.style.strokeDasharray = `${laenge.toFixed(2)} 1000`;
          p.style.strokeDashoffset = `${(-von).toFixed(2)}`;
          p.style.visibility = laenge < 0.4 ? "hidden" : "visible";
        }
      }
      if (this.bogenMod) {
        const von = Math.max(0, a - this.mod), bis = Math.min(1, a + this.mod);
        this.bogenMod.style.strokeDasharray = `${((bis - von) * 100).toFixed(2)} 1000`;
        this.bogenMod.style.strokeDashoffset = `${(-von * 100).toFixed(2)}`;
      }
      if (this.punkte.length) {
        const n = this.punkte.length - 1;
        this.punkte.forEach((p, i) => p.classList.toggle("an", i / n <= a + 1e-6 && (a > 0.001 || i === 0)));
      }
      this.rastnamen.forEach((s, i) => s.classList.toggle("an", i === m.wert));
    }
  }

  class Schieber extends Regler {
    bauen() {
      const m = this.modell;
      const grenzen = m.raster ? m.raster : attr(this, "grenzen", "").split("|").filter(Boolean);
      const segmente = num(this, "segmente", 0);
      if (segmente) this.style.setProperty("--seg-w", `${100 / segmente}%`);
      this.innerHTML = `<div class="ak-schieber-kopf"><span class="ak-dreh-name">${attr(this, "name", "")}</span><span class="ak-dreh-wert" title="Klicken zum Eintippen"></span></div>
        <div class="ak-schieber-feld"><div class="ak-schieber-bahn"><div class="ak-schieber-fuellung"></div>${segmente ? `<div class="segmente"></div>` : ""}</div><div class="ak-schieber-griff"></div></div>
        ${grenzen.length ? `<div class="ak-schieber-grenzen">${grenzen.map((g) => `<span>${g}</span>`).join("")}</div>` : ""}`;
      this.wertFeld = this.querySelector(".ak-dreh-wert");
      this.feld = this.querySelector(".ak-schieber-feld");
      this.grenzNamen = m.raster ? [...this.querySelectorAll(".ak-schieber-grenzen span")] : [];
      this.segmente = segmente;
      this.setAttribute("aria-orientation", attr(this, "richtung", "waagrecht") === "senkrecht" ? "vertical" : "horizontal");
    }
    ziel() {
      const griff = this.querySelector(".ak-schieber-griff");
      const art = attr(this, "art", "");
      return { el: this, modell: this.modell, griff: this.feld, bahn: this.feld, richtung: attr(this, "richtung", "waagrecht"),
               griffMass: art === "balken" ? 0 : (attr(this, "richtung") === "senkrecht" ? griff.offsetHeight : griff.offsetWidth) || 22,
               wertFeld: this.wertFeld, zeigen: () => this.zeigen() };
    }
    zeigen() {
      this.zeigenGemeinsam();
      if (this.segmente) {
        // Leuchtbalken: nur ganze Segmente leuchten
        this.style.setProperty("--a", (Math.round(this.modell.anteil * this.segmente) / this.segmente).toFixed(4));
      }
      this.grenzNamen.forEach((s, i) => s.classList.toggle("an", i === this.modell.wert));
    }
  }

  // ─── Taster: rasten (an und aus), tasten (an, solange gedrückt), tippen (Tempo aus dem Abstand der Tipps) ───
  class Taster extends HTMLElement {
    connectedCallback() {
      if (this.knopf) return;
      const art = attr(this, "art", "flach"), modus = attr(this, "modus", "rasten");
      if (this.hasAttribute("farbe")) this.style.setProperty("--farbe", `var(--led-${this.getAttribute("farbe")})`);
      const symbol = this.getAttribute("symbol");
      const innen = art === "fuss" ? `<span class="ak-taster-mutter"></span>` : art === "flach" ? `<span class="ak-taster-streifen"></span><span>${attr(this, "beschriftung", "")}</span>`
        : symbol ? `<i class="fa-solid ${symbol}" aria-hidden="true"></i>` : `<span>${attr(this, "beschriftung", "")}</span>`;
      const led = this.hasAttribute("led") ? `<ak-led farbe="${this.getAttribute("led")}" groesse="${art === "fuss" ? "mittel" : "klein"}"></ak-led>` : "";
      const text = attr(this, "text", "");
      this.innerHTML = `${led}<button class="ak-taster-knopf" type="button" aria-label="${text || attr(this, "beschriftung", "")}">${innen}</button>${text ? `<span class="ak-taster-text">${text}</span>` : ""}`;
      this.knopf = this.querySelector("button");
      this.led = this.querySelector("ak-led");
      this.tipps = [];
      hilfe(this, this.knopf);
      if (modus === "rasten") this.knopf.setAttribute("aria-pressed", String(this.hasAttribute("an")));
      const druecken = (an) => { this.classList.toggle("gedrueckt", an); if (modus === "tasten") this.setzen(an); };
      this.knopf.addEventListener("pointerdown", () => druecken(true));
      this.knopf.addEventListener("pointerup", () => druecken(false));
      this.knopf.addEventListener("pointerleave", () => druecken(false));
      this.knopf.addEventListener("keydown", (e) => { if ((e.key === " " || e.key === "Enter") && !e.repeat) druecken(true); });
      this.knopf.addEventListener("keyup", (e) => { if (e.key === " " || e.key === "Enter") druecken(false); });
      this.knopf.addEventListener("click", () => {
        if (modus === "rasten") this.setzen(!this.hasAttribute("an"));
        if (modus === "tippen") this.tippen();
      });
      this.setzen(this.hasAttribute("an"));
    }
    setzen(an) {
      this.toggleAttribute("an", an);
      if (this.knopf.hasAttribute("aria-pressed")) this.knopf.setAttribute("aria-pressed", String(an));
      this.led?.setAttribute("zustand", an ? "an" : "aus");
      document.dispatchEvent(new CustomEvent("ak-eingabe", { detail: { name: attr(this, "text", attr(this, "beschriftung", "")), text: an ? "an" : "aus", art: "Taster" } }));
      this.dispatchEvent(new CustomEvent("input", { bubbles: true }));
    }
    tippen() {
      const t = performance.now();
      this.tipps = [...this.tipps.filter((x) => t - x < 2500), t].slice(-5);
      this.led?.setAttribute("zustand", "an");
      setTimeout(() => this.led?.setAttribute("zustand", "aus"), 90);
      if (this.tipps.length >= 2) {
        const abstand = (this.tipps.at(-1) - this.tipps[0]) / (this.tipps.length - 1);
        this.tempo = 60000 / abstand;
        this.dispatchEvent(new CustomEvent("tempo", { bubbles: true, detail: { tempo: this.tempo } }));
        document.dispatchEvent(new CustomEvent("ak-eingabe", { detail: { name: "Tippen", text: `${zahl(this.tempo, 1)} Schläge je Minute`, art: "Taster" } }));
      }
    }
  }

  // ─── Kippschalter: zwei oder drei Stellungen ───
  class Kippschalter extends HTMLElement {
    connectedCallback() {
      if (this.knopf) return;
      const namen = attr(this, "beschriftung", "An|Aus").split("|");   // oben|unten oder oben|mitte|unten
      this.stellungen = namen.length === 3 ? ["oben", "mitte", "unten"] : ["oben", "unten"];
      this.namen = namen;
      if (!this.hasAttribute("stellung")) this.setAttribute("stellung", this.stellungen.at(-1));
      const mitte = namen.length === 3 ? `<span class="ak-kipp-text mitte">${namen[1]}</span>` : "";
      this.innerHTML = `<span class="ak-kipp-text oben">${namen[0]}</span>
        <button class="ak-kipp-knopf" type="button"><span class="ak-kipp-mutter"></span><span class="ak-kipp-hebel"></span></button>
        <span class="ak-kipp-text unten">${namen.at(-1)}</span>${mitte}${this.hasAttribute("name") ? `<span class="ak-etikett">${this.getAttribute("name")}</span>` : ""}`;
      this.knopf = this.querySelector("button");
      if (namen.length === 3) { this.knopf.setAttribute("role", "slider"); this.knopf.setAttribute("aria-valuemin", "0"); this.knopf.setAttribute("aria-valuemax", "2"); }
      else this.knopf.setAttribute("role", "switch");
      this.knopf.setAttribute("aria-label", attr(this, "name", namen.join(" oder ")));
      hilfe(this, this.knopf);
      this.knopf.addEventListener("click", (e) => {
        const r = this.knopf.getBoundingClientRect();
        const lage = e.detail === 0 ? null : (e.clientY - r.top) / r.height;       // Tastatur: detail 0
        if (lage === null) return this.wechseln(1);
        if (this.stellungen.length === 3) this.stellen(lage < 0.36 ? "oben" : lage > 0.64 ? "unten" : "mitte");
        else this.stellen(lage < 0.5 ? "oben" : "unten");
      });
      this.knopf.addEventListener("keydown", (e) => {
        if (e.key === "ArrowUp" || e.key === "ArrowRight") { e.preventDefault(); this.wechseln(-1, false); }
        if (e.key === "ArrowDown" || e.key === "ArrowLeft") { e.preventDefault(); this.wechseln(1, false); }
      });
      this.zeigen();
    }
    wechseln(richtung, rundum = true) {
      const i = this.stellungen.indexOf(this.getAttribute("stellung"));
      let j = i + richtung;
      if (rundum) j = (j + this.stellungen.length) % this.stellungen.length;
      this.stellen(this.stellungen[Math.min(this.stellungen.length - 1, Math.max(0, j))]);
    }
    stellen(s) {
      this.setAttribute("stellung", s); this.zeigen();
      document.dispatchEvent(new CustomEvent("ak-eingabe", { detail: { name: attr(this, "name", "Kippschalter"), text: this.namen[this.stellungen.indexOf(s)], art: "Kippschalter" } }));
      this.dispatchEvent(new CustomEvent("input", { bubbles: true }));
    }
    zeigen() {
      const i = this.stellungen.indexOf(this.getAttribute("stellung"));
      if (this.stellungen.length === 3) { this.knopf.setAttribute("aria-valuenow", String(i)); this.knopf.setAttribute("aria-valuetext", this.namen[i]); }
      else this.knopf.setAttribute("aria-checked", String(i === 0));
      this.querySelectorAll(".ak-kipp-text").forEach((t) => t.classList.toggle("an", t.classList.contains(this.getAttribute("stellung"))));
    }
  }

  // ─── Wahltasten und Schiebeschalter: genau eine Wahl, Pfeiltasten wandern ───
  class Wahl extends HTMLElement {
    connectedCallback() {
      if (this.knoepfe) return;
      const optionen = attr(this, "optionen", "I|II").split("|");
      if (this.hasAttribute("farbe")) this.style.setProperty("--farbe", `var(--led-${this.getAttribute("farbe")})`);
      const name = attr(this, "name", "");
      this.innerHTML = `${name ? `<span class="ak-etikett">${name}</span>` : ""}<div class="ak-wahl-reihe" role="radiogroup" aria-label="${name || "Wahl"}" style="--n:${optionen.length}">
        ${this.getAttribute("art") === "schiebe" ? `<span class="ak-wahl-schieber"></span>` : ""}${optionen.map((o) => `<button type="button" role="radio">${o}</button>`).join("")}</div>`;
      this.knoepfe = [...this.querySelectorAll("button")];
      this.optionen = optionen;
      hilfe(this, this.querySelector(".ak-wahl-reihe"));
      this.knoepfe.forEach((k, i) => {
        k.addEventListener("click", () => this.waehlen(i));
        k.addEventListener("keydown", (e) => {
          const n = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
          if (!n) return;
          e.preventDefault();
          const j = (i + n + optionen.length) % optionen.length;
          this.waehlen(j); this.knoepfe[j].focus();
        });
      });
      this.waehlen(Math.max(0, optionen.indexOf(attr(this, "wert", optionen[0]))), true);
    }
    waehlen(i, still = false) {
      this.setAttribute("wert", this.optionen[i]);
      this.style.setProperty("--i", i);
      this.querySelector(".ak-wahl-schieber")?.style.setProperty("--i", i);
      this.knoepfe.forEach((k, j) => { k.setAttribute("aria-checked", String(i === j)); k.tabIndex = i === j ? 0 : -1; });
      if (!still) {
        document.dispatchEvent(new CustomEvent("ak-eingabe", { detail: { name: attr(this, "name", "Wahl"), text: this.optionen[i], art: "Wahl" } }));
        this.dispatchEvent(new CustomEvent("input", { bubbles: true }));
      }
    }
  }

  // ─── Leuchte ───
  class Leuchte extends HTMLElement {
    static observedAttributes = ["zustand", "farbe"];
    connectedCallback() {
      if (!this.firstElementChild) {
        const text = attr(this, "text", "");
        this.innerHTML = `<span class="ak-led-licht"></span>${text ? `<span class="ak-led-text">${text}</span>` : ""}`;
      }
      this.setAttribute("role", "img");
      hilfe(this);
      this.attributeChangedCallback();
    }
    attributeChangedCallback() {
      if (this.hasAttribute("farbe")) this.style.setProperty("--farbe", `var(--led-${this.getAttribute("farbe")})`);
      const z = attr(this, "zustand", "aus");
      this.setAttribute("aria-label", `${attr(this, "text", "Leuchte")}: ${{ an: "an", aus: "aus", blinkt: "blinkt", atmet: "pulsiert", flackert: "flackert" }[z] ?? z}`);
    }
  }

  customElements.define("ak-dreh", Drehregler);
  customElements.define("ak-schieber", Schieber);
  customElements.define("ak-taster", Taster);
  customElements.define("ak-kipp", Kippschalter);
  customElements.define("ak-wahl", Wahl);
  customElements.define("ak-led", Leuchte);
  window.Appkern = Object.assign(window.Appkern || {}, { Wert, zahl });
})();
