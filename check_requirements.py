"""
Requirements checker for Alliance Simulator
Run this script to check if all required dependencies are installed.
"""

def check_requirements():
    """Check if all required packages are installed."""
    required_packages = [
        ('cv2', 'opencv-python'),
        ('pyzbar', 'pyzbar'),
        ('tkinter', 'tkinter (built-in)'),
        ('matplotlib', 'matplotlib'),
        ('numpy', 'numpy (usually installed with opencv)')
    ]
    
    missing_packages = []
    
    print("Checking requirements for Alliance Simulator...")
    print("-" * 50)
    
    for module, package in required_packages:
        try:
            __import__(module)
            print(f"✓ {module} - OK")
        except ImportError:
            print(f"✗ {module} - MISSING")
            missing_packages.append(package)
    
    print("-" * 50)
    
    if missing_packages:
        print(f"\nMissing packages found: {len(missing_packages)}")
        print("\nTo install missing packages, run:")
        for package in missing_packages:
            if package != 'tkinter (built-in)':
                print(f"pip install {package}")
        print("\nNote: tkinter should be built-in with Python. If missing, you may need to reinstall Python.")
    else:
        print("\n✓ All requirements satisfied!")
    
    return len(missing_packages) == 0

if __name__ == "__main__":
    success = check_requirements()
    
    if success:
        print("\nYou can now run the Alliance Simulator!")
        
        # Test camera access if opencv is available
        try:
            import cv2
            print("\nTesting camera access...")
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                print("✓ Camera access successful!")
                cap.release()
            else:
                print("✗ Camera could not be opened. Check camera connection and permissions.")
        except:
            pass
    else:
        print("\nPlease install missing packages before running the simulator.")
