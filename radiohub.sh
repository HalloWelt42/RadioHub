#!/usr/bin/env bash
# ============================================================
# RadioHub Management Script
# Starten, Stoppen, Neustarten, Backup, Status, Logs
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/radiohub-backend"
FRONTEND_DIR="$SCRIPT_DIR/radiohub-frontend"
DATA_DIR="$BACKEND_DIR/data"
BACKUP_DIR="$SCRIPT_DIR/backups"
DB_FILE="$DATA_DIR/radiohub.db"
VENV_UVICORN="$BACKEND_DIR/.venv/bin/uvicorn"

BACKEND_PORT=9091
FRONTEND_PORT=5180

PID_DIR="$SCRIPT_DIR/.pids"
BACKEND_PID="$PID_DIR/backend.pid"
FRONTEND_PID="$PID_DIR/frontend.pid"
LOG_DIR="$SCRIPT_DIR/.logs"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ============================================================
# Hilfsfunktionen
# ============================================================

ensure_dirs() {
    mkdir -p "$PID_DIR" "$LOG_DIR" "$BACKUP_DIR"
}

print_header() {
    echo -e "${BOLD}${CYAN}RadioHub${NC} -- $1"
    echo ""
}

is_running() {
    local pidfile="$1"
    if [ -f "$pidfile" ]; then
        local pid
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
        rm -f "$pidfile"
    fi
    return 1
}

get_pid_on_port() {
    lsof -ti ":$1" 2>/dev/null | head -1 || true
}

# ============================================================
# Start
# ============================================================

start_backend() {
    if is_running "$BACKEND_PID"; then
        echo -e "  Backend: ${YELLOW}läuft bereits${NC} (PID $(cat "$BACKEND_PID"))"
        return 0
    fi
    # Prüfen ob Port belegt
    local existing_pid
    existing_pid=$(get_pid_on_port $BACKEND_PORT)
    if [ -n "$existing_pid" ]; then
        echo -e "  Backend: ${YELLOW}Port $BACKEND_PORT belegt${NC} (PID $existing_pid)"
        echo -e "  Stoppe fremden Prozess..."
        kill "$existing_pid" 2>/dev/null || true
        sleep 1
    fi
    echo -e "  Backend: ${CYAN}starte...${NC}"
    cd "$BACKEND_DIR"
    DATA_PATH="$DATA_DIR" nohup "$VENV_UVICORN" backend.main:app \
        --host 0.0.0.0 --port $BACKEND_PORT --reload \
        > "$BACKEND_LOG" 2>&1 &
    echo $! > "$BACKEND_PID"
    cd "$SCRIPT_DIR"
    sleep 1
    if is_running "$BACKEND_PID"; then
        echo -e "  Backend: ${GREEN}gestartet${NC} (PID $(cat "$BACKEND_PID"), Port $BACKEND_PORT)"
    else
        echo -e "  Backend: ${RED}Start fehlgeschlagen${NC} -- siehe $BACKEND_LOG"
        return 1
    fi
}

start_frontend() {
    if is_running "$FRONTEND_PID"; then
        echo -e "  Frontend: ${YELLOW}läuft bereits${NC} (PID $(cat "$FRONTEND_PID"))"
        return 0
    fi
    local existing_pid
    existing_pid=$(get_pid_on_port $FRONTEND_PORT)
    if [ -n "$existing_pid" ]; then
        echo -e "  Frontend: ${YELLOW}Port $FRONTEND_PORT belegt${NC} (PID $existing_pid)"
        echo -e "  Stoppe fremden Prozess..."
        kill "$existing_pid" 2>/dev/null || true
        sleep 1
    fi
    echo -e "  Frontend: ${CYAN}starte...${NC}"
    cd "$FRONTEND_DIR"
    nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
    echo $! > "$FRONTEND_PID"
    cd "$SCRIPT_DIR"
    sleep 2
    if is_running "$FRONTEND_PID"; then
        echo -e "  Frontend: ${GREEN}gestartet${NC} (PID $(cat "$FRONTEND_PID"), Port $FRONTEND_PORT)"
    else
        echo -e "  Frontend: ${RED}Start fehlgeschlagen${NC} -- siehe $FRONTEND_LOG"
        return 1
    fi
}

