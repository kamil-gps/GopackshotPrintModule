import os
import cups
from PIL import Image, ImageDraw, ImageFont

PRINTER_NAME = os.environ.get('QL_PRINTER', 'Brother_QL_1100')

conn = cups.Connection()
printers = conn.getPrinters()
if PRINTER_NAME not in printers:
    raise SystemExit(f"Printer '{PRINTER_NAME}' not found. Available: {list(printers.keys())}")

# Force 29x62 mm (die-cut) using PPD's DC06 (62 mm x 29 mm)
PAGE_SIZE_CODE = 'DC06'

# Generate a simple text image sized for 62mm x 29mm at 300 DPI (approx 732x343)
width_px, height_px = 732, 343
img = Image.new('1', (width_px, height_px), color=1)

draw = ImageDraw.Draw(img)
font = ImageFont.load_default()
text = 'Hello from QL-1100 (29x62)'
text_bbox = draw.textbbox((0, 0), text, font=font)
text_w = text_bbox[2] - text_bbox[0]
text_h = text_bbox[3] - text_bbox[1]
text_x = (width_px - text_w) // 2
text_y = (height_px - text_h) // 2

draw.text((text_x, text_y), text, font=font, fill=0)

out_path = '/tmp/ql1100_hello_29x62.png'
img.save(out_path)

options = {
    'PageSize': PAGE_SIZE_CODE,
    'media': PAGE_SIZE_CODE,
    'fit-to-page': 'false',
    'scaling': '100',
}

job_id = conn.printFile(PRINTER_NAME, out_path, 'QL1100 Hello Label 29x62', options)
print('Submitted job ID:', job_id)
