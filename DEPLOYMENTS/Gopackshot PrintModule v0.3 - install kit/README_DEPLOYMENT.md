# Gopackshot PrintModule

## Overview
- Desktop WYSIWYG label designer and direct print module.
- Supports Text, Barcode, QR elements with mm-precise layout.
- Ably Cloud Link for remote print-requests.

## Features
- Elements: text, barcode (code128), QR with rotation, z-order, rename.
- CSV data source to batch print rows.
- Fit Width clipping and Max Lines (1/2) for text to prevent overlap.
- Template save/load (JSON schema v2).
- Print via CUPS to Brother QL-1100 (configurable).

## Template JSON (schema v2) example
```json
{
  "schemaVersion": 2,
  "label": { "widthMm": 62.0, "heightMm": 29.0, "pixelsPerMm": 8.0, "gridMm": 1.0, "snap": true },
  "elements": [
    {
      "id": "T1",
      "type": "text",
      "xMm": 2.0,
      "yMm": 2.0,
      "wMm": 40.0,
      "hMm": 12.0,
      "text": "Sample Text",
      "font": {"family": "Arial", "size": 18, "bold": false},
      "align": "Left",
      "maxWidthMm": 40.0,
      "fitWidth": true,
      "maxLines": 2,
      "maxHeightMm": 12.0,
      "rotation": 0
    }
  ]
}
```

- xMm/yMm are the item origin (not the rotated bounding box).
- For v1 files (legacy), loader aligns by bounding box top-left.

## Cloud connectivity
- Uses Ably Realtime. Configure via env or QSettings:
  - GPP_CLOUD_ENABLED=1
  - GPP_CLOUD_AUTOCONNECT=1
  - GPP_ABLY_AUTH_URL=... (preferred) or GPP_ABLY_KEY=...
  - GPP_ABLY_CHANNEL=gopackshot:print-module:default
  - GPP_ABLY_CLIENT_ID=machine-name
- Heartbeat every 30s; inbound commands: ping, notify, request-status, print-request.

## Install
- DMG: open and drag app to /Applications.
- Or run scripts/install_from_folder.command.
