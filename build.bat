@echo off
title Alliance Simulator Build System
echo.
echo ========================================
echo    Alliance Simulator Build System
echo ========================================
echo.

echo What would you like to build?
echo.
echo 1. Create standalone executable (PyInstaller)
echo 2. Create one-click installer
echo 3. Create distribution packages  
echo 4. Build with Nuitka (better performance)
echo 5. Create all distributions
echo.

set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" (
    echo.
    echo Building standalone executable...
    python build_executable.py
) else if "%choice%"=="2" (
    echo.
    echo Creating one-click installer...
    echo The installer file will allow users to download and install automatically.
    echo File created: alliance_simulator_installer.py
    echo.
    echo Users can download and run: python alliance_simulator_installer.py
) else if "%choice%"=="3" (
    echo.
    echo Creating distribution packages...
    python create_distribution.py
) else if "%choice%"=="4" (
    echo.
    echo Building with Nuitka...
    python build_nuitka.py
) else if "%choice%"=="5" (
    echo.
    echo Creating all distributions...
    python create_distribution.py
    echo.
    echo Building executable...
    python build_executable.py
) else (
    echo Invalid choice. Please run the script again.
)

echo.
echo Build process completed!
echo.
pause
