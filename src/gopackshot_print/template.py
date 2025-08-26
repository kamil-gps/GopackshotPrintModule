from __future__ import annotations

import json
import re
from typing import Dict, Any, List


def serialize_scene(scene) -> Dict[str, Any]:
	"""Convert LabelScene to a JSON-serializable dict.
	Stores basic label settings and elements (text, barcode) with IDs and mm frames.
	"""
	ppm = scene.pixels_per_mm

	def px_to_mm(px: float) -> float:
		return px / ppm

	def rect_mm(item):
		r = item.sceneBoundingRect()
		return {
			"xMm": round(px_to_mm(r.left()), 2),
			"yMm": round(px_to_mm(r.top()), 2),
			"wMm": round(px_to_mm(r.width()), 2),
			"hMm": round(px_to_mm(r.height()), 2),
		}

	elements: List[Dict[str, Any]] = []
	for it in scene.items():
		# Items are returned in Z-order; we only care about types with element_id
		if hasattr(it, 'element_id'):
			elt: Dict[str, Any] = {"id": it.element_id, **rect_mm(it)}
			# Persist optional user-defined name and rotation
			name = getattr(it, 'user_name', '')
			if name:
				elt["name"] = name
			rot = int(round(getattr(it, 'rotation', lambda: 0)() if callable(getattr(it, 'rotation', None)) else getattr(it, 'rotation', 0)))
			if rot:
				elt["rotation"] = rot
			if it.__class__.__name__ == 'TextItem':
				fam = it.font().family(); size_pt = it.font().pointSize(); bold = it.font().bold()
				align = None
				try:
					align = it.get_alignment()
				except Exception:
					align = None
				# detect max width from textWidth if set
				try:
					max_w_px = it.textWidth()
				except Exception:
					max_w_px = 0
				payload = {"type": "text", "text": it.toPlainText(), "font": {"family": fam, "size": size_pt, "bold": bold}}
				if align:
					payload["align"] = align
				if max_w_px and max_w_px > 0:
					payload["maxWidthMm"] = round(max_w_px / ppm, 2)
				elt.update(payload)
			elif it.__class__.__name__ == 'BarcodeItem':
				elt.update({"type": "barcode", "data": it.data, "symbology": it.symbology,
							  "targetWmm": it.target_w_mm, "targetHmm": it.target_h_mm})
			elif it.__class__.__name__ == 'QrItem':
				elt.update({"type": "qr", "data": it.data, "targetWmm": it.target_w_mm, "targetHmm": it.target_h_mm})
			else:
				continue
			elements.append(elt)

	return {
		"schemaVersion": 1,
		"label": {
			"widthMm": scene.width_mm,
			"heightMm": scene.height_mm,
			"pixelsPerMm": scene.pixels_per_mm,
			"gridMm": scene.grid_mm,
			"snap": scene.snap_enabled,
		},
		"elements": list(reversed(elements)),  # reverse to match visual stacking top-first
	}


def _max_id(ids: List[str], prefix: str) -> int:
	maxn = 0
	for s in ids:
		m = re.match(rf"{re.escape(prefix)}(\d+)$", s)
		if m:
			n = int(m.group(1))
			if n > maxn:
				maxn = n
	return maxn


def deserialize_scene(scene, data: Dict[str, Any]) -> None:
	"""Clear and rebuild scene from JSON dict."""
	# Clear items
	for it in list(scene.items()):
		scene.removeItem(it)

	label = data.get('label', {})
	scene.width_mm = float(label.get('widthMm', 62.0))
	scene.height_mm = float(label.get('heightMm', 29.0))
	scene.grid_mm = float(label.get('gridMm', 1.0))
	scene.snap_enabled = bool(label.get('snap', True))
	# Keep scene.pixels_per_mm as-is to match display DPI settings
	# Recompute label rect
	scene.label_rect.setWidth(scene.width_mm * scene.pixels_per_mm)
	scene.label_rect.setHeight(scene.height_mm * scene.pixels_per_mm)
	scene.setSceneRect(scene.label_rect.adjusted(-40, -40, 40, 40))

	for elt in data.get('elements', []):
		etype = elt.get('type')
		id_ = elt.get('id')
		x = float(elt.get('xMm', 0)) * scene.pixels_per_mm
		y = float(elt.get('yMm', 0)) * scene.pixels_per_mm
		if etype == 'text':
			item = scene.add_text_with_id(id_, elt.get('text', ''))
			item.setPos(x, y)
			f = elt.get('font') or {}
			fam = f.get('family', 'Arial'); size_pt = int(f.get('size', 18) or 18); bold = bool(f.get('bold', False))
			try:
				item.set_font(fam, size_pt, bold)
			except Exception:
				pass
			# alignment
			if 'align' in elt:
				try:
					item.set_alignment(elt['align'])
				except Exception:
					pass
			# max width wrap
			if 'maxWidthMm' in elt:
				try:
					item.setTextWidth(float(elt['maxWidthMm']) * scene.pixels_per_mm)
				except Exception:
					pass
			# restore name and rotation
			if 'name' in elt:
				setattr(item, 'user_name', elt['name'])
			if 'rotation' in elt:
				try: item.setRotation(float(elt['rotation']))
				except Exception: pass
		elif etype == 'barcode':
			item = scene.add_barcode_with_id(id_, elt.get('data', ''), elt.get('symbology', 'code128'))
			item.setPos(x, y)
			if 'targetWmm' in elt: item.target_w_mm = float(elt['targetWmm'])
			if 'targetHmm' in elt: item.target_h_mm = float(elt['targetHmm'])
			item._render()
			if 'name' in elt:
				setattr(item, 'user_name', elt['name'])
			if 'rotation' in elt:
				try: item.setRotation(float(elt['rotation']))
				except Exception: pass
		elif etype == 'qr':
			item = scene.add_qr_with_id(id_, elt.get('data', ''))
			item.setPos(x, y)
			if 'targetWmm' in elt: item.target_w_mm = float(elt['targetWmm'])
			if 'targetHmm' in elt: item.target_h_mm = float(elt['targetHmm'])
			item._render()
			if 'name' in elt:
				setattr(item, 'user_name', elt['name'])
			if 'rotation' in elt:
				try: item.setRotation(float(elt['rotation']))
				except Exception: pass

	# Reset counters based on loaded IDs
	ids = [e.get('id', '') for e in data.get('elements', [])]
	scene._id_counters = {
		"text": _max_id(ids, 'T'),
		"barcode": _max_id(ids, 'B'),
		"qr": _max_id(ids, 'Q'),
	}


def save_template_file(scene, path: str) -> None:
	with open(path, 'w', encoding='utf-8') as f:
		json.dump(serialize_scene(scene), f, indent=2)


def load_template_file(scene, path: str) -> None:
	with open(path, 'r', encoding='utf-8') as f:
		data = json.load(f)
	deserialize_scene(scene, data)


