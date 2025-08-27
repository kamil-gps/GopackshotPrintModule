#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Building Gopackshot PrintModule macOS app, DMG, and PKG"

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "PyInstaller not found, installing into current environment..."
  python3 -m pip install --upgrade pip
  python3 -m pip install pyinstaller
fi

# Read version from package
VERSION=$(python3 - <<'PY'
import re, sys
from pathlib import Path
p=Path('src/gopackshot_print/__init__.py').read_text(encoding='utf-8')
m=re.search(r"__version__\s*=\s*'([^']+)'", p)
print(m.group(1) if m else '0.0.0')
PY
)
echo "==> Version: $VERSION"

APP_NAME="Gopackshot PrintModule"
DIST_DIR="$ROOT_DIR/dist"
BUILD_DIR="$ROOT_DIR/build"
APP_PATH="$DIST_DIR/$APP_NAME.app"

rm -rf "$BUILD_DIR" "$DIST_DIR"
mkdir -p "$DIST_DIR" "$BUILD_DIR"

echo "==> Running PyInstaller"
pyinstaller \
  --noconfirm \
  --windowed \
  --name "$APP_NAME" \
  --hidden-import=ably \
  --hidden-import=PySide6.QtCore \
  --hidden-import=PySide6.QtGui \
  --hidden-import=PySide6.QtWidgets \
  --add-data "Templates:Templates" \
  src/gopackshot_print/app.py

if [ ! -d "$APP_PATH" ]; then
  echo "ERROR: Built app not found at $APP_PATH"
  exit 1
fi

echo "==> Creating DMG"
DMG_DIR="$DIST_DIR/dmg"; mkdir -p "$DMG_DIR"
STAGE="$BUILD_DIR/dmg_stage"; rm -rf "$STAGE"; mkdir -p "$STAGE"
cp -R "$APP_PATH" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
hdiutil create -volname "$APP_NAME" -srcfolder "$STAGE" -ov -format UDZO "$DMG_DIR/Gopackshot_PrintModule-$VERSION.dmg" | cat

echo "==> Creating PKG"
PKG_DIR="$DIST_DIR/pkg"; mkdir -p "$PKG_DIR"
pkgbuild --install-location /Applications \
  --component "$APP_PATH" \
  "$PKG_DIR/Gopackshot_PrintModule-$VERSION.pkg" | cat

echo "==> Done"
echo "DMG: $DMG_DIR/Gopackshot_PrintModule-$VERSION.dmg"
echo "PKG: $PKG_DIR/Gopackshot_PrintModule-$VERSION.pkg"


