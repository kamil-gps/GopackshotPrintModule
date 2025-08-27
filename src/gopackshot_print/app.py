from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTabWidget, QListWidget, QPushButton, QToolBar, QLabel, QStatusBar,
    QFormLayout, QDoubleSpinBox, QCheckBox, QComboBox, QLineEdit, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QSpinBox, QFileDialog
)
from PySide6.QtCore import Qt, QSize, QMimeData, QSettings, QTimer, QObject, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont as QFontGui, QKeySequence
from .canvas import CanvasView
from .template import save_template_file, load_template_file
from .print_service import render_scene_to_png, cups_print_png
from .cloud_link import AblyLink
import os
import glob


class CsvTable(QTableWidget):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.setSelectionMode(QAbstractItemView.ExtendedSelection)
		self.setSelectionBehavior(QAbstractItemView.SelectItems)

	def keyPressEvent(self, event):
		if event.matches(QKeySequence.Copy):
			self._copy_selection()
			return
		if event.matches(QKeySequence.Paste):
			self._paste_from_clipboard()
			return
		super().keyPressEvent(event)

	def _copy_selection(self):
		ranges = self.selectedRanges()
		if not ranges:
			return
		r = ranges[0]
		rows = []
		for i in range(r.topRow(), r.bottomRow() + 1):
			cells = []
			for j in range(r.leftColumn(), r.rightColumn() + 1):
				it = self.item(i, j)
				cells.append((it.text() if it else ''))
			rows.append('\t'.join(cells))
		QApplication.clipboard().setText('\n'.join(rows))

	def _paste_from_clipboard(self):
		text = QApplication.clipboard().text()
		if not text:
			return
		start = self.currentIndex()
		row0 = start.row() if start.isValid() else max(0, self.rowCount() - 1)
		col0 = start.column() if start.isValid() else 0
		lines = [ln for ln in text.splitlines() if ln is not None]
		for dy, ln in enumerate(lines):
			# Support tab or comma separated
			vals = ln.split('\t') if ('\t' in ln) else ln.split(',')
			r = row0 + dy
			while r >= self.rowCount():
				self.insertRow(self.rowCount())
			for dx, val in enumerate(vals):
				c = col0 + dx
				if c >= self.columnCount():
					break
				if not self.item(r, c):
					self.setItem(r, c, QTableWidgetItem(val))
				else:
					self.item(r, c).setText(val)


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
		self.csv_table = CsvTable(0, 0)
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
		self.elements_list = QListWidget(); self.elements_list.setSelectionMode(QAbstractItemView.SingleSelection); self.elements_list.setStyleSheet('QListWidget { color: white; }')
		lf.addWidget(self.elements_list)
		# Rename + order controls
		rename_row = QHBoxLayout()
		self.rename_input = QLineEdit(); self.rename_btn = QPushButton('Rename')
		self.move_up_btn = QPushButton('Move Up'); self.move_down_btn = QPushButton('Move Down')
		rename_row.addWidget(self.rename_input); rename_row.addWidget(self.rename_btn)
		rename_row.addWidget(self.move_up_btn); rename_row.addWidget(self.move_down_btn)
		lf.addLayout(rename_row)
		# Saved templates section
		lf.addWidget(QLabel('Template name'))
		self.template_name = QLineEdit()
		lf.addWidget(self.template_name)
		self.saved_list = QListWidget()
		lf.addWidget(QLabel('Saved Templates'))
		lf.addWidget(self.saved_list)
		# Elements save/load/refresh buttons (moved inside Elements tab)
		el_btn_row = QHBoxLayout()
		self.btn_save = QPushButton('Save Elements')
		self.btn_load = QPushButton('Load Elements')
		self.btn_refresh = QPushButton('Refresh')
		el_btn_row.addWidget(self.btn_save)
		el_btn_row.addWidget(self.btn_load)
		el_btn_row.addWidget(self.btn_refresh)
		lf.addLayout(el_btn_row)
		self.choose_templates_btn = QPushButton('Choose Templates Folder…')
		lf.addWidget(self.choose_templates_btn)
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

		# Root layout for LeftTabs
		lay = QVBoxLayout(self)
		lay.addWidget(self.tabs)


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
		self.x = QSpinBox(); self.x.setRange(0, 100)
		self.y = QSpinBox(); self.y.setRange(0, 100)
		self.w = QSpinBox(); self.w.setRange(0, 100)
		self.h = QSpinBox(); self.h.setRange(0, 100)
		form.addRow('X (mm)', self.x)
		form.addRow('Y (mm)', self.y)
		form.addRow('Width (mm)', self.w)
		form.addRow('Height (mm)', self.h)
		self.font = QComboBox(); self.font.addItems(['Arial', 'Helvetica', 'Courier', 'Courier New', 'Noto Sans'])
		form.addRow('Font', self.font)
		self.font_size = QSpinBox(); self.font_size.setRange(6, 96); self.font_size.setValue(18)
		form.addRow('Font Size', self.font_size)
		self.font_bold = QCheckBox('Bold')
		form.addRow('', self.font_bold)
		self.align = QComboBox(); self.align.addItems(['Left', 'Center', 'Right'])
		form.addRow('Alignment', self.align)
		self.text_input = QLineEdit(); form.addRow('Text', self.text_input)
		self.code_input = QLineEdit(); form.addRow('Code Data', self.code_input)
		# New: text constraints
		self.text_fit_width = QCheckBox('Fit width (clip overflow)'); self.text_fit_width.setChecked(True)
		form.addRow('Fit Width', self.text_fit_width)
		self.max_lines = QComboBox(); self.max_lines.addItems(['1', '2']); self.max_lines.setCurrentText('1')
		form.addRow('Max Lines', self.max_lines)
		# Rotate button in inspector
		self.btn_rotate = QPushButton('Rotate 90°')
		form.addRow('', self.btn_rotate)

	def set_values(self, x: float, y: float, w: float, h: float):
		self._guard = True
		self.x.setValue(x); self.y.setValue(y); self.w.setValue(w); self.h.setValue(h)
		self._guard = False


