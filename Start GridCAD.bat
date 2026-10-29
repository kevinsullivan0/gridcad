@echo off
setlocal DisableDelayedExpansion
set "GRIDCAD_PACKAGE_ROOT=%~dp0"
set "PSModulePath=%SystemRoot%\System32\WindowsPowerShell\v1.0\Modules"
if not exist "%~dp0tools\windows_launcher.ps1" (
  echo Extract the complete GridCAD ZIP, then open Start GridCAD.bat in its folder.
  pause
  exit /b 1
)
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -Command "& ([scriptblock]::Create([IO.File]::ReadAllText((Join-Path $env:GRIDCAD_PACKAGE_ROOT 'tools\windows_launcher.ps1')))) %*"
set "GRIDCAD_RESULT=%ERRORLEVEL%"
if not "%GRIDCAD_RESULT%"=="0" pause
exit /b %GRIDCAD_RESULT%
