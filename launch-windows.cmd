@echo off
setlocal DisableDelayedExpansion
pushd "%~dp0" || exit /b 1
if not exist "runtime\python.exe" goto missing
"runtime\python.exe" "grabcad_grid_ui.py"
set "result=%errorlevel%"
popd
if not "%result%"=="0" pause
exit /b %result%
:missing
echo Please extract the entire portable ZIP before launching.
echo This package needs runtime\python.exe beside the app. No installation is needed.
popd
pause
exit /b 1
