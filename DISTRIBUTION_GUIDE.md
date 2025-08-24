# 📦 Alliance Simulator Distribution Guide

This guide explains how to create and distribute the Alliance Simulator as a single executable or easy-to-install package.

## 🎯 Distribution Options

### Option 1: One-Click Installer (Recommended)
**Best for**: Users who want the easiest installation experience

The `alliance_simulator_installer.py` is a single file that users can download and run. It automatically:
- Downloads the latest version from GitHub
- Installs all Python dependencies
- Sets up the application
- Creates desktop shortcuts

**How to use:**
1. Share the `alliance_simulator_installer.py` file
2. Users run: `python alliance_simulator_installer.py`
3. Everything installs automatically

### Option 2: Standalone Executable
**Best for**: Users who don't have Python installed

Creates a single `.exe` file that includes everything needed.

**How to create:**
```bash
python build_executable.py
```

**Output:** `dist/Alliance_Simulator.exe` - Single file, no installation needed

### Option 3: Portable Package
**Best for**: Teams that want to run from USB drives or shared folders

Creates a folder with everything included, no installation required.

**How to create:**
```bash
python create_distribution.py
```

### Option 4: Professional Installer
**Best for**: Large-scale deployment in organizations

Creates Windows installer with shortcuts, uninstall capability, etc.

## 🚀 Quick Build Process

### Simple Method (Windows)
1. Run `build.bat`
2. Select your preferred distribution type
3. Files are created automatically

### Manual Method
1. **For executable**: `python build_executable.py`
2. **For installer**: Share `alliance_simulator_installer.py`
3. **For packages**: `python create_distribution.py`

## 📋 System Requirements

### For Building
- Python 3.8 or higher
- PyInstaller or Nuitka (installed automatically)
- Internet connection (for downloading dependencies)

### For End Users
- **Executable**: None (everything included)
- **Installer**: Python 3.8+ and internet connection
- **Portable**: Python 3.8+

## 🔧 Customization Options

### Changing the GitHub Repository
Edit `alliance_simulator_installer.py`:
```python
GITHUB_REPO = "YourUsername/YourRepo"
```

### Adding Custom Icon
Place `icon.ico` in the project folder before building executable.

### Modifying Installation Directory
Edit `alliance_simulator_installer.py`:
```python
INSTALL_DIR = Path.home() / "Your_Custom_Directory"
```

## 📊 Comparison of Distribution Methods

| Method | File Size | Setup Time | User Requirements | Portability |
|--------|-----------|------------|-------------------|-------------|
| One-Click Installer | 15KB | 2-5 min | Python + Internet | Low |
| Standalone Executable | 150-300MB | Instant | None | High |
| Portable Package | 5MB | 1 min | Python | Medium |
| Professional Installer | 200MB | 2 min | None | Medium |

## 🎯 Recommended Distribution Strategy

### For Individual Users
1. **Primary**: Share the one-click installer (`alliance_simulator_installer.py`)
2. **Backup**: Provide standalone executable for users without Python

### For Teams/Organizations
1. **Primary**: Create portable package for shared drives
2. **Alternative**: Use professional installer for managed deployments

### For Competitions/Events
1. **Recommended**: Standalone executable on USB drives
2. **Backup**: Portable package for setup on event computers

## 📁 File Structure After Installation

```
Alliance_Simulator/
├── main.py                           # Desktop application
├── streamlit_app.py                  # Web interface
├── allianceSelector.py               # Alliance selection logic
├── school_system.py                  # Honor roll system
├── config_manager.py                 # Configuration management
├── csv_converter.py                  # Data conversion
├── test_data.csv                     # Sample data
├── columnsConfig.json                # Configuration file
├── README.md                         # User guide
├── ENHANCED_SYSTEMS_GUIDE.md         # Advanced features guide
└── [other supporting files]
```

## 🔄 Update Process

### For One-Click Installer
Users simply run the installer again - it automatically updates to the latest version.

### For Standalone Executable
Rebuild and redistribute the new `.exe` file.

### For Portable Package
Replace the package contents with new files.

## ⚠️ Important Notes

### Antivirus Software
- Some antivirus programs may flag executable files
- This is normal for PyInstaller-built executables
- Users may need to add exceptions

### Dependencies
- OpenCV and camera functionality require additional system libraries
- QR scanning needs camera access permissions
- Web interface requires internet for some features

### Performance
- Standalone executables may be slower to start (10-30 seconds)
- Nuitka builds are faster than PyInstaller
- Native Python installation has the best performance

## 🐛 Troubleshooting

### Build Issues
1. **PyInstaller fails**: Try Nuitka alternative
2. **Missing dependencies**: Check requirements_web.txt
3. **Large file size**: Exclude unnecessary modules

### Runtime Issues
1. **Executable won't start**: Check antivirus settings
2. **Missing data files**: Ensure they're included in spec file
3. **Import errors**: Add modules to hiddenimports

### Installation Issues
1. **Download fails**: Check internet connection
2. **Permission errors**: Run as administrator (Windows)
3. **Python not found**: Install Python 3.8+

## 📞 Support

For distribution and installation issues:
1. Check this guide first
2. Review the build scripts for error messages
3. Test on a clean system before distributing
4. Consider providing multiple distribution options

## 🔄 Automated Building

For automated building (CI/CD), create a script that:
1. Tests the application
2. Builds multiple distribution types
3. Creates release packages
4. Uploads to distribution platforms

Example GitHub Actions workflow available in the repository.

---

*This guide covers all aspects of distributing Alliance Simulator. Choose the method that best fits your users' technical expertise and deployment requirements.*
