#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

CONFIG_JSON="$ROOT_DIR/scripts/deploy_config.json"
[ -f "$CONFIG_JSON" ] || { echo "Missing deploy_config.json" >&2; exit 1; }

# Read config values
bundle_name=$(python3 - "$CONFIG_JSON" <<'PY'
import json,sys
cfg=json.load(open(sys.argv[1]))
print(cfg["bundle_name"])
PY
)

deploy_root=$(python3 - "$CONFIG_JSON" <<'PY'
import json,sys
cfg=json.load(open(sys.argv[1]))
print(cfg["default_deploy_root"])
PY
)

doc_filename=$(python3 - "$CONFIG_JSON" <<'PY'
import json,sys
cfg=json.load(open(sys.argv[1]))
print(cfg["doc_filename"])
PY
)

# Read current version (no bump)
VERSION=$(python3 - <<'PY'
import re
from pathlib import Path
t=Path('src/gopackshot_print/__init__.py').read_text(encoding='utf-8')
m=re.search(r"__version__\s*=\s*'([^']+)'", t)
print(m.group(1) if m else '0.0.0')
PY
)

echo "Packaging minimal kit for version $VERSION (PKG-only)"

# Build .app (PyInstaller) without creating a DMG
if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "PyInstaller not found, installing into current environment..."
  python3 -m pip install --upgrade pip
  python3 -m pip install pyinstaller
fi

APP_NAME="Gopackshot PrintModule"
DIST_DIR="$ROOT_DIR/dist"; BUILD_DIR="$ROOT_DIR/build"
mkdir -p "$DIST_DIR" "$BUILD_DIR"

echo "==> Running PyInstaller (app only)"
pyinstaller \
  --noconfirm \
  --windowed \
  --name "$APP_NAME" \
  --hidden-import=ably \
  --hidden-import=PySide6.QtCore \
  --hidden-import=PySide6.QtGui \
  --hidden-import=PySide6.QtWidgets \
  --add-data "Templates:Templates" \
  src/gopackshot_print/app.py | cat

APP_PATH="$DIST_DIR/$APP_NAME.app"
if [ ! -d "$APP_PATH" ]; then
  echo "ERROR: Built app not found at $APP_PATH" >&2
  exit 1
fi

echo "==> Creating PKG"
PKG_DIR="$DIST_DIR/pkg"; mkdir -p "$PKG_DIR"
pkgbuild --install-location /Applications \
  --component "$APP_PATH" \
  "$PKG_DIR/Gopackshot_PrintModule-$VERSION.pkg" | cat

mkdir -p "$deploy_root"
KIT_DIR="$deploy_root/${bundle_name} v$VERSION - minimal kit"
rm -rf "$KIT_DIR"
mkdir -p "$KIT_DIR/scripts"

# Copy only required files
cp -R "$PKG_DIR"/*.pkg "$KIT_DIR/" || { echo "PKG not found" >&2; exit 1; }
cp -R scripts/install_from_folder.command "$KIT_DIR/scripts/" || true

# Include docs: MD and TXTs
if [ -f "docs/README_DEPLOYMENT.md" ]; then
  cp "docs/README_DEPLOYMENT.md" "$KIT_DIR/"
fi
[ -f docs/INSTALL.txt ] && cp docs/INSTALL.txt "$KIT_DIR/INSTALL.txt"
[ -f docs/README.txt ] && cp docs/README.txt "$KIT_DIR/README.txt"

echo "Minimal deployment prepared at: $KIT_DIR"


