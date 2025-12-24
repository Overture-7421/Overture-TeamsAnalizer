#!/bin/bash
#
# Overture Teams Analyzer - Linux Service Installation Script
# This script sets up systemd services for the Streamlit web interface
# and the headless HID interceptor for barcode/QR scanner input.
#
# Tested on Debian/Ubuntu systems.
#
# Usage:
#   sudo ./scripts/install_services.sh [--install|--uninstall|--status|--enable-hid|--disable-hid]
#
# Services created:
#   - overture-app.service: Runs the Streamlit web interface
#   - overture-hid.service: Runs the headless HID interceptor (conditional)
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SERVICE_USER="${SUDO_USER:-$USER}"
SERVICE_GROUP="$(id -gn "$SERVICE_USER")"

# Paths
PYTHON_PATH="${PYTHON_PATH:-/usr/bin/python3}"
STREAMLIT_PATH="${STREAMLIT_PATH:-$(which streamlit 2>/dev/null || echo '/usr/local/bin/streamlit')}"
LIB_DIR="$PROJECT_ROOT/lib"
DATA_DIR="$PROJECT_ROOT/data"

# Service file locations
SYSTEMD_DIR="/etc/systemd/system"
APP_SERVICE="overture-app.service"
HID_SERVICE="overture-hid.service"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_dependencies() {
    print_info "Checking dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    # Check if streamlit is installed
    if ! command -v streamlit &> /dev/null; then
        print_warn "Streamlit not found in PATH. Please ensure it's installed:"
        print_warn "  pip install streamlit"
    fi
    
    # Check if evdev is installed (for HID service)
    if python3 -c "import evdev" 2>/dev/null; then
        print_info "evdev library found (HID interceptor available)"
    else
        print_warn "evdev library not installed. HID interceptor will not work."
        print_warn "Install with: pip install evdev"
    fi
    
    print_info "Project root: $PROJECT_ROOT"
    print_info "Service user: $SERVICE_USER"
}

create_app_service() {
    print_info "Creating Streamlit app service..."
    
    cat > "$SYSTEMD_DIR/$APP_SERVICE" << EOF
[Unit]
Description=Overture Teams Analyzer - Streamlit Web Interface
Documentation=https://github.com/Overture-7421/Overture-TeamsAnalizer
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$PROJECT_ROOT
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$LIB_DIR"
ExecStart=$STREAMLIT_PATH run $LIB_DIR/streamlit_app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=overture-app

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=$DATA_DIR

[Install]
WantedBy=multi-user.target
EOF

    print_info "Created $SYSTEMD_DIR/$APP_SERVICE"
}

create_hid_service() {
    print_info "Creating HID interceptor service..."
    
    cat > "$SYSTEMD_DIR/$HID_SERVICE" << EOF
[Unit]
Description=Overture Teams Analyzer - HID Barcode/QR Scanner Interceptor
Documentation=https://github.com/Overture-7421/Overture-TeamsAnalizer
After=local-fs.target
ConditionPathExists=$LIB_DIR/headless_interceptor.py
# Only start if headless mode is configured
ConditionPathExists=$LIB_DIR/columnsConfig.json

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$PROJECT_ROOT
Environment="PYTHONPATH=$LIB_DIR"
ExecStart=$PYTHON_PATH $LIB_DIR/headless_interceptor.py --config $LIB_DIR/columnsConfig.json --output $DATA_DIR/default_scouting.csv
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=overture-hid

# The HID service needs elevated permissions to access input devices
# AmbientCapabilities=CAP_DAC_READ_SEARCH

[Install]
WantedBy=multi-user.target
EOF

    print_info "Created $SYSTEMD_DIR/$HID_SERVICE"
}

