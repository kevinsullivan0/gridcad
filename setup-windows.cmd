@echo off
rem Portable package: setup never installs Python, uses pip, or accesses the network.
echo No setup is needed. Starting the included portable Python runtime.
call "%~dp0launch-windows.cmd"
exit /b %errorlevel%
