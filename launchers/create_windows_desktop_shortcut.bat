@echo off
setlocal

set "PYDRAC_LAUNCHER=%~dp0play_windows.bat"
set "PYDRAC_WORKDIR=%~dp0.."
set "PYDRAC_SHORTCUT=%USERPROFILE%\Desktop\Play PyDrac Valley.lnk"

if not exist "%PYDRAC_LAUNCHER%" goto missing_launcher

powershell -NoProfile -ExecutionPolicy Bypass -Command "$shell = New-Object -ComObject WScript.Shell; $shortcut = $shell.CreateShortcut($env:PYDRAC_SHORTCUT); $shortcut.TargetPath = $env:PYDRAC_LAUNCHER; $shortcut.WorkingDirectory = (Resolve-Path $env:PYDRAC_WORKDIR).Path; $shortcut.WindowStyle = 1; $shortcut.Save()"
if errorlevel 1 goto shortcut_error

echo.
echo Done. A shortcut named "Play PyDrac Valley" is now on the Desktop.
echo Double-click it whenever you want to play.
echo.
pause
exit /b 0

:missing_launcher
echo.
echo Could not find the PyDrac Valley launcher.
echo.
pause
exit /b 1

:shortcut_error
echo.
echo Could not create the desktop shortcut.
echo.
pause
exit /b 1
