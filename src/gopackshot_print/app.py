from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTabWidget, QListWidget, QPushButton, QToolBar, QLabel, QStatusBar,
    QFormLayout, QDoubleSpinBox, QCheckBox, QComboBox, QLineEdit, QTableWidget,
    QTableWidgetItem
)
from PySide6.QtCore import Qt, QSize, QMimeData
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont as QFontGui
from .canvas import CanvasView
from .template import save_template_file, load_template_file
from .print_service import render_scene_to_png, cups_print_png
import os
import glob


class LeftTabs(QWidget):
	def __init__(self):
		super().__init__()
		self.tabs = QTabWidget()
		# Data Sources tab with inner tabs
		t_ds = QWidget(); ld = QVBoxLayout(t_ds)
		self.ds_tabs = QTabWidget()
		# CSV tab
		csv_tab = QWidget(); lcsv = QVBoxLayout(csv_tab)
		self.csv_build = QPushButton('Build CSV structure from Elements')
		self.csv_table = QTableWidget(0, 0)
		row_btns = QHBoxLayout()
		self.csv_add_row = QPushButton('Add Row')
		self.csv_del_row = QPushButton('Remove Row')
		self.csv_print_all = QPushButton('Print All')
		row_btns.addWidget(self.csv_add_row)
		row_btns.addWidget(self.csv_del_row)
		row_btns.addWidget(self.csv_print_all)
		lcsv.addWidget(self.csv_build)
		lcsv.addWidget(self.csv_table)
		lcsv.addLayout(row_btns)
		lcsv.addWidget(QLabel('CSV name'))
		self.csv_name = QLineEdit(); lcsv.addWidget(self.csv_name)
		csv_sl = QHBoxLayout()
		self.csv_save = QPushButton('Save CSV')
		self.csv_load = QPushButton('Load Selected')
		self.csv_refresh = QPushButton('Refresh')
		csv_sl.addWidget(self.csv_save); csv_sl.addWidget(self.csv_load); csv_sl.addWidget(self.csv_refresh)
		lcsv.addLayout(csv_sl)
		self.csv_saved_list = QListWidget(); lcsv.addWidget(QLabel('Saved CSVs')); lcsv.addWidget(self.csv_saved_list)
		self.ds_tabs.addTab(csv_tab, 'CSV')
		# JSON/Web placeholders
		json_tab = QWidget(); json_l = QVBoxLayout(json_tab); json_l.addWidget(QLabel('JSON data source (coming soon)'))
		web_tab = QWidget(); web_l = QVBoxLayout(web_tab); web_l.addWidget(QLabel('Web JSON data source (coming soon)'))
		self.ds_tabs.addTab(json_tab, 'JSON')
		self.ds_tabs.addTab(web_tab, 'Web JSON')
		ld.addWidget(self.ds_tabs)
		self.tabs.addTab(t_ds, 'Data Sources')
		# Elements tab
		t_fields = QWidget()
		lf = QVBoxLayout(t_fields)
		self.elements_list = QListWidget()
		lf.addWidget(self.elements_list)
		# Saved templates section
		lf.addWidget(QLabel('Template name'))
		self.template_name = QLineEdit()
		lf.addWidget(self.template_name)
		self.saved_list = QListWidget()
		lf.addWidget(QLabel('Saved Templates'))
		lf.addWidget(self.saved_list)
		self.tabs.addTab(t_fields, 'Elements')
		# Printer/Media tab
		t_media = QWidget()
		fm = QFormLayout(t_media)
		pagesize = QComboBox()
		pagesize.addItems(['DC06 (62×29)', '62mm continuous'])
		fm.addRow('Page Size', pagesize)
		marg = QDoubleSpinBox(); marg.setRange(0, 10); marg.setValue(1.0)
		fm.addRow('Margin (mm)', marg)
		grid = QDoubleSpinBox(); grid.setRange(0.25, 5.0); grid.setSingleStep(0.25); grid.setValue(1.0)
		fm.addRow('Grid (mm)', grid)
		snap = QCheckBox('Snap to grid'); snap.setChecked(True)
		fm.addRow('', snap)
		self.tabs.addTab(t_media, 'Printer/Media')

		# Save/Load Template buttons
		btn_row = QHBoxLayout()
		self.btn_save = QPushButton('Save Template')
		self.btn_load = QPushButton('Load Selected')
		self.btn_refresh = QPushButton('Refresh')
		btn_row.addWidget(self.btn_save)
		btn_row.addWidget(self.btn_load)
		btn_row.addWidget(self.btn_refresh)
		lay = QVBoxLayout(self)
		lay.addWidget(self.tabs)
		lay.addLayout(btn_row)


