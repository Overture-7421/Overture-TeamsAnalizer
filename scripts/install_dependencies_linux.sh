#!/usr/bin/env bash
#
# Overture Teams Analyzer - Dependencies Installer for DietPi/Debian
#
# This script:
#   - Creates a Python virtual environment
#   - Installs all required Python packages
#   - Installs system dependencies (libzbar0 for QR scanning)
#
# Usage: ./scripts/install_dependencies_linux.sh
#

set -euo pipefail

# Find project root
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
log_step()  { echo -e "${CYAN}[→]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

echo ""
echo -e "${CYAN}Installing Overture Teams Analyzer Dependencies${NC}"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    log_error "Python 3 not found!"
    echo "Install with: sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
log_info "Python $PYTHON_VERSION detected"

# Create virtual environment
if [[ ! -d ".venv" ]]; then
    log_step "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate venv
log_step "Activating virtual environment..."
# shellcheck disable=SC1091
source .venv/bin/activate

# Upgrade pip
log_step "Upgrading pip..."
python -m pip install --upgrade pip wheel setuptools --quiet

# Install Python packages
log_step "Installing Python packages..."
python -m pip install -r requirements_web.txt --quiet

# Install system dependencies
log_step "Checking system dependencies..."
if command -v apt-get &>/dev/null; then
    # Check for libzbar (needed for QR scanning)
    if ! dpkg -l libzbar0 &>/dev/null 2>&1; then
        log_warn "libzbar0 not installed. Attempting to install..."
        if [[ $EUID -eq 0 ]]; then
            apt-get update && apt-get install -y libzbar0
        else
            sudo apt-get update && sudo apt-get install -y libzbar0 || {
                log_warn "Could not install libzbar0 automatically."
                echo "Install manually with: sudo apt-get install libzbar0"
            }
        fi
    else
        log_info "libzbar0 already installed"
    fi
fi

# Create required directories
mkdir -p data backups

log_info "Dependencies installed successfully!"
echo ""
echo -e "${GREEN}To start the application:${NC}"
echo ""
echo "  source .venv/bin/activate"
echo "  streamlit run lib/streamlit_app.py"
echo ""
echo -e "${GREEN}Or use the control script:${NC}"
echo ""
echo "  ./scripts/overture-ctl.sh start"
echo ""

# Show IP for convenience
IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')
echo -e "Web interface will be at: ${CYAN}http://$IP:8501${NC}"
echo ""

