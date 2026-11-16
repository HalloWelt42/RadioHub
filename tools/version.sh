#!/usr/bin/env bash
# Fassung hochzählen: tools/version.sh [patch|minor|major|id]. Einzige Quelle ist version.json ({version, id, voll});
# "id" vergibt nur eine neue Kennung. Gerechnet wird im Appkern (appkern.werkzeuge). Der Git-Haken zählt bei jedem
# Commit den Patch hoch; ein Feature hebt die Fassung vorher hiermit (minor) und merkt version.json vor.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source tools/werkzeug-python.sh
exec "$WERKZEUG_PYTHON" -m appkern.werkzeuge fassung "${1:-patch}"
