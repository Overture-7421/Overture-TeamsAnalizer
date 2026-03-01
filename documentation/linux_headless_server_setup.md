# Linux Headless Server Setup

Complete guide for setting up the Overture Teams Analyzer as a headless scouting server on Linux. Covers Raspberry Pi (DietPi, Raspberry Pi OS), as well as standard desktop distributions (Ubuntu, Debian, Fedora, Arch Linux, openSUSE).

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
│                  Linux Host (any distro)                      │
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

- **Any Linux-capable device:** Raspberry Pi 3B+/4/5, PC, laptop, mini-PC, or SBC
- **RAM:** 1 GB minimum, 2 GB+ recommended
- **Storage:** 8 GB minimum (SD card, SSD, or HDD)
- **USB Barcode/QR Scanner** (HID mode)
- **Network Connection** (Ethernet or Wi-Fi)

### Tested Configurations

| Device | OS | Desktop | Status |
|--------|-----|---------|--------|
| Raspberry Pi 4 | DietPi (Debian ARM) | LXQt | ✅ Tested |
| Raspberry Pi 4 | Raspberry Pi OS | None (headless) | ✅ Tested |
| Raspberry Pi 3B+ | DietPi | None (headless) | ✅ Tested |
| x86-64 PC | Ubuntu 22.04 | None (headless) | ✅ Tested |
| x86-64 PC | Fedora 40 | None (headless) | ✅ Tested |
| x86-64 PC | Arch Linux | None (headless) | ✅ Tested |

## System Setup

### 1. Update Your System

**Debian / Ubuntu / Raspberry Pi OS / DietPi:**
```bash
sudo apt update && sudo apt upgrade -y
```

**Fedora:**
```bash
sudo dnf upgrade -y
```

**Arch Linux:**
```bash
sudo pacman -Syu
```

**openSUSE:**
```bash
sudo zypper refresh && sudo zypper update -y
```

### 2. (Raspberry Pi / DietPi only) Install Desktop Environment (Optional)

If you want a desktop environment on DietPi:
```bash
sudo dietpi-software
# Navigate to: Software Optimized → Desktop → LXQt
# Select and install
```

## Installing Dependencies

### 1. Python 3 and pip

**Debian / Ubuntu / Raspberry Pi OS / DietPi:**
```bash
sudo apt install python3 python3-pip python3-venv -y
```

**Fedora:**
```bash
sudo dnf install python3 python3-pip -y
```

**Arch Linux:**
```bash
sudo pacman -S python python-pip --noconfirm
```

**openSUSE:**
```bash
sudo zypper install -y python3 python3-pip
```

### 2. System Libraries for QR Scanning (optional)

**Debian / Ubuntu / Raspberry Pi OS / DietPi:**
```bash
sudo apt install libzbar0 python3-dev -y
```

**Fedora:**
```bash
sudo dnf install zbar-devel python3-devel -y
```

**Arch Linux:**
```bash
sudo pacman -S zbar python --noconfirm
```

**openSUSE:**
```bash
sudo zypper install -y libzbar0 python3-devel
```

### 3. Create Virtual Environment

```bash
cd ~
python3 -m venv overture-env
source overture-env/bin/activate
```

### 4. Install Python Packages

```bash
pip install streamlit pandas numpy matplotlib plotly evdev
# Optional: for camera-based QR scanning
pip install opencv-python pyzbar
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
pip install evdev  # For HID interceptor (Linux only)
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

If you get no devices listed (can happen on some distros), check permissions:
```bash
ls -la /dev/input/event*
groups | grep input  # Verify you're in the input group
```

### 2. Configure Scanner ID

Edit `lib/config/columns.json` and add or update the `system_settings` section:

```json
{
    "system_settings": {
        "scanner_hardware_id": "0416:c141",
        "headless_mode_enabled": true,
        "default_csv_path": "data/default_scouting.csv"
    }
}
```

Replace `0416:c141` with your scanner's hardware ID.

### 3. Set Device Permissions

**Option A — Add to the input group (recommended, works on all distros):**
```bash
sudo usermod -a -G input $USER
# Log out and back in for the change to take effect
```

**Option B — Create a udev rule (persistent, no re-login needed):**
```bash
# Replace 0416 and c141 with your scanner's vendor/product IDs
echo 'SUBSYSTEM=="input", ATTRS{idVendor}=="0416", ATTRS{idProduct}=="c141", MODE="0666"' | \
    sudo tee /etc/udev/rules.d/99-barcode-scanner.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### 4. Test Scanner

