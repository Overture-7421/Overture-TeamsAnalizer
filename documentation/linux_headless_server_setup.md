# Linux Headless Server Setup

Complete guide for setting up the Overture Teams Analyzer as a headless scouting server on Raspberry Pi with DietPi (Debian ARM) and LXQt desktop environment.

## Table of Contents

1. [Overview](#overview)
2. [Hardware Requirements](#hardware-requirements)
3. [System Setup](#system-setup)
4. [Installing Dependencies](#installing-dependencies)
5. [Project Installation](#project-installation)
6. [Scanner Configuration](#scanner-configuration)
7. [Default CSV Loading](#default-csv-loading)
8. [Autostart Services](#autostart-services)
9. [Accessing the Web Interface](#accessing-the-web-interface)
10. [Troubleshooting](#troubleshooting)

## Overview

This guide sets up a headless scouting server that:

- Runs the Streamlit web interface on boot
- Captures barcode/QR scanner input without window focus
- Automatically saves scanned data to CSV
- Hot-reloads data in the web interface

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Raspberry Pi / DietPi                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐      ┌──────────────────────────────┐ │
│  │  Barcode Scanner │ ──►  │  HID Interceptor Service     │ │
│  │  (USB HID)       │      │  (overture-hid.service)      │ │
│  └──────────────────┘      └─────────────┬────────────────┘ │
│                                          │                   │
│                                          ▼                   │
│                            ┌──────────────────────────────┐ │
│                            │  data/default_scouting.csv   │ │
│                            └─────────────┬────────────────┘ │
│                                          │                   │
│                                          ▼                   │
│  ┌──────────────────┐      ┌──────────────────────────────┐ │
│  │  Web Browser     │ ◄──  │  Streamlit App Service       │ │
│  │  (any device)    │      │  (overture-app.service)      │ │
│  └──────────────────┘      └──────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Hardware Requirements

- **Raspberry Pi 3B+, 4, or 5** (2GB+ RAM recommended)
- **MicroSD Card** (16GB+ recommended)
- **USB Barcode/QR Scanner** (HID mode)
- **Power Supply** (appropriate for your Pi model)
- **Network Connection** (Ethernet or WiFi)

### Tested Configurations

| Device | OS | Desktop | Status |
|--------|-----|---------|--------|
| Raspberry Pi 4 | DietPi (Debian ARM) | LXQt | ✅ Tested |
| Raspberry Pi 4 | Raspberry Pi OS | None (headless) | ✅ Tested |
| Raspberry Pi 3B+ | DietPi | None (headless) | ✅ Tested |

## System Setup

### 1. Install DietPi

1. Download DietPi from [dietpi.com](https://dietpi.com/)
2. Flash to MicroSD using Balena Etcher or Raspberry Pi Imager
3. Boot and complete initial setup
4. Run `dietpi-launcher` to configure system

### 2. Install LXQt (Optional)

If you want a desktop environment:

```bash
sudo dietpi-software
# Navigate to: Software Optimized → Desktop → LXQt
# Select and install
```

### 3. Update System

```bash
sudo apt update && sudo apt upgrade -y
```

## Installing Dependencies

### 1. Python and pip

```bash
sudo apt install python3 python3-pip python3-venv -y
```

### 2. Required Libraries

```bash
# For QR scanning (optional, if using camera)
sudo apt install libzbar0 -y

# For evdev HID support
sudo apt install python3-dev -y
```

### 3. Create Virtual Environment

```bash
cd ~
python3 -m venv overture-env
source overture-env/bin/activate
```

### 4. Install Python Packages

```bash
pip install streamlit pandas numpy matplotlib plotly opencv-python pyzbar evdev
```

## Project Installation

### 1. Clone Repository

```bash
cd ~
git clone https://github.com/Overture-7421/Overture-TeamsAnalizer.git
cd Overture-TeamsAnalizer
```

### 2. Install Requirements

```bash
source ~/overture-env/bin/activate
pip install -r requirements_web.txt
pip install evdev  # For HID interceptor
```

### 3. Create Data Directory

```bash
mkdir -p data
```

### 4. Verify Installation

```bash
# Test Streamlit
streamlit run lib/streamlit_app.py --server.port 8501

# Test HID Interceptor (list devices)
python lib/headless_interceptor.py --list
```

## Scanner Configuration

### 1. Find Your Scanner's Hardware ID

Connect your scanner and run:

```bash
python lib/headless_interceptor.py --list
```

Example output:
```
Available input devices:
--------------------------------------------------------------------------------
Path: /dev/input/event3
  Name: USB Barcode Scanner
  Hardware ID: 0416:c141 (vendor:product)
  Physical: usb-0000:00:14.0-2/input0
```

Note the **Hardware ID** (e.g., `0416:c141`).

### 2. Configure Scanner ID

Edit `lib/columnsConfig.json`:

```bash
nano lib/columnsConfig.json
```

Find the `system_settings` section and update:

```json
{
    "system_settings": {
        "scanner_hardware_id": "0416:c141",
        "headless_mode_enabled": true,
        "default_csv_path": "data/default_scouting.csv",
        "auto_reload_enabled": true,
        "reload_interval_seconds": 5
    }
}
```

Replace `0416:c141` with your scanner's hardware ID.

### 3. Set Device Permissions

Add your user to the input group:

```bash
sudo usermod -a -G input $USER
```

**Important:** Log out and log back in for changes to take effect!

### 4. Test Scanner

```bash
python lib/headless_interceptor.py
```

Scan a barcode - you should see:
```
Connected to device: USB Barcode Scanner
  Vendor ID: 0416
  Product ID: c141
  Path: /dev/input/event3
  Output CSV: /home/dietpi/Overture-TeamsAnalizer/data/default_scouting.csv
Device grabbed - input is exclusive to this process

Listening for scanner input... (Press Ctrl+C to stop)
[14:32:15] Record appended: ['7421', '42', 'Yes']... (33 fields)
```

## Default CSV Loading

The engine automatically loads `data/default_scouting.csv` on startup.

### How It Works

1. When `AnalizadorRobot` initializes, it checks for `data/default_scouting.csv`
2. If found, data is loaded automatically
3. Hot-reload monitors the file for changes (every 5 seconds by default)
4. When HID interceptor adds new data, web interface updates automatically

### Manual CSV Setup

If you have existing data:

```bash
cp /path/to/your/scouting_data.csv data/default_scouting.csv
```

### CSV Format

The CSV should match the headers in `columnsConfig.json`:

```csv
Scouter Initials,Match Number,Robot,Future Alliance,Team Number,...
AB,1,R1,Red,7421,...
CD,1,R2,Red,254,...
```

## Autostart Services

### Install Services

```bash
cd ~/Overture-TeamsAnalizer
sudo ./scripts/install_services.sh --install
```

This creates:
- `overture-app.service` - Streamlit web interface
- `overture-hid.service` - HID interceptor (disabled by default)

### Enable HID Service

```bash
sudo ./scripts/install_services.sh --enable-hid
```

### Check Service Status

```bash
sudo ./scripts/install_services.sh --status
```

Or individually:

```bash
sudo systemctl status overture-app
sudo systemctl status overture-hid
```

### View Logs

```bash
# Streamlit app logs
journalctl -u overture-app -f

# HID interceptor logs
journalctl -u overture-hid -f
```

### Service Commands

```bash
# Restart services
sudo systemctl restart overture-app
sudo systemctl restart overture-hid

# Stop services
sudo systemctl stop overture-app
sudo systemctl stop overture-hid

# Disable autostart
sudo systemctl disable overture-app
sudo systemctl disable overture-hid
```

### Uninstall Services

```bash
sudo ./scripts/install_services.sh --uninstall
```

## Accessing the Web Interface

### Local Access

Open a browser on the Pi and go to:
```
http://localhost:8501
```

### Remote Access

From another device on the network:
```
http://<PI_IP_ADDRESS>:8501
```

Find your Pi's IP:
```bash
hostname -I
```

### LXQt Auto-Launch Browser (Optional)

Create autostart entry for LXQt:

```bash
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/overture-browser.desktop << EOF
[Desktop Entry]
Type=Application
Name=Overture Browser
Exec=chromium-browser --kiosk http://localhost:8501
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
```

## Troubleshooting

### Service Won't Start

```bash
# Check detailed logs
journalctl -u overture-app --no-pager -n 50
journalctl -u overture-hid --no-pager -n 50

# Check Python path
which python3
which streamlit

# Verify virtual environment
ls -la ~/overture-env/bin/
```

### Scanner Not Detected

```bash
# List USB devices
lsusb

# List input devices
ls -la /dev/input/event*

# Check if evdev is installed
python3 -c "import evdev; print('evdev OK')"

# Check user groups
groups
```

### Permission Denied

```bash
# Add to input group
sudo usermod -a -G input $USER

# Log out and back in, then verify
groups | grep input
```

### Web Interface Not Loading

```bash
# Check if Streamlit is running
ps aux | grep streamlit

# Try manual run
cd ~/Overture-TeamsAnalizer
source ~/overture-env/bin/activate
streamlit run lib/streamlit_app.py --server.port 8501

# Check firewall
sudo ufw status
# If active, allow port 8501
sudo ufw allow 8501
```

### Data Not Updating

```bash
# Check if CSV exists
ls -la data/default_scouting.csv

# Check file permissions
stat data/default_scouting.csv

# Verify hot-reload is enabled in config
cat lib/columnsConfig.json | grep -A5 system_settings
```

## Performance Tips

### For Raspberry Pi 3

```bash
# Reduce Streamlit memory usage
streamlit run lib/streamlit_app.py \
    --server.maxUploadSize 10 \
    --server.maxMessageSize 50
```

### Disable Unused Features

If only using HID scanner (no camera):
- Skip installing opencv-python
- Skip pyzbar

### Optimize Swap

```bash
# Increase swap for low-RAM systems
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=1024
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

## Security Considerations

- The web interface has no authentication by default
- Limit network access with firewall rules
- Consider using reverse proxy (nginx) with HTTPS for production
- Keep system and packages updated
