#!/usr/bin/env bash
# Stil der laufenden App für Entwürfe (RAD-35): baut die Oberfläche und legt ihr Stylesheet samt Schriften nach
# mockups/radio-filter/app-stil/ (nicht im Repository, jederzeit neu erzeugbar). Entwürfe, die "auf dem CSS der App"
# stehen sollen, binden app-stil/app.css ein statt der Entwurfskopien (radio-bausteine.css und Co.).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
ziel=mockups/radio-filter/app-stil
(cd frontend && npm run build >/dev/null)
rm -rf "$ziel" && mkdir -p "$ziel"
css=$(ls frontend/dist/assets/index-*.css | head -1)
sed 's#url(/assets/#url(#g' "$css" > "$ziel/app.css"
grep -o 'url([^)]*\.\(woff2\|woff\|ttf\))' "$ziel/app.css" | sed 's/url(\(.*\))/\1/' | sort -u | while read -r datei; do
  cp "frontend/dist/assets/$datei" "$ziel/"
done
echo "Stil der App $(grep -o '"version": "[^"]*"' version.json) nach $ziel ($(ls "$ziel" | wc -l | tr -d ' ') Dateien)"
