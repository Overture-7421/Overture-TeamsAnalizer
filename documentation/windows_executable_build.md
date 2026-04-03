# Windows Executable Build

This guide explains how to build a Windows executable distribution for the Streamlit app.

## Prerequisites

- Windows 10/11
- Python 3.8+
- Git (optional, only needed if cloning)

## Build Command

From the repository root, run:

```cmd
scripts\build_windows_exe.cmd
```

The script will:

1. Create `.venv` if it does not exist.
2. Install/update `pyinstaller`.
3. Install app dependencies from `requirements_web.txt`.
4. Build a one-folder executable distribution.

## Build Output

- Executable: `dist\OvertureTeamsAnalyzer\OvertureTeamsAnalyzer.exe`

## Run The Executable

Double-click the executable, or run:

```cmd
dist\OvertureTeamsAnalyzer\OvertureTeamsAnalyzer.exe
```

The app starts a local Streamlit server (default port `8501`).

If you need another port:

```cmd
set OVERTURE_PORT=8502
dist\OvertureTeamsAnalyzer\OvertureTeamsAnalyzer.exe
```

## Notes

- This package includes `lib`, `data`, and `config` folders required by the app.
- If QR scanning fails on a target machine, install required camera/decoder runtime dependencies (for example, ZBar where needed by `pyzbar`).

## Zip Distribution

To create a shareable zip archive after building:

```cmd
scripts\zip_windows_release.cmd
```

Output archive:

- `releases\OvertureTeamsAnalyzer-windows.zip`
