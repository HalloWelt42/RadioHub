#!/usr/bin/env bash
# Einmaliger Umzug von RadioHub auf dem Pi aus dem alten Ordner (deploy/ausrollen.toml, [radio] umzug_von) in den Ordner
# des Betriebs (handbuch ziel radiohub wurzel), Entscheidung 21 in docs/umbau/PLAN.md. Läuft vom Mac aus über ssh und
# fasst nur die beiden Ordner und die Container von RadioHub an. Danach baut und startet tools/ausrollen.sh den neuen
# Stand im neuen Ordner; bis dahin ist RadioHub aus.
#
#   tools/umzug-mnt-data.sh --probe    zeigt Größe, Platz, Besitzer, Stand des alten Ordners und jeden Schritt, ändert nichts
#   tools/umzug-mnt-data.sh            zieht um
#   tools/umzug-mnt-data.sh --sofort   ohne auf eine laufende Aufnahme zu warten
#
# Ablauf:
#   1. Vorprüfung: alter Ordner mit data/, sudo ohne Kennwort, Nutzer mit UID 1000 (die Container laufen als 1000:1000),
#      genug Platz im Ziel. Steht im neuen Ordner schon das Merkzeichen .umzug-fertig, ist nichts mehr zu tun (Ende 0).
#   2. erste Abschrift im laufenden Betrieb (rsync, alles samt .git, .env, data, zertifikate)
#   3. auf das Ende einer laufenden Aufnahme warten, dann den alten Betrieb anhalten (docker compose down im alten Ordner)
#   4. zweite Abschrift im Stillstand (nur noch die Änderungen; die Datenbank samt -wal/-shm ist danach stimmig)
#   5. Besitz und Rechte: alles 1000:1000 (bisher liefen die Container als root), .env 600, Schlüssel des Zertifikats 640
#   6. docker-compose.override.yml im neuen Ordner heißt danach docker-compose.override.yml.vor-umzug (ihr Inhalt steht
#      jetzt in compose.pi.yml); Merkzeichen .umzug-fertig schreiben
# Ein abgebrochener Lauf lässt sich einfach wiederholen: rsync setzt fort, das Merkzeichen entsteht erst am Ende.
# Der alte Ordner bleibt unverändert stehen (Rückweg).
#
# Rückweg (auf dem Pi), solange der alte Ordner steht:
#   cd <neu> && docker compose -f compose.pi.yml down
#   sudo rsync -aH --numeric-ids <neu>/data/ <alt>/data/   # nur, wenn seit dem Umzug Daten dazukamen, die bleiben sollen
#   rm <neu>/.umzug-fertig                                 # sonst hält das Ausrollen den neuen Ordner für fertig
#   cd <alt> && docker compose up -d                       # alter Stand mit seiner docker-compose.override.yml
# Die alten Container liefen als root; nach dem Zurückspielen mit rsync bleiben die Dateien 1000:1000, das stört root nicht.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source tools/werkzeug-python.sh

probe=0; sofort=0
for arg in "$@"; do
  case "$arg" in
    --probe) probe=1 ;;
    --sofort) sofort=1 ;;
    *) echo "unbekannte Angabe: $arg" >&2; exit 2 ;;
  esac
done

RECHNER="$(handbuch ziel "$(pwd)" rechner)"
NEU="$(handbuch ziel "$(pwd)" wurzel)"
ALT="$("$WERKZEUG_PYTHON" -c 'import tomllib; print(tomllib.load(open("deploy/ausrollen.toml", "rb"))["radio"]["umzug_von"])')"
FERTIG=".umzug-fertig"
NUTZER_ID=1000
q() { printf '%q' "$1"; }
pi() { ssh -o BatchMode=yes -o ConnectTimeout=10 "$RECHNER" "$1"; }
# Ein Schritt mit Änderung: im Probelauf nur zeigen
schritt() {
  if [ "$probe" = 1 ]; then echo "    würde ausführen: $1"; else pi "$1"; fi
}

echo "Umzug von RadioHub auf $RECHNER: $ALT -> $NEU$([ "$probe" = 1 ] && echo ' (Probelauf, ändert nichts)')"

