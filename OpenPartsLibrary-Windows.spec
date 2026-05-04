# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


datas = collect_data_files(
    "openpartslibrary",
    includes=[
        "images/**/*",
        "sample/**/*",
        "static/**/*",
        "templates/**/*",
        "translations/**/*",
        "search_synonyms.json",
        "tools/*.py",
    ],
)

hiddenimports = (
    collect_submodules("babel")
    + collect_submodules("flask_admin")
    + collect_submodules("flask_babel")
    + collect_submodules("odf")
    + collect_submodules("openpyxl")
    + collect_submodules("webview")
)

a = Analysis(
    ["run_desktop.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name="OpenPartsLibrary",
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
    name="OpenPartsLibrary",
)
