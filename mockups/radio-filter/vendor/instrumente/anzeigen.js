// Entwurf RAD-3 (RadioHub, Radio mit Filterung): Kopie aus hifi-regler/appkern/anzeigen.js, Stand hifi-regler 9a7c0fe vom 09.11.2026.
// Laut Plan RAD-1 (Entscheidung 7) wandert die Vorlage HiFi samt Instrumenten in den Appkern; dann kommt diese Datei von
// dort. Im Entwurf unverändert lassen, eigene Regeln stehen in radio-marken.css und radio-bausteine.css.
// Anzeigen des Appkerns: Segmentanzeigen (7 und 14 Segmente, Punktmatrix), Zeigerinstrumente, Pegel und
// Schirme (Wellenform, LFO, Spektrum, Hüllkurve, Take). Alles Bewegte hängt an einem Takt: ein requestAnimationFrame für
// die ganze Seite, nur für Anzeigen im Bild (IntersectionObserver), Pause bei verdecktem Tab, bei reduzierter Bewegung
// höchstens acht Bilder je Sekunde. Pegel und Schirme zeichnen in eine Leinwand (ein Bild je Takt, keine Stilberechnung),
// Segmente und Zeiger ändern nur Klassen und transform. Die Beispieldaten liefert eine Quelle: ein sprachähnliches
// Signal (Silben, Tonhöhe mit Vibrato, wandernde Formanten), deterministisch, damit Bilder vergleichbar bleiben.

