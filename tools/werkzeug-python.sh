# shellcheck shell=bash
# Eingebunden (source) von den Git-Haken, tools/version.sh und tools/ausrollen.sh: setzt WERKZEUG_PYTHON auf ein Python,
# das das Paket appkern kennt. Die Prüfungen (Zeichen, Stil, Architekturregeln, Commit-Nachricht) und das Hochzählen der
# Fassung stehen für alle Apps an einer Stelle im Appkern (appkern.werkzeuge).
#
# Reihenfolge: die Umgebung des Backends, sobald ihr Appkern die Regelprüfung kennt (Etappe 2, Umbau auf den Appkern); bis dahin
# APPKERN_PYTHON oder die Umgebung des Appkerns am Mac, wie im Atelier vor seinem eigenen Backend.
werkzeug_python_finden() {
  local wurzel kandidat
  wurzel="$(git rev-parse --show-toplevel)"
  for kandidat in "$wurzel/radiohub-backend/.venv/bin/python" "${APPKERN_PYTHON:-}" \
                  "$HOME/Entwicklung/Werkzeuge/Appkern/.venv/bin/python"; do
    if [ -n "$kandidat" ] && [ -x "$kandidat" ] && "$kandidat" -c "import appkern.werkzeuge.regeln" 2>/dev/null; then
      export WERKZEUG_PYTHON="$kandidat"
      return 0
    fi
  done
  echo "Abbruch: kein Python mit dem Appkern gefunden (radiohub-backend/.venv, APPKERN_PYTHON oder" \
       "$HOME/Entwicklung/Werkzeuge/Appkern/.venv; dort ./einrichten.sh)" >&2
  return 1
}
werkzeug_python_finden
