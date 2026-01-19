#!/usr/bin/env bash
#
# Overture Teams Analyzer - Control Script for DietPi/Debian
# A single unified script for managing the Overture scouting system
#
# Usage: overture-ctl [command] [options]
#
# Commands:
#   install     - Install dependencies and set up services
#   start       - Start the Streamlit web app
#   stop        - Stop all services
#   restart     - Restart services
#   status      - Show service status
#   logs        - View live logs
#   backup      - Backup current scouting data with custom name
#   clear       - Clear/reset scouting data (with confirmation)
#   hid-start   - Start HID scanner interceptor
#   hid-stop    - Stop HID scanner interceptor
#   hid-list    - List available HID devices
#   uninstall   - Remove services (keeps data)
#
# Tested on: DietPi (Debian-based), Raspberry Pi 4

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LIB_DIR="$PROJECT_ROOT/lib"
DATA_DIR="$PROJECT_ROOT/data"
BACKUP_DIR="$PROJECT_ROOT/backups"
VENV_DIR="$PROJECT_ROOT/.venv"
DEFAULT_CSV="$DATA_DIR/default_scouting.csv"

# Service configuration
SYSTEMD_DIR="/etc/systemd/system"
APP_SERVICE="overture-app.service"
HID_SERVICE="overture-hid.service"
SERVICE_USER="${SUDO_USER:-$USER}"
SERVICE_GROUP="$(id -gn "$SERVICE_USER" 2>/dev/null || echo "$SERVICE_USER")"

# Streamlit settings
STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ============================================================================
# Helper Functions
# ============================================================================

log_info()  { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_step()  { echo -e "${BLUE}[→]${NC} $1"; }

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This command requires root. Run with sudo."
        exit 1
    fi
}

check_not_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warn "Running as root. Using SUDO_USER=$SERVICE_USER for file ownership."
    fi
}

ensure_dirs() {
    mkdir -p "$DATA_DIR" "$BACKUP_DIR"
    if [[ $EUID -eq 0 ]]; then
        chown -R "$SERVICE_USER:$SERVICE_GROUP" "$DATA_DIR" "$BACKUP_DIR" 2>/dev/null || true
    fi
}

get_python() {
    if [[ -f "$VENV_DIR/bin/python" ]]; then
        echo "$VENV_DIR/bin/python"
    elif command -v python3 &>/dev/null; then
        echo "python3"
    else
        log_error "Python 3 not found!"
        exit 1
    fi
}

get_streamlit() {
    if [[ -f "$VENV_DIR/bin/streamlit" ]]; then
        echo "$VENV_DIR/bin/streamlit"
    elif command -v streamlit &>/dev/null; then
        command -v streamlit
    else
        log_error "Streamlit not found! Run: overture-ctl install"
        exit 1
    fi
}

activate_venv() {
    if [[ -f "$VENV_DIR/bin/activate" ]]; then
        # shellcheck disable=SC1091
        source "$VENV_DIR/bin/activate"
    fi
}

# ============================================================================
# Installation Commands
# ============================================================================

cmd_install() {
    log_step "Installing Overture Teams Analyzer..."
    
    cd "$PROJECT_ROOT"
    
    # Check Python
    if ! command -v python3 &>/dev/null; then
        log_error "Python 3 not found. Install with: sudo apt install python3 python3-venv python3-pip"
        exit 1
    fi
    
    # Create virtual environment
    if [[ ! -d "$VENV_DIR" ]]; then
        log_step "Creating Python virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi
    
    # Activate and install dependencies
    log_step "Installing Python dependencies..."
    activate_venv
    pip install --upgrade pip wheel setuptools
    pip install -r requirements_web.txt
    
    # Install system dependencies for QR scanning
    log_step "Checking system dependencies..."
    if command -v apt-get &>/dev/null; then
        if ! dpkg -l libzbar0 &>/dev/null 2>&1; then
            log_warn "libzbar0 not found. Installing (requires sudo)..."
            sudo apt-get update && sudo apt-get install -y libzbar0 || {
                log_warn "Could not install libzbar0. QR scanning may not work."
            }
        fi
    fi
    
    # Ensure directories exist
    ensure_dirs
    
    log_info "Installation complete!"
    echo ""
    log_info "To start the web app:"
    echo "    $0 start"
    echo ""
    log_info "Access the web interface at:"
    echo "    http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost'):$STREAMLIT_PORT"
}

