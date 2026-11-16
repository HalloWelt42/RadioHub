#!/usr/bin/env bash
# Ausrollen auf den Pi (vom Mac aus) nach deploy/ausrollen.toml. Ablauf in tools/ausrollen.py aus den Bausteinen des
# Appkerns: nur gepushte Stände, harte Regeln und Tests grün, Ordner nach dem Umzug, Zertifikat, bauen, keine laufende
# Aufnahme abschießen, Datenbank sichern nach der Regel der Sicherung, neu starten, Fassungen, HTTP/2 und Symbole, danach
# Docker aufräumen. Rechner, Ordner, Adresse und Namen kommen aus der privaten Wahrheit (handbuch ziel); die Adresse ist
# die des Vorschaltdienstes (HTTPS, Port vorne), die http-Adresse im Verbund ist nur noch die Umleitung des Vorbaus.
#
#   tools/ausrollen.sh            ausrollen
#   tools/ausrollen.sh --sofort   nicht auf eine laufende Aufnahme warten
set -euo pipefail
# >>> handbuch: vorher Seite, Einrichtungsskript, Probelauf und Bau des Handbuchs (eingesetzt von "handbuch einbinden")
handbuch_befehl="$(command -v handbuch || true)"
[ -n "$handbuch_befehl" ] || handbuch_befehl="$HOME/.local/bin/handbuch"
if [ ! -x "$handbuch_befehl" ]; then
  echo "Abbruch: das Werkzeug handbuch fehlt (Handbuch, Grundlage Mac)" >&2
  exit 1
fi
"$handbuch_befehl" freigabe "$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)" || {
  echo "Abbruch: das Handbuch ist nicht in Ordnung, nichts ausgerollt" >&2
  exit 1
}
# <<< handbuch
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source tools/werkzeug-python.sh
ergaenzung="$(mktemp)"
trap 'rm -f "$ergaenzung"' EXIT
handbuch ziel "$(pwd)" --toml | grep -v '^adresse = ' > "$ergaenzung" \
  || { echo "Abbruch: kein Ziel in der privaten Wahrheit (handbuch ziel)" >&2; exit 1; }
rechner="$(handbuch ziel "$(pwd)" rechner)"
port="$(handbuch ziel "$(pwd)" port:vorne)"
echo "adresse = \"https://${rechner#*@}:$port\"" >> "$ergaenzung"
exec "$WERKZEUG_PYTHON" tools/ausrollen.py --ergaenzung "$ergaenzung" "$@"
