"""
QR Scanner Utilities for Alliance Simulator
Ported from legacy/qr_scanner.py for the modern lib/ architecture.

This module provides QR code scanning functionality using opencv-python and pyzbar.
"""

import time
from typing import Callable, Dict, List, Optional, Set

# Lazy imports for better performance and optional dependency handling
_cv2 = None
_pyzbar = None
_np = None


def _ensure_cv2():
    """Lazily import cv2 to avoid startup overhead when not used."""
    global _cv2
    if _cv2 is None:
        try:
            import cv2
            _cv2 = cv2
        except ImportError:
            raise ImportError(
                "opencv-python is required for QR scanning. "
                "Install with: pip install opencv-python"
            )
    return _cv2


def _ensure_pyzbar():
    """Lazily import pyzbar to avoid startup overhead when not used."""
    global _pyzbar
    if _pyzbar is None:
        try:
            from pyzbar import pyzbar
            _pyzbar = pyzbar
        except ImportError:
            raise ImportError(
                "pyzbar is required for QR scanning. "
                "Install with: pip install pyzbar. "
                "Note: On some systems, you may need to install the ZBar library separately."
            )
    return _pyzbar


def _ensure_numpy():
    """Lazily import numpy for image processing."""
    global _np
    if _np is None:
        try:
            import numpy as np
            _np = np
        except ImportError:
            raise ImportError(
                "numpy is required for QR scanning. "
                "Install with: pip install numpy"
            )
    return _np


def play_beep():
    """Play a beep sound when a QR code is detected (platform-dependent)."""
    try:
        import winsound
        winsound.Beep(1000, 200)  # Frequency 1000 Hz, duration 200 ms
    except ImportError:
        # winsound not available on non-Windows platforms
        pass


def test_camera(camera_index: int = 0) -> bool:
    """
    Test if the camera is available and accessible.
    
    Args:
        camera_index: The camera device index (default: 0)
        
    Returns:
        True if the camera works, False otherwise
    """
    cv2 = _ensure_cv2()
    try:
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return False
        
        ret, frame = cap.read()
        cap.release()
        
        return ret and frame is not None
    except Exception as e:
        print(f"Error testing camera: {e}")
        return False


def scan_qr_codes(
    update_callback: Optional[Callable[[str], None]] = None,
    camera_index: int = 0,
    debounce_seconds: float = 2.0,
    show_window: bool = True
) -> List[str]:
    """
    Activate the camera to scan QR codes and return the data as a list of strings.
    
    Args:
        update_callback: Optional function to call immediately when a QR code is detected.
                        Should accept a single string parameter (the QR data).
        camera_index: The camera device index (default: 0)
        debounce_seconds: Time in seconds to wait before accepting the same QR code again (per-code)
        show_window: Whether to show the camera preview window (requires display)
    
    Returns:
        List of newly scanned QR code data strings
    """
    cv2 = _ensure_cv2()
    pyzbar = _ensure_pyzbar()
    np = _ensure_numpy()
    
    # Initialize the camera
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return []

    print("Camera opened. Point a QR code at the camera.")
    print("Press 'q' to quit.")
    if update_callback:
        print("Real-time updates enabled - data will be processed immediately!")

    scanned_codes: Set[str] = set()
    # Per-code debounce: track when each code was last scanned
    code_last_scan_time: Dict[str, float] = {}
    newly_scanned_data: List[str] = []

    try:
        while True:
            # Read a frame from the camera
            ret, frame = cap.read()
            if not ret:
                print("Error: Can't receive frame (stream end?). Exiting...")
                break

            # Find and decode QR codes
            decoded_objects = pyzbar.decode(frame)
            current_time = time.time()

            for obj in decoded_objects:
                data = obj.data.decode('utf-8')
                
                # Per-code debounce: check if this specific code was scanned recently
                last_scan = code_last_scan_time.get(data, 0.0)
                if current_time - last_scan > debounce_seconds:
                    if data not in scanned_codes:
                        print(f"New QR Code Detected: {data}")
                        scanned_codes.add(data)
                        newly_scanned_data.append(data)
                        
                        # Call the update callback immediately if provided
                        if update_callback:
                            try:
                                preview = data[:50] + "..." if len(data) > 50 else data
                                print(f"Calling real-time update for: {preview}")
                                update_callback(data)
                                print("✓ Real-time update successful!")
                            except Exception as e:
                                print(f"Error in real-time update: {e}")
                        
                        play_beep()
                    
                    # Update the per-code last scan time
                    code_last_scan_time[data] = current_time

                # Draw a bounding box around the QR code for visual feedback
                if show_window:
                    points = obj.polygon
                    # Convert points to numpy array with correct format for polylines
                    if len(points) > 4:
                        points_array = np.array([[p.x, p.y] for p in points], dtype=np.int32)
                        hull = cv2.convexHull(points_array, clockwise=True)
                        cv2.polylines(frame, [hull], True, (0, 255, 0), 2)
                    else:
                        points_array = np.array([[p.x, p.y] for p in points], dtype=np.int32)
                        cv2.polylines(frame, [points_array], True, (0, 255, 0), 2)

            # Display the resulting frame
            if show_window:
                cv2.imshow('QR Code Scanner - Press Q to quit', frame)

                # Check for 'q' key to exit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                # In headless mode, just yield control briefly
                time.sleep(0.01)
    finally:
        # Release resources
        cap.release()
        if show_window:
            cv2.destroyAllWindows()
    
    print(f"Scanner stopped. Found {len(newly_scanned_data)} new QR codes.")
    return newly_scanned_data


