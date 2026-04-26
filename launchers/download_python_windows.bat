@echo off
setlocal

echo.
echo Opening the official Python download page...
echo.
echo On the page that opens:
echo 1. Click the latest Python 3 download for Windows.
echo 2. Open the downloaded installer.
echo 3. IMPORTANT: Check the box that says "Add python.exe to PATH".
echo 4. Click Install Now.
echo 5. Then come back and run create_windows_desktop_shortcut.bat.
echo.

start "" "https://www.python.org/downloads/windows/"

pause
