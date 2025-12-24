#!/usr/bin/env python3
"""
Headless HID Event Interceptor for Barcode/QR Scanners

This module provides a solution for capturing barcode/QR scanner input in a headless
Linux environment (Debian/Ubuntu) where the scanner acts as a Human Interface Device (HID).

The scanner "grabs" the input device so events don't leak to the OS, translates keycodes
to ASCII, handles Tab as delimiters and Enter as end of record, then writes captured
data to the default scouting CSV file.

Requirements:
- Linux operating system (Debian/Ubuntu recommended)
- python-evdev library: pip install evdev
- Appropriate permissions to read /dev/input/event* devices

Usage:
    python headless_interceptor.py [--device /dev/input/eventX] [--config path/to/config.json]
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Base directory for resolving relative paths
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
DATA_DIR = ROOT_DIR / "data"
DEFAULT_CSV_PATH = DATA_DIR / "default_scouting.csv"
CONFIG_PATH = BASE_DIR / "columnsConfig.json"

# evdev is only available on Linux
try:
    import evdev
    from evdev import InputDevice, categorize, ecodes, list_devices
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False


# Keycode to character mapping for US keyboard layout
# This maps evdev keycodes to their ASCII equivalents
KEYCODE_MAP: Dict[int, Tuple[str, str]] = {
    # Format: keycode: (lowercase, uppercase/shifted)
    2: ('1', '!'),
    3: ('2', '@'),
    4: ('3', '#'),
    5: ('4', '$'),
    6: ('5', '%'),
    7: ('6', '^'),
    8: ('7', '&'),
    9: ('8', '*'),
    10: ('9', '('),
    11: ('0', ')'),
    12: ('-', '_'),
    13: ('=', '+'),
    16: ('q', 'Q'),
    17: ('w', 'W'),
    18: ('e', 'E'),
    19: ('r', 'R'),
    20: ('t', 'T'),
    21: ('y', 'Y'),
    22: ('u', 'U'),
    23: ('i', 'I'),
    24: ('o', 'O'),
    25: ('p', 'P'),
    26: ('[', '{'),
    27: (']', '}'),
    30: ('a', 'A'),
    31: ('s', 'S'),
    32: ('d', 'D'),
    33: ('f', 'F'),
    34: ('g', 'G'),
    35: ('h', 'H'),
    36: ('j', 'J'),
    37: ('k', 'K'),
    38: ('l', 'L'),
    39: (';', ':'),
    40: ("'", '"'),
    41: ('`', '~'),
    43: ('\\', '|'),
    44: ('z', 'Z'),
    45: ('x', 'X'),
    46: ('c', 'C'),
    47: ('v', 'V'),
    48: ('b', 'B'),
    49: ('n', 'N'),
    50: ('m', 'M'),
    51: (',', '<'),
    52: ('.', '>'),
    53: ('/', '?'),
    57: (' ', ' '),  # Space
}

# Special keys
KEY_TAB = 15
KEY_ENTER = 28
KEY_LEFTSHIFT = 42
KEY_RIGHTSHIFT = 54


class HIDInterceptorConfig:
    """Configuration for the HID interceptor loaded from columnsConfig.json."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or CONFIG_PATH
        self.scanner_vendor_id: Optional[str] = None
        self.scanner_product_id: Optional[str] = None
        self.scanner_hardware_id: Optional[str] = None
        self.headless_mode_enabled: bool = False
        self.csv_headers: List[str] = []
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            print(f"Warning: Config file not found at {self.config_path}")
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Load headers
            self.csv_headers = config.get('headers', [])
            
            # Load system settings if available
            system_settings = config.get('system_settings', {})
            self.scanner_hardware_id = system_settings.get('scanner_hardware_id')
            self.headless_mode_enabled = system_settings.get('headless_mode_enabled', False)
            
            # Parse hardware ID into vendor/product IDs if provided
            if self.scanner_hardware_id:
                parts = self.scanner_hardware_id.split(':')
                if len(parts) == 2:
                    self.scanner_vendor_id = parts[0]
                    self.scanner_product_id = parts[1]
                    
        except Exception as e:
            print(f"Error loading config: {e}")


