from __future__ import annotations

from PySide6.QtGui import QImage
from PySide6.QtCore import Qt, QRectF
import cups
import os


def render_scene_to_png(scene, out_path: str, dpi: int = 300) -> str:
	"""Render the given QGraphicsScene to a monochrome PNG at the specified dpi.
	WYSIWYG: render the logical label rect only.
	"""
	label_rect: QRectF = scene.label_rect
	px_w = int(label_rect.width() / scene.pixels_per_mm * (dpi / 25.4))
	px_h = int(label_rect.height() / scene.pixels_per_mm * (dpi / 25.4))
	img = QImage(px_w, px_h, QImage.Format_Grayscale8)
	img.fill(255)
	# Render scene portion directly; Qt 6 signature is render(painter, target, source, aspectRatioMode)
	from PySide6.QtGui import QPainter
	p = QPainter(img)
	p.setRenderHint(QPainter.Antialiasing)
	scene.render(p, QRectF(0, 0, px_w, px_h), label_rect, Qt.KeepAspectRatio)
	p.end()
	img.save(out_path)
	return out_path


def cups_print_png(png_path: str, printer: str = 'Brother_QL_1100', pagesize: str = 'DC06', autocut: bool = True) -> int:
	conn = cups.Connection()
	printers = conn.getPrinters()
	if printer not in printers:
		raise RuntimeError(f"Printer '{printer}' not found")
	opts = {
		'PageSize': pagesize,
		'media': pagesize,
		'fit-to-page': 'false',
		'scaling': '100',
		'BrBiDiPrint': 'OFF',
	}
	if autocut:
		opts['BrAutoTapeCut'] = 'ON'; opts['BrCutAtEnd'] = 'ON'
	job_id = conn.printFile(printer, png_path, 'Gopackshot WYSIWYG', opts)
	return job_id


