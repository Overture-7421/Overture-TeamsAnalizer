#!/usr/bin/env python3
"""
Alliance Simulator Distribution Creator

Creates different distribution packages for various deployment scenarios.
"""

import os
import sys
import zipfile
import shutil
import json
from pathlib import Path
import datetime

def create_distribution_info():
    """Create distribution information file"""
    info = {
        "name": "Alliance Simulator",
        "version": "2.0.0", 
        "description": "Team Analysis and Alliance Selection Tool for FIRST Robotics",
        "author": "Alliance Simulator Team",
        "created": datetime.datetime.now().isoformat(),
        "python_required": ">=3.8",
        "platforms": ["Windows", "macOS", "Linux"],
        "components": {
            "desktop_app": "main.py - Full-featured desktop application",
            "web_app": "streamlit_app.py - Web-based interface",
            "alliance_selector": "Enhanced alliance selection with strategic analysis",
            "honor_roll": "Comprehensive team scoring and ranking system",
            "data_conversion": "CSV format detection and conversion"
        },
        "dependencies": [
            "pandas>=2.0.0",
            "numpy>=1.24.0",
            "matplotlib>=3.7.0",
            "opencv-python>=4.8.0",
            "pyzbar>=0.1.9",
            "streamlit>=1.28.0",
            "plotly>=5.15.0",
            "Pillow>=10.0.0"
        ]
    }
    
    with open("DISTRIBUTION_INFO.json", "w") as f:
        json.dump(info, f, indent=2)
    
    return info

def create_installer_package():
    """Create comprehensive installer package"""
    print("📦 Creating installer package...")
    
    package_dir = Path("Alliance_Simulator_Installer")
    if package_dir.exists():
        shutil.rmtree(package_dir)
    
    package_dir.mkdir()
    
    # Core application files
    core_files = [
        "main.py", "streamlit_app.py", "allianceSelector.py", "school_system.py",
        "config_manager.py", "csv_converter.py", "foreshadowing.py", "foreshadowing_web.py",
        "main_web.py", "qr_scanner.py", "setup.py", "alliance_simulator_installer.py"
    ]
    
    # Configuration and data files
    data_files = [
        "columnsConfig.json", "test_data.csv", "extended_test_data.csv",
        "test_data_config.json", "example_phase_config.json", "simple_presets.py"
    ]
    
    # Documentation files
    doc_files = [
        "README.md", "ENHANCED_SYSTEMS_GUIDE.md", "WEB_VERSION_README.md", 
        "TEST_DATA_GUIDE.md", "requirements_web.txt"
    ]
    
    # Copy all files
    all_files = core_files + data_files + doc_files
    for file in all_files:
        if os.path.exists(file):
            shutil.copy2(file, package_dir)
    
    # Create installer batch file
    installer_bat = '''@echo off
title Alliance Simulator Installer
echo.
echo =====================================
echo    Alliance Simulator Installer
echo =====================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found. Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo ✅ Python detected

:: Run Python installer
python alliance_simulator_installer.py

echo.
echo Installation process completed.
pause
'''
    
    with open(package_dir / "INSTALL.bat", "w") as f:
        f.write(installer_bat)
    
    # Create README for installer package
    installer_readme = '''# Alliance Simulator Installer Package

## Quick Installation

### Windows
1. Double-click `INSTALL.bat`
2. Follow the on-screen instructions

### All Platforms
1. Ensure Python 3.8+ is installed
2. Run: `python alliance_simulator_installer.py`

## What This Installs

- Complete Alliance Simulator application
- All required Python dependencies
- Sample data and configuration files
- Desktop and start menu shortcuts (Windows)
- Complete documentation

## Manual Installation

If automatic installation fails:

1. Install dependencies: `pip install -r requirements_web.txt`
2. Run desktop app: `python main.py`
3. Run web app: `streamlit run streamlit_app.py`

## System Requirements

- Python 3.8 or higher
- 500MB free disk space
- Internet connection (for installation only)

## Support

See included documentation files:
- README.md - Basic usage
- ENHANCED_SYSTEMS_GUIDE.md - Advanced features
- TEST_DATA_GUIDE.md - Sample data guide
'''
    
    with open(package_dir / "README_INSTALLER.txt", "w") as f:
        f.write(installer_readme)
    
    print(f"✅ Installer package created: {package_dir}")
    return package_dir

