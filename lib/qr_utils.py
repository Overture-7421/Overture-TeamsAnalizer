"""
QR Scanner Utilities for Alliance Simulator
Ported from legacy/qr_scanner.py for the modern lib/ architecture.

Uses pyzbar when available; falls back to cv2.QRCodeDetector so no
native ZBar DLL is required.
"""

import platform
import time
from typing import Callable, Dict, List, NamedTuple, Optional, Set

# Lazy imports for better performance and optional dependency handling
_cv2 = None
_pyzbar = None          # None means "not yet tried"; False means "unavailable"
_np = None


# ---------------------------------------------------------------------------
# Internal unified QR result type
# ---------------------------------------------------------------------------

class _QRResult(NamedTuple):
    data: str
    points: Optional[list]   # list of (x, y) ints, or None


# ---------------------------------------------------------------------------
# Lazy importers
# ---------------------------------------------------------------------------

def _ensure_cv2():
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


def _load_pyzbar():
    """Try to load pyzbar once; return the module or None."""
    global _pyzbar
    if _pyzbar is None:
        try:
            from pyzbar import pyzbar as _pb
            _pyzbar = _pb
        except Exception:
            _pyzbar = False   # mark as unavailable
    return _pyzbar if _pyzbar is not False else None


def _ensure_numpy():
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


# ---------------------------------------------------------------------------
# Unified frame decoder — pyzbar preferred, cv2 fallback
# ---------------------------------------------------------------------------

def _decode_frame(frame) -> List[_QRResult]:
    """Decode QR codes from a frame using pyzbar or cv2 fallback."""
    pyzbar = _load_pyzbar()
    if pyzbar is not None:
        results = []
        for obj in pyzbar.decode(frame):
            data = obj.data.decode("utf-8")
            points = [(p.x, p.y) for p in obj.polygon]
            results.append(_QRResult(data, points))
        return results

    # Fallback: cv2.QRCodeDetector (no external DLL required)
    cv2 = _ensure_cv2()
    detector = cv2.QRCodeDetector()
    try:
        ok, texts, pts, _ = detector.detectAndDecodeMulti(frame)
    except Exception:
        ok = False
    if not ok or not texts:
        return []
    results = []
    for text, quad in zip(texts, pts):
        if text:
            # quad is shape (1,4,2) or (4,2)
            flat = quad.reshape(-1, 2).astype(int)
            points = [(int(p[0]), int(p[1])) for p in flat]
            results.append(_QRResult(text, points))
    return results


def _draw_qr_overlay(cv2, np, frame, points):
    """Draw a bounding polygon around a detected QR code."""
    if not points:
        return
    pts_array = np.array(points, dtype=np.int32)
    if len(points) > 4:
        hull = cv2.convexHull(pts_array, clockwise=True)
        cv2.polylines(frame, [hull], True, (0, 255, 0), 2)
    else:
        cv2.polylines(frame, [pts_array], True, (0, 255, 0), 2)


# ---------------------------------------------------------------------------
# Camera helpers
# ---------------------------------------------------------------------------

def _open_camera(cv2, camera_index: int):
    """Open VideoCapture with a platform-specific backend to avoid obsensor errors."""
    if platform.system() == "Windows":
        return cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    elif platform.system() == "Linux":
        return cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
    else:
        return cv2.VideoCapture(camera_index)


def play_beep():
    """Play a beep sound when a QR code is detected (platform-dependent)."""
    try:
        import winsound
        winsound.Beep(1000, 200)
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def test_camera(camera_index: int = 0) -> bool:
    cv2 = _ensure_cv2()
    try:
        cap = _open_camera(cv2, camera_index)
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
    show_window: bool = True,
    stop_on_first_scan: bool = False
) -> List[str]:
    cv2 = _ensure_cv2()
    np = _ensure_numpy()

    backend = "pyzbar" if _load_pyzbar() is not None else "cv2.QRCodeDetector"
    print(f"QR backend: {backend}")

    cap = _open_camera(cv2, camera_index)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return []

    print("Camera opened. Point a QR code at the camera.")
    print("Press 'q' to quit.")
    if update_callback:
        print("Real-time updates enabled - data will be processed immediately!")

    scanned_codes: Set[str] = set()
    code_last_scan_time: Dict[str, float] = {}
    newly_scanned_data: List[str] = []

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Can't receive frame (stream end?). Exiting...")
                break

            results = _decode_frame(frame)
            current_time = time.time()

            for qr in results:
                last_scan = code_last_scan_time.get(qr.data, 0.0)
                if current_time - last_scan > debounce_seconds:
                    if qr.data not in scanned_codes:
                        print(f"New QR Code Detected: {qr.data}")
                        scanned_codes.add(qr.data)
                        newly_scanned_data.append(qr.data)

                        if update_callback:
                            try:
                                preview = qr.data[:50] + "..." if len(qr.data) > 50 else qr.data
                                print(f"Calling real-time update for: {preview}")
                                update_callback(qr.data)
                                print("✓ Real-time update successful!")
                            except Exception as e:
                                print(f"Error in real-time update: {e}")

                        play_beep()

                        if stop_on_first_scan:
                            print("Stopping scanner after first scan.")
                            return newly_scanned_data

                    code_last_scan_time[qr.data] = current_time

                if show_window and qr.points:
                    _draw_qr_overlay(cv2, np, frame, qr.points)

            if show_window:
                cv2.imshow('QR Code Scanner - Press Q to quit', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                time.sleep(0.01)
    finally:
        cap.release()
        if show_window:
            cv2.destroyAllWindows()

    print(f"Scanner stopped. Found {len(newly_scanned_data)} new QR codes.")
    return newly_scanned_data


def decode_qr_from_frame(frame) -> List[str]:
    return [qr.data for qr in _decode_frame(frame)]


def get_camera_frame(camera_index: int = 0):
    cv2 = _ensure_cv2()
    cap = _open_camera(cv2, camera_index)
    if not cap.isOpened():
        return False, None
    try:
        ret, frame = cap.read()
        return ret, frame if ret else None
    finally:
        cap.release()


class QRScannerSession:
    """Context manager for continuous QR scanning sessions."""

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.cap = None
        self.scanned_codes: Set[str] = set()
        self.last_scan_time = 0.0
        self.debounce_seconds = 2.0

    def __enter__(self):
        cv2 = _ensure_cv2()
        self.cap = _open_camera(cv2, self.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError("Could not open camera")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cap:
            self.cap.release()
        return False

    def scan_frame(self) -> Optional[str]:
        if not self.cap:
            return None
        ret, frame = self.cap.read()
        if not ret:
            return None

        current_time = time.time()
        for qr in _decode_frame(frame):
            if qr.data not in self.scanned_codes:
                if current_time - self.last_scan_time > self.debounce_seconds:
                    self.scanned_codes.add(qr.data)
                    self.last_scan_time = current_time
                    play_beep()
                    return qr.data
        return None

    def get_frame_with_overlay(self):
        cv2 = _ensure_cv2()
        np = _ensure_numpy()

        if not self.cap:
            return None, None
        ret, frame = self.cap.read()
        if not ret:
            return None, None

        detected_data = None
        for qr in _decode_frame(frame):
            detected_data = qr.data
            if qr.points:
                _draw_qr_overlay(cv2, np, frame, qr.points)

        return frame, detected_data

    def reset_scanned_codes(self):
        self.scanned_codes.clear()
        self.last_scan_time = 0.0


if __name__ == '__main__':
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
