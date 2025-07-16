import cv2
from pyzbar import pyzbar
import time

try:
    import winsound
    def play_beep():
        winsound.Beep(1000, 200)  # Frequency 1000 Hz, duration 200 ms
except ImportError:
    print("winsound not available. Beep sound will not be played. Install winsound for audio feedback.")
    def play_beep():
        pass

def scan_qr_codes():
    """
    Activates the camera to scan QR codes and returns the data as a list of strings.
    """
    # Initialize the camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return []

    print("Camera opened. Point a QR code at the camera.")
    print("Press 'q' to quit.")

    scanned_codes = set()
    last_scan_time = 0
    newly_scanned_data = []


    while True:
        # Read a frame from the camera
        ret, frame = cap.read()
        if not ret:
            print("Error: Can't receive frame (stream end?). Exiting ...")
            break

        # Find and decode QR codes
        decoded_objects = pyzbar.decode(frame)

        for obj in decoded_objects:
            data = obj.data.decode('utf-8')
            
            # To avoid re-scanning the same code immediately
            if data not in scanned_codes:
                current_time = time.time()
                # Debounce to avoid multiple writes for the same QR code
                if current_time - last_scan_time > 2:
                    print(f"New QR Code Detected: {data}")
                    scanned_codes.add(data)
                    newly_scanned_data.append(data)
                    
                    play_beep()
                    last_scan_time = current_time

            # Draw a bounding box around the QR code for visual feedback
            points = obj.polygon
            if len(points) > 4:
                hull = cv2.convexHull(points, clockwise=True)
                cv2.polylines(frame, [hull], True, (0, 255, 0), 2)
            else:
                cv2.polylines(frame, [points], True, (0, 255, 0), 2)

            # You can also draw the data on the screen
            # cv2.putText(frame, data, (points[0].x, points[0].y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)


        # Display the resulting frame
        cv2.imshow('QR Code Scanner - Press Q to quit', frame)

        # Check for 'q' key to exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # When everything done, release the capture
    cap.release()
    cv2.destroyAllWindows()
    print(f"Scanner stopped. Found {len(newly_scanned_data)} new QR codes.")
    return newly_scanned_data

def test_camera():
    """Test function to check if camera access is working."""
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open camera.")
            return False
        
        print("Camera test successful!")
        cap.release()
        return True
    except Exception as e:
        print(f"Camera test failed: {e}")
        return False

if __name__ == '__main__':
    # To run this scanner, you might need to install the required libraries:
    # pip install opencv-python pyzbar
    # On Windows, winsound should be part of the standard library.
    # On some systems, you may need to install ZBar library separately for pyzbar to work.
    
    print("Testing camera access...")
    if test_camera():
        print("Starting QR scanner...")
        scanned_data = scan_qr_codes()
        if scanned_data:
            print("\n--- Scanned Data ---")
            for item in scanned_data:
                print(item)
        else:
            print("No data was scanned.")
    else:
        print("Camera test failed. Please check your camera setup.")
