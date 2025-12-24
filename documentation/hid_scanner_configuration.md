# HID Scanner Configuration

Complete guide for configuring barcode and QR code scanners as HID (Human Interface Device) for use with the Overture Teams Analyzer headless interceptor.

## Overview

Most barcode/QR scanners present themselves as USB keyboards (HID devices). When you scan a code, the scanner sends keystrokes to the computer. The HID interceptor captures these keystrokes directly from the device, bypassing the need for window focus.

## Supported Scanners

The HID interceptor works with most USB barcode/QR scanners that:

- Present as USB HID keyboard
- Send Tab characters as field delimiters
- Send Enter at end of scan
- Use US keyboard layout

### Tested Scanners

| Brand | Model | Hardware ID | Status |
|-------|-------|-------------|--------|
| Generic | USB Barcode Scanner | 0416:c141 | ✅ Working |
| Honeywell | Various | Varies | ✅ Working |
| Datalogic | Various | Varies | ✅ Working |
| Symbol | Various | Varies | ✅ Working |

## Finding Your Scanner's Hardware ID

### Method 1: Using the Interceptor

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

### Method 2: Using lsusb

```bash
lsusb
```

Output:
```
Bus 001 Device 003: ID 0416:c141 Winbond Electronics Corp. USB Barcode Scanner
```

The `0416:c141` is the hardware ID.

### Method 3: Using dmesg

```bash
# Unplug scanner, wait 2 seconds, plug in
dmesg | tail -20
```

Look for lines like:
```
[12345.678901] usb 1-2: Product: USB Barcode Scanner
[12345.678902] usb 1-2: Manufacturer: Winbond Electronics Corp.
[12345.678903] input: USB Barcode Scanner as /devices/...
```

## Configuring the Hardware ID

### Edit columnsConfig.json

Open the configuration file:
```bash
nano lib/columnsConfig.json
```

Find the `system_settings` section:

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

### Configuration Fields

| Field | Description | Example |
|-------|-------------|---------|
| `scanner_hardware_id` | Vendor:Product ID | `"0416:c141"` |
| `headless_mode_enabled` | Enable HID mode | `true` |
| `default_csv_path` | Output file path | `"data/default_scouting.csv"` |
| `auto_reload_enabled` | Hot-reload data | `true` |
| `reload_interval_seconds` | Reload check interval | `5` |

## Scanner Programming

Many scanners can be programmed to change their behavior.

### Common Settings

Configure your scanner to:

1. **Add Tab after each field** - For multi-field barcodes
2. **Add Enter after scan** - To mark end of record
3. **Use US keyboard layout** - For correct character mapping
4. **Disable keyboard locale** - Avoid special character issues

### Programming Barcodes

Consult your scanner's manual for programming barcodes. Common settings:

```
Prefix: None
Suffix: Enter (or CR/LF)
Field Separator: Tab (0x09)
Keyboard Layout: US English
```

### QR Code Data Format

Design your QR codes with tab-separated fields:

```
ScouterInitials<TAB>MatchNumber<TAB>Robot<TAB>Team<TAB>...
```

Example QR content:
```
AB	42	R1	7421	Left	Yes	3	2	1	0	...
```

## Device Permissions

### Add User to Input Group

```bash
sudo usermod -a -G input $USER
# Log out and back in
```

Verify:
```bash
groups | grep input
```

### Udev Rules (Alternative)

Create a udev rule for automatic permissions:

```bash
# Create rule file
sudo nano /etc/udev/rules.d/99-barcode-scanner.rules
```

Add:
```
SUBSYSTEM=="input", ATTRS{idVendor}=="0416", ATTRS{idProduct}=="c141", MODE="0666", GROUP="input"
```

Replace `0416` and `c141` with your scanner's IDs.

Apply rules:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## Testing the Scanner

### Interactive Test

```bash
# Start interceptor manually
python lib/headless_interceptor.py

# Scan a barcode
# You should see output like:
# [14:32:15] Record appended: ['7421', '42', 'Yes']... (33 fields)
```

### Test Without Grabbing

To test without exclusive device access:

```bash
python lib/headless_interceptor.py --no-grab
```

This allows events to pass through to the OS (useful for debugging).

### Verify CSV Output

```bash
# Check if data was written
cat data/default_scouting.csv

# Watch for new entries
tail -f data/default_scouting.csv
```

## Multiple Scanners

### Using Multiple Scanners

Each scanner needs its own interceptor instance:

```bash
# Terminal 1
python lib/headless_interceptor.py --device /dev/input/event3 --output data/scanner1.csv

# Terminal 2
python lib/headless_interceptor.py --device /dev/input/event4 --output data/scanner2.csv
```

### Single Output File

To have multiple scanners write to the same file, ensure they're configured with the same output path:

```bash
python lib/headless_interceptor.py --device /dev/input/event3 --output data/default_scouting.csv &
python lib/headless_interceptor.py --device /dev/input/event4 --output data/default_scouting.csv &
```

Note: File locking may be needed for concurrent writes.

## Troubleshooting

### Scanner Not Found

```bash
# Check if connected
lsusb | grep -i barcode

# Check input devices
ls -la /dev/input/event*

# Run as root to check permissions
sudo python lib/headless_interceptor.py --list
```

### Wrong Characters

The keycode mapping uses US keyboard layout. If getting wrong characters:

1. Verify scanner is set to US English
2. Check if scanner has special encoding
3. Review keycode mapping in `headless_interceptor.py`

### Data Not Appearing

```bash
# Check if CSV exists
ls -la data/

# Check file permissions
stat data/default_scouting.csv

# Try writing test data
echo "test,data,here" >> data/default_scouting.csv
```

### Permission Denied

```bash
# Check device permissions
ls -la /dev/input/event*

# Run with sudo (for testing only)
sudo python lib/headless_interceptor.py

# Fix permanently with user groups
sudo usermod -a -G input $USER
# Log out and back in
```

### Scanner Works in Terminal but Not Service

```bash
# Check service logs
journalctl -u overture-hid -f

# Verify paths in service file
sudo systemctl cat overture-hid

# Check if device path changed
python lib/headless_interceptor.py --list
```

## Advanced Configuration

### Custom Keycode Mapping

To modify the keycode mapping, edit `lib/headless_interceptor.py`:

```python
KEYCODE_MAP: Dict[int, Tuple[str, str]] = {
    # Format: keycode: (lowercase, uppercase/shifted)
    2: ('1', '!'),
    3: ('2', '@'),
    # ... add or modify as needed
}
```

### Custom Delimiters

By default:
- Tab (keycode 15) = Field delimiter
- Enter (keycode 28) = Record end

To change, modify the constants in `headless_interceptor.py`:
```python
KEY_TAB = 15
KEY_ENTER = 28
```

### Logging

Enable debug output:

```bash
python lib/headless_interceptor.py 2>&1 | tee scanner.log
```

## Best Practices

1. **Test before deploying** - Always test scanner configuration manually first
2. **Use consistent QR format** - Ensure all QR codes follow the same field order
3. **Verify field count** - Check that scanned data matches expected column count
4. **Monitor logs** - Watch service logs during initial deployment
5. **Backup data** - Regular backups of the CSV file
6. **Document settings** - Keep record of scanner programming settings
