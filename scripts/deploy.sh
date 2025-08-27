#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

CONFIG_JSON="$ROOT_DIR/scripts/deploy_config.json"
if [ ! -f "$CONFIG_JSON" ]; then
  echo "Missing deploy_config.json" >&2
  exit 1
fi

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

inc=$(python3 - "$CONFIG_JSON" <<'PY'
import json,sys
cfg=json.load(open(sys.argv[1]))
print(cfg["version_increment"])
PY
)

# Read current package version
VERSION=$(python3 - <<'PY'
import re
from pathlib import Path
t=Path('src/gopackshot_print/__init__.py').read_text(encoding='utf-8')
m=re.search(r"__version__\s*=\s*'([^']+)'", t)
print(m.group(1) if m else '0.0.0')
PY
)

# Compute next version (minor + 0.1) unless overridden
if [ -n "${NEXT_VERSION_OVERRIDE:-}" ]; then
  NEXT_VERSION="$NEXT_VERSION_OVERRIDE"
else
  NEXT_VERSION=$(python3 - <<PY
v = "$VERSION"
inc = float("$inc")
parts = v.split('.')
try:
    maj, minor = (int(parts[0]), int(parts[1])) if len(parts) >= 2 else (0, 1)
except Exception:
    maj, minor = 0, 1
minor = minor + int(round(inc*10))
print(f"{maj}.{minor}")
PY
  )
fi

echo "Current: $VERSION  Next: $NEXT_VERSION"

# Update __init__.py version
python3 - <<PY
from pathlib import Path
p=Path('src/gopackshot_print/__init__.py')
t=p.read_text(encoding='utf-8')
import re
t=re.sub(r"__version__\s*=\s*'[^']+'", "__version__ = '{}'".format("$NEXT_VERSION"), t)
p.write_text(t, encoding='utf-8')
print('Version bumped to', "$NEXT_VERSION")
PY

# Build .app, DMG, PKG
bash scripts/build_macos.sh | cat

mkdir -p "$deploy_root"
KIT_DIR="$deploy_root/${bundle_name} v$NEXT_VERSION - install kit"
rm -rf "$KIT_DIR"
mkdir -p "$KIT_DIR/scripts"

# Move artifacts
cp -R dist/dmg/*.dmg "$KIT_DIR/" || true
cp -R dist/pkg/*.pkg "$KIT_DIR/" || true
cp -R scripts/install_from_folder.command "$KIT_DIR/scripts/" || true

export BUNDLE_NAME="$bundle_name"
python3 - "$KIT_DIR" "$doc_filename" <<'PY'
import os, sys
from pathlib import Path
root = Path(sys.argv[1])
doc_name = sys.argv[2]
doc = root / doc_name
bundle = os.environ.get('BUNDLE_NAME','App')
doc.write_text((
f"# {bundle}\n\n"
"## Overview\n"
"- Desktop WYSIWYG label designer and direct print module.\n"
"- Supports Text, Barcode, QR elements with mm-precise layout.\n"
"- Ably Cloud Link for remote print-requests.\n\n"
"## Features\n"
"- Elements: text, barcode (code128), QR with rotation, z-order, rename.\n"
"- CSV data source to batch print rows.\n"
"- Fit Width clipping and Max Lines (1/2) for text to prevent overlap.\n"
"- Template save/load (JSON schema v2).\n"
"- Print via CUPS to Brother QL-1100 (configurable).\n\n"
"## Template JSON (schema v2) example\n"
"```json\n"
"{\n"
"  \"schemaVersion\": 2,\n"
"  \"label\": { \"widthMm\": 62.0, \"heightMm\": 29.0, \"pixelsPerMm\": 8.0, \"gridMm\": 1.0, \"snap\": true },\n"
"  \"elements\": [\n"
"    {\n"
"      \"id\": \"T1\",\n"
"      \"type\": \"text\",\n"
"      \"xMm\": 2.0,\n"
"      \"yMm\": 2.0,\n"
"      \"wMm\": 40.0,\n"
"      \"hMm\": 12.0,\n"
"      \"text\": \"Sample Text\",\n"
"      \"font\": {\"family\": \"Arial\", \"size\": 18, \"bold\": false},\n"
"      \"align\": \"Left\",\n"
"      \"maxWidthMm\": 40.0,\n"
"      \"fitWidth\": true,\n"
"      \"maxLines\": 2,\n"
"      \"maxHeightMm\": 12.0,\n"
"      \"rotation\": 0\n"
"    }\n"
"  ]\n"
"}\n"
"```\n\n"
"- xMm/yMm are the item origin (not the rotated bounding box).\n"
"- For v1 files (legacy), loader aligns by bounding box top-left.\n\n"
"## Cloud connectivity\n"
"- Uses Ably Realtime. Configure via env or QSettings:\n"
"  - GPP_CLOUD_ENABLED=1\n"
"  - GPP_CLOUD_AUTOCONNECT=1\n"
"  - GPP_ABLY_AUTH_URL=... (preferred) or GPP_ABLY_KEY=...\n"
"  - GPP_ABLY_CHANNEL=gopackshot:print-module:default\n"
"  - GPP_ABLY_CLIENT_ID=machine-name\n"
"- Heartbeat every 30s; inbound commands: ping, notify, request-status, print-request.\n\n"
"## Install\n"
"- DMG: open and drag app to /Applications.\n"
"- Or run scripts/install_from_folder.command.\n"
), encoding='utf-8')
PY

# Copy plain-text docs if present
[ -f docs/INSTALL.txt ] && cp docs/INSTALL.txt "$KIT_DIR/INSTALL.txt"
[ -f docs/README.txt ] && cp docs/README.txt "$KIT_DIR/README.txt"

echo "Deployment prepared at: $KIT_DIR"