class DesignToolbar(QToolBar):
	def __init__(self):
		super().__init__('Design Toolbar')
		def make_icon(lbl: str) -> QIcon:
			pix = QPixmap(32, 32); pix.fill(Qt.transparent)
			p = QPainter(pix); p.setPen(QColor('#ffffff'))
			f = QFontGui('Arial', 12, QFontGui.Bold); p.setFont(f)
			p.drawText(pix.rect(), Qt.AlignCenter, lbl); p.end(); return QIcon(pix)
		self.setIconSize(QSize(32, 32))
		self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
		self.setStyleSheet('QToolBar { color: white; }')
		self.act_select = self.addAction(make_icon('⟡'), 'Select')
		self.act_add_text = self.addAction(make_icon('T'), 'Add Text')
		self.act_add_qr = self.addAction(make_icon('QR'), 'Add QR')
		self.act_add_barcode = self.addAction(make_icon('||'), 'Add Barcode')
		self.addSeparator()
		self.act_delete = self.addAction(make_icon('🗑'), 'Delete')
		self.addSeparator()
		self.act_undo = self.addAction(make_icon('↶'), 'Undo')
		self.act_redo = self.addAction(make_icon('↷'), 'Redo')
		self.addSeparator()
		self.act_grid = self.addAction(make_icon('#'), 'Grid')
		self.act_snap = self.addAction(make_icon('✚'), 'Snap')
		self.addSeparator()
		self.act_zoom_out = self.addAction(make_icon('−'), 'Zoom -')
		self.act_zoom_in = self.addAction(make_icon('+'), 'Zoom +')
		self.act_fit = self.addAction(make_icon('▭'), 'Fit')
		self.addSeparator()
		self.act_print = self.addAction(make_icon('🖨'), 'Print')


class InspectorPane(QWidget):
	def __init__(self):
		super().__init__()
		self._guard = False
		form = QFormLayout(self)
		self.x = QDoubleSpinBox(); self.x.setRange(0, 100); self.x.setDecimals(1)
		self.y = QDoubleSpinBox(); self.y.setRange(0, 100); self.y.setDecimals(1)
		self.w = QDoubleSpinBox(); self.w.setRange(0, 100); self.w.setDecimals(1)
		self.h = QDoubleSpinBox(); self.h.setRange(0, 100); self.h.setDecimals(1)
		form.addRow('X (mm)', self.x)
		form.addRow('Y (mm)', self.y)
		form.addRow('Width (mm)', self.w)
		form.addRow('Height (mm)', self.h)
		self.font = QComboBox(); self.font.addItems(['Arial', 'Helvetica', 'Noto Sans'])
		form.addRow('Font', self.font)
		self.font_size = QDoubleSpinBox(); self.font_size.setRange(6, 96); self.font_size.setValue(18)
		form.addRow('Font Size', self.font_size)
		self.font_bold = QCheckBox('Bold')
		form.addRow('', self.font_bold)
		self.text_input = QLineEdit(); form.addRow('Text', self.text_input)
		self.code_input = QLineEdit(); form.addRow('Code Data', self.code_input)

	def set_values(self, x: float, y: float, w: float, h: float):
		self._guard = True
		self.x.setValue(x); self.y.setValue(y); self.w.setValue(w); self.h.setValue(h)
		self._guard = False


