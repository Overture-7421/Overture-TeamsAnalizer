# Overture Teams Analyzer Documentation

Welcome to the documentation for the **Overture Teams Analyzer** — an FRC scouting and alliance simulation tool developed by Team Overture 7421 for the **FRC REBUILT 2026** season.

## Table of Contents

### Program Documentation

- [Engine (engine.py)](./engine.md) - Core data processing and analysis engine
- [QR Utilities (qr_utils.py)](./qr_utils.md) - Camera-based QR code scanning
- [Headless Interceptor (headless_interceptor.py)](./headless_interceptor.md) - HID barcode scanner capture for Linux
- [Streamlit App (streamlit_app.py)](./streamlit_app.md) - Web interface for the application
- [Alliance Selector (allianceSelector.py)](./alliance_selector.md) - Alliance selection and optimization (3-robot alliances)
- [Config Manager (config_manager.py)](./config_manager.md) - Configuration file management
- [TBA Manager (tba_manager.py)](./tba_manager.md) - The Blue Alliance API integration
- [School System (school_system.py)](./school_system.md) - Honor Roll scoring system
- [Foreshadowing (foreshadowing.py)](./foreshadowing.md) - Match prediction and simulation
- [CSV Converter (csv_converter.py)](./csv_converter.md) - CSV format conversion utilities

### Linux Server Guides

- [Linux Headless Server Setup](./linux_headless_server_setup.md) - Complete guide for setting up a headless scouting server on any Linux system (Raspberry Pi, DietPi, Fedora, Arch, Ubuntu, etc.)
- [Systemd Services Configuration](./systemd_services.md) - Autostart services configuration for Linux
- [HID Scanner Configuration](./hid_scanner_configuration.md) - Configuring barcode/QR scanners as HID devices

### Build & Packaging

- [Windows Executable Build](./windows_executable_build.md) - Build a distributable `.exe` package with PyInstaller
- [macOS Executable Build](./macos_executable_build.md) - Build a distributable macOS executable package with PyInstaller

## Quick Start

### For Desktop Users (GUI)
```bash
pip install -r requirements_web.txt
streamlit run lib/streamlit_app.py
```

### For Headless Linux Servers
See [Linux Headless Server Setup](./linux_headless_server_setup.md) for complete instructions.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                Overture Teams Analyzer — FRC REBUILT 2026         │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐    ┌─────────────────┐    ┌───────────────┐ │
│  │  Streamlit App  │    │ Headless HID    │    │  QR Scanner   │ │
│  │  (Web UI)       │    │ Interceptor     │    │  (Camera)     │ │
│  └────────┬────────┘    └────────┬────────┘    └───────┬───────┘ │
│           │                      │                      │         │
│           └──────────────────────┼──────────────────────┘         │
│                                  ▼                                │
│                       ┌──────────────────┐                        │
│                       │   AnalizadorRobot │                        │
│                       │   (Engine)        │                        │
│                       └────────┬─────────┘                        │
│                                │                                  │
│           ┌────────────────────┼────────────────────┐             │
│           ▼                    ▼                    ▼             │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐     │
│  │  Config Manager │ │  CSV Converter  │ │  TBA Manager    │     │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘     │
│                                                                   │
│           ┌────────────────────┼────────────────────┐             │
│           ▼                    ▼                    ▼             │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐     │
│  │ Alliance Selector│ │ Foreshadowing  │ │  School System  │     │
│  │ (3 robots/allnc) │ │                │ │                 │     │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘     │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow

1. **Data Input Sources:**
   - Manual CSV upload via web interface
   - QR code scanning via camera
   - HID barcode scanner (headless mode)

2. **Processing:**
   - Data is loaded into `AnalizadorRobot` engine
   - Statistics are calculated per team
   - Rankings are generated

3. **Output:**
   - Web dashboard with visualizations
   - Alliance recommendations (3 robots per alliance: captain + pick 1 + pick 2)
   - Match predictions
   - Post-match analytics
   - Export to CSV/TierList format

## Game: FRC REBUILT 2026

### Scoring Summary

| Action | Points |
|--------|--------|
| Leave Launch Line (Auto) | 3 |
| FUEL in Active HUB | 1 each |
| Tower Level 1 (Auto, max 2 robots) | 15 |
| Tower Level 1 (Endgame) | 10 |
| Tower Level 2 (Endgame) | 20 |
| Tower Level 3 (Endgame) | 30 |
| Minor Foul (opponent) | +5 |
| Major Foul (opponent) | +15 |

### Ranking Points
- **ENERGIZED RP:** 100+ Fuel in active HUB
- **SUPERCHARGED RP:** 360+ Fuel in active HUB
- **TRAVERSAL RP:** 50+ Tower points
- **Win:** 3 RP | **Tie:** 1 RP

## Requirements

- Python 3.8+
- See `requirements_web.txt` for full dependencies

## Support

For issues or questions, please open an issue on the GitHub repository.