(() => {
  "use strict";
  const attr = (el, n, v) => (el.hasAttribute(n) ? el.getAttribute(n) : v);
  const num = (el, n, v) => (el.hasAttribute(n) ? parseFloat(el.getAttribute(n)) : v);
  const ns = "http://www.w3.org/2000/svg";
  /** Erklärung im Hover wie bei den Reglern (instrumente.js): die Beschriftung bleibt der Fachbegriff */
  const hilfe = (el) => { if (el.hasAttribute("hilfe")) { el.title = el.getAttribute("hilfe"); el.setAttribute("aria-description", el.getAttribute("hilfe")); } };

  // ═══ Takt ═══
  const ruhig = matchMedia("(prefers-reduced-motion: reduce)");
  const Takt = {
    teilnehmer: new Set(), sichtbar: new Set(), laeuft: false, letztes: 0, bild: 0, messung: null,
    beobachter: new IntersectionObserver((eintraege) => {
      for (const e of eintraege) (e.isIntersecting ? Takt.sichtbar.add(e.target) : Takt.sichtbar.delete(e.target));
      Takt.wecken();
    }, { rootMargin: "120px" }),
    anmelden(el) { this.teilnehmer.add(el); this.beobachter.observe(el); },
    abmelden(el) { this.teilnehmer.delete(el); this.sichtbar.delete(el); this.beobachter.unobserve(el); },
    wecken() { if (!this.laeuft && this.sichtbar.size && !document.hidden) { this.laeuft = true; requestAnimationFrame((t) => this.schlag(t)); } },
    schlag(t) {
      if (!this.sichtbar.size || document.hidden) { this.laeuft = false; return; }
      const dt = Math.min(0.1, (t - (this.letztes || t)) / 1000);
      if (!ruhig.matches || t - this.letztes > 125) {
        this.letztes = t; this.bild++;
        const t0 = performance.now();
        for (const el of this.sichtbar) el.schritt?.(t / 1000, dt);
        if (this.messung) this.messung.skript += performance.now() - t0;
      }
      requestAnimationFrame((x) => this.schlag(x));
    },
    /** Leuchtstärke und Thema ändern sich selten: Leinwände lesen sie neu, wenn das Wurzelelement sich ändert */
    stand: 0,
  };
  new MutationObserver(() => { Takt.stand++; }).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme", "data-effekte", "data-vorlage"] });
  document.addEventListener("visibilitychange", () => Takt.wecken());

  // ═══ Quelle: sprachähnliches Signal ═══
  const Quelle = (() => {
    let saat = 7;
    const zufall = () => { saat = (saat * 16807) % 2147483647; return (saat - 1) / 2147483646; };
    const silben = [];           // [beginn, dauer, stärke]
    let ende = 0;
    const silbenBis = (t) => { while (ende < t + 2) { const pause = 0.04 + zufall() * (zufall() < 0.15 ? 0.6 : 0.16); const dauer = 0.11 + zufall() * 0.2;
      silben.push([ende + pause, dauer, 0.45 + zufall() * 0.55]); ende += pause + dauer; } while (silben.length && silben[0][0] + silben[0][1] < t - 3) silben.shift(); };
    const huelle = (t) => { silbenBis(t); let h = 0; for (const [b, d, s] of silben) { if (t < b - 0.03 || t > b + d + 0.08) continue;
      const x = t < b ? (t - b + 0.03) / 0.03 : t > b + d ? 1 - (t - b - d) / 0.08 : 1; h = Math.max(h, s * Math.sin(Math.min(1, x) * Math.PI / 2)); } return h; };
    const FORMANTEN = (t) => [520 + 220 * Math.sin(t * 7.1) + 90 * Math.sin(t * 2.3), 1450 + 520 * Math.sin(t * 5.3 + 1.2), 2550 + 260 * Math.sin(t * 3.1 + 0.4)];
    const verstaerkung = (f, F) => 0.035 + Math.exp(-(((f - F[0]) / 160) ** 2)) + 0.6 * Math.exp(-(((f - F[1]) / 220) ** 2)) + 0.35 * Math.exp(-(((f - F[2]) / 300) ** 2));
    let stand = -1, werte = null;
    const BAENDER = Array.from({ length: 31 }, (_, i) => 20 * Math.pow(2, i / 3));
    return {
      BAENDER,
      jetzt(t) {
        const b = Takt.bild;
        if (stand === b && werte) return werte;
        stand = b;
        const h = huelle(t), f0 = 132 + 16 * Math.sin(t * 4.4) + 22 * Math.sin(t * 0.9), F = FORMANTEN(t);
        const rausch = 0.012 + 0.006 * Math.sin(t * 13);
        const pegel = (x) => 20 * Math.log10(Math.max(1e-4, x));
        werte = {
          t, huelle: h, f0, F,
          links: pegel(h * 0.42 + rausch), rechts: pegel(h * 0.36 + rausch * 0.9),
          spitzeL: pegel(Math.min(1, h * 0.75 + rausch)), spitzeR: pegel(Math.min(1, h * 0.66 + rausch)),
          spektrum: BAENDER.map((f) => { let g = 0; if (f > f0 * 0.7) g = verstaerkung(f, F) * (f < 6000 ? 1 : Math.exp(-(f - 6000) / 3000));
            return pegel(h * 0.55 * g + 0.0012 * (1 + Math.sin(f * 0.01 + t * 9))); }),
          probe: (x) => { let s = 0; for (let k = 1; k <= 14; k++) s += (verstaerkung(k * f0, F) / k ** 0.35) * Math.sin(2 * Math.PI * k * x + k * 0.6); return s * h * 0.42; },
        };
        return werte;
      },
      /** Übersicht eines Takes: 600 Spitzenwerte aus demselben Silbenmodell */
      take: (() => { let liste = null; return () => (liste ??= Array.from({ length: 600 }, (_, i) => Math.min(1, huelle(40 + i * 0.03) * 0.95 + 0.02))); })(),
    };
  })();

  // ═══ Segmentschriften ═══
  const T = 8, G = 1.4;  // Strichstärke und Fuge in Einheiten der Zeichenzelle
  const waag = (x1, x2, y) => `${x1},${y} ${x1 + T / 2},${y - T / 2} ${x2 - T / 2},${y - T / 2} ${x2},${y} ${x2 - T / 2},${y + T / 2} ${x1 + T / 2},${y + T / 2}`;
  const senk = (x, y1, y2) => `${x},${y1} ${x + T / 2},${y1 + T / 2} ${x + T / 2},${y2 - T / 2} ${x},${y2} ${x - T / 2},${y2 - T / 2} ${x - T / 2},${y1 + T / 2}`;
  const schraeg = (x1, y1, x2, y2, b = 3.4) => { const l = Math.hypot(x2 - x1, y2 - y1), nx = (-(y2 - y1) / l) * b, ny = ((x2 - x1) / l) * b;
    return `${x1 + nx},${y1 + ny} ${x2 + nx},${y2 + ny} ${x2 - nx},${y2 - ny} ${x1 - nx},${y1 - ny}`; };
  const SIEBEN = (() => { const L = 8, R = 50, O = 6, M = 50, U = 94;
    return { breite: 62, oben: 0, hoehe: 100, teile: { a: waag(L + G, R - G, O), b: senk(R, O + G, M - G), c: senk(R, M + G, U - G), d: waag(L + G, R - G, U),
      e: senk(L, M + G, U - G), f: senk(L, O + G, M - G), g: waag(L + G, R - G, M) }, punkt: [57.5, 94] }; })();
  const VIERZEHN = (() => { const L = 8, R = 52, O = 6, M = 50, U = 94, C = 30, h = T / 2 + G + 1.5;
    return { breite: 64, oben: -13, hoehe: 113, teile: { a: waag(L + G, R - G, O), b: senk(R, O + G, M - G), c: senk(R, M + G, U - G), d: waag(L + G, R - G, U),
      e: senk(L, M + G, U - G), f: senk(L, O + G, M - G), g1: waag(L + G, C - G, M), g2: waag(C + G, R - G, M), i: senk(C, O + G, M - G), l: senk(C, M + G, U - G),
      h: schraeg(L + h, O + h, C - h, M - h), j: schraeg(R - h, O + h, C + h, M - h), k: schraeg(C - h, M + h, L + h, U - h), m: schraeg(C + h, M + h, R - h, U - h) },
      punkt: [59.5, 94], tuepfel: [[C - 10, -6], [C + 10, -6]] }; })();
  const ZEICHEN7 = { 0: "abcdef", 1: "bc", 2: "abdeg", 3: "abcdg", 4: "bcfg", 5: "acdfg", 6: "acdefg", 7: "abc", 8: "abcdefg", 9: "abcdfg", "-": "g", " ": "",
    A: "abcefg", B: "cdefg", C: "adef", D: "bcdeg", E: "adefg", F: "aefg", H: "bcefg", L: "def", O: "abcdef", P: "abefg", R: "eg", S: "acdfg", T: "defg", U: "bcdef", N: "ceg", "_": "d" };
  const ZEICHEN14 = { 0: "abcdefjk", 1: "bcj", 2: "abdeg1g2", 3: "abcdg2", 4: "bcfg1g2", 5: "acdfg1g2", 6: "acdefg1g2", 7: "abc", 8: "abcdefg1g2", 9: "abcdfg1g2",
    A: "abcefg1g2", B: "abcdg2il", C: "adef", D: "abcdil", E: "adefg1", F: "aefg1", G: "acdefg2", H: "bcefg1g2", I: "adil", J: "bcde", K: "efg1jm", L: "def", M: "bcefhj",
    N: "bcefhm", O: "abcdef", P: "abefg1g2", Q: "abcdefm", R: "abefg1g2m", S: "acdfg1g2", T: "ail", U: "bcdef", V: "efkj", W: "bcefkm", X: "hjkm", Y: "hjl", Z: "adjk",
    "Ä": "abcefg1g2u", "Ö": "abcdefu", "Ü": "bcdefu", "ß": "abcdg2il", " ": "", "-": "g1g2", "+": "g1g2il", "/": "jk", "%": "cfjkg1g2", "'": "i", "*": "g1g2hijklm" };
  const MATRIX = { 0: [14, 17, 19, 21, 25, 17, 14], 1: [4, 12, 4, 4, 4, 4, 14], 2: [14, 17, 1, 2, 4, 8, 31], 3: [31, 2, 4, 2, 1, 17, 14], 4: [2, 6, 10, 18, 31, 2, 2],
    5: [31, 16, 30, 1, 1, 17, 14], 6: [6, 8, 16, 30, 17, 17, 14], 7: [31, 1, 2, 4, 8, 8, 8], 8: [14, 17, 17, 14, 17, 17, 14], 9: [14, 17, 17, 15, 1, 2, 12],
    A: [14, 17, 17, 17, 31, 17, 17], B: [30, 17, 17, 30, 17, 17, 30], C: [14, 17, 16, 16, 16, 17, 14], D: [28, 18, 17, 17, 17, 18, 28], E: [31, 16, 16, 30, 16, 16, 31],
    F: [31, 16, 16, 30, 16, 16, 16], G: [14, 17, 16, 23, 17, 17, 15], H: [17, 17, 17, 31, 17, 17, 17], I: [14, 4, 4, 4, 4, 4, 14], J: [7, 2, 2, 2, 2, 18, 12],
    K: [17, 18, 20, 24, 20, 18, 17], L: [16, 16, 16, 16, 16, 16, 31], M: [17, 27, 21, 21, 17, 17, 17], N: [17, 17, 25, 21, 19, 17, 17], O: [14, 17, 17, 17, 17, 17, 14],
    P: [30, 17, 17, 30, 16, 16, 16], Q: [14, 17, 17, 17, 21, 18, 13], R: [30, 17, 17, 30, 20, 18, 17], S: [15, 16, 16, 14, 1, 1, 30], T: [31, 4, 4, 4, 4, 4, 4],
    U: [17, 17, 17, 17, 17, 17, 14], V: [17, 17, 17, 17, 17, 10, 4], W: [17, 17, 17, 21, 21, 21, 10], X: [17, 17, 10, 4, 10, 17, 17], Y: [17, 17, 17, 10, 4, 4, 4],
    Z: [31, 1, 2, 4, 8, 16, 31], "Ä": [10, 0, 14, 17, 31, 17, 17], "Ö": [10, 0, 14, 17, 17, 17, 14], "Ü": [10, 0, 17, 17, 17, 17, 14], "ß": [14, 17, 17, 22, 17, 17, 22],
    " ": [0, 0, 0, 0, 0, 0, 0], ".": [0, 0, 0, 0, 0, 12, 12], ",": [0, 0, 0, 0, 12, 4, 8], ":": [0, 12, 12, 0, 12, 12, 0], "-": [0, 0, 0, 31, 0, 0, 0],
    "%": [24, 25, 2, 4, 8, 19, 3], "/": [0, 1, 2, 4, 8, 16, 0], "+": [0, 4, 4, 31, 4, 4, 0], "·": [0, 0, 0, 4, 0, 0, 0] };
  const teileVon = (s) => s.match(/g1|g2|[a-mu]/g) ?? [];

  /** Text in Zellen zerlegen: Punkt und Doppelpunkt hängen an der Zelle davor (wie bei echten Anzeigen) */
  function zellen(text, art) {
    const z = [];
    for (const ch of text.toUpperCase()) {
      if ((ch === "." || ch === ",") && art !== "punkt" && z.length && !z.at(-1).punkt) { z.at(-1).punkt = true; continue; }
      if (ch === ":" && art === "7") { z.push({ ch: ":", doppel: true }); continue; }
      z.push({ ch });
    }
    return z;
  }

  class Segmente extends HTMLElement {
    static observedAttributes = ["text"];
    connectedCallback() {
      if (this.glas) return;
      this.art = attr(this, "art", "7");
      this.stellen = num(this, "stellen", 4);
      if (this.hasAttribute("farbe")) this.style.setProperty("--farbe", `var(--led-${this.getAttribute("farbe")})`);
      this.setAttribute("role", "img");
      hilfe(this);
      this.innerHTML = `<div class="ak-glas ak-segmente-glas"></div>`;
      this.glas = this.firstElementChild;
      this.lauf = num(this, "lauf", 0);
      this.zeigen(attr(this, "text", ""));
      if (this.lauf) Takt.anmelden(this);
    }
    attributeChangedCallback(_, alt, neu) { if (this.glas && alt !== neu) this.zeigen(neu); }
    set text(t) { this.setAttribute("text", t); }
    get text() { return attr(this, "text", ""); }
    schritt(t) {
      if (!this.langtext) return;
      const i = Math.floor(t / (this.lauf / 1000)) % (this.langtext.length + 1);
      if (i !== this.laufstand) { this.laufstand = i; this.malen((this.langtext + " ").repeat(2).slice(i, i + this.stellen)); }
    }
    zeigen(text) {
      this.setAttribute("aria-label", text);
      if (this.lauf && text.length > this.stellen) { this.langtext = text + "   "; this.laufstand = -1; return; }
      this.langtext = null;
      this.malen(text);
    }
    /** Zellen anlegen, wenn sich ihre Zahl oder Art ändert; sonst nur Klassen umschalten */
    malen(text) {
      const art = this.art;
      let liste = zellen(text, art);
      // rechtsbündig wie ein Zählwerk (7 Segmente), sonst linksbündig
      const anzahl = this.stellen + liste.filter((z) => z.doppel).length;
      if (art === "7") liste = [...Array(Math.max(0, anzahl - liste.length)).fill({ ch: " " }), ...liste].slice(-anzahl);
      else liste = [...liste, ...Array(Math.max(0, anzahl - liste.length)).fill({ ch: " " })].slice(0, anzahl);
      const form = liste.map((z) => (z.doppel ? ":" : "z")).join("");
      if (form !== this.form) {
        this.form = form; this.anlegen(liste);
        // Breite in Stellen: ein Doppelpunkt ist schmaler als eine Ziffer
        const doppel = liste.filter((z) => z.doppel).length;
        this.style.setProperty("--stellen", (liste.length - doppel + doppel * (0.22 / 0.62)).toFixed(3));
      }
      liste.forEach((z, i) => this.setzen(this.svgs[i], z));
    }
    anlegen(liste) {
      const art = this.art;
      this.glas.textContent = "";
      this.svgs = liste.map((z) => {
        const svg = document.createElementNS(ns, "svg");
        svg.setAttribute("aria-hidden", "true");
        if (z.doppel) {
          svg.setAttribute("viewBox", "0 0 22 100");
          svg.innerHTML = `<g transform="skewX(-6) translate(6 0)"><circle class="schein" cx="11" cy="33" r="5"/><circle class="schein" cx="11" cy="67" r="5"/><circle cx="11" cy="33" r="5"/><circle cx="11" cy="67" r="5"/></g>`;
          svg.teile = { ":": [...svg.querySelectorAll("circle")] };
        } else if (art === "punkt") {
          svg.setAttribute("viewBox", "0 0 6 8");   // fünf Punkte und eine Lücke breit, sieben und eine hoch: 0,75
          let html = "";
          for (let r = 0; r < 7; r++) for (let c = 0; c < 5; c++) html += `<circle class="aus" data-p="${r * 5 + c}" cx="${c + 0.5}" cy="${r + 0.5}" r=".42"/>`;
          svg.innerHTML = html;
          svg.punkte = [...svg.children];
        } else {
          const f = art === "14" ? VIERZEHN : SIEBEN;
          svg.setAttribute("viewBox", `0 ${f.oben} ${f.breite} ${f.hoehe}`);
          const teile = Object.entries(f.teile);
          svg.innerHTML = `<g transform="skewX(-6) translate(6 0)">${teile.map(([n, p]) => `<polygon class="schein" data-t="${n}" points="${p}"/>`).join("")}
            ${teile.map(([n, p]) => `<polygon class="aus" data-t="${n}" points="${p}"/>`).join("")}
            <circle class="schein" data-t="p" cx="${f.punkt[0]}" cy="${f.punkt[1]}" r="4.2"/><circle class="aus" data-t="p" cx="${f.punkt[0]}" cy="${f.punkt[1]}" r="4.2"/>
            ${f.tuepfel ? f.tuepfel.map(([x, y]) => `<circle class="schein" data-t="u" cx="${x}" cy="${y}" r="3.6"/><circle class="aus" data-t="u" cx="${x}" cy="${y}" r="3.6"/>`).join("") : ""}</g>`;
          svg.teile = {};
          for (const el of svg.querySelectorAll("[data-t]")) (svg.teile[el.dataset.t] ??= []).push(el);
        }
        this.glas.append(svg);
        return svg;
      });
    }
    setzen(svg, z) {
      if (z.doppel) { svg.teile[":"].forEach((e) => e.classList.add("an")); return; }
      if (this.art === "punkt") {
        const zeilen = MATRIX[z.ch] ?? MATRIX[" "];
        svg.punkte.forEach((p, i) => { const an = (zeilen[Math.floor(i / 5)] >> (4 - (i % 5))) & 1; p.classList.toggle("an", !!an); p.classList.toggle("aus", !an); });
        return;
      }
      const an = new Set(teileVon((this.art === "14" ? ZEICHEN14 : ZEICHEN7)[z.ch] ?? ""));
      if (z.punkt) an.add("p");
      for (const [n, liste] of Object.entries(svg.teile)) {
        const ein = an.has(n);
        for (const el of liste) el.classList.toggle("an", ein), el.classList.contains("schein") || el.classList.toggle("aus", !ein);
      }
    }
  }

  // ═══ Zeigerinstrument: Aussteuerung (VU) oder Stimmgerät ═══
  const ZEIGER_ARTEN = {
    vu: { name: "VU", von: -40, bis: 40, marken: [-20, -10, -7, -5, -3, -2, -1, 0, 1, 2, 3], zahlen: [-20, -10, -7, -5, -3, 0, 3], haupt: [-20, 0, 3], rot: 0,
          lage: (db) => { const v = (x) => Math.pow(10, x / 20); return (v(db) - v(-20)) / (v(3) - v(-20)); } },
    stimmen: { name: "Cent", von: -40, bis: 40, marken: [-50, -40, -30, -20, -10, 0, 10, 20, 30, 40, 50], zahlen: [-50, -25, 0, 25, 50], haupt: [-50, 0, 50], rot: null, lage: (c) => (c + 50) / 100 },
  };
  class Zeiger extends HTMLElement {
    connectedCallback() {
      if (this.nadel) return;
      const a = ZEIGER_ARTEN[attr(this, "art", "vu")];
      this.a = a; this.kanal = attr(this, "kanal", "links");
      const px = (r, w) => [80 + r * Math.sin((w * Math.PI) / 180), 118 - r * Math.cos((w * Math.PI) / 180)];
      const winkel = (x) => a.von + Math.min(1, Math.max(0, a.lage(x))) * (a.bis - a.von);
      const linie = (x, r1, r2, k) => { const [x1, y1] = px(r1, winkel(x)), [x2, y2] = px(r2, winkel(x)); return `<line class="strich${k}" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`; };
      const [bx1, by1] = px(88, a.von), [bx2, by2] = px(88, a.bis);
      const rotVon = a.rot !== null ? winkel(a.rot) : null;
      const [rx1, ry1] = rotVon !== null ? px(91, rotVon) : [0, 0], [rx2, ry2] = px(91, a.bis);
      const zahl = (z) => (z > 0 ? `+${z}` : `${z}`);
      this.innerHTML = `<div class="ak-glas ak-zeiger-fenster">
        <svg viewBox="0 0 160 100" aria-hidden="true"><path class="bogen" d="M${bx1} ${by1}A88 88 0 0 1 ${bx2} ${by2}"/>
          ${rotVon !== null ? `<path class="rot" d="M${rx1} ${ry1}A91 91 0 0 1 ${rx2} ${ry2}"/>` : ""}
          ${a.marken.map((m) => linie(m, a.zahlen.includes(m) ? 82 : 85, 92, a.rot !== null && m > a.rot ? " rot" : "")).join("")}</svg>
        ${a.zahlen.map((z) => { const [x, y] = px(101, winkel(z)); return `<span class="ak-zeiger-zahl${a.rot !== null && z > a.rot ? " rot" : ""}${a.haupt.includes(z) ? "" : " neben"}" style="left:${(x / 1.6).toFixed(2)}%;top:${y.toFixed(2)}%">${zahl(z)}</span>`; }).join("")}
        <span class="ak-zeiger-name">${attr(this, "beschriftung", a.name)}</span>
        <div class="ak-zeiger-nadel"></div><div class="ak-zeiger-nabe"></div>
        ${this.hasAttribute("spitze") ? `<ak-led class="ak-zeiger-spitze" farbe="rot" groesse="klein"></ak-led>` : ""}</div>`;
      this.nadel = this.querySelector(".ak-zeiger-nadel");
      this.spitze = this.querySelector(".ak-zeiger-spitze");
      this.winkel = winkel; this.th = a.von; this.om = 0;
      this.setAttribute("role", "img");
      this.setAttribute("aria-label", attr(this, "beschriftung", a.name));
      hilfe(this);
      Takt.anmelden(this);
    }
    schritt(t, dt) {
      const q = Quelle.jetzt(t);
      let ziel;
      if (attr(this, "art", "vu") === "stimmen") ziel = this.winkel(18 * Math.sin(t * 0.5) + 6 * Math.sin(t * 2.7) + 3 * Math.sin(t * 11));
      else ziel = this.winkel(q[this.kanal] + 18 + 3 * q.huelle);   // Aussteuerung: digitaler Pegel um 18 dB angehoben (Bezugspegel)
      // Masse und Feder: Eigenfrequenz 2 Hz, gedämpft 0,8 (leichtes Überschwingen wie ein echtes Drehspulinstrument)
      const k = (2 * Math.PI * 2) ** 2, c = 2 * 0.8 * 2 * Math.PI * 2;
      for (let n = 0, h = dt / 4; n < 4; n++) { this.om += (k * (ziel - this.th) - c * this.om) * h; this.th += this.om * h; }
      this.nadel.style.setProperty("--zeiger-winkel", `${this.th.toFixed(2)}deg`);
      if (this.spitze) { const ueber = this.th > this.winkel(0); if (ueber !== this.ueber) { this.ueber = ueber; this.spitze.setAttribute("zustand", ueber ? "an" : "aus"); } }
    }
  }

  // ═══ Leinwand: Größe nach dem Kasten, Pixel nach der Bildschirmdichte ═══
  class Leinwand extends HTMLElement {
    leinwandBauen(glas) {
      this.cv = document.createElement("canvas");
      this.cv.setAttribute("aria-hidden", "true");
      glas.append(this.cv);
      this.ctx = this.cv.getContext("2d");
      new ResizeObserver(() => this.groesse()).observe(this.cv);
      this.farbenStand = -1;
      Takt.anmelden(this);
    }
    groesse() {
      const r = this.cv.getBoundingClientRect(), d = Math.min(2, devicePixelRatio || 1);
      this.b = Math.max(1, Math.round(r.width)); this.h = Math.max(1, Math.round(r.height));
      this.cv.width = Math.round(this.b * d); this.cv.height = Math.round(this.h * d);
      this.ctx.setTransform(d, 0, 0, d, 0, 0);
      this.farbenStand = -1;
    }
    farben() {
      if (this.farbenStand === Takt.stand) return;
      this.farbenStand = Takt.stand;
      const s = getComputedStyle(this);
      this.f = { farbe: s.getPropertyValue("--farbe").trim() || "#5ff2ff", glas: s.getPropertyValue("--ak-glas").trim() || "#07090c",
                 gut: s.getPropertyValue("--pegel-gut").trim(), warn: s.getPropertyValue("--pegel-warn").trim(), spitze: s.getPropertyValue("--pegel-spitze").trim(),
                 leuchten: parseFloat(s.getPropertyValue("--ak-leuchten")) || 0.35 };
    }
    /** leuchtende Linie ohne Weichzeichner: zweimal breit und blass, einmal schmal und hell */
    linie(pfad, farbe, breite = 1.8) {
      const c = this.ctx, l = this.f.leuchten;
      c.lineJoin = "round"; c.lineCap = "round"; c.strokeStyle = farbe;
      c.globalAlpha = 0.1 * l; c.lineWidth = breite * 5; c.stroke(pfad);
      c.globalAlpha = 0.24 * l; c.lineWidth = breite * 2.6; c.stroke(pfad);
      c.globalAlpha = 1; c.lineWidth = breite; c.stroke(pfad);
    }
    raster(nx, ny) {
      const c = this.ctx; c.globalAlpha = 1; c.strokeStyle = "rgba(160, 190, 220, .09)"; c.lineWidth = 1; c.beginPath();
      for (let i = 1; i < nx; i++) { const x = Math.round((i * this.b) / nx) + 0.5; c.moveTo(x, 0); c.lineTo(x, this.h); }
      for (let i = 1; i < ny; i++) { const y = Math.round((i * this.h) / ny) + 0.5; c.moveTo(0, y); c.lineTo(this.b, y); }
      c.stroke();
    }
  }

  // ═══ Pegel: LED-Kette, Leuchtbalken, Pegelminderung ═══
  class Pegel extends Leinwand {
    connectedCallback() {
      if (this.cv) return;
      this.art = attr(this, "art", "kette");
      this.kanaele = num(this, "kanaele", 2);
      this.senkrecht = attr(this, "richtung", "waagrecht") === "senkrecht";
      this.n = num(this, "segmente", this.senkrecht ? 24 : 32);
      this.von = num(this, "von", this.art === "gr" ? -24 : -48); this.bis = num(this, "bis", 0);
      if (this.hasAttribute("farbe")) this.style.setProperty("--farbe", `var(--led-${this.getAttribute("farbe")})`);
      const skala = attr(this, "skala", this.art === "gr" ? "0|-6|-12|-18|-24" : "-48|-36|-24|-12|-6|0");
      this.innerHTML = `<div class="ak-glas ak-pegel-glas"></div>${skala ? `<div class="ak-pegel-skala" aria-hidden="true">${skala.split("|").map((s) => `<span>${s}</span>`).join("")}</div>` : ""}`;
      this.setAttribute("role", "img");
      this.setAttribute("aria-label", attr(this, "beschriftung", "Pegel"));
      hilfe(this);
      this.stand = [this.von, this.von]; this.halten = [{ w: this.von, t: 0 }, { w: this.von, t: 0 }];
      this.leinwandBauen(this.firstElementChild);
    }
    schritt(t, dt) {
      this.farben();
      const q = Quelle.jetzt(t), c = this.ctx, f = this.f;
      const ziele = this.art === "gr" ? [-Math.max(0, (q.links + 20) * 0.6)] : this.hasAttribute("wert") ? [num(this, "wert", 0)] : [q.spitzeL, q.spitzeR];
      // Anstieg sofort, Rückgang 24 dB je Sekunde; Spitze 1,2 Sekunden halten, dann fallen
      for (let k = 0; k < this.kanaele; k++) {
        const z = Math.min(this.bis, ziele[k] ?? ziele[0]);
        if (this.art === "gr") this.stand[k] = z < this.stand[k] ? z : Math.min(0, this.stand[k] + 30 * dt);
        else this.stand[k] = z > this.stand[k] ? z : Math.max(this.von, this.stand[k] - 24 * dt);
        const h = this.halten[k];
        if (this.stand[k] >= h.w || t - h.t > 1.2) { if (this.stand[k] >= h.w) { h.w = this.stand[k]; h.t = t; } else h.w = Math.max(this.von, h.w - 20 * dt); }
      }
      c.globalAlpha = 1; c.clearRect(0, 0, this.b, this.h);
      const lang = this.senkrecht ? this.h : this.b, quer = this.senkrecht ? this.b : this.h;
      const spur = (quer - (this.kanaele - 1) * 3) / this.kanaele, n = this.n, fuge = this.art === "balken" ? 0 : 2, seg = (lang - (n - 1) * fuge) / n;
      const lage = (db) => (db - this.von) / (this.bis - this.von);
      const farbeVon = (i) => { if (this.art === "gr") return f.farbe; const db = this.von + ((i + 0.5) / n) * (this.bis - this.von);
        return db >= -3 ? f.spitze : db >= -12 ? f.warn : this.art === "balken" ? f.farbe : f.gut; };
      const rechteck = (k, i, x0 = 0) => { const a = i * (seg + fuge) + x0, b = k * (spur + 3);
        return this.senkrecht ? [b, this.h - a - seg, spur, seg] : [a, b, seg, spur]; };
      for (let k = 0; k < this.kanaele; k++) {
        const an = this.art === "gr" ? Math.round((1 - lage(this.stand[k])) * n) : Math.round(lage(this.stand[k]) * n);
        const spitze = Math.min(n - 1, Math.floor(lage(this.halten[k].w) * n));
        for (let i = 0; i < n; i++) {
          const index = this.art === "gr" ? n - 1 - i : i;   // Pegelminderung wächst von oben (0 dB) nach unten
          const leuchtet = i < an;
          const [x, y, w, hh] = rechteck(k, index);
          c.fillStyle = farbeVon(index);
          c.globalAlpha = leuchtet ? 1 : 0.1;
          c.fillRect(x, y, w, hh);
          if (leuchtet && f.leuchten > 0.05) { c.globalAlpha = 0.22 * f.leuchten; c.fillRect(x - 1.5, y - 1.5, w + 3, hh + 3); }
        }
        if (this.art !== "gr" && spitze > 0 && spitze >= an) { const [x, y, w, hh] = rechteck(k, spitze); c.globalAlpha = 1; c.fillStyle = farbeVon(spitze); c.fillRect(x, y, w, hh); }
      }
      c.globalAlpha = 1;
    }
  }

  // ═══ Schirm: Wellenform, LFO, Spektrum, Hüllkurve, Take ═══
  class Schirm extends Leinwand {
    connectedCallback() {
      if (this.cv) return;
      this.art = attr(this, "art", "welle");
      if (this.hasAttribute("farbe")) this.style.setProperty("--farbe", `var(--led-${this.getAttribute("farbe")})`);
      if (this.hasAttribute("verhaeltnis")) this.style.setProperty("--verhaeltnis", this.getAttribute("verhaeltnis"));
      const fuss = attr(this, "fuss", "");
      this.innerHTML = `<div class="ak-glas ak-schirm-glas"></div>${fuss ? `<div class="ak-schirm-fuss" aria-hidden="true">${fuss.split("|").map((s) => `<span>${s}</span>`).join("")}</div>` : ""}`;
      this.setAttribute("role", "img");
      this.setAttribute("aria-label", attr(this, "beschriftung", "Schirm"));
      hilfe(this);
      this.spitzen = Quelle.BAENDER.map(() => -90);
      this.leinwandBauen(this.firstElementChild);
    }
    regler(name) { const sel = this.getAttribute(name); return sel ? document.querySelector(sel) : null; }
    schritt(t, dt) {
      this.farben();
      const c = this.ctx, b = this.b, h = this.h, f = this.f, q = Quelle.jetzt(t);
      c.globalAlpha = 1;
      if (this.art === "welle") { c.fillStyle = f.glas; c.globalAlpha = 0.42; c.fillRect(0, 0, b, h); c.globalAlpha = 1; }   // Nachleuchten des Phosphors
      else c.clearRect(0, 0, b, h);
      this.raster(this.art === "spektrum" || this.art === "linie" ? 10 : 8, 4);
      const p = new Path2D();
      if (this.art === "welle") {
        for (let x = 0; x <= b; x += 2) { const y = h / 2 - q.probe((x / b) * 2.5) * h * 0.42; x ? p.lineTo(x, y) : p.moveTo(x, y); }
        this.linie(p, f.farbe);
      } else if (this.art === "lfo") {
        const tempo = this.regler("tempo")?.wert ?? 1.2, tiefe = (this.regler("tiefe")?.anteil ?? 0.7);
        this.phase = ((this.phase ?? 0) + dt * tempo) % 1;
        for (let x = 0; x <= b; x += 2) { const y = h / 2 - Math.sin(((x / b) * 2 + this.phase) * 2 * Math.PI) * h * 0.38 * tiefe; x ? p.lineTo(x, y) : p.moveTo(x, y); }
        this.linie(p, f.farbe, 2.2);
        const yp = h / 2 - Math.sin(this.phase * 2 * Math.PI) * h * 0.38 * tiefe;
        c.fillStyle = "#fff"; c.globalAlpha = 1; c.beginPath(); c.arc(4, yp, 3.5, 0, 7); c.fill();
      } else if (this.art === "spektrum" || this.art === "linie") {
        const n = q.spektrum.length, unten = -78, oben = -6, lage = (db) => Math.min(1, Math.max(0, (db - unten) / (oben - unten)));
        if (this.art === "spektrum") {
          const w = b / n;
          for (let i = 0; i < n; i++) {
            const v = lage(q.spektrum[i]); this.spitzen[i] = Math.max(v, this.spitzen[i] - dt * 0.5);
            const gr = c.createLinearGradient(0, h, 0, 0); gr.addColorStop(0, f.farbe); gr.addColorStop(0.75, f.warn); gr.addColorStop(1, f.spitze);
            c.fillStyle = gr; c.globalAlpha = 0.9; c.fillRect(i * w + 1.5, h - v * h, w - 3, v * h);
            c.globalAlpha = 0.18 * f.leuchten; c.fillRect(i * w, h - v * h - 2, w, v * h + 2);
            c.globalAlpha = 1; c.fillStyle = "#fff"; c.fillRect(i * w + 1.5, h - this.spitzen[i] * h - 2, w - 3, 2);
          }
        } else {
          p.moveTo(0, h);
          for (let i = 0; i < n; i++) { const v = lage(q.spektrum[i]); this.spitzen[i] = this.spitzen[i] * 0.7 + v * 0.3; p.lineTo((i / (n - 1)) * b, h - this.spitzen[i] * h * 0.94); }
          const fuellung = new Path2D(p); fuellung.lineTo(b, h); fuellung.closePath();
          c.fillStyle = f.farbe; c.globalAlpha = 0.16; c.fill(fuellung); c.globalAlpha = 1;
          this.linie(p, f.farbe);
        }
      } else if (this.art === "huelle") {
        const pts = [[0, 1], [0.12, 0], [0.32, 0.35], [0.72, 0.35], [1, 1]];
        pts.forEach(([x, y], i) => (i ? p.lineTo(x * b * 0.96 + b * 0.02, y * h * 0.8 + h * 0.1) : p.moveTo(x * b * 0.96 + b * 0.02, y * h * 0.8 + h * 0.1)));
        this.linie(p, f.farbe, 2.2);
        const s = (t * 0.5) % 1;
        let px = 0, py = 0;
        for (let i = 1; i < pts.length; i++) if (s <= pts[i][0]) { const [x0, y0] = pts[i - 1], [x1, y1] = pts[i], u = (s - x0) / (x1 - x0); px = s; py = y0 + (y1 - y0) * u; break; }
        c.fillStyle = "#fff"; c.beginPath(); c.arc(px * b * 0.96 + b * 0.02, py * h * 0.8 + h * 0.1, 4, 0, 7); c.fill();
      } else if (this.art === "take") {
        const liste = Quelle.take(), n = liste.length, kopf = ((t * 0.05) % 1) * b;
        for (let i = 0; i < n; i++) { const x = (i / n) * b, a = liste[i] * h * 0.44; c.fillStyle = x < kopf ? f.farbe : "rgba(190, 210, 230, .45)"; c.globalAlpha = 1; c.fillRect(x, h / 2 - a, Math.max(1, b / n - 0.4), a * 2); }
        c.fillStyle = "#fff"; c.fillRect(kopf - 1, 0, 2, h);
        c.globalAlpha = 0.3 * f.leuchten; c.fillRect(kopf - 4, 0, 8, h); c.globalAlpha = 1;
      }
    }
  }

  customElements.define("ak-segmente", Segmente);
  customElements.define("ak-zeiger", Zeiger);
  customElements.define("ak-pegel", Pegel);
  customElements.define("ak-schirm", Schirm);
  window.Appkern = Object.assign(window.Appkern || {}, { Takt, Quelle });
})();