class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle('Gopackshot ImageFlow – PrintModule')
		self.resize(QSize(1480, 900))
		self.status = QStatusBar(); self.setStatusBar(self.status)
		self.toolbar = DesignToolbar(); self.addToolBar(self.toolbar)
		splitter = QSplitter(Qt.Horizontal)
		self.left = LeftTabs()
		splitter.addWidget(self.left)
		center = QWidget(); cv = QVBoxLayout(center); self.canvas = CanvasView(); cv.addWidget(self.canvas)
		splitter.addWidget(center)
		self.inspector = InspectorPane()
		splitter.addWidget(self.inspector)
		splitter.setSizes([260, 700, 260])
		container = QWidget(); layout = QVBoxLayout(container)
		layout.addWidget(splitter)
		self.setCentralWidget(container)

		# Wire toolbar actions
		self.toolbar.act_add_text.triggered.connect(self._add_text)
		self.toolbar.act_add_barcode.triggered.connect(self._add_barcode)
		self.toolbar.act_add_qr.triggered.connect(self._add_qr)
		self.toolbar.act_delete.triggered.connect(self._delete_selected)
		self.toolbar.act_zoom_in.triggered.connect(self.canvas.zoom_in)
		self.toolbar.act_zoom_out.triggered.connect(self.canvas.zoom_out)
		self.toolbar.act_fit.triggered.connect(self.canvas.fit_label)
		self.toolbar.act_grid.triggered.connect(self.canvas.toggle_grid)
		self.toolbar.act_snap.triggered.connect(self.canvas.toggle_snap)

		# Update left elements list when items are added
		self.canvas.scene_obj.element_added.connect(self._on_element_added)
		self.left.btn_save.clicked.connect(self._save_template)
		self.left.btn_load.clicked.connect(self._load_template)
		self.left.btn_refresh.clicked.connect(self._refresh_saved)
		self.toolbar.act_print.triggered.connect(self._print_current)
		self.canvas.scene_obj.selection_changed.connect(self._sync_inspector)
		self.inspector.x.valueChanged.connect(self._apply_inspector)
		self.inspector.y.valueChanged.connect(self._apply_inspector)
		self.inspector.w.valueChanged.connect(self._apply_inspector)
		self.inspector.h.valueChanged.connect(self._apply_inspector)
		self.inspector.font.currentTextChanged.connect(self._apply_font)
		self.inspector.font_size.valueChanged.connect(self._apply_font)
		self.inspector.font_bold.stateChanged.connect(self._apply_font)
		self.inspector.text_input.editingFinished.connect(self._apply_text)
		self.inspector.code_input.editingFinished.connect(self._apply_code)
		self.left.elements_list.currentRowChanged.connect(lambda _: self._select_from_list())
		self.left.saved_list.itemDoubleClicked.connect(lambda _: self._load_template())

		self._ensure_templates_dir(); self._refresh_saved()
		# CSV dir
		self._ensure_csv_dir(); self._refresh_csv()
		# CSV wiring
		self.left.csv_build.clicked.connect(self._csv_build_from_elements)
		self.left.csv_add_row.clicked.connect(lambda: self.left.csv_table.insertRow(self.left.csv_table.rowCount()))
		self.left.csv_del_row.clicked.connect(self._csv_del_row)
		self.left.csv_save.clicked.connect(self._csv_save)
		self.left.csv_refresh.clicked.connect(self._refresh_csv)
		self.left.csv_load.clicked.connect(self._csv_load)
		self.left.csv_print_all.clicked.connect(self._csv_print_all)

	def _templates_dir(self):
		return os.path.expanduser('~/GopackshotTemplates')

	def _csv_dir(self):
		return os.path.join(self._templates_dir(), 'csv')

	def _ensure_templates_dir(self):
		os.makedirs(self._templates_dir(), exist_ok=True)

	def _ensure_csv_dir(self):
		os.makedirs(self._csv_dir(), exist_ok=True)

	def _refresh_saved(self):
		self.left.saved_list.clear()
		for p in sorted(glob.glob(os.path.join(self._templates_dir(), '*.json'))):
			self.left.saved_list.addItem(p)

	def _refresh_csv(self):
		self.left.csv_saved_list.clear()
		for p in sorted(glob.glob(os.path.join(self._csv_dir(), '*.csv'))):
			self.left.csv_saved_list.addItem(p)

	def _add_text(self):
		item = self.canvas.add_text('Sample Text')
		# rely on element_added signal to populate list

	def _add_barcode(self):
		item = self.canvas.add_barcode('123456789012', 'code128')

	def _add_qr(self):
		item = self.canvas.add_qr('QR DATA')

	def _delete_selected(self):
		it = self._selected()
		if not it:
			return
		elt_id = getattr(it, 'element_id', None)
		self.canvas.scene_obj.removeItem(it)
		# remove from list
		for i in range(self.left.elements_list.count()):
			if self.left.elements_list.item(i).text().startswith(elt_id + ' '):
				self.left.elements_list.takeItem(i)
				break
		self.status.showMessage(f'Deleted {elt_id}', 2000)

	def _on_element_added(self, element_id: str, typ: str):
		self.left.elements_list.addItem(f"{element_id} • {typ}")
		self.left.elements_list.setCurrentRow(self.left.elements_list.count()-1)
		self._select_from_list()

	def _select_from_list(self):
		row = self.left.elements_list.currentItem()
		if not row:
			return
		text = row.text()
		elt_id = text.split(' ')[0]
		for it in self.canvas.scene_obj.items():
			if hasattr(it, 'element_id') and it.element_id == elt_id:
				# clear other selections
				for other in self.canvas.scene_obj.selectedItems():
					other.setSelected(False)
				it.setSelected(True)
				self._sync_inspector()
				break

	def _save_template(self):
		name = self.left.template_name.text().strip() or 'template'
		path = os.path.join(self._templates_dir(), f'{name}.json')
		save_template_file(self.canvas.scene_obj, path)
		self.status.showMessage(f'Saved template to {path}', 3000)
		self._refresh_saved()

	def _load_template(self):
		row = self.left.saved_list.currentItem()
		if not row:
			self.status.showMessage('Select a saved template first', 3000); return
		path = row.text()
		if os.path.exists(path):
			self.left.elements_list.clear()
			load_template_file(self.canvas.scene_obj, path)
			self.status.showMessage(f'Loaded template from {path}', 3000)
			# repopulate list already handled by element_added signals during load
		else:
			self.status.showMessage('Template file missing', 3000)

	def _print_current(self):
		out = os.path.expanduser('~/gpp_preview.png')
		render_scene_to_png(self.canvas.scene_obj, out, dpi=300)
		try:
			jid = cups_print_png(out, printer=os.environ.get('QL_PRINTER', 'Brother_QL_1100'), pagesize='DC06', autocut=True)
			self.status.showMessage(f'Print submitted (job {jid})', 5000)
		except Exception as e:
			self.status.showMessage(f'Print error: {e}', 8000)

	# ---- Selection/Inspector sync ----
	def _selected(self):
		items = self.canvas.scene_obj.selectedItems()
		return items[0] if items else None

	def _sync_inspector(self):
		it = self._selected()
		if not it:
			self.inspector.set_values(0, 0, 0, 0); return
		ppm = self.canvas.scene_obj.pixels_per_mm
		x = it.pos().x() / ppm; y = it.pos().y() / ppm
		if hasattr(it, 'target_w_mm'):
			w = it.target_w_mm; h = it.target_h_mm
			self.inspector.code_input.setText(getattr(it, 'data', ''))
			self.inspector.text_input.setText('')
			# hide font controls for codes? keep but no-op
		else:
			bw = it.boundingRect().width() / ppm; bh = it.boundingRect().height() / ppm
			try:
				tw = it.textWidth()
				if tw and tw > 0:
					bw = tw / ppm
			except Exception:
				pass
			w, h = bw, bh
			self.inspector.text_input.setText(it.toPlainText())
			self.inspector.code_input.setText('')
			# font reflect
			f = it.font(); self.inspector.font.setCurrentText(f.family()); self.inspector.font_size.setValue(max(6, f.pointSize())); self.inspector.font_bold.setChecked(f.bold())
		self.inspector.set_values(round(x,1), round(y,1), round(w,1), round(h,1))

	def _apply_inspector(self):
		if self.inspector._guard:
			return
		it = self._selected()
		if not it:
			return
		ppm = self.canvas.scene_obj.pixels_per_mm
		x = self.inspector.x.value() * ppm
		y = self.inspector.y.value() * ppm
		it.setPos(x, y)
		wmm = self.inspector.w.value(); hmm = self.inspector.h.value()
		if hasattr(it, 'target_w_mm'):
			it.target_w_mm = max(5.0, wmm); it.target_h_mm = max(5.0, hmm)
			try:
				it._render()
			except Exception:
				pass
		else:
			try:
				it.setTextWidth(max(0.0, wmm * ppm))
			except Exception:
				pass

	def _apply_font(self):
		it = self._selected()
		if not it or not hasattr(it, 'set_font'):
			return
		fam = self.inspector.font.currentText()
		size = int(self.inspector.font_size.value())
		bold = self.inspector.font_bold.isChecked()
		try:
			it.set_font(fam, size, bold)
		except Exception:
			pass

	def _apply_text(self):
		it = self._selected()
		if not it or not hasattr(it, 'toPlainText'):
			return
		it.setPlainText(self.inspector.text_input.text())

	def _apply_code(self):
		it = self._selected()
		if not it or not hasattr(it, 'element_id'):
			return
		if hasattr(it, 'data'):
			it.data = self.inspector.code_input.text() or ''
			try:
				it._render()
			except Exception:
				pass

	def _csv_build_from_elements(self):
		# Columns based on Elements list order (IDs)
		cols = [self.left.elements_list.item(i).text().split(' ')[0] for i in range(self.left.elements_list.count())]
		self.left.csv_table.setColumnCount(len(cols))
		self.left.csv_table.setHorizontalHeaderLabels(cols)
		# keep existing rows
		self.status.showMessage('CSV columns built from current Elements', 3000)

	def _csv_del_row(self):
		row = self.left.csv_table.currentRow()
		if row >= 0:
			self.left.csv_table.removeRow(row)

	def _csv_save(self):
		name = self.left.csv_name.text().strip() or 'data'
		path = os.path.join(self._csv_dir(), f'{name}.csv')
		# Write simple CSV: header row of IDs; then rows of cell text
		cols = [self.left.csv_table.horizontalHeaderItem(c).text() for c in range(self.left.csv_table.columnCount())]
		with open(path, 'w', encoding='utf-8') as f:
			f.write(','.join(cols) + '\n')
			for r in range(self.left.csv_table.rowCount()):
				cells = []
				for c in range(self.left.csv_table.columnCount()):
					item = self.left.csv_table.item(r, c)
					cells.append((item.text() if item else '').replace(',', ' '))
				f.write(','.join(cells) + '\n')
		self._refresh_csv(); self.status.showMessage(f'Saved CSV to {path}', 3000)

	def _csv_load(self):
		row = self.left.csv_saved_list.currentItem()
		if not row: return
		path = row.text()
		if not os.path.exists(path): return
		with open(path, 'r', encoding='utf-8') as f:
			lines = [ln.rstrip('\n') for ln in f]
		if not lines: return
		head = [h.strip() for h in lines[0].split(',')]
		self.left.csv_table.setColumnCount(len(head))
		self.left.csv_table.setHorizontalHeaderLabels(head)
		self.left.csv_table.setRowCount(0)
		for data_ln in lines[1:]:
			if not data_ln: continue
			vals = [v for v in data_ln.split(',')]
			r = self.left.csv_table.rowCount(); self.left.csv_table.insertRow(r)
			for c, v in enumerate(vals):
				self.left.csv_table.setItem(r, c, QTableWidgetItem(v))
		self.status.showMessage(f'Loaded CSV {path}', 3000)

	def _csv_print_all(self):
		# For each row: set content of elements (Text/QR/Barcode) by matching ID header
		cols = [self.left.csv_table.horizontalHeaderItem(c).text() for c in range(self.left.csv_table.columnCount())]
		for r in range(self.left.csv_table.rowCount()):
			# Apply row values
			for c, col in enumerate(cols):
				val = self.left.csv_table.item(r, c)
				val_text = val.text() if val else ''
				# Find element by id
				for it in self.canvas.scene_obj.items():
					if hasattr(it, 'element_id') and it.element_id == col:
						if hasattr(it, 'toPlainText'):
							it.setPlainText(val_text)
						elif hasattr(it, 'data'):
							it.data = val_text; 
							try: it._render()
							except Exception: pass
			# Print once for this row
			out = os.path.expanduser('~/gpp_preview.png')
			render_scene_to_png(self.canvas.scene_obj, out, dpi=300)
			try:
				cups_print_png(out, printer=os.environ.get('QL_PRINTER', 'Brother_QL_1100'), pagesize='DC06', autocut=True)
			except Exception as e:
				self.status.showMessage(f'Print error: {e}', 5000)


def run_app():
	app = QApplication.instance() or QApplication([])
	twin = MainWindow(); twin.show()
	return app.exec()


if __name__ == '__main__':
	run_app()


