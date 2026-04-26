# Teacher Install Guide

These launchers are for someone who just wants to double-click and play. Start by installing Python, then create the desktop shortcut. The game shortcut will install the game requirements the first time it runs.

## macOS

1. Open the `launchers` folder.
2. Double-click `download_python_macos.command`.
3. On the page that opens, download the latest Python 3 installer for macOS.
4. Open the downloaded `.pkg` file and click through the installer.
5. Go back to the `launchers` folder and double-click `create_macos_desktop_shortcut.command`.
6. A new `Play PyDrac Valley` shortcut will appear on the Desktop.
7. Double-click `Play PyDrac Valley` whenever you want to play.

If macOS says the script cannot be opened, right-click it, choose **Open**, then choose **Open** again.

## Windows

1. Open the `launchers` folder.
2. Double-click `download_python_windows.bat`.
3. On the page that opens, download the latest Python 3 installer for Windows.
4. Open the downloaded installer.
5. Check the box that says **Add python.exe to PATH**.
6. Click **Install Now**.
7. Go back to the `launchers` folder and double-click `create_windows_desktop_shortcut.bat`.
8. A new `Play PyDrac Valley` shortcut will appear on the Desktop.
9. Double-click `Play PyDrac Valley` whenever you want to play.

## If Python Is Missing

The game shortcut will also check for Python. If Python is missing, it opens the official Python download page automatically and tells you what to do.

## What The Shortcut Does

The first time it runs, it creates a private environment in the game folder and installs `pygame` and `pytmx`. After that, it starts the game immediately.

Keep the game folder in the same place after creating the desktop shortcut. If you move the folder, run the shortcut creator again.