def create_portable_zip():
    """Create portable ZIP distribution"""
    print("📦 Creating portable ZIP package...")
    
    zip_name = "Alliance_Simulator_Portable.zip"
    
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add all Python files
        for py_file in Path(".").glob("*.py"):
            if py_file.name not in ["build_executable.py", "build_nuitka.py", "create_distribution.py"]:
                zipf.write(py_file, py_file.name)
        
        # Add configuration and data files
        data_files = [
            "columnsConfig.json", "test_data.csv", "extended_test_data.csv",
            "test_data_config.json", "example_phase_config.json",
            "requirements_web.txt"
        ]
        
        for file in data_files:
            if os.path.exists(file):
                zipf.write(file, file.name)
        
        # Add documentation
        doc_files = [
            "README.md", "ENHANCED_SYSTEMS_GUIDE.md", "WEB_VERSION_README.md", 
            "TEST_DATA_GUIDE.md"
        ]
        
        for file in doc_files:
            if os.path.exists(file):
                zipf.write(file, file.name)
        
        # Add portable run scripts
        run_desktop = '''@echo off
python main.py
pause'''
        
        run_web = '''@echo off
echo Starting Alliance Simulator Web Interface...
echo Open browser to: http://localhost:8501
streamlit run streamlit_app.py'''
        
        zipf.writestr("Run_Desktop.bat", run_desktop)
        zipf.writestr("Run_Web.bat", run_web)
        zipf.writestr("DISTRIBUTION_INFO.json", json.dumps(create_distribution_info(), indent=2))
    
    print(f"✅ Portable ZIP created: {zip_name}")
    return zip_name

def create_web_only_package():
    """Create web-only deployment package"""
    print("📦 Creating web-only package...")
    
    web_dir = Path("Alliance_Simulator_Web")
    if web_dir.exists():
        shutil.rmtree(web_dir)
    
    web_dir.mkdir()
    
    # Web-specific files
    web_files = [
        "streamlit_app.py", "foreshadowing_web.py", "main_web.py",
        "allianceSelector.py", "school_system.py", "config_manager.py",
        "csv_converter.py", "simple_presets.py"
    ]
    
    # Data and config files
    data_files = [
        "columnsConfig.json", "test_data.csv", "extended_test_data.csv",
        "test_data_config.json", "example_phase_config.json"
    ]
    
    # Documentation
    doc_files = ["WEB_VERSION_README.md", "requirements_web.txt"]
    
    # Copy files
    for file_list in [web_files, data_files, doc_files]:
        for file in file_list:
            if os.path.exists(file):
                shutil.copy2(file, web_dir)
    
    # Create deployment scripts
    dockerfile = '''FROM python:3.11-slim

WORKDIR /app

COPY requirements_web.txt .
RUN pip install --no-cache-dir -r requirements_web.txt

COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
'''
    
    with open(web_dir / "Dockerfile", "w") as f:
        f.write(dockerfile)
    
    # Docker compose
    docker_compose = '''version: '3.8'

services:
  alliance-simulator:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
    environment:
      - STREAMLIT_SERVER_PORT=8501
      - STREAMLIT_SERVER_ADDRESS=0.0.0.0
    restart: unless-stopped
'''
    
    with open(web_dir / "docker-compose.yml", "w") as f:
        f.write(docker_compose)
    
    # Deploy script
    deploy_script = '''#!/bin/bash
# Alliance Simulator Web Deployment Script

echo "🚀 Deploying Alliance Simulator Web Interface..."

# Install dependencies
pip install -r requirements_web.txt

# Run with Streamlit
echo "Starting web interface on http://localhost:8501"
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
'''
    
    with open(web_dir / "deploy.sh", "w") as f:
        f.write(deploy_script)
    
    # Make script executable on Unix systems
    try:
        os.chmod(web_dir / "deploy.sh", 0o755)
    except:
        pass
    
    print(f"✅ Web-only package created: {web_dir}")
    return web_dir

