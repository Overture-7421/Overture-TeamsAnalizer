# Legacy Code Directory

This directory contains Python scripts that are no longer actively used by the main application but have been preserved for historical reference and potential future use.

## Files in this directory:

### main.py
The original Tkinter-based GUI application. This was the primary desktop application before the migration to Streamlit. Contains the `AnalizadorRobot` class with full GUI integration.

### inspect_stats.py
A utility script for inspecting and debugging team statistics. Used for development and testing of the AnalizadorRobot statistics functionality.

### create_example_images.py
Utility script for generating example robot images for testing the tier list export feature.

### setup.py
Quick setup script that helps users configure the Alliance Simulator with the new CSV format. Provides interactive configuration options.

### qr_scanner.py
QR code scanning functionality using OpenCV and pyzbar. Was integrated with the Tkinter GUI for live QR code scanning during scouting.

### simple_presets.py
Configuration presets module with simplified settings for common scouting scenarios (basic scouting, offensive focused, defensive focused).

## Usage Note

These files are kept for:
1. Historical reference
2. Potential code reuse
3. Understanding the evolution of the application

The main application now uses `lib/streamlit_app.py` as the web-based entry point.

To run the legacy Tkinter GUI (if needed):
```bash
cd legacy
python main.py
```

**Note:** Some dependencies may need to be installed separately for these scripts to work.
