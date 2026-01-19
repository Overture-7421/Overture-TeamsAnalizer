#!/bin/bash
#
# Overture Teams Analyzer - Systemd Service Installer
#
# This is a wrapper that calls overture-ctl.sh for service management.
# For full functionality, use overture-ctl.sh directly.
#
# Usage:
#   sudo ./scripts/install_services.sh [--install|--uninstall|--status]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CTL_SCRIPT="$SCRIPT_DIR/overture-ctl.sh"

# Make sure control script is executable
chmod +x "$CTL_SCRIPT"

show_help() {
    echo ""
    echo "Overture Teams Analyzer - Service Manager"
    echo ""
    echo "This script is a wrapper for overture-ctl.sh"
    echo ""
    echo "Usage: sudo $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  --install      Install systemd services"
    echo "  --uninstall    Remove systemd services"
    echo "  --status       Show service status"
    echo "  --help         Show this help"
    echo ""
    echo "For full functionality, use overture-ctl.sh:"
    echo "  $CTL_SCRIPT --help"
    echo ""
}

case "${1:---help}" in
    --install|install)
        "$CTL_SCRIPT" install-services
        ;;
    --uninstall|uninstall)
        "$CTL_SCRIPT" uninstall
        ;;
    --status|status)
        "$CTL_SCRIPT" status
        ;;
    --enable-hid|enable-hid)
        echo "To start HID scanner, use:"
        echo "  sudo $CTL_SCRIPT hid-start"
        ;;
    --disable-hid|disable-hid)
        "$CTL_SCRIPT" hid-stop
        ;;
    --help|help|-h)
        show_help
        ;;
    *)
        echo "Unknown option: $1"
        show_help
        exit 1
        ;;
esac

