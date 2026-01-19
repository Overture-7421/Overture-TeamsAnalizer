#!/usr/bin/env bash
#
# Overture Teams Analyzer - Uninstaller for DietPi/Debian
#
# This script:
#   1. Stops all running services and processes
#   2. Removes systemd service files
#   3. Removes the installation directory
#   4. Keeps the installer available for reinstallation
#
# Usage:
#   ./uninstall_linux.sh
#

set -euo pipefail

# Configuration
INSTALL_DIR="${INSTALL_DIR:-$HOME/Overture-TeamsAnalizer}"
SYSTEMD_DIR="/etc/systemd/system"
APP_SERVICE="overture-app.service"
HID_SERVICE="overture-hid.service"
SYMLINK_PATH="/usr/local/bin/overture-ctl"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_step()  { echo -e "${CYAN}[→]${NC} $1"; }

echo ""
echo -e "${RED}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║       Overture Teams Analyzer - Uninstaller                  ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if installation exists
if [[ ! -d "$INSTALL_DIR" ]]; then
    log_warn "Installation directory not found: $INSTALL_DIR"
    echo ""
    read -rp "Enter installation path (or press Enter to cancel): " custom_path
    if [[ -z "$custom_path" ]]; then
        log_info "Uninstall cancelled"
        exit 0
    fi
    INSTALL_DIR="$custom_path"
    if [[ ! -d "$INSTALL_DIR" ]]; then
        log_error "Directory does not exist: $INSTALL_DIR"
        exit 1
    fi
fi

echo -e "Installation directory: ${CYAN}$INSTALL_DIR${NC}"
echo ""

# Check for data files
DATA_DIR="$INSTALL_DIR/data"
BACKUP_DIR="$INSTALL_DIR/backups"
has_data=false

if [[ -f "$DATA_DIR/default_scouting.csv" ]]; then
    lines=$(wc -l < "$DATA_DIR/default_scouting.csv" 2>/dev/null || echo "1")
    lines=$((lines - 1))
    if [[ $lines -gt 0 ]]; then
        has_data=true
        echo -e "${YELLOW}WARNING: You have $lines scouting records that will be deleted!${NC}"
    fi
fi

if [[ -d "$BACKUP_DIR" ]]; then
    backup_count=$(find "$BACKUP_DIR" -name "*.csv" 2>/dev/null | wc -l)
    if [[ $backup_count -gt 0 ]]; then
        has_data=true
        echo -e "${YELLOW}WARNING: You have $backup_count backup files that will be deleted!${NC}"
    fi
fi

echo ""
echo -e "${RED}This will permanently delete:${NC}"
echo "  • All scouting data"
echo "  • All backup files"
echo "  • The virtual environment"
echo "  • All application files"
echo ""

# Offer to backup before uninstall
if [[ "$has_data" == true ]]; then
    read -rp "Would you like to backup data before uninstalling? [Y/n] " backup_choice
    if [[ ! "$backup_choice" =~ ^[Nn]$ ]]; then
        backup_dest="$HOME/overture_backup_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$backup_dest"
        
        if [[ -d "$DATA_DIR" ]]; then
            cp -r "$DATA_DIR" "$backup_dest/" 2>/dev/null || true
        fi
        if [[ -d "$BACKUP_DIR" ]]; then
            cp -r "$BACKUP_DIR" "$backup_dest/" 2>/dev/null || true
        fi
        
        log_info "Data backed up to: $backup_dest"
        echo ""
    fi
fi

# Final confirmation
read -rp "Are you sure you want to uninstall? Type 'yes' to confirm: " confirm

if [[ "$confirm" != "yes" ]]; then
    log_info "Uninstall cancelled"
    exit 0
fi

echo ""
log_step "Stopping services and processes..."

# Stop any running processes
pkill -f "streamlit.*streamlit_app.py" 2>/dev/null || true
pkill -f "headless_interceptor.py" 2>/dev/null || true

# Stop and remove systemd services (requires sudo)
if [[ $EUID -eq 0 ]]; then
    # Running as root
    systemctl stop "$APP_SERVICE" 2>/dev/null || true
    systemctl stop "$HID_SERVICE" 2>/dev/null || true
    systemctl disable "$APP_SERVICE" 2>/dev/null || true
    systemctl disable "$HID_SERVICE" 2>/dev/null || true
    rm -f "$SYSTEMD_DIR/$APP_SERVICE" 2>/dev/null || true
    rm -f "$SYSTEMD_DIR/$HID_SERVICE" 2>/dev/null || true
    systemctl daemon-reload 2>/dev/null || true
    log_info "Systemd services removed"
else
    # Not running as root, try with sudo
    if sudo -n true 2>/dev/null; then
        sudo systemctl stop "$APP_SERVICE" 2>/dev/null || true
        sudo systemctl stop "$HID_SERVICE" 2>/dev/null || true
        sudo systemctl disable "$APP_SERVICE" 2>/dev/null || true
        sudo systemctl disable "$HID_SERVICE" 2>/dev/null || true
        sudo rm -f "$SYSTEMD_DIR/$APP_SERVICE" 2>/dev/null || true
        sudo rm -f "$SYSTEMD_DIR/$HID_SERVICE" 2>/dev/null || true
        sudo systemctl daemon-reload 2>/dev/null || true
        log_info "Systemd services removed"
    else
        log_warn "Cannot remove systemd services without sudo"
        echo "  Run manually if needed:"
        echo "    sudo systemctl stop $APP_SERVICE"
        echo "    sudo systemctl disable $APP_SERVICE"
        echo "    sudo rm /etc/systemd/system/$APP_SERVICE"
    fi
fi

log_step "Removing symlink..."

# Remove symlink
if [[ -L "$SYMLINK_PATH" ]]; then
    if [[ $EUID -eq 0 ]]; then
        rm -f "$SYMLINK_PATH"
        log_info "Symlink removed: $SYMLINK_PATH"
    elif sudo -n true 2>/dev/null; then
        sudo rm -f "$SYMLINK_PATH"
        log_info "Symlink removed: $SYMLINK_PATH"
    else
        log_warn "Cannot remove symlink without sudo: $SYMLINK_PATH"
    fi
fi

log_step "Removing installation directory..."

# Save installer to temp location before deleting
INSTALLER_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
TEMP_INSTALLER="/tmp/overture_install_linux.sh"

# Copy installer to /tmp so it survives deletion
if [[ -f "$INSTALLER_SCRIPT" ]]; then
    cp "$INSTALLER_SCRIPT" "$TEMP_INSTALLER"
    chmod +x "$TEMP_INSTALLER"
fi

# Also copy the installer to home directory for easy reinstall
HOME_INSTALLER="$HOME/overture_install_linux.sh"
if [[ -f "$INSTALLER_SCRIPT" ]]; then
    cp "$INSTALLER_SCRIPT" "$HOME_INSTALLER"
    chmod +x "$HOME_INSTALLER"
fi

# Remove installation directory
rm -rf "$INSTALL_DIR"
log_info "Installation directory removed"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Uninstallation Complete!                        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "The installer has been saved to:"
echo -e "  ${CYAN}$HOME_INSTALLER${NC}"
echo ""
echo -e "To reinstall, run:"
echo -e "  ${CYAN}bash $HOME_INSTALLER${NC}"
echo ""

if [[ "$has_data" == true ]] && [[ -d "${backup_dest:-}" ]]; then
    echo -e "Your data backup is at:"
    echo -e "  ${CYAN}$backup_dest${NC}"
    echo ""
fi

log_info "Thank you for using Overture Teams Analyzer!"
echo ""
