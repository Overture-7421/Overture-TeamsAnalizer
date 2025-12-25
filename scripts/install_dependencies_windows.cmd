@echo off
setlocal

rem Installs Python dependencies for Overture-TeamsAnalizer (Windows)
rem - Creates a local venv in .venv
rem - Installs requirements_web.txt

pushd %~dp0\..

where python >nul 2>&1
if %errorlevel% neq 0 (
  echo Python not found in PATH.
  echo Install Python 3.8+ and ensure it's added to PATH.
  popd
  exit /b 1
)

if not exist ".venv" (
  echo Creating virtual environment in .venv ...
  python -m venv .venv
)

echo Upgrading pip ...
.venv\Scripts\python.exe -m pip install --upgrade pip

echo Installing dependencies from requirements_web.txt ...
.venv\Scripts\python.exe -m pip install -r requirements_web.txt

echo.
echo Done.
echo Run the app with:
echo   .venv\Scripts\activate
echo   streamlit run streamlit_app.py

echo.
echo Note: If QR scanning errors mention ZBar, you may need to install ZBar for Windows.

popd
endlocal
