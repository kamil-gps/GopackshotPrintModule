#!/bin/zsh

set -euo pipefail

echo "Gopackshot PrintModule installer (local)"
echo "This will copy the app to /Applications."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
KIT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

APP_SRC="$KIT_DIR/dist/Gopackshot PrintModule.app"
if [ ! -d "$APP_SRC" ]; then
  # Fallback: search one level up
  if [ -d "$KIT_DIR/../Gopackshot PrintModule.app" ]; then
    APP_SRC="$KIT_DIR/../Gopackshot PrintModule.app"
  else
    echo "Cannot find app bundle next to this script. Please build or open the DMG."
    exit 1
  fi
fi

DEST="/Applications/Gopackshot PrintModule.app"
echo "Copying to $DEST…"
rm -rf "$DEST"
cp -R "$APP_SRC" "$DEST"

echo "Removing Gatekeeper quarantine flag (if present)…"
set +e
xattr -dr com.apple.quarantine "$DEST"
set -e

echo "Done. You can launch 'Gopackshot PrintModule' from Applications."
echo "If macOS warns about an unknown developer, right-click → Open once."

open -a "Gopackshot PrintModule" || true


