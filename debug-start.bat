@echo off
cd /d %~dp0
if not exist logs mkdir logs
if not exist logs\app.log type nul > logs\app.log
start "" "%~dp0ai-order-system.exe"
echo ai-order-system.exe started.
echo Showing logs\app.log. Press Ctrl+C to stop watching logs.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Content -Path 'logs\app.log' -Tail 80 -Wait"
