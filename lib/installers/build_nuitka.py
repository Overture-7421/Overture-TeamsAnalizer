#!/usr/bin/env python3
"""
Alliance Simulator Nuitka Builder

Nuitka provides better performance and smaller executables compared to PyInstaller.
This script builds the Alliance Simulator using Nuitka.

Usage:
    python build_nuitka.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_nuitka():
    """Check if Nuitka is installed"""
    try:
        result = subprocess.run(["nuitka3", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Nuitka is installed")
            return True
    except FileNotFoundError:
        pass
    
    print("❌ Nuitka not found. Installing...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "nuitka"], check=True)
        print("✅ Nuitka installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install Nuitka")
        return False

def build_with_nuitka():
    """Build executable using Nuitka"""
    print("🔨 Building with Nuitka...")
    
    # Prepare build command
    build_cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--enable-plugin=tk-inter",
        "--enable-plugin=numpy",
        "--enable-plugin=matplotlib",
        "--disable-console",  # No console for GUI
        "--output-filename=Alliance_Simulator.exe",
        "--company-name=Alliance Simulator",
        "--product-name=Alliance Simulator",
        "--file-description=Team Analysis and Alliance Selection Tool",
        "--product-version=2.0.0",
        "--include-data-dir=.",
        "--include-package=pandas",
        "--include-package=numpy",
        "--include-package=matplotlib",
        "--include-package=cv2",
        "--include-package=PIL",
        "--include-package=pyzbar",
        "--nofollow-import-to=streamlit",  # Exclude web dependencies
        "--nofollow-import-to=plotly",
        "--nofollow-import-to=tornado",
        "main.py"
    ]
    
    try:
        subprocess.run(build_cmd, check=True)
        print("✅ Nuitka build completed successfully!")
        
        # Move executable to dist folder
        dist_dir = Path("dist")
        dist_dir.mkdir(exist_ok=True)
        
        exe_file = Path("Alliance_Simulator.exe")
        if exe_file.exists():
            shutil.move(exe_file, dist_dir / exe_file.name)
            print(f"📁 Executable moved to: {dist_dir / exe_file.name}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Nuitka build failed: {e}")
        return False

def main():
    """Main build function"""
    print("🚀 Alliance Simulator Nuitka Builder")
    print("=" * 40)
    
    if check_nuitka():
        build_with_nuitka()
    else:
        print("Cannot proceed without Nuitka")

if __name__ == "__main__":
    main()
