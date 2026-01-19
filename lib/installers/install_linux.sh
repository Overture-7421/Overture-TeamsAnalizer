#!/usr/bin/env bash
#
# Overture Teams Analyzer - Quick Installer for DietPi/Debian
#
# This script:
#   1. Clones the repository (or updates if exists)
#   2. Runs the installation
#   3. Sets up the control script
#
# Usage:
#   curl -sSL <url> | bash
#   or
#   ./install_linux.sh
#

set -euo pipefail

# Configuration
REPO_URL="https://github.com/Overture-7421/Overture-TeamsAnalizer.git"
REPO_SSH="git@github.com:Overture-7421/Overture-TeamsAnalizer.git"
INSTALL_DIR="${INSTALL_DIR:-$HOME/Overture-TeamsAnalizer}"

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
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       Overture Teams Analyzer - Quick Installer              ║${NC}"
echo -e "${CYAN}║                   For DietPi/Debian                          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Branch selection
echo -e "${YELLOW}Select branch to install:${NC}"
echo ""
echo "  1) FTC-Emergencia  (FTC scouting - recommended)"
echo "  2) main            (Stable release)"
echo "  3) FRC             (FRC scouting)"
echo "  4) Custom          (Enter branch name)"
echo ""
read -rp "Choice [1-4, default=1]: " branch_choice

case "${branch_choice:-1}" in
    1|"")
        BRANCH="FTC-Emergencia"
        ;;
    2)
        BRANCH="main"
        ;;
    3)
        BRANCH="FRC"
        ;;
    4)
        read -rp "Enter branch name: " custom_branch
        if [[ -z "$custom_branch" ]]; then
            log_error "Branch name cannot be empty"
            exit 1
        fi
        BRANCH="$custom_branch"
        ;;
    *)
        log_error "Invalid choice"
        exit 1
        ;;
esac

log_info "Selected branch: $BRANCH"
echo ""

# Check prerequisites
log_step "Checking prerequisites..."

if ! command -v git &>/dev/null; then
    log_error "git not found. Install with: sudo apt install git"
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    log_error "Python 3 not found. Install with: sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
log_info "Python $PYTHON_VERSION detected"

# Clone or update repository
if [[ -d "$INSTALL_DIR/.git" ]]; then
    log_step "Updating existing installation..."
    cd "$INSTALL_DIR"
    git fetch origin
    git checkout "$BRANCH" 2>/dev/null || git checkout -b "$BRANCH" "origin/$BRANCH" 2>/dev/null || true
    git pull origin "$BRANCH" || log_warn "Could not pull updates (may have local changes)"
else
    log_step "Cloning repository..."
    
    # Try HTTPS first (more likely to work without SSH key)
    if git clone --depth 1 -b "$BRANCH" "$REPO_URL" "$INSTALL_DIR" 2>/dev/null; then
        log_info "Cloned via HTTPS"
    elif git clone --depth 1 -b "$BRANCH" "$REPO_SSH" "$INSTALL_DIR" 2>/dev/null; then
        log_info "Cloned via SSH"
    else
        log_error "Failed to clone repository"
        exit 1
    fi
fi

cd "$INSTALL_DIR"

# Make control script executable
chmod +x scripts/overture-ctl.sh

# Run installation
log_step "Running installation..."
./scripts/overture-ctl.sh install

# Create symlink for easy access
SYMLINK_PATH="/usr/local/bin/overture-ctl"
if [[ -w "/usr/local/bin" ]] || [[ $EUID -eq 0 ]]; then
    ln -sf "$INSTALL_DIR/scripts/overture-ctl.sh" "$SYMLINK_PATH" 2>/dev/null || true
    log_info "Created symlink: overture-ctl"
else
    log_warn "Run this to create global command (optional):"
    echo "    sudo ln -sf $INSTALL_DIR/scripts/overture-ctl.sh $SYMLINK_PATH"
fi

# Final instructions
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                 Installation Complete!                       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Installation directory: ${CYAN}$INSTALL_DIR${NC}"
echo ""
echo -e "${YELLOW}Quick Start:${NC}"
echo ""
echo "  Start the web app:"
echo -e "    ${CYAN}cd $INSTALL_DIR && ./scripts/overture-ctl.sh start${NC}"
echo ""
echo "  Or if symlink was created:"
echo -e "    ${CYAN}overture-ctl start${NC}"
echo ""
echo -e "${YELLOW}Other Commands:${NC}"
echo "  overture-ctl status      # Check status"
echo "  overture-ctl backup      # Backup data"
echo "  overture-ctl clear       # Clear data"
echo "  overture-ctl --help      # Full help"
echo ""

IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')
echo -e "${GREEN}Web interface will be at: http://$IP:8501${NC}"
echo ""
