# Headless Interceptor (headless_interceptor.py)

## Overview

The `headless_interceptor.py` module provides a solution for capturing barcode/QR scanner input in headless Linux environments. Barcode scanners typically act as HID (Human Interface Device) keyboards, sending keystrokes to the focused application. This module "grabs" the raw input device so events don't leak to the OS.

Compatible with **any Linux distribution** that provides `/dev/input/event*` devices, including:
- Debian, Ubuntu, Raspberry Pi OS, DietPi
- Fedora, RHEL, CentOS
- Arch Linux, Manjaro
- openSUSE, SUSE Linux Enterprise
- Any other distro with `udev`

## Location

```
lib/headless_interceptor.py
```

## Key Features

- **Device Grabbing**: Exclusive access to scanner input
- **Keycode Translation**: Convert keycodes to ASCII characters
- **Tab/Enter Handling**: Tab as field delimiter, Enter as record end
- **Auto-detection**: Find scanner by hardware ID (vendor:product)
- **Fallback Discovery**: Uses `/proc/bus/input/devices` when `evdev.list_devices()` returns empty (common on some distros/permission setups)
- **CSV Writing**: Append captured data directly to scouting CSV

## Requirements

- **Linux only** (any modern distribution)
- `evdev` library: `pip install evdev`
- Read access to `/dev/input/event*` devices

## Installation

```bash
# Install evdev library
pip install evdev

# Add user to input group for device access (works on all distros)
sudo usermod -a -G input $USER
# Log out and back in for group changes to take effect

# Alternative: create a udev rule (no re-login required)
echo 'SUBSYSTEM=="input", ATTRS{idVendor}=="0416", ATTRS{idProduct}=="c141", MODE="0666"' | \
    sudo tee /etc/udev/rules.d/99-barcode-scanner.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

## Command Line Usage

### List Available Devices

```bash
python lib/headless_interceptor.py --list
```

Output:
```
Available input devices:
--------------------------------------------------------------------------------
Path: /dev/input/event3
  Name: USB Barcode Scanner
  Hardware ID: 0416:c141 (vendor:product)
  Physical: usb-0000:00:14.0-2/input0
```

### Start Interceptor

```bash
# Auto-detect scanner
python lib/headless_interceptor.py

# Specify device path
python lib/headless_interceptor.py --device /dev/input/event3

# Custom output file
python lib/headless_interceptor.py --output /path/to/output.csv

# Don't grab device (allow events to pass through)
python lib/headless_interceptor.py --no-grab
```

### Command Line Arguments

| Argument | Short | Description |
|----------|-------|-------------|
| `--device` | `-d` | Device path (e.g., /dev/input/event5) |
| `--config` | `-c` | Path to config/columns.json |
| `--output` | `-o` | Output CSV file path |
| `--list` | `-l` | List all available input devices |
| `--no-grab` | | Don't grab device exclusively |

## Configuration

Configure the scanner hardware ID in `lib/config/columns.json`:

```json
{
    "system_settings": {
        "scanner_hardware_id": "0416:c141",
        "headless_mode_enabled": true,
        "default_csv_path": "data/default_scouting.csv"
    }
}
```

### Finding Your Scanner's Hardware ID

1. Connect the scanner
2. Run: `python lib/headless_interceptor.py --list`
3. Look for your scanner in the list
4. Copy the hardware ID (e.g., "0416:c141")
5. Update `lib/config/columns.json`

## Python API

```python
from headless_interceptor import HIDInterceptor, HIDInterceptorConfig
from pathlib import Path

config = HIDInterceptorConfig(Path("lib/config/columns.json"))

interceptor = HIDInterceptor(
    device_path="/dev/input/event3",
    output_csv=Path("data/default_scouting.csv"),
    config=config
)

# Start capturing (blocks until Ctrl+C or SIGTERM)
interceptor.start(grab_device=True)
```

## Device Discovery

The module uses a two-stage device discovery process:

1. **Primary**: `evdev.list_devices()` — fast and reliable on most distros
2. **Fallback**: `/proc/bus/input/devices` — used when `evdev` returns no devices (can happen on some setups or when `udev` is not fully running)

This ensures the interceptor works reliably across all Linux distributions without any distro-specific configuration.

## Permissions

```bash
# Option 1: Add to input group (recommended, all distros)
sudo usermod -a -G input $USER
# Log out and back in

# Option 2: Create udev rule for specific device (no re-login)
echo 'SUBSYSTEM=="input", ATTRS{idVendor}=="0416", ATTRS{idProduct}=="c141", MODE="0666"' | \
    sudo tee /etc/udev/rules.d/99-barcode-scanner.rules
sudo udevadm control --reload-rules && sudo udevadm trigger

# Option 3: Run with sudo (not recommended for production)
sudo python lib/headless_interceptor.py
```

> **Note on Fedora/Arch:** If the `input` group doesn't exist, create it first:
> ```bash
> sudo groupadd -f input
> sudo usermod -a -G input $USER
> ```

## Integration with Systemd

See [Systemd Services Configuration](./systemd_services.md) for running the interceptor as a background service.

## Troubleshooting

### No Devices Listed
```bash
# Check if /dev/input/event* devices exist
ls -la /dev/input/event*

# Check user groups
groups

# Try running as root temporarily to diagnose
sudo python lib/headless_interceptor.py --list
```

### Permission Denied
```bash
# Add to input group (all distros)
sudo usermod -a -G input $USER
# Log out and back in

# Or use udev rule (instant, no re-login)
echo 'SUBSYSTEM=="input", ATTRS{idVendor}=="XXXX", ATTRS{idProduct}=="XXXX", MODE="0666"' | \
    sudo tee /etc/udev/rules.d/99-scanner.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### evdev Not Available
```bash
pip install evdev
# Note: Only works on Linux
```

## Non-Linux Platforms

For Windows/macOS, use the camera-based QR scanner (`qr_utils.py`) instead.

