#!/usr/bin/env bash
# Einrichten von RadioHub am Rechner der Entwicklung.
#
#   ./einrichten.sh     Python-Umgebung des Backends mit den Testpaketen, Pakete der Oberfläche (npm ci), Git-Haken
set -euo pipefail
HIER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

entwicklung() {
  cd "$HIER/radiohub-backend"
  [ -x .venv/bin/python ] || python3 -m venv .venv
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements-test.txt
  cd "$HIER/radiohub-frontend"
  npm ci --no-audit --no-fund
  # Haken nur, wenn dieser Ordner selbst das Repo ist (nie in einem Repo, in dem er zufällig liegt)
  if [ "$(git -C "$HIER" rev-parse --show-toplevel 2>/dev/null)" = "$HIER" ]; then
    git -C "$HIER" config core.hooksPath tools/git-hooks
  fi
  echo "RadioHub eingerichtet. Tests: radiohub-backend/.venv/bin/python -m pytest (in radiohub-backend), npx vitest run (in radiohub-frontend)"
}

entwicklung