cmd_install_services() {
    check_root
    
    log_step "Installing systemd services..."
    
    local PYTHON_PATH STREAMLIT_PATH
    PYTHON_PATH="$(get_python)"
    STREAMLIT_PATH="$(get_streamlit)"
    
    ensure_dirs
    
    # Create app service
    cat > "$SYSTEMD_DIR/$APP_SERVICE" << EOF
[Unit]
Description=Overture Teams Analyzer - Streamlit Web Interface
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$PROJECT_ROOT
Environment="PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$LIB_DIR"
ExecStart=$STREAMLIT_PATH run $LIB_DIR/streamlit_app.py --server.port=$STREAMLIT_PORT --server.address=0.0.0.0 --server.headless=true
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=overture-app

[Install]
WantedBy=multi-user.target
EOF

    # Create HID service
    cat > "$SYSTEMD_DIR/$HID_SERVICE" << EOF
[Unit]
Description=Overture Teams Analyzer - HID Scanner Interceptor
After=local-fs.target
ConditionPathExists=$LIB_DIR/headless_interceptor.py

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_ROOT
Environment="PYTHONPATH=$LIB_DIR"
ExecStart=$PYTHON_PATH $LIB_DIR/headless_interceptor.py --config $LIB_DIR/config/columns.json --output $DEFAULT_CSV
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=overture-hid

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    
    log_info "Services installed!"
    log_info "Enable with: sudo systemctl enable $APP_SERVICE"
}

# ============================================================================
# Service Control Commands
# ============================================================================

cmd_start() {
    log_step "Starting Overture web app..."
    
    cd "$PROJECT_ROOT"
    activate_venv
    ensure_dirs
    
    local STREAMLIT_PATH
    STREAMLIT_PATH="$(get_streamlit)"
    
    local IP
    IP="$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')"
    
    log_info "Starting Streamlit on port $STREAMLIT_PORT..."
    log_info "Access at: http://$IP:$STREAMLIT_PORT"
    echo ""
    log_warn "Press Ctrl+C to stop"
    echo ""
    
    PYTHONPATH="$LIB_DIR" "$STREAMLIT_PATH" run "$LIB_DIR/streamlit_app.py" \
        --server.port="$STREAMLIT_PORT" \
        --server.address=0.0.0.0 \
        --server.headless=true
}

cmd_start_bg() {
    check_root
    
    if systemctl is-active --quiet "$APP_SERVICE" 2>/dev/null; then
        log_warn "Service already running"
        return
    fi
    
    systemctl start "$APP_SERVICE"
    log_info "Service started"
    
    sleep 2
    if systemctl is-active --quiet "$APP_SERVICE"; then
        local IP
        IP="$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')"
        log_info "Access at: http://$IP:$STREAMLIT_PORT"
    else
        log_error "Service failed to start. Check: journalctl -u $APP_SERVICE -n 50"
    fi
}

cmd_stop() {
    log_step "Stopping Overture services..."
    
    # Try systemd first
    if [[ $EUID -eq 0 ]]; then
        systemctl stop "$APP_SERVICE" 2>/dev/null || true
        systemctl stop "$HID_SERVICE" 2>/dev/null || true
    fi
    
    # Also kill any running processes
    pkill -f "streamlit.*streamlit_app.py" 2>/dev/null || true
    pkill -f "headless_interceptor.py" 2>/dev/null || true
    
    log_info "Services stopped"
}

cmd_restart() {
    cmd_stop
    sleep 1
    
    if [[ $EUID -eq 0 ]] && systemctl is-enabled --quiet "$APP_SERVICE" 2>/dev/null; then
        cmd_start_bg
    else
        cmd_start
    fi
}

