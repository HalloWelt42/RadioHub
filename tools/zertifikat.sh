#!/usr/bin/env bash
# Blattzertifikat für den HTTPS-Zugang des RadioHub (Port 9093) aus der Hausstelle (mkcert) ausstellen und auf den
# Rechner des RadioHub bringen. Der Schlüssel der Hausstelle bleibt auf diesem Mac; auf den Zielrechner gehen nur
# Blattzertifikat, Blattschlüssel (600) und das öffentliche Zertifikat der Hausstelle. Ein Telefon, das der Hausstelle
# vertraut (wie bei Kellerwolke und Kiste), vertraut damit auch dem RadioHub.
#
# Ziel und Namen gehören dem Haus und stehen nicht im Repo:
#   RADIOHUB_ZIEL=pi@<rechner> RADIOHUB_ORDNER=/home/pi/RadioHub RADIOHUB_NAMEN="<ip> <rechnername> ..." \
#     tools/zertifikat.sh [--pruefen]
#   --pruefen  nur die Restlaufzeit auf dem Ziel prüfen; Status 1 unter 60 Tagen oder ohne Zertifikat
set -euo pipefail
: "${RADIOHUB_ZIEL:?RADIOHUB_ZIEL fehlt (ssh-Ziel, etwa pi@rechner)}"
: "${RADIOHUB_ORDNER:?RADIOHUB_ORDNER fehlt (Ordner des RadioHub auf dem Ziel)}"
ZIEL="$RADIOHUB_ORDNER/zertifikate"
SCHWELLE_S=$((60 * 86400))

if [ "${1:-}" = "--pruefen" ]; then
  ssh -o BatchMode=yes "$RADIOHUB_ZIEL" "openssl x509 -in '$ZIEL/radiohub.pem' -noout -checkend $SCHWELLE_S" >/dev/null 2>&1
  exit $?
fi

: "${RADIOHUB_NAMEN:?RADIOHUB_NAMEN fehlt (Adressen und Namen im Zertifikat, durch Leerzeichen getrennt)}"
command -v mkcert >/dev/null 2>&1 || { echo "mkcert fehlt auf diesem Mac."; exit 1; }
HAUSSTELLE="$(mkcert -CAROOT)/rootCA.pem"
[ -f "$HAUSSTELLE" ] || { echo "Die Hausstelle fehlt: $HAUSSTELLE"; exit 1; }

ARBEIT="$(mktemp -d)"
trap 'rm -rf "$ARBEIT"' EXIT
# shellcheck disable=SC2086 - die Namen sind eine Liste
(cd "$ARBEIT" && mkcert -cert-file radiohub.pem -key-file radiohub-schluessel.pem radiohub.local $RADIOHUB_NAMEN >/dev/null 2>&1)
cp "$HAUSSTELLE" "$ARBEIT/rootCA.pem"

ssh -o BatchMode=yes "$RADIOHUB_ZIEL" "mkdir -p '$ZIEL'"
scp -q "$ARBEIT/radiohub.pem" "$ARBEIT/radiohub-schluessel.pem" "$ARBEIT/rootCA.pem" "$RADIOHUB_ZIEL:$ZIEL/"
ssh -o BatchMode=yes "$RADIOHUB_ZIEL" "chmod 644 '$ZIEL/radiohub.pem' '$ZIEL/rootCA.pem' && chmod 600 '$ZIEL/radiohub-schluessel.pem'"
echo "Zertifikat ausgestellt und übertragen, gültig bis: $(openssl x509 -in "$ARBEIT/radiohub.pem" -noout -enddate | sed 's/^.*=//')"
