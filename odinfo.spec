# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['flask_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('opsdata', 'opsdata'),
        ('ref-data', 'ref-data'),
        ('templates', 'templates'),
        ('instance', 'instance')
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'scripts',
        'opsdata/*.sqlite',
        '.venv',
        'out',
        'test',
        'secret.txt',
        'instance'
    ],
    noarchive=True,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [('v', None, 'OPTION')],
    name='odinfo',
    debug='all',
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