install_services() {
    check_root
    check_dependencies
    
    print_info "Installing Overture services..."
    
    # Ensure data directory exists
    mkdir -p "$DATA_DIR"
    chown "$SERVICE_USER:$SERVICE_GROUP" "$DATA_DIR"
    
    # Create service files
    create_app_service
    create_hid_service
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable and start the app service
    systemctl enable "$APP_SERVICE"
    systemctl start "$APP_SERVICE"
    
    print_info "Services installed successfully!"
    print_info ""
    print_info "The Streamlit app service is now running."
    print_info "Access the web interface at: http://localhost:8501"
    print_info ""
    print_info "To enable the HID interceptor service (for barcode scanner), run:"
    print_info "  sudo $0 --enable-hid"
    print_info ""
    print_info "View logs with:"
    print_info "  journalctl -u overture-app -f"
    print_info "  journalctl -u overture-hid -f"
}

uninstall_services() {
    check_root
    
    print_info "Uninstalling Overture services..."
    
    # Stop services
    systemctl stop "$APP_SERVICE" 2>/dev/null || true
    systemctl stop "$HID_SERVICE" 2>/dev/null || true
    
    # Disable services
    systemctl disable "$APP_SERVICE" 2>/dev/null || true
    systemctl disable "$HID_SERVICE" 2>/dev/null || true
    
    # Remove service files
    rm -f "$SYSTEMD_DIR/$APP_SERVICE"
    rm -f "$SYSTEMD_DIR/$HID_SERVICE"
    
    # Reload systemd
    systemctl daemon-reload
    
    print_info "Services uninstalled successfully!"
}

enable_hid_service() {
    check_root
    
    print_info "Enabling HID interceptor service..."
    
    # Add user to input group for device access
    if ! groups "$SERVICE_USER" | grep -q '\binput\b'; then
        print_info "Adding $SERVICE_USER to 'input' group..."
        usermod -a -G input "$SERVICE_USER"
        print_warn "User added to 'input' group. A logout/login may be required for changes to take effect."
    fi
    
    # Enable and start HID service
    systemctl enable "$HID_SERVICE"
    systemctl start "$HID_SERVICE"
    
    print_info "HID interceptor service enabled and started!"
    print_info ""
    print_info "Make sure to configure the scanner hardware ID in:"
    print_info "  $LIB_DIR/columnsConfig.json"
    print_info ""
    print_info "To find your scanner's hardware ID, run:"
    print_info "  python3 $LIB_DIR/headless_interceptor.py --list"
}

disable_hid_service() {
    check_root
    
    print_info "Disabling HID interceptor service..."
    
    systemctl stop "$HID_SERVICE" 2>/dev/null || true
    systemctl disable "$HID_SERVICE" 2>/dev/null || true
    
    print_info "HID interceptor service disabled."
}

show_status() {
    print_info "Service Status"
    echo ""
    echo "=== Streamlit App Service ==="
    systemctl status "$APP_SERVICE" --no-pager 2>/dev/null || echo "Not installed"
    echo ""
    echo "=== HID Interceptor Service ==="
    systemctl status "$HID_SERVICE" --no-pager 2>/dev/null || echo "Not installed"
}

show_help() {
    echo "Overture Teams Analyzer - Service Installation Script"
    echo ""
    echo "Usage: sudo $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  --install      Install and start services (default)"
    echo "  --uninstall    Stop and remove services"
    echo "  --status       Show service status"
    echo "  --enable-hid   Enable the HID interceptor service"
    echo "  --disable-hid  Disable the HID interceptor service"
    echo "  --help         Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  PYTHON_PATH    Path to Python 3 interpreter (default: /usr/bin/python3)"
    echo "  STREAMLIT_PATH Path to streamlit command (default: auto-detect)"
    echo ""
    echo "Examples:"
    echo "  sudo $0 --install           # Install and start services"
    echo "  sudo $0 --enable-hid        # Enable barcode scanner support"
    echo "  sudo $0 --status            # Check service status"
}

# Main script logic
case "${1:-install}" in
    --install|install)
        install_services
        ;;
    --uninstall|uninstall)
        uninstall_services
        ;;
    --status|status)
        show_status
        ;;
    --enable-hid|enable-hid)
        enable_hid_service
        ;;
    --disable-hid|disable-hid)
        disable_hid_service
        ;;
    --help|help|-h)
        show_help
        ;;
    *)
        print_error "Unknown option: $1"
        show_help
        exit 1
        ;;
esac