class CloudBridge(QObject):
	# Signal args: (name, data)
	message = Signal(str, object)
	# Signal args: (status, err)
	status = Signal(str, object)


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
		self.toolbar.act_print.triggered.connect(self._print_current)
		self.canvas.scene_obj.selection_changed.connect(self._sync_inspector)
		self.inspector.x.valueChanged.connect(self._apply_inspector)
		self.inspector.y.valueChanged.connect(self._apply_inspector)
		self.inspector.w.valueChanged.connect(self._apply_inspector)
		self.inspector.h.valueChanged.connect(self._apply_inspector)
		self.inspector.font.currentTextChanged.connect(self._apply_font)
		self.inspector.font_size.valueChanged.connect(self._apply_font)
		self.inspector.font_bold.stateChanged.connect(self._apply_font)
		self.inspector.align.currentTextChanged.connect(self._apply_alignment)
		self.inspector.text_input.editingFinished.connect(self._apply_text)
		self.inspector.code_input.editingFinished.connect(self._apply_code)
		self.inspector.text_fit_width.stateChanged.connect(self._apply_text_constraints)
		self.inspector.max_lines.currentTextChanged.connect(self._apply_text_constraints)
		self.inspector.btn_rotate.clicked.connect(self._rotate_selected)
		self.left.elements_list.currentRowChanged.connect(lambda _: self._select_from_list())
		self.left.saved_list.itemDoubleClicked.connect(lambda _: self._load_template())
		self.left.btn_save.clicked.connect(self._save_template)
		self.left.btn_load.clicked.connect(self._load_template)
		self.left.btn_refresh.clicked.connect(self._refresh_saved)
		self.left.choose_templates_btn.clicked.connect(self._choose_templates_dir)
		self.left.rename_btn.clicked.connect(self._rename_element)
		self.left.move_up_btn.clicked.connect(lambda: self._reorder_selected(-1))
		self.left.move_down_btn.clicked.connect(lambda: self._reorder_selected(1))
		self._load_templates_dir_from_settings(); self._ensure_templates_dir(); self._refresh_saved()
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
		self.left.csv_table.verticalHeader().sectionClicked.connect(self._csv_preview_row)

		# ---- Cloud Link UI / Status ----
		self.cloud_status_lbl = QLabel('Cloud: disabled')
		self.status.addPermanentWidget(self.cloud_status_lbl)
		mb = self.menuBar()
		tools = mb.addMenu('Tools')
		self.act_cloud_connect = tools.addAction('Cloud Connect')
		self.act_cloud_disconnect = tools.addAction('Cloud Disconnect')
		self.act_cloud_test = tools.addAction('Cloud Send Test')
		self.act_cloud_settings = tools.addAction('Cloud Settings…')
		self.act_cloud_connect.triggered.connect(self._cloud_connect)
		self.act_cloud_disconnect.triggered.connect(self._cloud_disconnect)
		self.act_cloud_test.triggered.connect(self._cloud_send_test)
		self.act_cloud_settings.triggered.connect(self._open_cloud_settings)

		# Cloud internals
		self.cloud_link: AblyLink | None = None
		self._cloud_bridge = CloudBridge()
		self._cloud_bridge.message.connect(self._handle_cloud_message)
		self._cloud_bridge.status.connect(self._handle_cloud_status)
		self._cloud_hb = QTimer(self)
		self._cloud_hb.setInterval(30000)
		self._cloud_hb.timeout.connect(self._send_cloud_heartbeat)
		self._cloud_cfg = self._load_cloud_settings()
		if self._cloud_cfg.get('cloudEnabled') and self._cloud_cfg.get('cloudAutoconnect'):
			self._cloud_connect()

	def _load_templates_dir_from_settings(self):
		settings = QSettings('Gopackshot', 'ImageFlowPrint')
		path = settings.value('templates_dir', '', type=str)
		if path and os.path.isdir(path):
			self._templates_dir_path = path
		else:
			base = os.path.dirname(os.path.abspath(__file__))
			# If packaged with PyInstaller, bundled data lives under sys._MEIPASS/Templates
			try:
				import sys
				if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
					self._templates_dir_path = os.path.join(sys._MEIPASS, 'Templates')
					return
			except Exception:
				pass
			# Dev mode: repository Templates folder
			self._templates_dir_path = os.path.abspath(os.path.join(base, '..', '..', 'Templates'))

	def _templates_dir(self):
		return self._templates_dir_path

	def _app_root(self):
		return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

	def _runtime_dir(self):
		# Store runtime files in user Application Support to avoid writing inside app bundle
		base = os.path.expanduser('~/Library/Application Support/GopackshotPrintModule')
		os.makedirs(base, exist_ok=True)
		return base

	def _runtime_file(self, name: str) -> str:
		return os.path.join(self._runtime_dir(), name)

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

	def _choose_templates_dir(self):
		path = QFileDialog.getExistingDirectory(self, 'Choose Templates Folder', self._templates_dir())
		if path:
			self._templates_dir_path = path
			QSettings('Gopackshot', 'ImageFlowPrint').setValue('templates_dir', path)
			self._ensure_templates_dir(); self._refresh_saved(); self._ensure_csv_dir(); self._refresh_csv()

	# ---- Cloud Link implementation ----
	def _load_cloud_settings(self) -> dict:
		# QSettings with env fallbacks
		settings = QSettings('Gopackshot', 'ImageFlowPrint')
		import os
		def _get_bool(key: str, env: str, default: bool) -> bool:
			val = settings.value(key, None)
			if val is None:
				val = os.environ.get(env, str(default))
			return str(val).lower() in ('1', 'true', 'yes', 'on')
		cfg = {
			'cloudEnabled': _get_bool('cloudEnabled', 'GPP_CLOUD_ENABLED', False),
			'cloudAutoconnect': _get_bool('cloudAutoconnect', 'GPP_CLOUD_AUTOCONNECT', True),
			'cloudProvider': settings.value('cloudProvider', os.environ.get('GPP_CLOUD_PROVIDER', 'ably'), type=str),
			'ably': {
				'auth_url': settings.value('ably.auth_url', os.environ.get('GPP_ABLY_AUTH_URL', ''), type=str),
				'api_key': settings.value('ably.api_key', os.environ.get('GPP_ABLY_KEY', ''), type=str),
				'channel': settings.value('ably.channel', os.environ.get('GPP_ABLY_CHANNEL', 'gopackshot:print-module:default'), type=str),
				'client_id': settings.value('ably.client_id', os.environ.get('GPP_ABLY_CLIENT_ID', ''), type=str),
			},
		}
		return cfg

	def _cloud_connect(self):
		# Setup and start AblyLink
		cfg = self._cloud_cfg
		if cfg.get('cloudProvider') != 'ably':
			self.status.showMessage('Cloud provider not supported', 3000); return
		ably_cfg = cfg.get('ably', {})
		api_key = (ably_cfg.get('api_key') or '').strip() or None
		auth_url = (ably_cfg.get('auth_url') or '').strip() or None
		client_id = (ably_cfg.get('client_id') or '').strip() or None
		channel = ably_cfg.get('channel') or 'gopackshot:print-module:default'
		if not api_key and not auth_url:
			self.status.showMessage('Cloud connect: missing Ably credentials (auth_url or api_key)', 6000)
			self.cloud_status_lbl.setText('Cloud: error (no credentials)')
			return
		if self.cloud_link:
			# already created; stop first
			try:
				self.cloud_link.stop()
			except Exception:
				pass
		self.cloud_status_lbl.setText('Cloud: connecting…')
		# Route callbacks via Qt signals to the GUI thread
		self.cloud_link = AblyLink(
			api_key=api_key,
			auth_url=auth_url,
			client_id=client_id,
			channel=channel,
			on_message=self._cloud_bridge.message.emit,
			on_status=lambda s, e: self._cloud_bridge.status.emit(s, e),
			logger=None,
		)
		try:
			self.cloud_link.start()
		except Exception as exc:
			self.status.showMessage(f'Cloud connect failed: {exc}', 6000)
			self.cloud_status_lbl.setText('Cloud: error')

	def _cloud_disconnect(self):
		try:
			if self._cloud_hb.isActive():
				self._cloud_hb.stop()
		except Exception:
			pass
		try:
			if self.cloud_link:
				self.cloud_link.stop()
				self.cloud_link = None
		except Exception:
			pass
		self.cloud_status_lbl.setText('Cloud: disconnected')
		self.status.showMessage('Cloud disconnected', 3000)

	def _handle_cloud_status(self, status: str, err: object):
		# status: connecting, connected, disconnected, failed, error, publish
		st = str(status).lower() if status else 'unknown'
		if st == 'connected':
			self.cloud_status_lbl.setText('Cloud: connected')
			if not self._cloud_hb.isActive():
				self._cloud_hb.start()
			# send initial heartbeat
			self._send_cloud_heartbeat()
		elif st in ('disconnected', 'failed', 'error'):
			self.cloud_status_lbl.setText(f'Cloud: {st}')
			if self._cloud_hb.isActive():
				self._cloud_hb.stop()
		elif st == 'publish':
			# no-op; could flash something
			pass
		else:
			self.cloud_status_lbl.setText(f'Cloud: {st}')
		if err:
			self.status.showMessage(f'Cloud status: {st} ({err})', 3000)

	def _cloud_publish(self, name: str, data: object) -> bool:
		if not self.cloud_link:
			return False
		try:
			return self.cloud_link.publish(name, data)
		except Exception:
			return False

	def _send_cloud_heartbeat(self):
		from . import __version__
		payload = {
			'clientId': self._cloud_cfg.get('ably', {}).get('client_id') or '',
			'app': 'GopackshotPrintModule',
			'version': __version__,
			'templatesDir': self._templates_dir(),
			'ts': int(__import__('time').time()),
		}
		self._cloud_publish('heartbeat', payload)

	def _cloud_send_test(self):
		ok = self._cloud_publish('status', self._status_snapshot())
		self.status.showMessage('Cloud test message sent' if ok else 'Cloud test failed', 3000)

	def _handle_cloud_message(self, name: str, data: object):
		try:
			cmd = (name or '').lower()
			if cmd == 'ping':
				self._cloud_publish('pong', {'clientId': self._cloud_cfg.get('ably', {}).get('client_id') or '', 'app': 'GopackshotPrintModule'})
				return
			if cmd == 'notify':
				msg = '' if data is None else (data if isinstance(data, str) else str(data))
				self.status.showMessage(msg[:200], 5000)
				return
			if cmd == 'request-status':
				self._cloud_publish('status', self._status_snapshot())
				return
			if cmd == 'open-cloud-settings':
				self._open_cloud_settings()
				self._cloud_publish('ack', {'ok': True})
				return
			if cmd == 'print-request':
				self._handle_print_request(data)
				return
		except Exception as exc:
			self.status.showMessage(f'Cloud message error: {exc}', 6000)

	def _status_snapshot(self) -> dict:
		import os
		return {
			'clientId': self._cloud_cfg.get('ably', {}).get('client_id') or '',
			'printer': os.environ.get('QL_PRINTER', 'Brother_QL_1100'),
			'pagesizeDefault': 'DC06',
			'app': 'GopackshotPrintModule',
		}

	def _open_cloud_settings(self):
		self.status.showMessage('Cloud settings not implemented yet. Use env/QSettings.', 5000)

	def _apply_elements_mapping(self, mapping: dict[str, str]):
		# Set element content by id, for text/barcode/qr items
		if not mapping:
			return
		for it in self.canvas.scene_obj.items():
			if not hasattr(it, 'element_id'):
				continue
			elt_id = it.element_id
			if elt_id in mapping:
				val_text = mapping.get(elt_id) or ''
				if hasattr(it, 'toPlainText'):
					it.setPlainText(val_text)
				elif hasattr(it, 'data'):
					it.data = val_text
					try:
						it._render()
					except Exception:
						pass

	def _handle_print_request(self, data: object):
		# data expected: dict with templatePath (optional), elements mapping, printer/pagesize/dpi/autocut/previewOnly, requestId
		try:
			payload = data if isinstance(data, dict) else {}
			request_id = payload.get('requestId')
			tpl = payload.get('templatePath')
			if tpl and isinstance(tpl, str) and os.path.exists(tpl):
				self.left.elements_list.clear()
				load_template_file(self.canvas.scene_obj, tpl)
				self._rebuild_elements_list()
			# Apply elements mapping
			elts = payload.get('elements') or {}
			if isinstance(elts, dict):
				self._apply_elements_mapping({str(k): (v if v is not None else '') for k, v in elts.items()})
			# Render and maybe print
			out = self._runtime_file('gpp_preview.png')
			dpi = int(payload.get('dpi') or 300)
			render_scene_to_png(self.canvas.scene_obj, out, dpi=dpi)
			job_id = None
			if not bool(payload.get('previewOnly')):
				printer = payload.get('printer') or os.environ.get('QL_PRINTER', 'Brother_QL_1100')
				pagesize = payload.get('pagesize') or 'DC06'
				autocut = bool(payload.get('autocut', True))
				job_id = cups_print_png(out, printer=printer, pagesize=pagesize, autocut=autocut)
			ack = {'requestId': request_id, 'ok': True}
			if job_id is not None:
				ack['jobId'] = job_id
			self._cloud_publish('print-ack', ack)
			self.status.showMessage('Cloud print-request handled', 3000)
		except Exception as exc:
			self._cloud_publish('print-ack', {'requestId': (payload.get('requestId') if isinstance(data, dict) else None), 'ok': False, 'error': str(exc)})
			self.status.showMessage(f'Cloud print error: {exc}', 6000)

	def _refresh_csv(self):
		self.left.csv_saved_list.clear()
		for p in sorted(glob.glob(os.path.join(self._csv_dir(), '*.csv'))):
			self.left.csv_saved_list.addItem(p)

	def _add_text(self):
		item = self.canvas.add_text('Sample Text')
		self._on_element_added(getattr(item, 'element_id', 'T?'), 'text')

	def _add_barcode(self):
		item = self.canvas.add_barcode('123456789012', 'code128')
		self._on_element_added(getattr(item, 'element_id', 'B?'), 'barcode')

	def _add_qr(self):
		item = self.canvas.add_qr('QR DATA')
		self._on_element_added(getattr(item, 'element_id', 'Q?'), 'qr')

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
		# Guard against duplicates
		for i in range(self.left.elements_list.count()):
			if self.left.elements_list.item(i).text().startswith(element_id + ' '):
				break
		else:
			name = self._get_item_name(element_id) or ''
			label = f"{element_id} • {typ}"
			if name:
				label += f" • {name}"
			self.left.elements_list.addItem(label)
		self.left.elements_list.setCurrentRow(self.left.elements_list.count()-1)
		self._select_from_list()

	def _rebuild_elements_list(self):
		self.left.elements_list.clear()
		items = [it for it in self.canvas.scene_obj.items() if hasattr(it, 'element_id')]
		items.sort(key=lambda it: it.zValue())
		for it in items:
			elt_id = it.element_id
			if hasattr(it, 'toPlainText') and not hasattr(it, 'data'):
				typ = 'text'
			elif hasattr(it, 'symbology'):
				typ = 'barcode'
			else:
				typ = 'qr'
			name = getattr(it, 'user_name', '')
			label = f"{elt_id} • {typ}"
			if name:
				label += f" • {name}"
			self.left.elements_list.addItem(label)

	def _get_item_by_id(self, elt_id: str):
		for it in self.canvas.scene_obj.items():
			if hasattr(it, 'element_id') and it.element_id == elt_id:
				return it
		return None

	def _get_item_name(self, elt_id: str) -> str:
		it = self._get_item_by_id(elt_id)
		return getattr(it, 'user_name', '') if it else ''

	def _rename_element(self):
		row = self.left.elements_list.currentItem()
		if not row:
			return
		elt_id = row.text().split(' ')[0]
		new_name = self.left.rename_input.text().strip()
		it = self._get_item_by_id(elt_id)
		if it is None:
			return
		setattr(it, 'user_name', new_name)
		# Update label text
		typ = 'text' if hasattr(it, 'toPlainText') and not hasattr(it, 'data') else ('barcode' if hasattr(it, 'symbology') else 'qr')
		label = f"{elt_id} • {typ}"
		if new_name:
			label += f" • {new_name}"
		row.setText(label)

	def _reorder_selected(self, delta: int):
		idx = self.left.elements_list.currentRow()
		if idx < 0:
			return
		new_idx = idx + delta
		if new_idx < 0 or new_idx >= self.left.elements_list.count():
			return
		item = self.left.elements_list.takeItem(idx)
		self.left.elements_list.insertItem(new_idx, item)
		self.left.elements_list.setCurrentRow(new_idx)
		# Rebuild z-order: top of list gets higher z
		self._rebuild_z_order()

	def _rebuild_z_order(self):
		for i in range(self.left.elements_list.count()):
			text = self.left.elements_list.item(i).text()
			elt_id = text.split(' ')[0]
			it = self._get_item_by_id(elt_id)
			if it:
				it.setZValue(i)

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
			# Ensure list reflects loaded elements
			self._rebuild_elements_list()
		else:
			self.status.showMessage('Template file missing', 3000)

	def _print_current(self):
		out = self._runtime_file('gpp_preview.png')
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
		x = int(round(it.pos().x() / ppm))
		y = int(round(it.pos().y() / ppm))
		if hasattr(it, 'target_w_mm'):
			w = int(round(it.target_w_mm)); h = int(round(it.target_h_mm))
			self.inspector.code_input.setText(getattr(it, 'data', ''))
			self.inspector.text_input.setText('')
			# hide font controls for codes? keep but no-op
		else:
			bw = int(round(it.boundingRect().width() / ppm)); bh = int(round(it.boundingRect().height() / ppm))
			try:
				tw = it.textWidth()
				if tw and tw > 0:
					bw = int(round(tw / ppm))
			except Exception:
				pass
			w, h = bw, bh
			self.inspector.text_input.setText(it.toPlainText())
			self.inspector.code_input.setText('')
			# font reflect
			f = it.font(); self.inspector.font.setCurrentText(f.family()); self.inspector.font_size.setValue(max(6, int(f.pointSize()))); self.inspector.font_bold.setChecked(f.bold())
			# constraints reflect
			self.inspector.text_fit_width.setChecked(getattr(it, 'fit_width', True))
			self.inspector.max_lines.setCurrentText(str(getattr(it, 'max_lines', 1)))
		self.inspector.set_values(x, y, w, h)

	def _apply_inspector(self):
		if self.inspector._guard:
			return
		it = self._selected()
		if not it:
			return
		ppm = self.canvas.scene_obj.pixels_per_mm
		x = int(self.inspector.x.value()) * ppm
		y = int(self.inspector.y.value()) * ppm
		it.setPos(x, y)
		wmm = int(self.inspector.w.value()); hmm = int(self.inspector.h.value())
		if hasattr(it, 'target_w_mm'):
			it.target_w_mm = max(5.0, float(wmm)); it.target_h_mm = max(5.0, float(hmm))
			try:
				it._render()
			except Exception:
				pass
		else:
			try:
				it.setTextWidth(max(0.0, float(wmm) * ppm))
			except Exception:
				pass
			# apply max height override for text items
			try:
				if hasattr(it, 'set_max_height_mm'):
					it.set_max_height_mm(float(hmm) if hmm > 0 else None)
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

	def _apply_alignment(self):
		it = self._selected()
		if not it or not hasattr(it, 'set_alignment'):
			return
		try:
			it.set_alignment(self.inspector.align.currentText())
		except Exception:
			pass

	def _apply_text(self):
		it = self._selected()
		if not it or not hasattr(it, 'toPlainText'):
			return
		it.setPlainText(self.inspector.text_input.text())

	def _apply_text_constraints(self):
		it = self._selected()
		if not it or not hasattr(it, 'set_fit_width'):
			return
		try:
			it.set_fit_width(self.inspector.text_fit_width.isChecked())
		except Exception:
			pass
		try:
			it.set_max_lines(int(self.inspector.max_lines.currentText()))
		except Exception:
			pass

	def _rotate_selected(self):
		# Rotate each selected item by 90 degrees around its center
		items = self.canvas.scene_obj.selectedItems()
		for it in items:
			c = it.boundingRect().center()
			it.setTransformOriginPoint(c)
			it.setRotation((it.rotation() + 90) % 360)

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
		# Columns based on Elements list order (IDs + optional custom names)
		headers = []
		for i in range(self.left.elements_list.count()):
			label = self.left.elements_list.item(i).text()
			parts = [p.strip() for p in label.split('•')]
			elt_id = parts[0]
			elt_name = parts[2] if len(parts) >= 3 else ''
			headers.append(f"{elt_id} • {elt_name}" if elt_name else elt_id)
		self.left.csv_table.setColumnCount(len(headers))
		self.left.csv_table.setHorizontalHeaderLabels(headers)
		# keep existing rows
		self.status.showMessage('CSV columns built from current Elements', 3000)

	def _csv_del_row(self):
		row = self.left.csv_table.currentRow()
		if row >= 0:
			self.left.csv_table.removeRow(row)

	def _csv_save(self):
		name = self.left.csv_name.text().strip() or 'data'
		path = os.path.join(self._csv_dir(), f'{name}.csv')
		# Write simple CSV: header row of IDs (with names); then rows of cell text
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

	def _csv_header_to_id(self, header: str) -> str:
		h = header.strip()
		if '•' in h:
			return h.split('•')[0].strip()
		# fallback: take first token
		return h.split(' ')[0] if ' ' in h else h

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

	def _csv_preview_row(self, r: int):
		cols = [self.left.csv_table.horizontalHeaderItem(c).text() for c in range(self.left.csv_table.columnCount())]
		self._apply_csv_row_to_canvas(r, cols)
		self.status.showMessage(f'Previewed row {r+1} on canvas', 2000)

	def _csv_print_all(self):
		# For each row: set content of elements (Text/QR/Barcode) by matching ID header
		cols_headers = [self.left.csv_table.horizontalHeaderItem(c).text() for c in range(self.left.csv_table.columnCount())]
		col_ids = [self._csv_header_to_id(h) for h in cols_headers]
		for r in range(self.left.csv_table.rowCount()):
			# Apply row values
			for c, elt_id in enumerate(col_ids):
				val = self.left.csv_table.item(r, c)
				val_text = val.text() if val else ''
				# Find element by id
				for it in self.canvas.scene_obj.items():
					if hasattr(it, 'element_id') and it.element_id == elt_id:
						if hasattr(it, 'toPlainText'):
							it.setPlainText(val_text)
						elif hasattr(it, 'data'):
							it.data = val_text; 
							try: it._render()
							except Exception: pass
			# Print once for this row
			out = self._runtime_file('gpp_preview.png')
			render_scene_to_png(self.canvas.scene_obj, out, dpi=300)
			try:
				cups_print_png(out, printer=os.environ.get('QL_PRINTER', 'Brother_QL_1100'), pagesize='DC06', autocut=True)
			except Exception as e:
				self.status.showMessage(f'Print error: {e}', 5000)

	def _apply_csv_row_to_canvas(self, r: int, cols: list[str] | None = None):
		if cols is None:
			cols = [self.left.csv_table.horizontalHeaderItem(c).text() for c in range(self.left.csv_table.columnCount())]
		col_ids = [self._csv_header_to_id(h) for h in cols]
		for c, elt_id in enumerate(col_ids):
			val = self.left.csv_table.item(r, c)
			val_text = val.text() if val else ''
			for it in self.canvas.scene_obj.items():
				if hasattr(it, 'element_id') and it.element_id == elt_id:
					if hasattr(it, 'toPlainText'):
						it.setPlainText(val_text)
					elif hasattr(it, 'data'):
						it.data = val_text
						try: it._render()
						except Exception: pass


def run_app():
	app = QApplication.instance() or QApplication([])
	twin = MainWindow(); twin.show()
	return app.exec()


if __name__ == '__main__':
	run_app()


