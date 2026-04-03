#!/usr/bin/env bash
set -euo pipefail

# Create a zip release for the macOS onedir distribution.
# Output: releases/OvertureTeamsAnalyzer-macos.zip

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script must be run on macOS (Darwin)."
  exit 1
fi

if [[ ! -x "dist/OvertureTeamsAnalyzer/OvertureTeamsAnalyzer" ]]; then
  echo "macOS build not found."
  echo "Run ./scripts/build_macos_executable.sh first."
  exit 1
fi

mkdir -p releases

ditto -c -k --sequesterRsrc --keepParent \
  "dist/OvertureTeamsAnalyzer" \
  "releases/OvertureTeamsAnalyzer-macos.zip"

echo
echo "Zip package created successfully."
echo "Archive: releases/OvertureTeamsAnalyzer-macos.zip"
