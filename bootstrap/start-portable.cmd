@echo off
setlocal DisableDelayedExpansion
rem This launcher lives in bootstrap; the runtime and UI live one level above it.
pushd "%~dp0.." || exit /b 1
if not exist "runtime\python.exe" goto missing
if not exist "grabcad_grid_ui.py" goto missing
"runtime\python.exe" "grabcad_grid_ui.py"
set "result=%errorlevel%"
popd
if not "%result%"=="0" pause
exit /b %result%
:missing
echo Please extract the entire portable ZIP first. The runtime or app is missing.
echo Use the complete portable Windows package, not just this launcher.
popd
pause
exit /b 1
