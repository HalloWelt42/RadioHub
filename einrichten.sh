#!/usr/bin/env bash
# Einrichten von RadioHub. Die Schritte der Neueinrichtung mit ihren Proben stehen in docs/handbuch.md.
#
#   ./einrichten.sh                                       Entwicklung am Mac: Python-Umgebung des Backends mit den
#                                                         Testpaketen, Pakete der Oberfläche (npm ci), Git-Haken
#   ./einrichten.sh --probe --ziel DIR --port-versatz N   Probelauf des Handbuchs: DIR enthält einen Stand der App; daraus
#                                                         entsteht der Betrieb wie auf dem Pi (compose.pi.yml) mit
#                                                         Wegwerfzertifikat, abgeschottet von jeder echten Gegenstelle
#                                                         (deploy/probelauf.compose.yml), Port um N verschoben und nur an
#                                                         127.0.0.1
#   ./einrichten.sh --probe --ziel DIR --abbauen          entfernt alles, was der Probelauf angelegt hat
#
# Der Betrieb auf dem Pi entsteht mit tools/ausrollen.sh (deploy/ausrollen.toml), beim ersten Mal nach dem Umzug mit
# tools/umzug-mnt-data.sh.
set -euo pipefail
HIER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KENNUNG="radiohub"
PROBE_COMPOSE=(-f compose.pi.yml -f deploy/probelauf.compose.yml)
PROBE_WARTEN_S=300

entwicklung() {
  cd "$HIER/backend"
  [ -x .venv/bin/python ] || python3.12 -m venv .venv
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements-test.txt
  cd "$HIER/frontend"
  npm ci --no-audit --no-fund
  # Haken nur, wenn dieser Ordner selbst das Repo ist (nie in einem Repo, in dem er zufällig liegt)
  if [ "$(git -C "$HIER" rev-parse --show-toplevel 2>/dev/null)" = "$HIER" ]; then
    git -C "$HIER" config core.hooksPath tools/git-hooks
  fi
  echo "RadioHub eingerichtet. Tests: backend/.venv/bin/python -m pytest (in backend), npx vitest run (in frontend)"
}

# veröffentlichter Port des Vorschaltdienstes laut compose.pi.yml (er steht nur dort)
grundport() {
  docker compose -f "$1/compose.pi.yml" config --format json | python3 -c '
import json, sys
print(json.load(sys.stdin)["services"]["vorne"]["ports"][0]["published"])'
}

probe_aufbauen() {
  local ziel="$1" versatz="$2" port
  port=$(( $(grundport "$ziel") + versatz ))
  cd "$ziel"
  mkdir -p data sicherungen zertifikate
  # Wegwerf-Hausstelle in DIR, nie die echte: das Blattzertifikat gilt nur für diesen Rechner, mit dem Namen, den der
  # Vorschaltdienst ohne Servernamen nimmt (radiohub.local, deploy/Caddyfile)
  CAROOT="$ziel/hausstelle" mkcert -cert-file "zertifikate/$KENNUNG.pem" -key-file "zertifikate/$KENNUNG-schluessel.pem" \
    127.0.0.1 localhost "$KENNUNG.local" >/dev/null 2>&1
  cp hausstelle/rootCA.pem zertifikate/rootCA.pem
  # ohne Kellerwolke, Vertonung und Zeit-Stimme: die Werte des Hauses bleiben leer (die App wartet dann auf die erste
  # Einrichtung, /health und die Anmeldeseite antworten trotzdem)
  ( umask 077; printf 'PROBE_PORT=%s\n' "$port" > .env )
  docker compose "${PROBE_COMPOSE[@]}" up -d --build --quiet-pull
  local ende=$(( $(date +%s) + PROBE_WARTEN_S ))
  while [ "$(date +%s)" -lt "$ende" ]; do
    if curl -sf --cacert zertifikate/rootCA.pem "https://127.0.0.1:$port/health" >/dev/null \
       && curl -sf -o /dev/null --cacert zertifikate/rootCA.pem "https://127.0.0.1:$port/"; then
      echo "ANTWORTET https://127.0.0.1:$port/health"
      return 0
    fi
    sleep 2
  done
  echo "RadioHub antwortet nach $PROBE_WARTEN_S s nicht" >&2
  docker compose "${PROBE_COMPOSE[@]}" logs --tail 40 >&2 || true
  return 1
}

probe_abbauen() {
  cd "$1"
  [ -f .env ] || return 0
  docker compose "${PROBE_COMPOSE[@]}" down --volumes --remove-orphans
  docker image rm -f "${COMPOSE_PROJECT_NAME:?}-radiohub" >/dev/null 2>&1 || true
}

probe=0; abbauen=0; ziel=""; versatz=""
while [ $# -gt 0 ]; do
  case "$1" in
    --probe) probe=1 ;;
    --abbauen) abbauen=1 ;;
    --ziel) ziel="${2:?--ziel braucht einen Ordner}"; shift ;;
    --port-versatz) versatz="${2:?--port-versatz braucht eine Zahl}"; shift ;;
    *) echo "unbekannte Angabe: $1" >&2; exit 2 ;;
  esac
  shift
done

if [ "$probe" = 0 ]; then
  entwicklung
elif [ -z "$ziel" ] || [ ! -d "$ziel" ]; then
  echo "--probe braucht --ziel mit einem vorhandenen Ordner" >&2; exit 2
elif [ "$abbauen" = 1 ]; then
  probe_abbauen "$(cd "$ziel" && pwd)"
else
  probe_aufbauen "$(cd "$ziel" && pwd)" "${versatz:?--port-versatz fehlt}"
fi
