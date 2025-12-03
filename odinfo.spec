# -*- mode: python ; coding: utf-8 -*-

import os
import sys

# Add the current directory to sys.path so imports work
sys.path.insert(0, os.path.abspath('.'))

a = Analysis(
    ['odinfoweb/flask_app.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # Include templates directory - Flask needs this
        ('odinfoweb/templates', 'templates'),
        # Include reference data - the app reads YAML/JSON files from here
        ('ref-data', 'ref-data'),
        # Include schema files for database operations
        ('odinfo/opsdata/schema.sql', 'odinfo/opsdata'),
        # Include any schema update scripts
        ('odinfo/opsdata/schema-updates', 'odinfo/opsdata/schema-updates') if os.path.exists('odinfo/opsdata/schema-updates') else None,
    ],
    hiddenimports=[
        # Flask and web framework
        'flask',
        'flask_login', 
        'flask_sqlalchemy',
        'wtforms',
        'jinja2',
        # Database
        'sqlite3',
        'sqlalchemy',
        'sqlalchemy.ext.declarative',
        'sqlalchemy.orm',
        # HTTP and web scraping
        'requests',
        'bs4',
        'urllib3',
        # Image and plotting
        'PIL',
        'PIL.Image',
        'matplotlib',
        'matplotlib.pyplot',
        # Data formats
        'yaml',
        'json',
        # All odinfo modules - PyInstaller might miss some
        'odinfo',
        'odinfo.config',
        'odinfo.timeutils', 
        'odinfo.domain',
        'odinfo.domain.models',
        'odinfo.domain.refdata',
        'odinfo.repositories',
        'odinfo.repositories.game',
        'odinfo.domain.domainhelper',
        'odinfo.domain.magic',
        'odinfo.domain.unknown',
        'odinfo.facade',
        'odinfo.facade.odinfo',
        'odinfo.facade.graphs',
        'odinfo.facade.awardstats',
        'odinfo.facade.discord',
        'odinfo.facade.towncrier',
        'odinfo.calculators',
        'odinfo.calculators.military',
        'odinfo.calculators.economy', 
        'odinfo.calculators.networthcalculator',
        'odinfo.opsdata',
        'odinfo.opsdata.db',
        'odinfo.opsdata.ops',
        'odinfo.opsdata.scrapetools',
        'odinfo.opsdata.updater',
        'odinfo.sim',
        'odinfo.sim.simulator',
        'odinfo.sim.commands',
        'odinfo.sim.refdata',
        'odinfoweb',
        'odinfoweb.user',
        'odinfoweb.forms',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude test and development modules
        'test',
        'tests', 
        'testing',
        'pytest',
        'setuptools',
        'pip',
        'wheel',
        'distutils',
    ],
    noarchive=False,
    optimize=0,
)

# Filter out None entries from datas (for conditional includes)
a.datas = [item for item in a.datas if item is not None]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries, 
    a.datas,
    [],
    name='odinfo',
    debug=False,
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