```bash
python lib/headless_interceptor.py
```

Scan a barcode — you should see:
```
Device:     USB Barcode Scanner
Output CSV: /home/user/Overture-TeamsAnalizer/data/default_scouting.csv
Mode:       Exclusive (device grabbed)

Listening for scanner input... (Press Ctrl+C to stop)
[14:32:15] Record appended: ['7421', '42', 'Yes']... (21 fields)
```

## Default CSV Loading

The engine automatically loads `data/default_scouting.csv` on startup.

### How It Works

1. When `AnalizadorRobot` initializes, it checks for `data/default_scouting.csv`
2. If found, data is loaded automatically
3. Hot-reload monitors the file for changes (every 5 seconds by default)
4. When HID interceptor adds new data, web interface updates automatically

### Manual CSV Setup

```bash
cp /path/to/your/scouting_data.csv data/default_scouting.csv
```

## Autostart Services

### Install Services

```bash
cd ~/Overture-TeamsAnalizer
sudo ./scripts/install_services.sh --install
```

This creates:
- `overture-app.service` — Streamlit web interface
- `overture-hid.service` — HID interceptor (disabled by default)

### Enable HID Service

```bash
sudo ./scripts/install_services.sh --enable-hid
```

### Check Service Status

```bash
sudo systemctl status overture-app
sudo systemctl status overture-hid
```

### View Logs

```bash
journalctl -u overture-app -f
journalctl -u overture-hid -f
```

## Accessing the Web Interface

### Local Access
```
http://localhost:8501
```

### Remote Access (from another device on the network)
```
http://<YOUR_IP_ADDRESS>:8501
```

Find your IP address:
```bash
hostname -I
# or
ip addr show | grep "inet " | awk '{print $2}'
```

### Firewall Configuration

**UFW (Ubuntu/Debian):**
```bash
sudo ufw allow 8501
```

**firewalld (Fedora/openSUSE):**
```bash
sudo firewall-cmd --permanent --add-port=8501/tcp
sudo firewall-cmd --reload
```

**iptables (any distro):**
```bash
sudo iptables -A INPUT -p tcp --dport 8501 -j ACCEPT
```

## Troubleshooting

### Scanner Not Detected

```bash
# List USB devices
lsusb

# List input devices
ls -la /dev/input/event*

# Check if evdev is installed
python3 -c "import evdev; print('evdev OK')"

# Check user groups
groups | grep input
```

**On Fedora/Arch:** The `input` group may not exist by default.
Create it and add your user:
```bash
sudo groupadd -f input
sudo usermod -a -G input $USER
```

### Permission Denied

```bash
# Add to input group (all distros)
sudo usermod -a -G input $USER
# Log out and back in

# Or use a udev rule (no re-login needed)
echo 'SUBSYSTEM=="input", ATTRS{idVendor}=="0416", ATTRS{idProduct}=="c141", MODE="0666"' | \
    sudo tee /etc/udev/rules.d/99-barcode-scanner.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### Web Interface Not Loading

```bash
# Check if Streamlit is running
ps aux | grep streamlit

# Try manual run
cd ~/Overture-TeamsAnalizer
source ~/overture-env/bin/activate
streamlit run lib/streamlit_app.py --server.port 8501
```

### Data Not Updating

```bash
# Check if CSV exists and has correct permissions
ls -la data/default_scouting.csv
stat data/default_scouting.csv
```

## Performance Tips

### For Low-RAM Devices (Raspberry Pi 3, 1 GB RAM)

```bash
streamlit run lib/streamlit_app.py \
    --server.maxUploadSize 10 \
    --server.maxMessageSize 50
```

### Increase Swap Space

```bash
# Check current swap
free -h

# Increase swap (example: set to 1 GB)
sudo swapoff -a
sudo dd if=/dev/zero of=/swapfile bs=1M count=1024
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## Security Considerations

- The web interface has no authentication by default — only expose it on trusted networks
- Limit network access with firewall rules (see [Firewall Configuration](#firewall-configuration))
- Use a reverse proxy (nginx/caddy) with HTTPS if accessible from outside the local network
- Keep your system and Python packages updated regularly
- The `data/` directory may contain scouting data; restrict read access if needed:
  ```bash
  chmod 750 data/
  ```


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
