#!/bin/bash

PYTHON_DOWNLOAD_URL="https://www.python.org/downloads/macos/"

echo
echo "Opening the official Python download page..."
echo
echo "On the page that opens:"
echo "1. Click the latest Python 3 download for macOS."
echo "2. Open the downloaded .pkg file."
echo "3. Click Continue/Install until it finishes."
echo "4. Then come back and run create_macos_desktop_shortcut.command."
echo

open "$PYTHON_DOWNLOAD_URL"

read -r -p "Press Return to close this window..."
