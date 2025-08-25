import os
import cups
from PIL import Image, ImageDraw, ImageFont

PRINTER_NAME = os.environ.get('QL_PRINTER', 'Brother_QL_1100')
PAGE_SIZE = os.environ.get('QL_PAGE_SIZE', '62mm')  # default to continuous 62mm
TEXT = os.environ.get('QL_TEXT', 'HELLO QL-1100 (BIG)')

conn = cups.Connection()
printers = conn.getPrinters()
if PRINTER_NAME not in printers:
    raise SystemExit(f"Printer '{PRINTER_NAME}' not found. Available: {list(printers.keys())}")

# Canvas: approx 62mm wide at 300dpi -> ~732 px; height ~343 px
width_px, height_px = 732, 343
img = Image.new('1', (width_px, height_px), color=1)

draw = ImageDraw.Draw(img)

# Try to load a large TrueType font; fall back to default
font_paths = [
    '/System/Library/Fonts/Helvetica.ttc',
    '/Library/Fonts/Arial.ttf',
    '/System/Library/Fonts/Supplemental/Arial.ttf',
    '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
    '/System/Library/Fonts/Supplemental/Helvetica.ttc',
]
font = None
for p in font_paths:
    try:
        # Start very large; we'll downsize to fit
        font = ImageFont.truetype(p, size=180)
        break
    except Exception:
        continue
if font is None:
    font = ImageFont.load_default()

# Fit text to width with margins
margin_x = 20
max_width = width_px - 2 * margin_x
if hasattr(font, 'size') and isinstance(font, ImageFont.FreeTypeFont):
    size = font.size
    while size > 10:
        font = ImageFont.truetype(font.path, size=size)
        bbox = draw.textbbox((0, 0), TEXT, font=font)
        if (bbox[2] - bbox[0]) <= max_width and (bbox[3] - bbox[1]) <= height_px - 20:
            break
        size -= 4
else:
    # Default bitmap font – no scaling; proceed as-is
    pass

bbox = draw.textbbox((0, 0), TEXT, font=font)
text_w = bbox[2] - bbox[0]
text_h = bbox[3] - bbox[1]
text_x = (width_px - text_w) // 2
text_y = (height_px - text_h) // 2

draw.text((text_x, text_y), TEXT, font=font, fill=0)

out_path = '/tmp/ql1100_big.png'
img.save(out_path)

options = {
    'PageSize': PAGE_SIZE,
    'media': PAGE_SIZE,
    'BrAutoTapeCut': 'ON',
    'BrCutAtEnd': 'ON',
    'BrBiDiPrint': 'OFF',
    'fit-to-page': 'false',
    'scaling': '100',
}
job_id = conn.printFile(PRINTER_NAME, out_path, 'QL1100 BIG TEST', options)
print('Submitted job ID:', job_id)
