# Gopackshot PrintModule – Deployment & Usage Guide

## Overview
- Desktop WYSIWYG label designer and direct print module for Brother QL series.
- Elements: Text, Barcode (code128), QR with rotation, z-order, rename.
- CSV data source to preview/print batches.
- Cloud Link via Ably for remote print-requests.

## Installation
- DMG: open `.dmg` and drag `Gopackshot PrintModule.app` to `/Applications`.
- PKG: double-click `.pkg` and follow the installer (writes to `/Applications`).
- First run on macOS: Right‑click the app → Open.

## Printers and CUPS setup
- Install your Brother QL printer (e.g., QL‑1100) using Brother’s macOS driver or ensure it is available in CUPS (System Settings → Printers).
- Verify the printer name (e.g., `Brother_QL_1100`).
- Optional: set environment variable `QL_PRINTER` to override the default.
- Supported page sizes: `DC06 (62×29)` or `62mm continuous` (match your roll).
- App uses CUPS via `pycups`; printing requires the printer to be installed in the OS.

## Cloud Link (Ably)
- Configure via env or QSettings:
  - `GPP_CLOUD_ENABLED=1`
  - `GPP_CLOUD_AUTOCONNECT=1`
  - `GPP_ABLY_AUTH_URL=...` (preferred) or `GPP_ABLY_KEY=...`
  - `GPP_ABLY_CHANNEL=gopackshot:print-module:default`
  - `GPP_ABLY_CLIENT_ID=machine-name`
- Tools → Cloud Connect/Disconnect/Send Test.
- Inbound events: `ping`, `notify`, `request-status`, `print-request`.
- Heartbeat every 30s when connected.

## Template JSON (schema v2)
All geometry is in millimeters. For text, `xMm`/`yMm` are the element origin (not the rotated bounding box). For legacy v1 templates, loader aligns by bounding box top‑left.

```json
{
  "schemaVersion": 2,
  "label": {
    "widthMm": 62.0,
    "heightMm": 29.0,
    "pixelsPerMm": 8.0,
    "gridMm": 1.0,
    "snap": true
  },
  "elements": [
    {
      "id": "T1",
      "type": "text",
      "xMm": 2.0,
      "yMm": 2.0,
      "wMm": 40.0,      // sceneBoundingRect width (mm) at save time
      "hMm": 12.0,      // sceneBoundingRect height (mm) at save time
      "text": "Sample Text",
      "font": { "family": "Arial", "size": 18, "bold": false },
      "align": "Left",  // Left | Center | Right
      "maxWidthMm": 40.0, // if present, sets text wrap width
      "fitWidth": true,   // clip horizontally to width when true
      "maxLines": 2,      // 1 or 2; controls vertical clipping/wrapping
      "maxHeightMm": 12.0,// optional: overrides vertical clip in mm
      "rotation": 0       // degrees; pivot at element center
    },
    {
      "id": "B1",
      "type": "barcode",
      "xMm": 2.0,
      "yMm": 12.0,
      "wMm": 40.0,
      "hMm": 12.0,
      "data": "123456789012",
      "symbology": "code128",
      "targetWmm": 40.0,
      "targetHmm": 12.0,
      "rotation": 0
    },
    {
      "id": "Q1",
      "type": "qr",
      "xMm": 40.0,
      "yMm": 10.0,
      "wMm": 20.0,
      "hMm": 20.0,
      "data": "QR DATA",
      "targetWmm": 20.0,
      "targetHmm": 20.0,
      "rotation": 0
    }
  ]
}
```

### Field definitions
- `schemaVersion`: 2 for the current format.
- `label.widthMm/heightMm`: logical label size.
- `label.pixelsPerMm`: display/render scale; keep default unless you change the editor’s DPI scale.
- `label.gridMm`: grid spacing used for snapping.
- `label.snap`: whether elements snap to grid (interactive). During load, snapping is disabled to preserve exact saved positions.

- For each element:
  - `id`: unique per element.
  - `type`: `text` | `barcode` | `qr`.
  - `xMm`/`yMm`: element origin in scene, millimeters.
  - `wMm`/`hMm`: saved scene-bounds width/height (informational; size derives from text/targets).
  - `rotation`: degrees; pivot is the center of the element after geometry is applied.

- Text specifics:
  - `text`, `font.family|size|bold`, `align`.
  - `maxWidthMm`: applied as `textWidth` to enable wrapping/clipping.
  - `fitWidth`: if true, horizontal clip at width; if false, text may exceed width.
  - `maxLines`: 1 = single line no wrap; 2 = wrap to width and clip to 2 lines.
  - `maxHeightMm`: optional explicit vertical clip; when omitted, auto height uses font metrics and `maxLines`.

- Barcode specifics:
  - `data`, `symbology` (e.g., `code128`).
  - `targetWmm`, `targetHmm`: requested render size; element’s pixmap is generated to fit these dimensions.

- QR specifics:
  - `data` string.
  - `targetWmm`, `targetHmm`: requested render size.

## CSV printing
- Build columns from current elements (Elements tab → Build CSV structure).
- Save/load CSV under Templates/csv.
- Print All iterates rows, sets element values by ID, renders, and prints each.

## Ably print-request schema (example)
```json
{
  "templatePath": "/absolute/path/to/template.json",
  "elements": { "T1": "Hello", "B1": "5901234123457", "Q1": "QRDATA" },
  "printer": "Brother_QL_1100",
  "pagesize": "DC06",
  "dpi": 300,
  "autocut": true,
  "previewOnly": false,
  "requestId": "req-123"
}
```
- Responses include `print-ack` with `{ requestId, ok, jobId?, error? }`.

## Troubleshooting
- If elements shift after load: ensure you’re on schema v2. For v1 files, loader aligns by bounding box; re‑save to upgrade.
- If bottom text is clipped: increase Height (mm) in Inspector or lower font size; Fit Width + Max Lines control clipping.
- If printer not found: check CUPS/System Settings; ensure correct printer name and media.

---
This document is included in each deployment kit and can be updated as features evolve.
