@echo off
setlocal

rem Build a Windows executable distribution for Overture Teams Analyzer.
rem Output: dist\OvertureTeamsAnalyzer\OvertureTeamsAnalyzer.exe

pushd %~dp0\..

where python >nul 2>&1
if %errorlevel% neq 0 (
  echo Python not found in PATH.
  echo Install Python 3.8+ and ensure it is available from cmd.
  popd
  exit /b 1
)

if not exist ".venv" (
  echo Creating virtual environment in .venv ...
  python -m venv .venv
)

echo Installing/updating build dependencies ...
.venv\Scripts\python.exe -m pip install --upgrade pip pyinstaller

echo Installing application dependencies ...
.venv\Scripts\python.exe -m pip install -r requirements_web.txt
if %errorlevel% neq 0 (
  echo Failed to install application dependencies.
  popd
  exit /b 1
)

echo Validating required modules for packaging ...
.venv\Scripts\python.exe -c "import streamlit, pandas, numpy, cv2, plotly, PIL, pyzbar"
if %errorlevel% neq 0 (
  echo Missing required modules after dependency installation.
  echo Review requirements_web.txt and environment compatibility.
  popd
  exit /b 1
)

echo Building executable with PyInstaller ...
.venv\Scripts\python.exe -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onedir ^
  --specpath "build" ^
  --name "OvertureTeamsAnalyzer" ^
  --add-data "%CD%\streamlit_app.py;." ^
  --add-data "%CD%\lib;lib" ^
  --add-data "%CD%\data;data" ^
  --add-data "%CD%\config;config" ^
  --collect-all streamlit ^
  --collect-all plotly ^
  --collect-all pyzbar ^
  --collect-all PIL ^
  --hidden-import cv2 ^
  --hidden-import numpy ^
  --hidden-import pandas ^
  --paths "." ^
  "scripts\streamlit_launcher.py"

if %errorlevel% neq 0 (
  echo.
  echo Build failed.
  popd
  exit /b 1
)

echo.
echo Build completed successfully.
echo Executable: dist\OvertureTeamsAnalyzer\OvertureTeamsAnalyzer.exe
echo.
echo Optional: set OVERTURE_PORT before launch if you need a custom port.
echo   set OVERTURE_PORT=8502

popd
endlocal
