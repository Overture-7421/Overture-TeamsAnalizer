#!/usr/bin/env bash
set -euo pipefail

# Build a macOS executable distribution for Overture Teams Analyzer.
# Output: dist/OvertureTeamsAnalyzer/OvertureTeamsAnalyzer

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script must be run on macOS (Darwin)."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found in PATH."
  echo "Install Python 3.8+ and try again."
  exit 1
fi

if [[ ! -d ".venv" ]]; then
  echo "Creating virtual environment in .venv ..."
  python3 -m venv .venv
fi

VENV_PYTHON=".venv/bin/python"

echo "Installing/updating build dependencies ..."
"$VENV_PYTHON" -m pip install --upgrade pip pyinstaller

echo "Installing application dependencies ..."
"$VENV_PYTHON" -m pip install -r requirements_web.txt

echo "Validating required modules for packaging ..."
"$VENV_PYTHON" -c "import streamlit, pandas, numpy, cv2, plotly, PIL, pyzbar"

echo "Building executable with PyInstaller ..."
"$VENV_PYTHON" -m PyInstaller \
  --noconfirm \
  --clean \
  --onedir \
  --specpath "build" \
  --name "OvertureTeamsAnalyzer" \
  --add-data "$ROOT_DIR/streamlit_app.py:." \
  --add-data "$ROOT_DIR/lib:lib" \
  --add-data "$ROOT_DIR/data:data" \
  --add-data "$ROOT_DIR/config:config" \
  --collect-all streamlit \
  --collect-all plotly \
  --collect-all pyzbar \
  --collect-all PIL \
  --hidden-import cv2 \
  --hidden-import numpy \
  --hidden-import pandas \
  --paths "." \
  "scripts/streamlit_launcher.py"

echo
echo "Build completed successfully."
echo "Executable: dist/OvertureTeamsAnalyzer/OvertureTeamsAnalyzer"
echo
echo "Optional: set OVERTURE_PORT before launch if you need a custom port."
echo "  export OVERTURE_PORT=8502"
