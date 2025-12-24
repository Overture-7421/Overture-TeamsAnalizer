# QR Utilities (qr_utils.py)

## Overview

The `qr_utils.py` module provides QR code scanning functionality using OpenCV and pyzbar. It's designed for camera-based QR code scanning with real-time processing and debouncing.

## Location

```
lib/qr_utils.py
```

## Key Features

- **Camera-based QR Scanning**: Use webcam or external camera to scan QR codes
- **Real-time Processing**: Immediate callbacks when QR codes are detected
- **Per-code Debouncing**: Prevents duplicate scans of the same code
- **Visual Feedback**: Draw bounding boxes around detected QR codes
- **Session-based Scanning**: Context manager for controlled scanning sessions

## Dependencies

```bash
pip install opencv-python pyzbar numpy
```

On some Linux systems, you may need to install ZBar library:
```bash
# Debian/Ubuntu
sudo apt-get install libzbar0

# DietPi/Raspberry Pi
sudo apt-get install libzbar0
```

## Functions

### test_camera()

Test if the camera is available and accessible.

```python
from qr_utils import test_camera

if test_camera(camera_index=0):
    print("Camera is ready!")
else:
    print("Camera not available")
```

### scan_qr_codes()

Main scanning function with callback support.

```python
from qr_utils import scan_qr_codes

def on_qr_detected(data):
    print(f"Scanned: {data}")
    # Process the data...

# Start scanning (opens camera window)
scanned_data = scan_qr_codes(
    update_callback=on_qr_detected,
    camera_index=0,
    debounce_seconds=2.0,
    show_window=True
)

print(f"Total scanned: {len(scanned_data)} codes")
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `update_callback` | `Callable` | `None` | Function called when QR is detected |
| `camera_index` | `int` | `0` | Camera device index |
| `debounce_seconds` | `float` | `2.0` | Time before accepting same code again |
| `show_window` | `bool` | `True` | Show camera preview window |

### decode_qr_from_frame()

Decode QR codes from a single image frame.

```python
import cv2
from qr_utils import decode_qr_from_frame

frame = cv2.imread("image_with_qr.png")
codes = decode_qr_from_frame(frame)
# Returns: ["QR data 1", "QR data 2", ...]
```

### get_camera_frame()

Capture a single frame from the camera.

```python
from qr_utils import get_camera_frame

success, frame = get_camera_frame(camera_index=0)
if success:
    # Process frame...
    pass
```

## QRScannerSession Class

Context manager for controlled scanning sessions.

```python
from qr_utils import QRScannerSession

with QRScannerSession(camera_index=0) as session:
    while True:
        # Scan single frame
        data = session.scan_frame()
        if data:
            print(f"Detected: {data}")
        
        # Or get frame with overlay
        frame, detected = session.get_frame_with_overlay()
        if frame is not None:
            # Display or process frame
            pass
        
        # Check for exit condition
        if should_stop:
            break
    
    # Reset to allow rescanning same codes
    session.reset_scanned_codes()
```

### Session Methods

| Method | Description |
|--------|-------------|
| `scan_frame()` | Scan single frame, return QR data or None |
| `get_frame_with_overlay()` | Get frame with bounding boxes drawn |
| `reset_scanned_codes()` | Clear scanned codes set to allow rescanning |

## Per-Code Debouncing

The scanner uses per-code debouncing to prevent multiple detections:

```python
# Each unique QR code has its own debounce timer
# Scanning code A doesn't block scanning code B

Time 0.0s: Scan code "A" → Accepted
Time 0.5s: Scan code "A" → Rejected (debounce)
Time 0.5s: Scan code "B" → Accepted (different code)
Time 2.5s: Scan code "A" → Accepted (debounce expired)
```

## Integration with Streamlit

In the Streamlit app, QR scanning is available in the Data Management tab:

```python
# In streamlit_app.py
from qr_utils import test_camera, QRScannerSession

if st.button("Test Camera"):
    if test_camera():
        st.success("Camera ready!")
    else:
        st.error("Camera not available")
```

## Headless Mode

For headless servers without a display, use `show_window=False`:

```python
scanned = scan_qr_codes(
    update_callback=process_data,
    show_window=False  # No GUI window
)
```

Note: For truly headless environments with barcode scanners, consider using the HID Interceptor instead.

## Troubleshooting

### Camera Not Found
```python
# Try different camera indices
for i in range(5):
    if test_camera(camera_index=i):
        print(f"Found camera at index {i}")
        break
```

### pyzbar Import Error
```bash
# Install ZBar library
sudo apt-get install libzbar0
pip install pyzbar
```

### Performance Issues
- Reduce camera resolution
- Increase debounce time
- Use `show_window=False` to reduce overhead
