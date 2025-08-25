from PySide6.QtCore import QRectF, QPointF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPen, QFont, QImage, QPixmap
from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsTextItem, QGraphicsView, QGraphicsPixmapItem
import qrcode
import io
import barcode
from barcode.writer import ImageWriter


def mm_to_px(mm: float, pixels_per_mm: float) -> float:
	return mm * pixels_per_mm


def px_to_mm(px: float, pixels_per_mm: float) -> float:
	return px / pixels_per_mm



class TextItem(QGraphicsTextItem):
	def __init__(self, text: str, scene: 'LabelScene', element_id: str):
		super().__init__(text)
		self.scene_ref = scene
		self.element_id = element_id
		self.setFlags(
			QGraphicsItem.ItemIsSelectable |
			QGraphicsItem.ItemIsMovable |
			QGraphicsItem.ItemSendsGeometryChanges
		)
		# Do not enter text editing on click; allow selection/drag. We'll enable editing later via explicit action.
		self.setTextInteractionFlags(Qt.NoTextInteraction)
		f = QFont('Arial', 18)
		self.setFont(f)
		self.setDefaultTextColor(Qt.black)

	def set_font(self, family: str, size_pt: int, bold: bool):
		f = QFont(family, size_pt)
		f.setBold(bool(bold))
		self.setFont(f)

	def itemChange(self, change, value):
		if change == QGraphicsItem.ItemPositionChange and self.scene_ref.snap_enabled:
			pos: QPointF = value
			ppm = self.scene_ref.pixels_per_mm
			grid = self.scene_ref.grid_mm
			x_mm = round(px_to_mm(pos.x(), ppm) / grid) * grid
			y_mm = round(px_to_mm(pos.y(), ppm) / grid) * grid
			return QPointF(mm_to_px(x_mm, ppm), mm_to_px(y_mm, ppm))
		return super().itemChange(change, value)