def find_scanner_device(
    vendor_id: Optional[str] = None,
    product_id: Optional[str] = None,
    device_name_pattern: Optional[str] = None
) -> Optional[str]:
    """
    Find the input device path for the barcode/QR scanner.
    
    Args:
        vendor_id: Vendor ID in hexadecimal format (e.g., "0416")
        product_id: Product ID in hexadecimal format (e.g., "c141")
        device_name_pattern: Optional pattern to match device name
        
    Returns:
        Device path (e.g., "/dev/input/event5") or None if not found
    """
    if not EVDEV_AVAILABLE:
        print("Error: evdev library not available. Install with: pip install evdev")
        return None
    
    devices = [InputDevice(path) for path in list_devices()]
    
    for device in devices:
        # Check by vendor/product ID
        if vendor_id and product_id:
            dev_vendor = f"{device.info.vendor:04x}"
            dev_product = f"{device.info.product:04x}"
            if dev_vendor.lower() == vendor_id.lower() and dev_product.lower() == product_id.lower():
                print(f"Found scanner by ID: {device.name} at {device.path}")
                return device.path
        
        # Check by name pattern
        if device_name_pattern:
            if device_name_pattern.lower() in device.name.lower():
                print(f"Found scanner by name: {device.name} at {device.path}")
                return device.path
        
        # Common scanner keywords
        scanner_keywords = ['barcode', 'scanner', 'hid', 'reader', 'symbol', 'honeywell', 'datalogic']
        device_name_lower = device.name.lower()
        if any(keyword in device_name_lower for keyword in scanner_keywords):
            print(f"Found potential scanner: {device.name} at {device.path}")
            return device.path
    
    return None


def list_all_input_devices() -> List[Dict]:
    """
    List all available input devices for debugging/configuration.
    
    Returns:
        List of device information dictionaries
    """
    if not EVDEV_AVAILABLE:
        print("Error: evdev library not available")
        return []
    
    devices_info = []
    for path in list_devices():
        try:
            device = InputDevice(path)
            devices_info.append({
                'path': path,
                'name': device.name,
                'phys': device.phys,
                'vendor_id': f"{device.info.vendor:04x}",
                'product_id': f"{device.info.product:04x}",
                'hardware_id': f"{device.info.vendor:04x}:{device.info.product:04x}"
            })
        except Exception:
            pass
    
    return devices_info


