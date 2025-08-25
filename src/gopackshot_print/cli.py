import os
import sys
import argparse
import cups
from PIL import Image, ImageDraw, ImageFont

DEFAULT_PRINTER = os.environ.get('QL_PRINTER', 'Brother_QL_1100')


def render_text_image(text: str, width_px: int = 732, height_px: int = 343) -> str:
	img = Image.new('1', (width_px, height_px), color=1)
	draw = ImageDraw.Draw(img)
	font = None
	for p in (
		'/System/Library/Fonts/Helvetica.ttc',
		'/Library/Fonts/Arial.ttf',
		'/System/Library/Fonts/Supplemental/Arial.ttf',
		'/System/Library/Fonts/Supplemental/Helvetica.ttc',
	):
		try:
			font = ImageFont.truetype(p, size=180)
			break
		except Exception:
			continue
	if font is None:
		font = ImageFont.load_default()
	# fit
	margin_x = 20
	max_width = width_px - 2 * margin_x
	if hasattr(font, 'size') and isinstance(font, ImageFont.FreeTypeFont):
		size = font.size
		while size > 10:
			font = ImageFont.truetype(font.path, size=size)
			bbox = draw.textbbox((0, 0), text, font=font)
			if (bbox[2] - bbox[0]) <= max_width and (bbox[3] - bbox[1]) <= height_px - 20:
				break
			size -= 4
	bbox = draw.textbbox((0, 0), text, font=font)
	text_w = bbox[2] - bbox[0]
	text_h = bbox[3] - bbox[1]
	text_x = (width_px - text_w) // 2
	text_y = (height_px - text_h) // 2
	draw.text((text_x, text_y), text, font=font, fill=0)
	out_path = '/tmp/gpp_text.png'
	img.save(out_path)
	return out_path


def print_file(printer: str, filepath: str, pagesize: str, autocut: bool = True, cut_at_end: bool = True) -> int:
	conn = cups.Connection()
	if printer not in conn.getPrinters():
		raise SystemExit(f"Printer '{printer}' not found")
	options = {
		'PageSize': pagesize,
		'media': pagesize,
		'BrBiDiPrint': 'OFF',
		'fit-to-page': 'false',
		'scaling': '100',
	}
	if autocut:
		options['BrAutoTapeCut'] = 'ON'
	if cut_at_end:
		options['BrCutAtEnd'] = 'ON'
	job_id = conn.printFile(printer, filepath, f'GopackshotPrint {pagesize}', options)
	return job_id


def main(argv=None) -> int:
	parser = argparse.ArgumentParser(description='Gopackshot Print Module (CUPS)')
	parser.add_argument('--printer', default=DEFAULT_PRINTER)
	parser.add_argument('--pagesize', default='DC06', help='e.g., DC06 (62x29 die-cut) or 62mm (continuous)')
	parser.add_argument('--text', default='HELLO QL-1100')
	parser.add_argument('--width', type=int, default=732)
	parser.add_argument('--height', type=int, default=343)
	args = parser.parse_args(argv)

	img_path = render_text_image(args.text, args.width, args.height)
	job = print_file(args.printer, img_path, args.pagesize)
	print('Submitted job:', job)
	return 0


if __name__ == '__main__':
	sys.exit(main())
