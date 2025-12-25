#!/usr/bin/env bash
set -euo pipefail

# One-shot installer (Linux) - clones and installs from:
#   git@github.com:Overture-7421/Overture-TeamsAnalizer.git

REPO_SSH="git@github.com:Overture-7421/Overture-TeamsAnalizer.git"
INSTALL_DIR="$HOME/Overture-TeamsAnalizer"

if ! command -v git >/dev/null 2>&1; then
  echo "git not found. Install git first." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3.8+ first." >&2
  exit 1
fi

if [ ! -d "$INSTALL_DIR" ]; then
  echo "Cloning repo into: $INSTALL_DIR"
  git clone --depth 1 "$REPO_SSH" "$INSTALL_DIR"
else
  echo "Repo folder already exists: $INSTALL_DIR"
  echo "Skipping clone."
fi

cd "$INSTALL_DIR"

if [ -f "scripts/install_dependencies_linux.sh" ]; then
  bash scripts/install_dependencies_linux.sh
else
  echo "Missing scripts/install_dependencies_linux.sh in repo." >&2
  echo "You can install deps manually with:" >&2
  echo "  python3 -m venv .venv" >&2
  echo "  source .venv/bin/activate" >&2
  echo "  pip install -r requirements_web.txt" >&2
fi