class HIDInterceptor:
    """
    Intercepts HID input from a barcode/QR scanner and processes the data.
    
    Note: This class only works on Linux systems with the evdev library installed.
    For non-Linux platforms, use the QR scanner camera-based approach instead.
    """
    
    def __init__(
        self,
        device_path: str,
        output_csv: Path = DEFAULT_CSV_PATH,
        config: Optional[HIDInterceptorConfig] = None
    ):
        if not EVDEV_AVAILABLE:
            raise RuntimeError(
                "evdev library not available. This module only works on Linux systems. "
                "For non-Linux platforms (Windows/macOS), use the camera-based QR scanner "
                "(lib/qr_utils.py) instead. "
                "On Linux, install with: pip install evdev"
            )
        
        self.device_path = device_path
        self.output_csv = output_csv
        self.config = config or HIDInterceptorConfig()
        self.device: Optional[InputDevice] = None
        self.current_buffer: List[str] = []
        self.current_record: List[str] = []
        self.shift_pressed = False
        self.running = False
        
    def _keycode_to_char(self, keycode: int) -> Optional[str]:
        """Convert a keycode to its ASCII character."""
        if keycode in KEYCODE_MAP:
            char_pair = KEYCODE_MAP[keycode]
            return char_pair[1] if self.shift_pressed else char_pair[0]
        return None
    
    def _process_key_event(self, event) -> Optional[str]:
        """
        Process a key event and return any completed data.
        
        Returns:
            The completed record as a CSV-formatted string, or None
        """
        if event.type != ecodes.EV_KEY:
            return None
        
        key_event = categorize(event)
        keycode = event.code
        
        # Handle key press (value 1) and hold (value 2)
        if event.value in (1, 2):
            # Track shift state
            if keycode in (KEY_LEFTSHIFT, KEY_RIGHTSHIFT):
                self.shift_pressed = True
                return None
            
            # Handle Tab - delimiter between fields
            if keycode == KEY_TAB:
                field_value = ''.join(self.current_buffer)
                self.current_record.append(field_value)
                self.current_buffer = []
                return None
            
            # Handle Enter - end of record
            if keycode == KEY_ENTER:
                # Add the last field
                field_value = ''.join(self.current_buffer)
                if field_value or self.current_record:
                    self.current_record.append(field_value)
                
                if self.current_record:
                    # Return the completed record
                    record = self.current_record.copy()
                    self.current_record = []
                    self.current_buffer = []
                    return record
                return None
            
            # Convert keycode to character and add to buffer
            char = self._keycode_to_char(keycode)
            if char:
                self.current_buffer.append(char)
        
        # Handle key release (value 0)
        elif event.value == 0:
            if keycode in (KEY_LEFTSHIFT, KEY_RIGHTSHIFT):
                self.shift_pressed = False
        
        return None
    
    def _ensure_csv_header(self) -> None:
        """Ensure the output CSV has a header row."""
        if not self.output_csv.exists():
            # Create the data directory if needed
            self.output_csv.parent.mkdir(parents=True, exist_ok=True)
            
            # Write header if we have column configuration
            if self.config.csv_headers:
                with open(self.output_csv, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(self.config.csv_headers)
                print(f"Created CSV with headers: {self.output_csv}")
    
    def _append_record(self, record: List[str]) -> None:
        """Append a record to the CSV file."""
        self._ensure_csv_header()
        
        # Pad or truncate record to match expected columns
        if self.config.csv_headers:
            num_cols = len(self.config.csv_headers)
            while len(record) < num_cols:
                record.append('')
            if len(record) > num_cols:
                record = record[:num_cols]
        
        with open(self.output_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(record)
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] Record appended: {record[:3]}... ({len(record)} fields)")
    
    def start(self, grab_device: bool = True) -> None:
        """
        Start intercepting HID input.
        
        Args:
            grab_device: If True, grab the device so events don't leak to the OS
        """
        try:
            self.device = InputDevice(self.device_path)
            print(f"Connected to device: {self.device.name}")
            print(f"  Vendor ID: {self.device.info.vendor:04x}")
            print(f"  Product ID: {self.device.info.product:04x}")
            print(f"  Path: {self.device_path}")
            print(f"  Output CSV: {self.output_csv}")
            
            if grab_device:
                self.device.grab()
                print("Device grabbed - input is exclusive to this process")
            
            print("\nListening for scanner input... (Press Ctrl+C to stop)")
            self.running = True
            
            for event in self.device.read_loop():
                if not self.running:
                    break
                
                record = self._process_key_event(event)
                if record:
                    self._append_record(record)
                    
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        except PermissionError:
            print(f"Permission denied for {self.device_path}")
            print("Try running with sudo or add your user to the 'input' group:")
            print(f"  sudo usermod -a -G input $USER")
            print("Then log out and back in.")
        except FileNotFoundError:
            print(f"Device not found: {self.device_path}")
            print("Use --list to see available devices")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop intercepting and release the device."""
        self.running = False
        if self.device:
            try:
                self.device.ungrab()
            except Exception:
                pass
            self.device.close()
            self.device = None
        print("Interceptor stopped")


def main():
    """Main entry point for the headless interceptor."""
    parser = argparse.ArgumentParser(
        description="Headless HID Interceptor for Barcode/QR Scanners"
    )
    parser.add_argument(
        '--device', '-d',
        type=str,
        help="Device path (e.g., /dev/input/event5)"
    )
    parser.add_argument(
        '--config', '-c',
        type=str,
        default=str(CONFIG_PATH),
        help="Path to columnsConfig.json"
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=str(DEFAULT_CSV_PATH),
        help="Output CSV file path"
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help="List all available input devices and exit"
    )
    parser.add_argument(
        '--no-grab',
        action='store_true',
        help="Don't grab the device exclusively (allows events to pass through)"
    )
    
    args = parser.parse_args()
    
    if not EVDEV_AVAILABLE:
        print("Error: This script requires the evdev library and only works on Linux.")
        print("Install with: pip install evdev")
        sys.exit(1)
    
    # List devices mode
    if args.list:
        print("Available input devices:")
        print("-" * 80)
        devices = list_all_input_devices()
        for dev in devices:
            print(f"Path: {dev['path']}")
            print(f"  Name: {dev['name']}")
            print(f"  Hardware ID: {dev['hardware_id']} (vendor:product)")
            print(f"  Physical: {dev['phys']}")
            print()
        return
    
    # Load configuration
    config = HIDInterceptorConfig(Path(args.config))
    
    # Find device
    device_path = args.device
    if not device_path:
        # Try to find scanner by configured hardware ID
        device_path = find_scanner_device(
            vendor_id=config.scanner_vendor_id,
            product_id=config.scanner_product_id
        )
        if not device_path:
            print("Error: Could not find scanner device")
            print("Please specify device path with --device or configure scanner_hardware_id")
            print("Use --list to see available devices")
            sys.exit(1)
    
    # Create and start interceptor
    output_path = Path(args.output)
    interceptor = HIDInterceptor(
        device_path=device_path,
        output_csv=output_path,
        config=config
    )
    
    interceptor.start(grab_device=not args.no_grab)


if __name__ == '__main__':
    main()
