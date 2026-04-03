@echo off
setlocal

rem Create a zip release for the Windows onedir distribution.
rem Output: releases\OvertureTeamsAnalyzer-windows.zip

pushd %~dp0\..

if not exist "dist\OvertureTeamsAnalyzer\OvertureTeamsAnalyzer.exe" (
  echo Windows build not found.
  echo Run scripts\build_windows_exe.cmd first.
  popd
  exit /b 1
)

if not exist "releases" mkdir releases

powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist/OvertureTeamsAnalyzer' -DestinationPath 'releases/OvertureTeamsAnalyzer-windows.zip' -Force"
if %errorlevel% neq 0 (
  echo.
  echo Failed to create zip package.
  popd
  exit /b 1
)

echo.
echo Zip package created successfully.
echo Archive: releases\OvertureTeamsAnalyzer-windows.zip

popd
endlocal
