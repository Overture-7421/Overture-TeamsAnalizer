@echo off
setlocal

if "%~1"=="" (
	echo Usage:
	echo   scripts\install_ctx7_skill_workaround.cmd /owner/repo skill-name
	echo   scripts\install_ctx7_skill_workaround.cmd -Repository /owner/repo -All
	echo   scripts\install_ctx7_skill_workaround.cmd -Repository /owner/repo -TargetSkillsDir .agents/skills -All
	exit /b 1
)

set SCRIPT_DIR=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install_ctx7_skill_workaround.ps1" %*
exit /b %errorlevel%
