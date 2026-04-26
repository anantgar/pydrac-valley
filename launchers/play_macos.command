#!/bin/bash

set -u

SCRIPT_PATH="${BASH_SOURCE[0]}"
while [ -L "$SCRIPT_PATH" ]; do
  SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
  SCRIPT_PATH="$(readlink "$SCRIPT_PATH")"
  [[ "$SCRIPT_PATH" != /* ]] && SCRIPT_PATH="$SCRIPT_DIR/$SCRIPT_PATH"
done

SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv-macos"
VENV_PYTHON="$VENV_DIR/bin/python"
READY_FILE="$VENV_DIR/.pydrac-ready"
PYTHON_DOWNLOAD_URL="https://www.python.org/downloads/macos/"

fail() {
  echo
  echo "PyDrac Valley could not start."
  echo "$1"
  echo
  echo "If you need help, send a screenshot of this window to the student."
  read -r -p "Press Return to close this window..."
  exit 1
}

cd "$PROJECT_DIR" || fail "Could not open the game folder."

if [ ! -x "$VENV_PYTHON" ]; then
  if ! command -v python3 >/dev/null 2>&1; then
    open "$PYTHON_DOWNLOAD_URL" >/dev/null 2>&1
    fail "Python 3 is not installed. A browser page was opened so you can download it. Install Python, then double-click this shortcut again."
  fi

  echo "Setting up PyDrac Valley. This may take a minute the first time..."
  python3 -m venv "$VENV_DIR" || fail "Could not create the Python environment."
fi

if [ ! -f "$READY_FILE" ]; then
  echo "Installing game requirements. This only happens the first time..."
  "$VENV_PYTHON" -m pip install --upgrade pip || fail "Could not update pip."
  "$VENV_PYTHON" -m pip install -r requirements.txt || fail "Could not install the game requirements."
  touch "$READY_FILE" || fail "Could not finish setup."
fi

echo "Starting PyDrac Valley..."
"$VENV_PYTHON" code/main.py || fail "The game stopped unexpectedly."