cmd_start() {
    print_header "Start"
    ensure_dirs
    local target="${1:-all}"
    case "$target" in
        backend|be)  start_backend ;;
        frontend|fe) start_frontend ;;
        all)         start_backend; start_frontend ;;
        *) echo "Unbekannt: $target (backend|frontend|all)"; exit 1 ;;
    esac
    echo ""
    echo -e "  ${GREEN}http://localhost:$FRONTEND_PORT${NC}"
}

# ============================================================
# Stop
# ============================================================

stop_process() {
    local name="$1"
    local pidfile="$2"
    local port="$3"

    if is_running "$pidfile"; then
        local pid
        pid=$(cat "$pidfile")
        echo -e "  $name: ${CYAN}stoppe${NC} (PID $pid)..."
        kill "$pid" 2>/dev/null || true
        # Warten bis Prozess beendet
        local wait=0
        while kill -0 "$pid" 2>/dev/null && [ $wait -lt 5 ]; do
            sleep 1
            wait=$((wait + 1))
        done
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$pidfile"
        echo -e "  $name: ${GREEN}gestoppt${NC}"
    else
        # Prüfen ob trotzdem was auf dem Port läuft
        local existing_pid
        existing_pid=$(get_pid_on_port "$port")
        if [ -n "$existing_pid" ]; then
            echo -e "  $name: ${CYAN}stoppe Prozess auf Port $port${NC} (PID $existing_pid)..."
            kill "$existing_pid" 2>/dev/null || true
            sleep 1
            echo -e "  $name: ${GREEN}gestoppt${NC}"
        else
            echo -e "  $name: ${YELLOW}läuft nicht${NC}"
        fi
        rm -f "$pidfile"
    fi
}

cmd_stop() {
    print_header "Stop"
    ensure_dirs
    local target="${1:-all}"
    case "$target" in
        backend|be)  stop_process "Backend" "$BACKEND_PID" $BACKEND_PORT ;;
        frontend|fe) stop_process "Frontend" "$FRONTEND_PID" $FRONTEND_PORT ;;
        all)         stop_process "Frontend" "$FRONTEND_PID" $FRONTEND_PORT
                     stop_process "Backend" "$BACKEND_PID" $BACKEND_PORT ;;
        *) echo "Unbekannt: $target (backend|frontend|all)"; exit 1 ;;
    esac
}

# ============================================================
# Restart
# ============================================================

cmd_restart() {
    print_header "Restart"
    ensure_dirs
    local target="${1:-all}"
    cmd_stop "$target"
    echo ""
    cmd_start "$target"
}

# ============================================================
# Status
# ============================================================

cmd_status() {
    print_header "Status"
    ensure_dirs

    # Backend
    if is_running "$BACKEND_PID"; then
        local bpid
        bpid=$(cat "$BACKEND_PID")
        echo -e "  Backend:  ${GREEN}ONLINE${NC}  PID $bpid  Port $BACKEND_PORT"
    else
        local existing_pid
        existing_pid=$(get_pid_on_port $BACKEND_PORT)
        if [ -n "$existing_pid" ]; then
            echo -e "  Backend:  ${YELLOW}ONLINE (extern)${NC}  PID $existing_pid  Port $BACKEND_PORT"
        else
            echo -e "  Backend:  ${RED}OFFLINE${NC}"
        fi
    fi

    # Frontend
    if is_running "$FRONTEND_PID"; then
        local fpid
        fpid=$(cat "$FRONTEND_PID")
        echo -e "  Frontend: ${GREEN}ONLINE${NC}  PID $fpid  Port $FRONTEND_PORT"
    else
        local existing_pid
        existing_pid=$(get_pid_on_port $FRONTEND_PORT)
        if [ -n "$existing_pid" ]; then
            echo -e "  Frontend: ${YELLOW}ONLINE (extern)${NC}  PID $existing_pid  Port $FRONTEND_PORT"
        else
            echo -e "  Frontend: ${RED}OFFLINE${NC}"
        fi
    fi

    # DB
    if [ -f "$DB_FILE" ]; then
        local dbsize
        dbsize=$(du -sh "$DB_FILE" | cut -f1)
        echo -e "  Datenbank: ${GREEN}$dbsize${NC}  $DB_FILE"
    else
        echo -e "  Datenbank: ${RED}nicht gefunden${NC}"
    fi

    # Backups
    local backup_count
    backup_count=$(find "$BACKUP_DIR" -name "*.db.gz" 2>/dev/null | wc -l | tr -d ' ')
    echo -e "  Backups:   ${CYAN}$backup_count${NC} vorhanden"
}