cmd_status() {
    echo ""
    echo -e "${CYAN}=== Overture Teams Analyzer Status ===${NC}"
    echo ""
    
    # Check systemd services
    echo -e "${BLUE}Systemd Services:${NC}"
    if systemctl is-active --quiet "$APP_SERVICE" 2>/dev/null; then
        echo -e "  Web App:     ${GREEN}● Running${NC}"
    elif systemctl is-enabled --quiet "$APP_SERVICE" 2>/dev/null; then
        echo -e "  Web App:     ${YELLOW}○ Stopped (enabled)${NC}"
    else
        echo -e "  Web App:     ${RED}○ Not installed${NC}"
    fi
    
    if systemctl is-active --quiet "$HID_SERVICE" 2>/dev/null; then
        echo -e "  HID Scanner: ${GREEN}● Running${NC}"
    elif systemctl is-enabled --quiet "$HID_SERVICE" 2>/dev/null; then
        echo -e "  HID Scanner: ${YELLOW}○ Stopped (enabled)${NC}"
    else
        echo -e "  HID Scanner: ${RED}○ Not installed${NC}"
    fi
    
    # Check processes
    echo ""
    echo -e "${BLUE}Running Processes:${NC}"
    if pgrep -f "streamlit.*streamlit_app.py" >/dev/null 2>&1; then
        echo -e "  Streamlit:   ${GREEN}● Running${NC}"
    else
        echo -e "  Streamlit:   ${RED}○ Not running${NC}"
    fi
    
    if pgrep -f "headless_interceptor.py" >/dev/null 2>&1; then
        echo -e "  HID Capture: ${GREEN}● Running${NC}"
    else
        echo -e "  HID Capture: ${RED}○ Not running${NC}"
    fi
    
    # Check data files
    echo ""
    echo -e "${BLUE}Data Files:${NC}"
    if [[ -f "$DEFAULT_CSV" ]]; then
        local lines
        lines=$(wc -l < "$DEFAULT_CSV" 2>/dev/null || echo "0")
        lines=$((lines - 1))  # Subtract header
        [[ $lines -lt 0 ]] && lines=0
        echo -e "  Scouting CSV: ${GREEN}$lines records${NC}"
        echo "    Path: $DEFAULT_CSV"
    else
        echo -e "  Scouting CSV: ${YELLOW}Not created${NC}"
    fi
    
    # List backups
    if [[ -d "$BACKUP_DIR" ]]; then
        local backup_count
        backup_count=$(find "$BACKUP_DIR" -name "*.csv" 2>/dev/null | wc -l)
        echo -e "  Backups:      ${CYAN}$backup_count files${NC}"
    fi
    
    echo ""
}

cmd_logs() {
    local service="${1:-app}"
    
    case "$service" in
        app|web|streamlit)
            journalctl -u "$APP_SERVICE" -f --no-pager
            ;;
        hid|scanner)
            journalctl -u "$HID_SERVICE" -f --no-pager
            ;;
        all)
            journalctl -u "$APP_SERVICE" -u "$HID_SERVICE" -f --no-pager
            ;;
        *)
            log_error "Unknown log target: $service"
            echo "Usage: $0 logs [app|hid|all]"
            ;;
    esac
}

# ============================================================================
# Data Management Commands
# ============================================================================

cmd_backup() {
    ensure_dirs
    
    if [[ ! -f "$DEFAULT_CSV" ]]; then
        log_warn "No scouting data to backup (file doesn't exist)"
        return 0
    fi
    
    local lines
    lines=$(wc -l < "$DEFAULT_CSV" 2>/dev/null || echo "1")
    lines=$((lines - 1))
    
    if [[ $lines -le 0 ]]; then
        log_warn "Scouting file is empty (no records)"
        return 0
    fi
    
    local backup_name="${1:-}"
    local timestamp
    timestamp="$(date +%Y%m%d_%H%M%S)"
    
    if [[ -n "$backup_name" ]]; then
        # Sanitize the name (remove special chars)
        backup_name=$(echo "$backup_name" | tr -cd '[:alnum:]_-')
        backup_name="${backup_name}_${timestamp}.csv"
    else
        backup_name="scouting_backup_${timestamp}.csv"
    fi
    
    local backup_path="$BACKUP_DIR/$backup_name"
    
    cp "$DEFAULT_CSV" "$backup_path"
    
    log_info "Backup created: $backup_path"
    log_info "Contains $lines records"
}

