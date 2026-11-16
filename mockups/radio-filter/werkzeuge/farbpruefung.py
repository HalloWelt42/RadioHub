# Prüft, dass Seiten- und Baustein-CSS (und Stile in HTML und JS) keine festen Farben enthalten: #..., rgb(, rgba(,
# hsl(, hsla( oder benannte Farben. Marken-Dateien dürfen Farben tragen und werden nur gezählt.
import re, sys, pathlib
wurzel = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent
pruefen = ["radio-bausteine.css", "rahmen.css", "rechner.css", "regeln.css", "telefon.css", "uebersicht.css"]
skripte = ["rechner.html", "regeln.html", "telefon.html", "index.html", "radio.js", "rechner.js", "regeln.js", "telefon.js", "daten.js", "darstellung.js"]
muster = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(|(?<![-\w])(?:white|black|red|green|blue|yellow|orange|gray|grey|silver)(?![-\w])")
fehler = 0
for name in pruefen:
    text = re.sub(r"/\*.*?\*/", "", (wurzel / name).read_text(), flags=re.S)
    for nr, zeile in enumerate(text.splitlines(), 1):
        for m in muster.finditer(zeile):
            fehler += 1; print(f"{name}:{nr}: {m.group(0)} in {zeile.strip()[:100]}")
for name in skripte:
    text = (wurzel / name).read_text()
    for m in re.finditer(r'style="([^"]*)"|style=\\?\'([^\']*)', text):
        stil = m.group(1) or m.group(2) or ""
        for f in muster.finditer(stil):
            fehler += 1; print(f"{name}: feste Farbe im Stil: {stil[:80]}")
marken = ["radio-marken.css", "vorlagen/hifi/marken.css", "vorlagen/ruhig/marken.css"]
for name in marken:
    text = re.sub(r"/\*.*?\*/", "", (wurzel / name).read_text(), flags=re.S)
    print(f"Marken {name}: {len(muster.findall(text))} Farbwerte (erlaubt)")
print("Ergebnis:", "keine festen Farben in Seiten und Bausteinen" if not fehler else f"{fehler} Fundstellen")
sys.exit(1 if fehler else 0)
