# Overture Teams Analyzer - DietPi/Raspberry Pi Setup Guide

## Quick Start

### 1. Install

Run the installer on your Raspberry Pi:

```bash
# Clone and install
git clone -b FTC-Emergencia https://github.com/Overture-7421/Overture-TeamsAnalizer.git
cd Overture-TeamsAnalizer
./scripts/overture-ctl.sh install
```

Or use the one-shot installer:
```bash
bash lib/installers/install_linux.sh
```

### 2. Start the Web App

```bash
./scripts/overture-ctl.sh start
```

Access the web interface at: `http://<raspberry-pi-ip>:8501`

---

## Control Script Commands

The `overture-ctl.sh` script is your main tool for managing the application.

### App Control

| Command | Description |
|---------|-------------|
| `./scripts/overture-ctl.sh start` | Start web app (foreground) |
| `sudo ./scripts/overture-ctl.sh start-bg` | Start as background service |
| `./scripts/overture-ctl.sh stop` | Stop all services |
| `./scripts/overture-ctl.sh restart` | Restart services |
| `./scripts/overture-ctl.sh status` | Show status |

### Data Management

| Command | Description |
|---------|-------------|
| `./scripts/overture-ctl.sh backup` | Backup scouting data |
| `./scripts/overture-ctl.sh backup "match_day_1"` | Backup with custom name |
| `./scripts/overture-ctl.sh list-backups` | Show available backups |
| `./scripts/overture-ctl.sh restore <filename>` | Restore from backup |
| `./scripts/overture-ctl.sh clear` | Clear all data (with confirmation) |

### HID Scanner (Barcode/QR)

| Command | Description |
|---------|-------------|
| `./scripts/overture-ctl.sh hid-list` | List available HID devices |
| `sudo ./scripts/overture-ctl.sh hid-start` | Start HID scanner capture |
| `./scripts/overture-ctl.sh hid-stop` | Stop HID scanner |

---

## Systemd Services (Optional)

For running as a background service that starts on boot:

```bash
# Install services
sudo ./scripts/overture-ctl.sh install-services

# Enable auto-start on boot
sudo systemctl enable overture-app

# View logs
journalctl -u overture-app -f
```

---

## File Locations

| Path | Description |
|------|-------------|
| `data/default_scouting.csv` | Main scouting data file |
| `backups/` | Backup files |
| `.venv/` | Python virtual environment |
| `lib/config/columns.json` | Column configuration |

---

## Troubleshooting

### Web app won't start

1. Check Python version: `python3 --version` (needs 3.8+)
2. Reinstall dependencies: `./scripts/overture-ctl.sh install`
3. Check logs: `journalctl -u overture-app -n 50`

### QR scanning fails

Install libzbar:
```bash
sudo apt-get install libzbar0
```

### HID scanner permission denied

Add your user to the input group:
```bash
sudo usermod -a -G input $USER
# Then log out and back in
```

Or run with sudo:
```bash
sudo ./scripts/overture-ctl.sh hid-start
```

### Find your scanner device

```bash
./scripts/overture-ctl.sh hid-list
```

Look for devices with "barcode", "scanner", or "HID" in the name.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STREAMLIT_PORT` | `8501` | Web interface port |
| `INSTALL_DIR` | `~/Overture-TeamsAnalizer` | Installation directory |
| `BRANCH` | `FTC-Emergencia` | Git branch to use |

---

## DietPi-Specific Notes

1. **LXQT Desktop**: The web app runs in any browser. Chromium is recommended.

2. **Performance**: The app is optimized for Raspberry Pi 4 with:
   - Lazy loading of heavy libraries (Plotly, PIL)
   - Cached configuration files
   - Minified CSS

3. **Memory**: Close other applications if running low on RAM.

4. **Auto-start**: Add to LXQT autostart or use systemd services.