cmd_clear() {
    if [[ ! -f "$DEFAULT_CSV" ]]; then
        log_info "No scouting data file exists"
        return 0
    fi
    
    local lines
    lines=$(wc -l < "$DEFAULT_CSV" 2>/dev/null || echo "1")
    lines=$((lines - 1))
    
    echo ""
    log_warn "This will DELETE all scouting data ($lines records)"
    echo ""
    
    # Auto-backup before clearing
    if [[ $lines -gt 0 ]]; then
        read -rp "Create backup before clearing? [Y/n] " backup_choice
        if [[ ! "$backup_choice" =~ ^[Nn]$ ]]; then
            cmd_backup "pre_clear"
        fi
    fi
    
    read -rp "Are you sure you want to clear all data? Type 'yes' to confirm: " confirm
    
    if [[ "$confirm" == "yes" ]]; then
        # Keep header only
        if [[ -f "$DEFAULT_CSV" ]]; then
            head -n 1 "$DEFAULT_CSV" > "$DEFAULT_CSV.tmp"
            mv "$DEFAULT_CSV.tmp" "$DEFAULT_CSV"
        fi
        log_info "Scouting data cleared (header preserved)"
    else
        log_warn "Cancelled"
    fi
}

cmd_list_backups() {
    ensure_dirs
    
    echo ""
    echo -e "${CYAN}=== Available Backups ===${NC}"
    echo ""
    
    if [[ -d "$BACKUP_DIR" ]]; then
        local found=0
        while IFS= read -r file; do
            if [[ -n "$file" ]]; then
                local size lines
                size=$(du -h "$file" 2>/dev/null | cut -f1)
                lines=$(wc -l < "$file" 2>/dev/null || echo "0")
                lines=$((lines - 1))
                echo "  $(basename "$file") - $lines records ($size)"
                found=1
            fi
        done < <(find "$BACKUP_DIR" -name "*.csv" -type f 2>/dev/null | sort -r)
        
        if [[ $found -eq 0 ]]; then
            echo "  No backups found"
        fi
    else
        echo "  Backup directory doesn't exist"
    fi
    echo ""
}

cmd_restore() {
    local backup_file="${1:-}"
    
    if [[ -z "$backup_file" ]]; then
        log_error "Please specify a backup file"
        cmd_list_backups
        echo "Usage: $0 restore <filename>"
        return 1
    fi
    
    # Check if it's a full path or just filename
    if [[ ! -f "$backup_file" ]]; then
        backup_file="$BACKUP_DIR/$backup_file"
    fi
    
    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    # Backup current before restore
    if [[ -f "$DEFAULT_CSV" ]]; then
        cmd_backup "pre_restore"
    fi
    
    cp "$backup_file" "$DEFAULT_CSV"
    log_info "Restored from: $(basename "$backup_file")"
}

# ============================================================================
# HID Scanner Commands
# ============================================================================

cmd_hid_list() {
    activate_venv
    local PYTHON_PATH
    PYTHON_PATH="$(get_python)"
    
    cd "$PROJECT_ROOT"
    PYTHONPATH="$LIB_DIR" "$PYTHON_PATH" "$LIB_DIR/headless_interceptor.py" --list
}

cmd_hid_start() {
    log_step "Starting HID scanner interceptor..."
    
    if [[ $EUID -ne 0 ]]; then
        log_warn "HID capture usually requires root. Trying anyway..."
    fi
    
    activate_venv
    ensure_dirs
    
    local PYTHON_PATH
    PYTHON_PATH="$(get_python)"
    
    cd "$PROJECT_ROOT"
    PYTHONPATH="$LIB_DIR" "$PYTHON_PATH" "$LIB_DIR/headless_interceptor.py" \
        --config "$LIB_DIR/config/columns.json" \
        --output "$DEFAULT_CSV" \
        "$@"
}

cmd_hid_stop() {
    log_step "Stopping HID interceptor..."
    
    if [[ $EUID -eq 0 ]]; then
        systemctl stop "$HID_SERVICE" 2>/dev/null || true
    fi
    
    pkill -f "headless_interceptor.py" 2>/dev/null || true
    
    log_info "HID interceptor stopped"
}

# ============================================================================
# Uninstall
# ============================================================================

