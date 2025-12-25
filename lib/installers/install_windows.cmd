@echo off
setlocal

rem One-shot installer (Windows) - clones and installs from:
rem   git@github.com:Overture-7421/Overture-TeamsAnalizer.git

set REPO_SSH=git@github.com:Overture-7421/Overture-TeamsAnalizer.git
set INSTALL_DIR=%USERPROFILE%\Overture-TeamsAnalizer

where git >nul 2>&1
if %errorlevel% neq 0 (
  echo Git not found in PATH. Install Git for Windows first.
  exit /b 1
)

where python >nul 2>&1
if %errorlevel% neq 0 (
  echo Python not found in PATH. Install Python 3.8+ first.
  exit /b 1
)

if not exist "%INSTALL_DIR%" (
  echo Cloning repo into: %INSTALL_DIR%
  git clone --depth 1 %REPO_SSH% "%INSTALL_DIR%"
) else (
  echo Repo folder already exists: %INSTALL_DIR%
  echo Skipping clone.
)

cd /d "%INSTALL_DIR%"

if exist "scripts\install_dependencies_windows.cmd" (
  call scripts\install_dependencies_windows.cmd
) else (
  echo Missing scripts\install_dependencies_windows.cmd in repo.
  echo You can install deps manually with:
  echo   python -m venv .venv
  echo   .venv\Scripts\python.exe -m pip install -r requirements_web.txt
)

endlocal