# ============================================================
# Backup
# ============================================================

cmd_backup() {
    print_header "Backup"
    ensure_dirs

    if [ ! -f "$DB_FILE" ]; then
        echo -e "  ${RED}Datenbank nicht gefunden:${NC} $DB_FILE"
        exit 1
    fi

    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/radiohub_${timestamp}.db"
    local backup_gz="${backup_file}.gz"

    # SQLite Online-Backup (sicher auch bei laufender DB)
    echo -e "  Erstelle Backup..."
    sqlite3 "$DB_FILE" ".backup '$backup_file'"
    gzip "$backup_file"

    local size
    size=$(du -sh "$backup_gz" | cut -f1)
    echo -e "  ${GREEN}Backup erstellt:${NC} $backup_gz ($size)"

    # Alte Backups aufraeumen (behalte letzte 10)
    local count
    count=$(ls -1t "$BACKUP_DIR"/radiohub_*.db.gz 2>/dev/null | wc -l | tr -d ' ')
    if [ "$count" -gt 10 ]; then
        local to_delete=$((count - 10))
        echo -e "  Raeume $to_delete alte Backups auf..."
        ls -1t "$BACKUP_DIR"/radiohub_*.db.gz | tail -n "$to_delete" | xargs rm -f
    fi

    echo -e "  Backups gesamt: $((count > 10 ? 10 : count))"
}

# ============================================================
# Restore
# ============================================================