cmd_uninstall_services() {
    check_root
    
    log_step "Uninstalling Overture services..."
    
    systemctl stop "$APP_SERVICE" 2>/dev/null || true
    systemctl stop "$HID_SERVICE" 2>/dev/null || true
    systemctl disable "$APP_SERVICE" 2>/dev/null || true
    systemctl disable "$HID_SERVICE" 2>/dev/null || true
    
    rm -f "$SYSTEMD_DIR/$APP_SERVICE"
    rm -f "$SYSTEMD_DIR/$HID_SERVICE"
    
    systemctl daemon-reload
    
    log_info "Services removed"
    log_info "Data in $DATA_DIR was NOT deleted"
    log_info "Virtual environment in $VENV_DIR was NOT deleted"
}

cmd_uninstall_all() {
    echo ""
    log_warn "This will completely uninstall Overture Teams Analyzer!"
    echo ""
    
    # Check for the uninstaller script
    local UNINSTALLER="$PROJECT_ROOT/lib/installers/uninstall_linux.sh"
    
    if [[ -f "$UNINSTALLER" ]]; then
        chmod +x "$UNINSTALLER"
        exec bash "$UNINSTALLER"
    else
        log_error "Uninstaller script not found: $UNINSTALLER"
        echo ""
        echo "To manually uninstall:"
        echo "  1. Stop services: $0 stop"
        echo "  2. Remove services: sudo $0 uninstall-services"
        echo "  3. Remove directory: rm -rf $PROJECT_ROOT"
        exit 1
    fi
}

# ============================================================================
# Help
# ============================================================================

cmd_help() {
    cat << EOF
${CYAN}Overture Teams Analyzer - Control Script${NC}

${BLUE}Usage:${NC} $0 <command> [options]

${BLUE}Installation:${NC}
  install             Install dependencies (creates venv, installs packages)
  install-services    Install systemd services (requires sudo)
  uninstall-services  Remove systemd services only (requires sudo)
  uninstall-all       Complete uninstall (stops services, removes everything)

${BLUE}App Control:${NC}
  start             Start the web app (foreground)
  start-bg          Start as background service (requires sudo)
  stop              Stop all services
  restart           Restart services
  status            Show status of services and data

${BLUE}Data Management:${NC}
  backup [name]     Backup scouting data with optional name
  clear             Clear scouting data (with confirmation)
  list-backups      Show available backups
  restore <file>    Restore from backup

${BLUE}HID Scanner:${NC}
  hid-list          List available HID input devices
  hid-start         Start HID scanner interceptor (usually needs sudo)
  hid-stop          Stop HID scanner interceptor

${BLUE}Logs:${NC}
  logs [app|hid|all]  View live logs (requires systemd services)

${BLUE}Examples:${NC}
  $0 install                # First-time setup
  $0 start                  # Run web app
  $0 backup "match_day_1"   # Backup with custom name
  $0 clear                  # Clear all data
  sudo $0 hid-start         # Start barcode scanner capture
  $0 uninstall-all          # Complete uninstall

${BLUE}Environment Variables:${NC}
  STREAMLIT_PORT    Port for web interface (default: 8501)

EOF
}

# ============================================================================
# Main
# ============================================================================

main() {
    local cmd="${1:-help}"
    shift || true
    
    case "$cmd" in
        install)
            cmd_install "$@"
            ;;
        install-services)
            cmd_install_services "$@"
            ;;
        start)
            cmd_start "$@"
            ;;
        start-bg)
            cmd_start_bg "$@"
            ;;
        stop)
            cmd_stop "$@"
            ;;
        restart)
            cmd_restart "$@"
            ;;
        status)
            cmd_status "$@"
            ;;
        logs)
            cmd_logs "$@"
            ;;
        backup)
            cmd_backup "$@"
            ;;
        clear)
            cmd_clear "$@"
            ;;
        list-backups)
            cmd_list_backups "$@"
            ;;
        restore)
            cmd_restore "$@"
            ;;
        hid-list)
            cmd_hid_list "$@"
            ;;
        hid-start)
            cmd_hid_start "$@"
            ;;
        hid-stop)
            cmd_hid_stop "$@"
            ;;
        uninstall-services)
            cmd_uninstall_services "$@"
            ;;
        uninstall-all)
            cmd_uninstall_all "$@"
            ;;
        help|--help|-h)
            cmd_help
            ;;
        *)
            log_error "Unknown command: $cmd"
            echo ""
            cmd_help
            exit 1
            ;;
    esac
}

main "$@"