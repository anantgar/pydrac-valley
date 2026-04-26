#!/bin/bash

set -u

SCRIPT_PATH="${BASH_SOURCE[0]}"
while [ -L "$SCRIPT_PATH" ]; do
  SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
  SCRIPT_PATH="$(readlink "$SCRIPT_PATH")"
  [[ "$SCRIPT_PATH" != /* ]] && SCRIPT_PATH="$SCRIPT_DIR/$SCRIPT_PATH"
done

SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
LAUNCHER="$SCRIPT_DIR/play_macos.command"
SHORTCUT="$HOME/Desktop/Play PyDrac Valley.command"

fail() {
  echo
  echo "Could not create the desktop shortcut."
  echo "$1"
  echo
  read -r -p "Press Return to close this window..."
  exit 1
}

[ -f "$LAUNCHER" ] || fail "The launcher was not found."
chmod +x "$LAUNCHER" || fail "Could not make the launcher clickable."

cat > "$SHORTCUT" <<EOF
#!/bin/bash
"$LAUNCHER"
EOF

chmod +x "$SHORTCUT" || fail "Could not make the desktop shortcut clickable."

echo
echo "Done. A shortcut named 'Play PyDrac Valley' is now on the Desktop."
echo "Double-click it whenever you want to play."
echo
read -r -p "Press Return to close this window..."
