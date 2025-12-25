#!/usr/bin/env bash
set -euo pipefail

# Installs Python dependencies for Overture-TeamsAnalizer (Linux)
# - Creates a local venv in .venv
# - Installs requirements_web.txt

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3.8+ first." >&2
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment in .venv ..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements_web.txt

echo
echo "Done."
echo "Run the app with:"
echo "  source .venv/bin/activate"
echo "  streamlit run streamlit_app.py"
echo
echo "If QR scanning fails with a ZBar error, install system ZBar (example on Debian/Ubuntu):"
echo "  sudo apt-get update && sudo apt-get install -y libzbar0"
