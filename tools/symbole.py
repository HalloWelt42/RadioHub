#!/usr/bin/env python3
"""Leitet aus dem Logo der App den Symbolsatz für Browser-Tabs, Startbildschirm und PWA ab.

Einzige Quelle ist QUELLE (SVG). Hat das Logo ein Rechteck über die ganze Fläche als Grund, wird dieser Grund für die
maskierbaren Symbole randlos gezogen; ohne Grund (freigestelltes Logo) steht es auf der Hintergrundfarbe der App.
Die Hintergrundfarbe kommt aus dem Manifest (background_color). Erzeugt in OEFFENTLICH:
  favicon.svg                                   Kopie der Quelle für moderne Browser
  favicon.ico                                   16, 32 und 48 in einer Datei
  favicon-32.png, icon-192.png, icon-512.png    wie die Quelle, Durchsichtiges bleibt (purpose any)
  icon-maskable-192.png, icon-maskable-512.png  randlos, Motiv in der sicheren Zone (purpose maskable)
  apple-touch-icon.png                          180, ohne Durchsichtigkeit auf der Hintergrundfarbe der App

Die Bilder liegen im Repo und werden nie zur Laufzeit erzeugt. Nach einer Änderung am Logo neu erzeugen:
  python3 tools/symbole.py
Braucht cairosvg und Pillow, nur auf dem Rechner, der die Bilder erzeugt.
"""

from __future__ import annotations

import io
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import cairosvg
from PIL import Image

WURZEL = Path(__file__).resolve().parent.parent
OEFFENTLICH = WURZEL / "radiohub-frontend" / "public"   # Ordner, den der Server der App als Wurzel ausliefert
QUELLE = OEFFENTLICH / "favicon.svg"           # Logo der App (Funkwellen)
MANIFEST = OEFFENTLICH / "site.webmanifest"
SVG = "http://www.w3.org/2000/svg"
# Anteile des Motivs: maskierbar bleibt alles im Kreis mit 80 % Durchmesser, den kein Gerät beschneidet;
# ein freigestelltes Logo bekommt auf dem Startbildschirm etwas Rand
SICHERE_ZONE = 0.66
FREI_MASKIERBAR = 0.6
FREI_APPLE = 0.78


def rastern(svg: bytes, groesse: int) -> Image.Image:
    png = cairosvg.svg2png(bytestring=svg, output_width=groesse, output_height=groesse)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def auf_grund(bild: Image.Image, groesse: int, anteil: float, farbe: str) -> Image.Image:
    """Bild auf anteil verkleinert mittig auf eine volle Fläche in farbe, ohne Durchsichtigkeit."""
    flaeche = Image.new("RGBA", (groesse, groesse), farbe)
    motiv = bild.resize((round(groesse * anteil),) * 2, Image.Resampling.LANCZOS)
    versatz = (groesse - motiv.width) // 2
    flaeche.alpha_composite(motiv, (versatz, versatz))
    return flaeche.convert("RGB")


def grund_randlos(svg: bytes) -> bytes | None:
    """Grund des Logos randlos über die ganze Fläche, Motiv um die Mitte auf SICHERE_ZONE verkleinert.
    None, wenn das Logo keinen Grund hat (kein Rechteck über die ganze Fläche)."""
    ET.register_namespace("", SVG)
    wurzel = ET.fromstring(svg)
    kasten = wurzel.get("viewBox")
    if not kasten:
        return None
    _, _, breite, hoehe = (float(z) for z in kasten.replace(",", " ").split())

    def masz(k: ET.Element, name: str) -> float | None:
        wert = k.get(name, "")
        if wert.endswith("%"):
            return float(wert[:-1]) / 100 * (breite if name == "width" else hoehe)
        try:
            return float(wert)
        except ValueError:
            return None

    grund = next((k for k in wurzel if k.tag == f"{{{SVG}}}rect" and masz(k, "width") == breite and masz(k, "height") == hoehe
                  and float(k.get("x", 0)) == 0 and float(k.get("y", 0)) == 0), None)
    if grund is None:
        return None
    grund.attrib.pop("rx", None)
    grund.attrib.pop("ry", None)
    motiv = [k for k in wurzel if k is not grund and k.tag != f"{{{SVG}}}defs"]
    x, y = breite / 2, hoehe / 2
    gruppe = ET.SubElement(wurzel, f"{{{SVG}}}g", transform=f"translate({x:g} {y:g}) scale({SICHERE_ZONE}) translate({-x:g} {-y:g})")
    for k in motiv:
        wurzel.remove(k)
        gruppe.append(k)
    return ET.tostring(wurzel)


def main() -> None:
    quelle = QUELLE.read_bytes()
    farbe = json.loads(MANIFEST.read_text(encoding="utf-8"))["background_color"]
    if QUELLE.resolve() != (OEFFENTLICH / "favicon.svg").resolve():
        shutil.copyfile(QUELLE, OEFFENTLICH / "favicon.svg")

    ico = [rastern(quelle, g) for g in (48, 32, 16)]
    ico[0].save(OEFFENTLICH / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)], append_images=ico[1:])
    for name, groesse in (("favicon-32.png", 32), ("icon-192.png", 192), ("icon-512.png", 512)):
        rastern(quelle, groesse).save(OEFFENTLICH / name, optimize=True)

    randlos = grund_randlos(quelle)
    for groesse in (192, 512):
        bild = rastern(randlos, groesse) if randlos else auf_grund(rastern(quelle, groesse), groesse, FREI_MASKIERBAR, farbe)
        bild.save(OEFFENTLICH / f"icon-maskable-{groesse}.png", optimize=True)
    apple = rastern(quelle, 180)
    apple = auf_grund(apple, 180, 1.0, farbe) if randlos else auf_grund(rastern(quelle, 360), 180, FREI_APPLE, farbe)
    apple.save(OEFFENTLICH / "apple-touch-icon.png", optimize=True)
    print(f"Symbolsatz aus {QUELLE.name} erzeugt in {OEFFENTLICH} ({'Grund randlos' if randlos else 'freigestellt auf ' + farbe})")


if __name__ == "__main__":
    sys.exit(main())
