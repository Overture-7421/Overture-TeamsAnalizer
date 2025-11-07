#!/usr/bin/env python3
"""
Alliance Simulator Executable Builder

This script creates a standalone executable for the Alliance Simulator
that includes all dependencies and can be distributed as a single file.

Usage:
    python build_executable.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_pyinstaller():
    """Check if PyInstaller is installed"""
    try:
        import PyInstaller
        print("✅ PyInstaller is installed")
        return True
    except ImportError:
        print("❌ PyInstaller not found. Installing...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
            print("✅ PyInstaller installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install PyInstaller")
            return False

def create_pyinstaller_spec():
    """Create PyInstaller spec file for better control"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Add all data files
a = Analysis(
    ['lib/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('lib/columnsConfig.json', '.'),
        ('archivos ejemplo/test_data.csv', '.'),
        ('archivos ejemplo/extended_test_data.csv', '.'),
        ('lib/test_data_config.json', '.'),
        ('lib/example_phase_config.json', '.'),
        ('lib/simple_presets.py', '.'),
        ('docs/*.md', '.'),
        ('requirements_web.txt', '.'),
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.simpledialog',
        'pandas',
        'numpy',
        'matplotlib',
        'matplotlib.pyplot',
        'json',
        'csv',
        'copy',
        'dataclasses',
        'typing',
        'enum',
        'math',
        'os',
        'sys',
        'pathlib',
        'datetime',
        'threading',
        'queue',
        'cv2',
        'pyzbar',
        'pyzbar.pyzbar',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'streamlit',  # Exclude web dependencies for desktop version
        'plotly',
        'tornado',
        'jinja2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Alliance_Simulator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)
'''
    
    with open('alliance_simulator.spec', 'w') as f:
        f.write(spec_content)
    
    print("✅ Created PyInstaller spec file")

def build_desktop_executable():
    """Build desktop executable using PyInstaller"""
    print("🔨 Building desktop executable...")
    
    # Create spec file
    create_pyinstaller_spec()
    
    # Build executable
    try:
        subprocess.run([
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--windowed",
            "--name", "Alliance_Simulator",
            "--add-data", "lib/columnsConfig.json;.",
            "--add-data", "archivos ejemplo/test_data.csv;.",
            "--add-data", "archivos ejemplo/extended_test_data.csv;.",
            "--add-data", "docs/README.md;.",
            "--hidden-import", "tkinter",
            "--hidden-import", "pandas",
            "--hidden-import", "numpy",
            "--hidden-import", "matplotlib",
            "--exclude-module", "streamlit",
            "main.py"
        ], check=True)
        
        print("✅ Desktop executable built successfully!")
        print("📁 Location: dist/Alliance_Simulator.exe")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return False

def create_installer_script():
    """Create an installer script"""
    installer_content = '''@echo off
title Alliance Simulator Installer
echo.
echo =====================================
echo    Alliance Simulator Installer
echo =====================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo ✅ Python found
echo.

:: Create installation directory
set INSTALL_DIR=%USERPROFILE%\\Alliance_Simulator
echo Creating installation directory: %INSTALL_DIR%
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Download or copy files (if running from USB/download)
echo Copying Alliance Simulator files...
xcopy /E /I /Y . "%INSTALL_DIR%" >nul

:: Install Python dependencies
echo Installing Python dependencies...
cd /d "%INSTALL_DIR%"
python -m pip install --upgrade pip
python -m pip install -r requirements_web.txt

:: Create desktop shortcut
echo Creating desktop shortcut...
set SHORTCUT_PATH=%USERPROFILE%\\Desktop\\Alliance Simulator.lnk
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT_PATH%'); $Shortcut.TargetPath = 'python'; $Shortcut.Arguments = '%INSTALL_DIR%\\lib\\main.py'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'Alliance Simulator - Team Analysis Tool'; $Shortcut.Save()"

:: Create start menu shortcut
echo Creating start menu shortcut...
set STARTMENU_PATH=%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Alliance Simulator.lnk
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%STARTMENU_PATH%'); $Shortcut.TargetPath = 'python'; $Shortcut.Arguments = '%INSTALL_DIR%\\lib\\main.py'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'Alliance Simulator - Team Analysis Tool'; $Shortcut.Save()"

:: Run initial setup
        echo Running initial setup...
        python lib\setup.py --check

echo.
echo ====================================
echo    Installation Complete! 🎉
echo ====================================
echo.
echo You can now run Alliance Simulator from:
echo • Desktop shortcut
echo • Start menu
echo • Or directly: %INSTALL_DIR%\\lib\\main.py
echo.
echo For web interface: streamlit run %INSTALL_DIR%\\streamlit_app.py
echo.
pause
'''
    
    with open('install.bat', 'w') as f:
        f.write(installer_content)
    
    print("✅ Created Windows installer script (install.bat)")

def create_portable_package():
    """Create a portable package with all dependencies"""
    print("📦 Creating portable package...")
    
    # Create portable directory structure
    portable_dir = Path("Alliance_Simulator_Portable")
    if portable_dir.exists():
        shutil.rmtree(portable_dir)
    
    portable_dir.mkdir()
    
    # Copy main application files
    app_files = [
        "main.py", "streamlit_app.py", "allianceSelector.py", "school_system.py",
        "config_manager.py", "csv_converter.py", "foreshadowing.py", "foreshadowing_web.py",
        "main_web.py", "qr_scanner.py", "simple_presets.py", "setup.py",
        "columnsConfig.json", "test_data.csv", "extended_test_data.csv",
        "test_data_config.json", "example_phase_config.json",
        "requirements_web.txt", "README.md", "ENHANCED_SYSTEMS_GUIDE.md",
        "WEB_VERSION_README.md", "TEST_DATA_GUIDE.md"
    ]
    
    for file in app_files:
        if os.path.exists(file):
            shutil.copy2(file, portable_dir)
    
    # Create run scripts
    run_desktop = '''@echo off
cd /d "%~dp0"
python main.py
pause
'''
    
    run_web = '''@echo off
cd /d "%~dp0"
echo Starting Alliance Simulator Web Interface...
echo Open your browser to: http://localhost:8501
echo Press Ctrl+C to stop the server
streamlit run streamlit_app.py
pause
'''
    
    setup_script = '''@echo off
cd /d "%~dp0"
echo Installing Alliance Simulator dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements_web.txt
echo.
echo Setup complete! You can now run:
echo - Run_Desktop.bat for desktop application
echo - Run_Web.bat for web interface
pause
'''
    
    with open(portable_dir / "Run_Desktop.bat", 'w') as f:
        f.write(run_desktop)
    
    with open(portable_dir / "Run_Web.bat", 'w') as f:
        f.write(run_web)
    
    with open(portable_dir / "Setup.bat", 'w') as f:
        f.write(setup_script)
    
    # Create README for portable version
    portable_readme = '''# Alliance Simulator - Portable Version

## Quick Start

1. Run `Setup.bat` first to install dependencies
2. Run `Run_Desktop.bat` for desktop application
3. Run `Run_Web.bat` for web interface

## Requirements

- Python 3.8 or higher installed
- Internet connection for initial setup

## What's Included

- Complete Alliance Simulator application
- Sample data files
- Configuration files
- Enhanced systems guide
- All documentation

## Support

For issues or questions, refer to README.md or ENHANCED_SYSTEMS_GUIDE.md
'''
    
    with open(portable_dir / "README_PORTABLE.txt", 'w') as f:
        f.write(portable_readme)
    
    print(f"✅ Portable package created in: {portable_dir}")

def create_web_installer():
    """Create web-only installer for server deployment"""
    web_installer = '''#!/usr/bin/env python3
"""
Alliance Simulator Web Installer
Installs only the web interface components for server deployment
"""

import os
import sys
import subprocess

def install_web_version():
    print("🌐 Installing Alliance Simulator Web Interface...")
    
    # Install requirements
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements_web.txt"], check=True)
        print("✅ Web dependencies installed")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False
    
    # Check Streamlit installation
    try:
        import streamlit
        print("✅ Streamlit ready")
    except ImportError:
        print("❌ Streamlit not properly installed")
        return False
    
    print("🎉 Web installation complete!")
    print("🚀 Run with: streamlit run streamlit_app.py")
    return True

if __name__ == "__main__":
    install_web_version()
'''
    
    with open('install_web.py', 'w') as f:
        f.write(web_installer)
    
    print("✅ Created web installer (install_web.py)")

def create_requirements_minimal():
    """Create minimal requirements file for desktop version"""
    minimal_reqs = '''# Minimal requirements for Alliance Simulator Desktop
pandas>=2.0.0
numpy>=1.24.0
matplotlib>=3.7.0
opencv-python>=4.8.0
pyzbar>=0.1.9

# GUI (usually included with Python)
# tkinter (built-in)

# Optional for QR scanning
Pillow>=10.0.0
'''
    
    with open('requirements_desktop.txt', 'w') as f:
        f.write(minimal_reqs)
    
    print("✅ Created minimal desktop requirements")

def main():
    """Main build function"""
    print("🚀 Alliance Simulator Executable Builder")
    print("=" * 50)
    
    print("\nWhat would you like to build?")
    print("1. Standalone executable (PyInstaller) - Recommended")
    print("2. Windows installer script")
    print("3. Portable package")
    print("4. Web-only installer")
    print("5. All of the above")
    
    choice = input("\nEnter your choice (1-5): ").strip()
    
    if choice == "1" or choice == "5":
        if check_pyinstaller():
            build_desktop_executable()
    
    if choice == "2" or choice == "5":
        create_installer_script()
    
    if choice == "3" or choice == "5":
        create_portable_package()
    
    if choice == "4" or choice == "5":
        create_web_installer()
    
    # Always create minimal requirements
    create_requirements_minimal()
    
    print("\n🎉 Build process complete!")
    print("\nDistribution options created:")
    print("• dist/Alliance_Simulator.exe - Standalone executable")
    print("• install.bat - Windows installer")
    print("• Alliance_Simulator_Portable/ - Portable package")
    print("• install_web.py - Web-only installer")
    
    print("\n📋 Distribution Instructions:")
    print("1. For single-file distribution: Share dist/Alliance_Simulator.exe")
    print("2. For easy installation: Share install.bat with source files")
    print("3. For portable use: Share Alliance_Simulator_Portable/ folder")
    print("4. For web deployment: Use install_web.py on server")

if __name__ == "__main__":
    main()
