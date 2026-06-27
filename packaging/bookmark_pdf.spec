# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for bookmark_pdf (onedir mode for macOS).

Build:
    pyinstaller --clean bookmark_pdf.spec

Output:
    dist/BookmarkPDF/              (distribution directory)
    dist/BookmarkPDF/BookmarkPDF   (launchable binary)
"""
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(
    ['../bookmark_pdf/__main__.py'],
    pathex=['..'],
    binaries=[],
    datas=[],
    hiddenimports=collect_submodules('pypdf'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Dev-only modules — strip them to reduce binary size
        'pytest',
        'reportlab',
        'PIL',
        'tkinter.test',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BookmarkPDF',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # --windowed: no terminal window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='BookmarkPDF',
)

# macOS .app BUNDLE is disabled due to a PyInstaller 6 + Python 3.13 issue:
# libpython3.13.dylib is not placed in Contents/Frameworks, causing load failures.
# Workaround: use the onedir build at dist/BookmarkPDF/BookmarkPDF,
# or wrap manually with py2app / codesign later.