#!/bin/bash
set -euo pipefail

APP_NAME="Gopackshot PrintModule.app"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_SRC="$SCRIPT_DIR/$APP_NAME"
TARGET_DIR="/Applications"
if [ ! -w "$TARGET_DIR" ]; then
  TARGET_DIR="$HOME/Applications"
  mkdir -p "$TARGET_DIR"
fi
APP_DST="$TARGET_DIR/$APP_NAME"

say_step() { printf "\n==> %s\n" "$1"; }

say_step "Copying app to $TARGET_DIR"
if [ -d "$APP_DST" ]; then
  rm -rf "$APP_DST"
fi
/usr/bin/ditto "$APP_SRC" "$APP_DST"

say_step "Clearing quarantine flag"
/usr/bin/xattr -dr com.apple.quarantine "$APP_DST" || true

TPL_SRC="$SCRIPT_DIR/Templates"
TPL_DST="$HOME/Library/Application Support/GopackshotPrintModule/Templates"
mkdir -p "$TPL_DST"
/usr/bin/rsync -a "$TPL_SRC/" "$TPL_DST/" || true

say_step "Setting Templates directory preference"
/usr/bin/defaults write com.Gopackshot.ImageFlowPrint templates_dir -string "$TPL_DST"

say_step "Ensuring CUPS print service is running (may prompt for password)"
if /usr/bin/id -Gn | grep -q admin; then
  if command -v launchctl >/dev/null 2>&1; then
    sudo /bin/launchctl kickstart -k system/org.cups.cupsd || true
  fi
fi

say_step "Installation complete"
echo "Installed: $APP_DST"
echo "Templates: $TPL_DST"

echo "\nTip: Ably credentials"
echo "  defaults write com.Gopackshot.ImageFlowPrint ably.api_key -string YOUR_ABLY_KEY"\necho "  defaults write com.Gopackshot.ImageFlowPrint ably.auth_url -string https://your-auth"\n\necho "\\nLaunching app..."\nopen -a "$APP_DST" || true\n