class LabelScene(QGraphicsScene):
	selection_changed = Signal()
	element_added = Signal(str, str)

	def __init__(self, width_mm: float = 62.0, height_mm: float = 29.0, pixels_per_mm: float = 8.0, grid_mm: float = 1.0):
		super().__init__()
		self.width_mm = width_mm
		self.height_mm = height_mm
		self.pixels_per_mm = pixels_per_mm
		self.grid_mm = grid_mm
		self.snap_enabled = True
		self.grid_enabled = True
		self.label_rect = QRectF(0, 0, mm_to_px(width_mm, pixels_per_mm), mm_to_px(height_mm, pixels_per_mm))
		self.setSceneRect(self.label_rect.adjusted(-40, -40, 40, 40))
		self.selectionChanged.connect(self.selection_changed)
		self._id_counters = {"text": 0, "barcode": 0, "qr": 0}

	def set_grid(self, enabled: bool):
		self.grid_enabled = enabled
		self.update()

	def set_snap(self, enabled: bool):
		self.snap_enabled = enabled

	def drawBackground(self, painter, rect):
		# Outside area
		painter.fillRect(rect, QBrush(QColor('#f3f3f4')))
		# Label board
		painter.fillRect(self.label_rect, QBrush(Qt.white))
		painter.setPen(QPen(QColor('#d0d0d0'), 1))
		painter.drawRect(self.label_rect)
		# Grid
		if self.grid_enabled:
			grid_px = mm_to_px(self.grid_mm, self.pixels_per_mm)
			left = self.label_rect.left()
			top = self.label_rect.top()
			right = self.label_rect.right()
			bottom = self.label_rect.bottom()
			pen_minor = QPen(QColor(210, 210, 210), 1)
			painter.setPen(pen_minor)
			i = 0
			y = top
			while y <= bottom:
				painter.drawLine(left, y, right, y)
				y += grid_px
				i += 1
			i = 0
			x = left
			while x <= right:
				painter.drawLine(x, top, x, bottom)
				x += grid_px
				i += 1

	def _next_id(self, typ: str) -> str:
		self._id_counters[typ] += 1
		prefix = 'T' if typ == 'text' else 'B' if typ == 'barcode' else 'Q' if typ == 'qr' else 'E'
		return f"{prefix}{self._id_counters[typ]}"

	def add_text(self, text: str = 'Sample Text') -> TextItem:
		eid = self._next_id('text')
		item = TextItem(text, self, eid)
		# default place at 2mm,2mm
		x = mm_to_px(2, self.pixels_per_mm)
		y = mm_to_px(2, self.pixels_per_mm)
		item.setPos(x, y)
		self.addItem(item)
		self.element_added.emit(eid, 'text')
		return item

	# helper used by template loader
	def add_text_with_id(self, element_id: str, text: str) -> TextItem:
		item = TextItem(text, self, element_id)
		x = mm_to_px(2, self.pixels_per_mm); y = mm_to_px(2, self.pixels_per_mm)
		item.setPos(x, y); self.addItem(item); self.element_added.emit(element_id, 'text'); return item

	def add_barcode(self, data: str = '123456789012', symbology: str = 'code128') -> 'BarcodeItem':
		eid = self._next_id('barcode')
		item = BarcodeItem(self, eid, data=data, symbology=symbology)
		x = mm_to_px(2, self.pixels_per_mm)
		y = mm_to_px(12, self.pixels_per_mm)
		item.setPos(x, y)
		self.addItem(item)
		self.element_added.emit(eid, 'barcode')
		return item

	def add_barcode_with_id(self, element_id: str, data: str, symbology: str = 'code128') -> 'BarcodeItem':
		item = BarcodeItem(self, element_id, data=data, symbology=symbology)
		x = mm_to_px(2, self.pixels_per_mm); y = mm_to_px(12, self.pixels_per_mm)
		item.setPos(x, y); self.addItem(item); self.element_added.emit(element_id, 'barcode'); return item

	def add_qr(self, data: str = 'QR DATA') -> 'QrItem':
		eid = self._next_id('qr')
		item = QrItem(self, eid, data=data)
		x = mm_to_px(40, self.pixels_per_mm)
		y = mm_to_px(10, self.pixels_per_mm)
		item.setPos(x, y)
		self.addItem(item)
		self.element_added.emit(eid, 'qr')
		return item

	def add_qr_with_id(self, element_id: str, data: str) -> 'QrItem':
		item = QrItem(self, element_id, data=data)
		x = mm_to_px(40, self.pixels_per_mm); y = mm_to_px(10, self.pixels_per_mm)
		item.setPos(x, y); self.addItem(item); self.element_added.emit(element_id, 'qr'); return item


class CanvasView(QGraphicsView):
	def __init__(self):
		self.pixels_per_mm = 8.0
		self.scene_obj = LabelScene(pixels_per_mm=self.pixels_per_mm)
		super().__init__(self.scene_obj)
		self.setRenderHints(self.renderHints() | self.RenderHint.Antialiasing if hasattr(self, 'RenderHint') else self.renderHints())
		self.setDragMode(QGraphicsView.RubberBandDrag)
		self.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)
		self.scale(1.0, 1.0)
		self.setAcceptDrops(True)
		# Initial fit
		self.fit_label()

	def zoom_in(self):
		self.scale(1.1, 1.1)

	def zoom_out(self):
		self.scale(0.9, 0.9)

	def fit_label(self):
		self.fitInView(self.scene_obj.label_rect, Qt.KeepAspectRatio)

	def resizeEvent(self, event):
		super().resizeEvent(event)
		# Always keep the label fitted to available space
		self.fit_label()

	def toggle_grid(self):
		self.scene_obj.set_grid(not self.scene_obj.grid_enabled)

	def toggle_snap(self):
		self.scene_obj.set_snap(not self.scene_obj.snap_enabled)

	def add_text(self, text: str = 'Sample Text') -> TextItem:
		return self.scene_obj.add_text(text)

	def add_barcode(self, data: str = '123456789012', symbology: str = 'code128') -> 'BarcodeItem':
		return self.scene_obj.add_barcode(data, symbology)

	def add_qr(self, data: str = 'QR DATA') -> 'QrItem':
		return self.scene_obj.add_qr(data)

	def dragEnterEvent(self, event):
		if event.mimeData().hasText():
			event.acceptProposedAction()
		else:
			event.ignore()

	def dropEvent(self, event):
		kind = event.mimeData().text()
		if kind == 'Text':
			self.add_text('Sample Text')
		elif kind == 'Barcode':
			self.add_barcode('123456789012', 'code128')
		event.acceptProposedAction()


