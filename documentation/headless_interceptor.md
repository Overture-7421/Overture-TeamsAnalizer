# Headless Interceptor (headless_interceptor.py)

## Overview

The `headless_interceptor.py` module provides a solution for capturing barcode/QR scanner input in headless Linux environments. Barcode scanners typically act as HID (Human Interface Device) keyboards, sending keystrokes to the focused application. This module "grabs" the raw input device so events don't leak to the OS.

## Location

```
lib/headless_interceptor.py
```

## Key Features

- **Device Grabbing**: Exclusive access to scanner input
- **Keycode Translation**: Convert keycodes to ASCII characters
- **Tab/Enter Handling**: Tab as field delimiter, Enter as record end
- **Auto-detection**: Find scanner by hardware ID (vendor:product)
- **CSV Writing**: Append captured data directly to scouting CSV

## Requirements

- **Linux only** (Debian/Ubuntu/DietPi)
- `evdev` library: `pip install evdev`
- Read access to `/dev/input/event*` devices

## Installation

```bash
# Install evdev library
pip install evdev

# Add user to input group for device access
sudo usermod -a -G input $USER

# Log out and back in for group changes to take effect
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

Path: /dev/input/event4
  Name: Keyboard
  Hardware ID: 046d:c31c (vendor:product)
  Physical: usb-0000:00:14.0-1/input0
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
| `--config` | `-c` | Path to columnsConfig.json |
| `--output` | `-o` | Output CSV file path |
| `--list` | `-l` | List all available input devices |
| `--no-grab` | | Don't grab device exclusively |

## Configuration

Configure the scanner hardware ID in `lib/columnsConfig.json`:

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
5. Update `columnsConfig.json`

## Python API

### HIDInterceptor Class

```python
from headless_interceptor import HIDInterceptor, HIDInterceptorConfig
from pathlib import Path

# Load configuration
config = HIDInterceptorConfig(Path("lib/columnsConfig.json"))

# Create interceptor
interceptor = HIDInterceptor(
    device_path="/dev/input/event3",
    output_csv=Path("data/default_scouting.csv"),
    config=config
)

# Start capturing (blocks until Ctrl+C)
interceptor.start(grab_device=True)
```

### find_scanner_device()

Auto-detect scanner by hardware ID:

```python
from headless_interceptor import find_scanner_device

device = find_scanner_device(
    vendor_id="0416",
    product_id="c141"
)
# Returns: "/dev/input/event3" or None
```

### list_all_input_devices()

Get information about all input devices:

```python
from headless_interceptor import list_all_input_devices

devices = list_all_input_devices()
for dev in devices:
    print(f"{dev['path']}: {dev['name']} ({dev['hardware_id']})")
```

## Data Format

The interceptor processes scanned data as follows:

1. **Tab characters** → Field delimiter (column separator)
2. **Enter key** → End of record (new row)
3. **Other keys** → Converted to ASCII characters

### Example

If your scanner sends:
```
7421<TAB>42<TAB>Yes<ENTER>
```

It becomes a CSV row:
```csv
7421,42,Yes
```

## Keycode Mapping

The interceptor supports US keyboard layout:

| Keys | Characters |
|------|------------|
| 0-9 | Numbers |
| A-Z | Letters (with shift detection) |
| Tab | Field delimiter |
| Enter | Record end |
| Space | Space |
| Common symbols | `-`, `=`, `[`, `]`, etc. |

## Permissions

The interceptor needs read access to input devices:

```bash
# Option 1: Run as root (not recommended for production)
sudo python lib/headless_interceptor.py

# Option 2: Add user to input group (recommended)
sudo usermod -a -G input $USER
# Then log out and back in

# Option 3: Create udev rule for specific device
echo 'SUBSYSTEM=="input", ATTRS{idVendor}=="0416", ATTRS{idProduct}=="c141", MODE="0666"' | \
    sudo tee /etc/udev/rules.d/99-barcode-scanner.rules
sudo udevadm control --reload-rules
```

## Integration with Systemd

See [Systemd Services Configuration](./systemd_services.md) for running the interceptor as a background service.

## Troubleshooting

### Permission Denied
```bash
# Add to input group
sudo usermod -a -G input $USER
# Log out and back in
```

### Device Not Found
```bash
# List devices to find correct path
python lib/headless_interceptor.py --list

# Check if device exists
ls -la /dev/input/event*
```

### evdev Not Available
```bash
# Install evdev
pip install evdev

# Note: Only works on Linux
```

### Wrong Characters
- Check keyboard layout
- Scanner may use different encoding
- Try adjusting keycode mapping in source

## Non-Linux Platforms

For Windows/macOS, use the camera-based QR scanner (`qr_utils.py`) instead. The HID interceptor is Linux-only due to evdev dependency.