def decode_qr_from_frame(frame) -> List[str]:
    """
    Decode QR codes from a single video frame.
    
    Args:
        frame: A numpy array representing an image/video frame
        
    Returns:
        List of decoded QR code data strings
    """
    pyzbar = _ensure_pyzbar()
    
    decoded_objects = pyzbar.decode(frame)
    return [obj.data.decode('utf-8') for obj in decoded_objects]


def get_camera_frame(camera_index: int = 0):
    """
    Capture a single frame from the camera.
    
    Args:
        camera_index: The camera device index
        
    Returns:
        Tuple of (success: bool, frame: numpy array or None)
    """
    cv2 = _ensure_cv2()
    
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        return False, None
    
    try:
        ret, frame = cap.read()
        return ret, frame if ret else None
    finally:
        cap.release()


class QRScannerSession:
    """
    Context manager for continuous QR scanning sessions.
    Useful for integration with Streamlit or other frameworks.
    """
    
    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.cap = None
        self.scanned_codes: Set[str] = set()
        self.last_scan_time = 0.0
        self.debounce_seconds = 2.0
        
    def __enter__(self):
        cv2 = _ensure_cv2()
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError("Could not open camera")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cap:
            self.cap.release()
        return False
    
    def scan_frame(self) -> Optional[str]:
        """
        Capture and scan a single frame for QR codes.
        
        Returns:
            The decoded QR data if a new code is found, None otherwise
        """
        if not self.cap:
            return None
            
        ret, frame = self.cap.read()
        if not ret:
            return None
        
        pyzbar = _ensure_pyzbar()
        decoded_objects = pyzbar.decode(frame)
        
        current_time = time.time()
        for obj in decoded_objects:
            data = obj.data.decode('utf-8')
            if data not in self.scanned_codes:
                if current_time - self.last_scan_time > self.debounce_seconds:
                    self.scanned_codes.add(data)
                    self.last_scan_time = current_time
                    play_beep()
                    return data
        
        return None
    
    def get_frame_with_overlay(self):
        """
        Get the current camera frame with QR code detection overlay.
        
        Returns:
            Tuple of (frame, detected_qr_data) or (None, None) if no frame
        """
        cv2 = _ensure_cv2()
        np = _ensure_numpy()
        
        if not self.cap:
            return None, None
            
        ret, frame = self.cap.read()
        if not ret:
            return None, None
        
        pyzbar = _ensure_pyzbar()
        decoded_objects = pyzbar.decode(frame)
        
        detected_data = None
        for obj in decoded_objects:
            data = obj.data.decode('utf-8')
            detected_data = data
            
            # Draw bounding box
            points = obj.polygon
            if len(points) > 4:
                points_array = np.array([[p.x, p.y] for p in points], dtype=np.int32)
                hull = cv2.convexHull(points_array, clockwise=True)
                cv2.polylines(frame, [hull], True, (0, 255, 0), 2)
            else:
                points_array = np.array([[p.x, p.y] for p in points], dtype=np.int32)
                cv2.polylines(frame, [points_array], True, (0, 255, 0), 2)
        
        return frame, detected_data
    
    def reset_scanned_codes(self):
        """Clear the set of scanned codes to allow rescanning."""
        self.scanned_codes.clear()
        self.last_scan_time = 0.0


if __name__ == '__main__':
    # Test the QR scanner
    print("Testing camera access...")
    if test_camera():
        print("Camera test successful! Starting QR scanner...")
        scanned_data = scan_qr_codes()
        if scanned_data:
            print("\n--- Scanned Data ---")
            for item in scanned_data:
                print(item)
        else:
            print("No data was scanned.")
    else:
        print("Camera test failed. Please check your camera setup.")
