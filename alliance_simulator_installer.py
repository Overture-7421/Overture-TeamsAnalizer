#!/usr/bin/env python3
"""
Alliance Simulator One-Click Installer

This script automatically downloads, installs, and configures the Alliance Simulator.
Users only need to download and run this single file.

Usage:
    python alliance_simulator_installer.py
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import json
import shutil
from pathlib import Path
import tempfile

# Configuration
GITHUB_REPO = "MarcoAlejandroLopezGomez/TeamsStatsAndSelector"
INSTALL_DIR = Path.home() / "Alliance_Simulator"
DESKTOP_SHORTCUT = Path.home() / "Desktop" / "Alliance Simulator.lnk"

class AllianceSimulatorInstaller:
    def __init__(self):
        self.install_dir = INSTALL_DIR
        self.temp_dir = None
        self.progress = 0
        
    def log(self, message, level="INFO"):
        """Simple logging"""
        symbols = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
        print(f"{symbols.get(level, 'ℹ️')} {message}")
    
    def check_python_version(self):
        """Check if Python version is compatible"""
        if sys.version_info < (3, 8):
            self.log(f"Python {sys.version_info.major}.{sys.version_info.minor} detected. Python 3.8+ required.", "ERROR")
            return False
        
        self.log(f"Python {sys.version_info.major}.{sys.version_info.minor} detected - Compatible!", "SUCCESS")
        return True
    
    def check_internet_connection(self):
        """Check internet connectivity"""
        try:
            urllib.request.urlopen('https://github.com', timeout=5)
            self.log("Internet connection verified", "SUCCESS")
            return True
        except:
            self.log("No internet connection. Cannot download files.", "ERROR")
            return False
    
    def download_latest_release(self):
        """Download the latest release from GitHub"""
        self.log("Downloading Alliance Simulator from GitHub...")
        
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix="alliance_sim_")
        
        try:
            # Download main branch as ZIP
            download_url = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/main.zip"
            zip_path = Path(self.temp_dir) / "alliance_simulator.zip"
            
            # Download with progress (simple version)
            urllib.request.urlretrieve(download_url, zip_path)
            
            # Extract ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)
            
            # Find extracted directory
            extracted_dirs = [d for d in Path(self.temp_dir).iterdir() if d.is_dir()]
            if extracted_dirs:
                self.source_dir = extracted_dirs[0]
                self.log("Download completed successfully", "SUCCESS")
                return True
            else:
                self.log("Could not find extracted files", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Download failed: {e}", "ERROR")
            return False
    
    def install_dependencies(self):
        """Install Python dependencies"""
        self.log("Installing Python dependencies...")
        
        try:
            # Upgrade pip first
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                         check=True, capture_output=True)
            
            # Install requirements
            requirements_file = self.source_dir / "requirements_web.txt"
            if requirements_file.exists():
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)], 
                             check=True, capture_output=True)
            else:
                # Install essential packages manually
                essential_packages = [
                    "pandas>=2.0.0",
                    "numpy>=1.24.0", 
                    "matplotlib>=3.7.0",
                    "opencv-python>=4.8.0",
                    "pyzbar>=0.1.9",
                    "streamlit>=1.28.0",
                    "plotly>=5.15.0",
                    "Pillow>=10.0.0"
                ]
                
                for package in essential_packages:
                    subprocess.run([sys.executable, "-m", "pip", "install", package], 
                                 check=True, capture_output=True)
            
            self.log("Dependencies installed successfully", "SUCCESS")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"Failed to install dependencies: {e}", "ERROR")
            return False
    
    def copy_files(self):
        """Copy application files to installation directory"""
        self.log(f"Installing to {self.install_dir}...")
        
        try:
            # Create installation directory
            self.install_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy all files
            for item in self.source_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, self.install_dir)
                elif item.is_dir() and item.name != "__pycache__":
                    shutil.copytree(item, self.install_dir / item.name, dirs_exist_ok=True)
            
            self.log("Files copied successfully", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Failed to copy files: {e}", "ERROR")
            return False
    
    def create_shortcuts(self):
        """Create desktop and start menu shortcuts"""
        self.log("Creating shortcuts...")
        
        try:
            # Create batch files for easy launching
            desktop_bat = self.install_dir / "Alliance_Simulator_Desktop.bat"
            web_bat = self.install_dir / "Alliance_Simulator_Web.bat"
            
            # Desktop app launcher
            desktop_content = f'''@echo off
cd /d "{self.install_dir}"
python main.py
pause
'''
            
            # Web app launcher  
            web_content = f'''@echo off
cd /d "{self.install_dir}"
echo Starting Alliance Simulator Web Interface...
echo Open your browser to: http://localhost:8501
echo Press Ctrl+C to stop the server
streamlit run streamlit_app.py
'''
            
            with open(desktop_bat, 'w') as f:
                f.write(desktop_content)
            
            with open(web_bat, 'w') as f:
                f.write(web_content)
            
            # Try to create Windows shortcuts using PowerShell
            if os.name == 'nt':  # Windows
                try:
                    # Desktop shortcut
                    ps_command = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{Path.home() / 'Desktop' / 'Alliance Simulator.lnk'}")
$Shortcut.TargetPath = "{desktop_bat}"
$Shortcut.WorkingDirectory = "{self.install_dir}"
$Shortcut.Description = "Alliance Simulator - Team Analysis Tool"
$Shortcut.Save()
'''
                    subprocess.run(["powershell", "-Command", ps_command], check=True, capture_output=True)
                    
                    # Start menu shortcut
                    start_menu_path = Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Alliance Simulator.lnk"
                    ps_command2 = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{start_menu_path}")
$Shortcut.TargetPath = "{desktop_bat}"
$Shortcut.WorkingDirectory = "{self.install_dir}"
$Shortcut.Description = "Alliance Simulator - Team Analysis Tool"
$Shortcut.Save()
'''
                    subprocess.run(["powershell", "-Command", ps_command2], check=True, capture_output=True)
                    
                except:
                    pass  # Shortcut creation is optional
            
            self.log("Shortcuts created", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Warning: Could not create shortcuts: {e}", "WARNING")
            return True  # Non-critical failure
    
    def run_initial_setup(self):
        """Run initial application setup"""
        self.log("Running initial setup...")
        
        try:
            # Change to installation directory
            os.chdir(self.install_dir)
            
            # Run setup script if it exists
            setup_script = self.install_dir / "setup.py"
            if setup_script.exists():
                subprocess.run([sys.executable, str(setup_script), "--check"], 
                             check=True, capture_output=True)
            
            self.log("Initial setup completed", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Setup warning: {e}", "WARNING")
            return True  # Non-critical
    
    def cleanup(self):
        """Clean up temporary files"""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
            self.log("Cleanup completed", "SUCCESS")
    
    def show_completion_message(self):
        """Show installation completion message"""
        message = f"""