class BarcodeItem(QGraphicsPixmapItem):
	def __init__(self, scene: 'LabelScene', element_id: str, data: str, symbology: str = 'code128'):
		super().__init__()
		self.scene_ref = scene
		self.element_id = element_id
		self.data = data
		self.symbology = symbology
		self.setFlags(
			QGraphicsItem.ItemIsSelectable |
			QGraphicsItem.ItemIsMovable |
			QGraphicsItem.ItemSendsGeometryChanges
		)
		self.target_w_mm = 40.0
		self.target_h_mm = 12.0
		self._render()

	def _render(self):
		writer = ImageWriter()
		writer.set_options({'foreground': 'black', 'background': 'white', 'write_text': False, 'quiet_zone': 2.0})
		cls = barcode.get_barcode_class(self.symbology)
		bc = cls(self.data, writer=writer)
		pil_img = bc.render()
		ppm = self.scene_ref.pixels_per_mm
		w = int(mm_to_px(self.target_w_mm, ppm))
		h = int(mm_to_px(self.target_h_mm, ppm))
		pil_img = pil_img.resize((w, h))
		buf = io.BytesIO(); pil_img.save(buf, format='PNG')
		qimg = QImage.fromData(buf.getvalue(), 'PNG')
		self.setPixmap(QPixmap.fromImage(qimg))

	def itemChange(self, change, value):
		if change == QGraphicsItem.ItemPositionChange and self.scene_ref.snap_enabled:
			pos: QPointF = value
			ppm = self.scene_ref.pixels_per_mm
			grid = self.scene_ref.grid_mm
			x_mm = round(px_to_mm(pos.x(), ppm) / grid) * grid
			y_mm = round(px_to_mm(pos.y(), ppm) / grid) * grid
			return QPointF(mm_to_px(x_mm, ppm), mm_to_px(y_mm, ppm))
		return super().itemChange(change, value)


class QrItem(QGraphicsPixmapItem):
	def __init__(self, scene: 'LabelScene', element_id: str, data: str):
		super().__init__()
		self.scene_ref = scene
		self.element_id = element_id
		self.data = data
		self.setFlags(
			QGraphicsItem.ItemIsSelectable |
			QGraphicsItem.ItemIsMovable |
			QGraphicsItem.ItemSendsGeometryChanges
		)
		self.target_w_mm = 20.0
		self.target_h_mm = 20.0
		self._render()

	def _render(self):
		qr = qrcode.QRCode(border=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
		qr.add_data(self.data)
		qr.make(fit=True)
		pil_img = qr.make_image(fill_color='black', back_color='white').convert('L')
		ppm = self.scene_ref.pixels_per_mm
		w = int(mm_to_px(self.target_w_mm, ppm))
		h = int(mm_to_px(self.target_h_mm, ppm))
		pil_img = pil_img.resize((w, h))
		buf = io.BytesIO(); pil_img.save(buf, format='PNG')
		qimg = QImage.fromData(buf.getvalue(), 'PNG')
		self.setPixmap(QPixmap.fromImage(qimg))

	def itemChange(self, change, value):
		if change == QGraphicsItem.ItemPositionChange and self.scene_ref.snap_enabled:
			pos: QPointF = value
			ppm = self.scene_ref.pixels_per_mm
			grid = self.scene_ref.grid_mm
			x_mm = round(px_to_mm(pos.x(), ppm) / grid) * grid
			y_mm = round(px_to_mm(pos.y(), ppm) / grid) * grid
			return QPointF(mm_to_px(x_mm, ppm), mm_to_px(y_mm, ppm))
		return super().itemChange(change, value)