echo "[1/6] Vorprüfung"
if pi "test -f $(q "$NEU/$FERTIG")"; then
  echo "    schon umgezogen ($NEU/$FERTIG: $(pi "cat $(q "$NEU/$FERTIG")")); nichts zu tun"
  exit 0
fi
pi "test -d $(q "$ALT/data")" || { echo "Abbruch: $ALT/data gibt es nicht" >&2; exit 1; }
pi "sudo -n true" 2>/dev/null || { echo "Abbruch: sudo ohne Kennwort geht auf $RECHNER nicht (Dateien der Container gehören root)" >&2; exit 1; }
uid="$(pi 'id -u')"
[ "$uid" = "$NUTZER_ID" ] || { echo "Abbruch: der Nutzer auf $RECHNER hat UID $uid, die Container laufen als $NUTZER_ID" >&2; exit 1; }
groesse_kb="$(pi "sudo du -sk $(q "$ALT") | cut -f1")"
eltern="$(dirname "$NEU")"
frei_kb="$(pi "df -Pk $(q "$eltern") | awk 'NR==2 {print \$4}'")"
echo "    alter Ordner $(( groesse_kb / 1024 )) MB, frei in $eltern $(( frei_kb / 1024 )) MB"
[ "$frei_kb" -gt $(( groesse_kb + groesse_kb / 10 )) ] || { echo "Abbruch: zu wenig Platz in $eltern" >&2; exit 1; }
echo "    Besitzer im alten Ordner: $(pi "sudo find $(q "$ALT") -maxdepth 2 \( -path '*/.git' -prune \) -o -printf '%u\n' | sort | uniq -c | tr '\n' ' '")"
echo "    Stand im alten Ordner: $(pi "cd $(q "$ALT") && git log --oneline -1 && git status --porcelain | head -20 | tr '\n' ' '")"
echo "    Dateien des Hauses: $(pi "cd $(q "$ALT") && ls -d .env docker-compose.override.yml zertifikate data/radiohub.db data/kellerwolke.schluessel data/storage.json 2>&1 | tr '\n' ' '")"

echo "[2/6] Erste Abschrift im laufenden Betrieb"
schritt "mkdir -p $(q "$NEU") && sudo rsync -aH --numeric-ids $(q "$ALT/") $(q "$NEU/")"

echo "[3/6] Laufende Aufnahme abwarten, alten Betrieb anhalten"
aufnahme='for p in status hls-status; do curl -sf -m 10 http://127.0.0.1:9091/api/recording/$p | grep -q "\"recording\": *true" && exit 0; done; exit 1'
if [ "$sofort" = 0 ]; then
  if [ "$probe" = 1 ]; then
    pi "$aufnahme" && echo "    eine Aufnahme läuft gerade; der Umzug würde auf ihr Ende warten" || echo "    keine laufende Aufnahme"
  else
    while pi "$aufnahme"; do echo "    eine Aufnahme läuft, warte ..."; sleep 30; done
  fi
fi
schritt "cd $(q "$ALT") && docker compose down"

echo "[4/6] Zweite Abschrift im Stillstand"
schritt "sudo rsync -aH --numeric-ids --delete $(q "$ALT/") $(q "$NEU/")"

echo "[5/6] Besitz und Rechte"
schritt "sudo chown -R $NUTZER_ID:$NUTZER_ID $(q "$NEU") && if [ -f $(q "$NEU/.env") ]; then chmod 600 $(q "$NEU/.env"); fi && if [ -d $(q "$NEU/zertifikate") ]; then chmod 640 $(q "$NEU/zertifikate")/*-schluessel.pem 2>/dev/null || true; fi"

echo "[6/6] Alte Erweiterung der Compose-Datei ablegen, Merkzeichen"
schritt "cd $(q "$NEU") && if [ -f docker-compose.override.yml ]; then mv docker-compose.override.yml docker-compose.override.yml.vor-umzug; fi && echo \"\$(date -Iseconds) aus $(q "$ALT")\" > $FERTIG"

if [ "$probe" = 1 ]; then
  echo "Probelauf zu Ende, nichts geändert. Danach: tools/umzug-mnt-data.sh, dann tools/ausrollen.sh"
else
  echo "Umgezogen nach $NEU; RadioHub ist aus, bis tools/ausrollen.sh den neuen Stand dort startet. $ALT bleibt als Rückweg."
fi
