# macOS Executable Build

This guide explains how to build a macOS executable distribution for the Streamlit app.

## Important Platform Note

PyInstaller builds are platform-specific.
To generate a macOS executable, run this build on a macOS machine.

## Prerequisites

- macOS (Intel or Apple Silicon)
- Python 3.8+
- Xcode Command Line Tools (recommended)

## Build Command

From the repository root, run:

```bash
chmod +x scripts/build_macos_executable.sh
./scripts/build_macos_executable.sh
```

The script will:

1. Create `.venv` if it does not exist.
2. Install/update `pyinstaller`.
3. Install app dependencies from `requirements_web.txt`.
4. Build a one-folder executable distribution.

## Build Output

- Executable: `dist/OvertureTeamsAnalyzer/OvertureTeamsAnalyzer`

## Run The Executable

```bash
./dist/OvertureTeamsAnalyzer/OvertureTeamsAnalyzer
```

The app starts a local Streamlit server (default port `8501`).

If you need another port:

```bash
export OVERTURE_PORT=8502
./dist/OvertureTeamsAnalyzer/OvertureTeamsAnalyzer
```

## Notes

- This package includes `lib`, `data`, and `config` folders required by the app.
- If the app is blocked by Gatekeeper, run from Terminal and allow execution in macOS Security settings if prompted.
- If QR scanning fails on a target machine, install required camera/decoder runtime dependencies (for example, ZBar where needed by `pyzbar`).

## Zip Distribution

To create a shareable zip archive after building:

```bash
chmod +x scripts/zip_macos_release.sh
./scripts/zip_macos_release.sh
```

Output archive:

- `releases/OvertureTeamsAnalyzer-macos.zip`