🎉 Alliance Simulator Installation Complete!

📍 Installation Location: {self.install_dir}

🚀 How to Run:
• Desktop App: Double-click "Alliance Simulator" shortcut on desktop
• Web Interface: Run "Alliance_Simulator_Web.bat" 
• Manual: Navigate to {self.install_dir} and run main.py

📚 Getting Started:
1. Load your CSV data or use the sample data
2. Configure columns if needed
3. Analyze teams and create alliances
4. Generate honor roll rankings

📖 Documentation:
• README.md - Basic usage guide
• ENHANCED_SYSTEMS_GUIDE.md - Advanced features
• TEST_DATA_GUIDE.md - Working with test data

For support: Check the documentation files or GitHub issues
        """
        
        print("=" * 60)
        print(message)
        print("=" * 60)
    
    def install(self):
        """Main installation process"""
        print("🤖 Alliance Simulator One-Click Installer")
        print("=" * 50)
        
        # Pre-installation checks
        if not self.check_python_version():
            input("Press Enter to exit...")
            return False
        
        if not self.check_internet_connection():
            input("Press Enter to exit...")
            return False
        
        # Installation steps
        steps = [
            ("Downloading latest version", self.download_latest_release),
            ("Installing dependencies", self.install_dependencies),
            ("Copying application files", self.copy_files),
            ("Creating shortcuts", self.create_shortcuts),
            ("Running initial setup", self.run_initial_setup),
        ]
        
        try:
            for step_name, step_func in steps:
                self.log(f"Step {len([s for s in steps if steps.index(s) <= steps.index((step_name, step_func))])}/{len(steps)}: {step_name}")
                if not step_func():
                    self.log(f"Installation failed at step: {step_name}", "ERROR")
                    return False
            
            self.show_completion_message()
            return True
            
        except KeyboardInterrupt:
            self.log("Installation cancelled by user", "WARNING")
            return False
        
        except Exception as e:
            self.log(f"Unexpected error during installation: {e}", "ERROR")
            return False
        
        finally:
            self.cleanup()

def main():
    """Main entry point"""
    installer = AllianceSimulatorInstaller()
    
    try:
        if installer.install():
            input("\nPress Enter to exit...")
        else:
            input("\nInstallation failed. Press Enter to exit...")
    
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled.")

if __name__ == "__main__":
    main()