def create_documentation_package():
    """Create comprehensive documentation package"""
    print("📚 Creating documentation package...")
    
    docs_dir = Path("Alliance_Simulator_Documentation")
    if docs_dir.exists():
        shutil.rmtree(docs_dir)
    
    docs_dir.mkdir()
    
    # Copy documentation files
    doc_files = [
        "README.md", "ENHANCED_SYSTEMS_GUIDE.md", "WEB_VERSION_README.md", 
        "TEST_DATA_GUIDE.md"
    ]
    
    for file in doc_files:
        if os.path.exists(file):
            shutil.copy2(file, docs_dir)
    
    # Create master documentation index
    index_content = '''# Alliance Simulator Documentation

Welcome to the comprehensive Alliance Simulator documentation package.

## 📋 Documentation Files

### Getting Started
- **README.md** - Main user guide and basic setup instructions
- **WEB_VERSION_README.md** - Web interface specific documentation

### Advanced Features  
- **ENHANCED_SYSTEMS_GUIDE.md** - Detailed guide for enhanced alliance selector and honor roll systems
- **TEST_DATA_GUIDE.md** - Working with test data and understanding sample datasets

### Quick Reference
- **API_REFERENCE.md** - Function and class references (generated)
- **CONFIGURATION_GUIDE.md** - Configuration options and customization

## 🎯 Quick Start

1. Read README.md for basic setup
2. Follow ENHANCED_SYSTEMS_GUIDE.md for advanced features
3. Use TEST_DATA_GUIDE.md to understand the sample data

## 🔧 Configuration

All configuration options are detailed in the individual documentation files. 
Key configuration files:
- columnsConfig.json - Column mapping and analysis configuration
- example_phase_config.json - Game phase configuration examples

## 📞 Support

For technical support:
1. Check the relevant documentation file
2. Review the GitHub repository issues
3. Contact the development team

## 📈 Version Information

This documentation corresponds to Alliance Simulator v2.0.0 with enhanced systems.

---
Generated: ''' + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '''
'''
    
    with open(docs_dir / "INDEX.md", "w") as f:
        f.write(index_content)
    
    print(f"✅ Documentation package created: {docs_dir}")
    return docs_dir

def main():
    """Main distribution creation function"""
    print("🚀 Alliance Simulator Distribution Creator")
    print("=" * 50)
    
    # Create distribution info
    dist_info = create_distribution_info()
    print(f"📋 Creating distributions for {dist_info['name']} v{dist_info['version']}")
    
    print("\nWhat distributions would you like to create?")
    print("1. Complete installer package")
    print("2. Portable ZIP package")
    print("3. Web-only deployment package")
    print("4. Documentation package")
    print("5. All distributions")
    
    choice = input("\nEnter your choice (1-5): ").strip()
    
    created_packages = []
    
    if choice == "1" or choice == "5":
        package = create_installer_package()
        created_packages.append(f"📦 {package}")
    
    if choice == "2" or choice == "5":
        package = create_portable_zip()
        created_packages.append(f"📦 {package}")
    
    if choice == "3" or choice == "5":
        package = create_web_only_package()
        created_packages.append(f"📦 {package}")
    
    if choice == "4" or choice == "5":
        package = create_documentation_package()
        created_packages.append(f"📚 {package}")
    
    print("\n🎉 Distribution creation complete!")
    print("\nCreated packages:")
    for package in created_packages:
        print(f"  {package}")
    
    print(f"\n📋 Distribution Summary:")
    print(f"• Complete installer: Easy installation for end users")
    print(f"• Portable ZIP: No installation required, just extract and run")
    print(f"• Web package: For server deployment with Docker support")
    print(f"• Documentation: Comprehensive user and developer guides")

if __name__ == "__main__":
    main()
