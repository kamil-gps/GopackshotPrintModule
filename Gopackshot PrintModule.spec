# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/launch_app.py'],
    pathex=['src'],
    binaries=[],
    datas=[('Templates', 'Templates')],
    hiddenimports=['ably', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Gopackshot PrintModule',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Gopackshot PrintModule',
)
app = BUNDLE(
    coll,
    name='Gopackshot PrintModule.app',
    icon=None,
    bundle_identifier=None,
)