cmd_restore() {
    print_header "Restore"
    ensure_dirs

    local backup_file="${1:-}"

    if [ -z "$backup_file" ]; then
        # Zeige verfügbare Backups
        echo "  Verfügbare Backups:"
        echo ""
        local i=1
        while IFS= read -r f; do
            local fname
            fname=$(basename "$f")
            local fsize
            fsize=$(du -sh "$f" | cut -f1)
            echo -e "  ${CYAN}[$i]${NC} $fname ($fsize)"
            i=$((i + 1))
        done < <(ls -1t "$BACKUP_DIR"/radiohub_*.db.gz 2>/dev/null)

        if [ "$i" -eq 1 ]; then
            echo -e "  ${YELLOW}Keine Backups vorhanden${NC}"
            return 1
        fi

        echo ""
        echo -e "  Aufruf: ${BOLD}$0 restore <dateiname>${NC}"
        echo -e "  Beispiel: $0 restore $(ls -1t "$BACKUP_DIR"/radiohub_*.db.gz 2>/dev/null | head -1 | xargs basename)"
        return 0
    fi

    # Vollstaendiger Pfad oder nur Dateiname
    if [[ "$backup_file" != /* ]]; then
        backup_file="$BACKUP_DIR/$backup_file"
    fi

    if [ ! -f "$backup_file" ]; then
        echo -e "  ${RED}Datei nicht gefunden:${NC} $backup_file"
        return 1
    fi

    echo -e "  ${YELLOW}ACHTUNG: Die aktuelle Datenbank wird überschrieben!${NC}"
    echo -n "  Fortfahren? (j/N) "
    read -r confirm
    if [[ "$confirm" != "j" && "$confirm" != "J" ]]; then
        echo "  Abgebrochen."
        return 0
    fi

    # Sicherheitsbackup vor Restore
    echo -e "  Erstelle Sicherheitskopie..."
    local safety_backup="$BACKUP_DIR/radiohub_pre_restore.db"
    sqlite3 "$DB_FILE" ".backup '$safety_backup'"
    gzip -f "$safety_backup"

    # Backend stoppen falls aktiv
    local was_running=false
    if is_running "$BACKEND_PID"; then
        was_running=true
        stop_process "Backend" "$BACKEND_PID" $BACKEND_PORT
    fi

    # Restore
    echo -e "  Restore von $(basename "$backup_file")..."
    gunzip -c "$backup_file" > "$DB_FILE"
    echo -e "  ${GREEN}Restore abgeschlossen${NC}"

    # Backend neu starten falls es lief
    if $was_running; then
        start_backend
    fi
}

# ============================================================
# Logs
# ============================================================

cmd_logs() {
    local target="${1:-all}"
    local lines="${2:-30}"

    case "$target" in
        backend|be)
            print_header "Backend Logs (letzte $lines Zeilen)"
            if [ -f "$BACKEND_LOG" ]; then
                tail -n "$lines" "$BACKEND_LOG"
            else
                echo -e "  ${YELLOW}Kein Backend-Log vorhanden${NC}"
            fi
            ;;
        frontend|fe)
            print_header "Frontend Logs (letzte $lines Zeilen)"
            if [ -f "$FRONTEND_LOG" ]; then
                tail -n "$lines" "$FRONTEND_LOG"
            else
                echo -e "  ${YELLOW}Kein Frontend-Log vorhanden${NC}"
            fi
            ;;
        all)
            cmd_logs backend "$lines"
            echo ""
            cmd_logs frontend "$lines"
            ;;
        *) echo "Unbekannt: $target (backend|frontend|all)"; exit 1 ;;
    esac
}

# ============================================================
# Build
# ============================================================

cmd_build() {
    print_header "Build"
    echo -e "  Frontend Build..."
    cd "$FRONTEND_DIR"
    npx vite build
    cd "$SCRIPT_DIR"
    echo -e "  ${GREEN}Build fertig${NC}"
}

# ============================================================
# Test
# ============================================================

cmd_test() {
    print_header "Tests"
    cd "$FRONTEND_DIR"
    npx vitest run
    cd "$SCRIPT_DIR"
}

# ============================================================
# Usage
# ============================================================

cmd_help() {
    echo -e "${BOLD}${CYAN}RadioHub${NC} Management Script"
    echo ""
    echo -e "  ${BOLD}Verwendung:${NC} $0 <befehl> [ziel]"
    echo ""
    echo -e "  ${BOLD}Befehle:${NC}"
    echo -e "    start   [be|fe|all]    Server starten (Standard: all)"
    echo -e "    stop    [be|fe|all]    Server stoppen (Standard: all)"
    echo -e "    restart [be|fe|all]    Server neustarten (Standard: all)"
    echo -e "    status                 Status aller Dienste anzeigen"
    echo -e "    logs    [be|fe|all] [n]  Logs anzeigen (Standard: 30 Zeilen)"
    echo -e "    backup                 Datenbank-Backup erstellen"
    echo -e "    restore [datei]        Backup wiederherstellen"
    echo -e "    build                  Frontend bauen"
    echo -e "    test                   Tests ausführen"
    echo ""
    echo -e "  ${BOLD}Kürzel:${NC} be = backend, fe = frontend"
    echo ""
    echo -e "  ${BOLD}Beispiele:${NC}"
    echo -e "    $0 start               Alles starten"
    echo -e "    $0 restart be           Nur Backend neustarten"
    echo -e "    $0 logs be 50           Letzte 50 Backend-Log-Zeilen"
    echo -e "    $0 backup               DB-Backup erstellen"
    echo -e "    $0 restore              Verfügbare Backups anzeigen"
}

# ============================================================
# Main
# ============================================================

ensure_dirs

case "${1:-help}" in
    start)   cmd_start "${2:-all}" ;;
    stop)    cmd_stop "${2:-all}" ;;
    restart) cmd_restart "${2:-all}" ;;
    status)  cmd_status ;;
    logs)    cmd_logs "${2:-all}" "${3:-30}" ;;
    backup)  cmd_backup ;;
    restore) cmd_restore "${2:-}" ;;
    build)   cmd_build ;;
    test)    cmd_test ;;
    help|-h|--help) cmd_help ;;
    *) echo "Unbekannter Befehl: $1"; cmd_help; exit 1 ;;
esac
