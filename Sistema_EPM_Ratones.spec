# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('Home.py', '.'), ('ui_theme.py', '.'), ('pages', 'pages'), ('src', 'src'), ('.streamlit', '.streamlit'), ('.env', '.'), ('assets', 'assets'), ('schema.sql', '.')]
binaries = []
hiddenimports = ['streamlit', 'streamlit.runtime', 'streamlit.runtime.scriptrunner', 'streamlit.runtime.scriptrunner.magic_funcs', 'streamlit.runtime.scriptrunner.script_runner', 'streamlit.web', 'streamlit.web.cli', 'streamlit.web.server', 'sqlalchemy', 'sqlalchemy.sql', 'sqlalchemy.ext.declarative', 'psycopg2', 'psycopg2.extensions', 'bcrypt', 'smtplib', 'email', 'email.mime', 'pandas', 'numpy', 'cv2', 'PIL', 'plotly', 'plotly.graph_objects', 'openpyxl', 'dotenv', 'pathlib', 'src', 'src.session_utils', 'src.auth', 'src.config', 'src.email_utils', 'src.security_logger', 'src.treatments', 'src.ui_components', 'src.video_context_banner', 'src.zone_templates', 'src.analysis_logic', 'src.reporting', 'src.simba_roi_bridge', 'src.db', 'src.db.connection', 'src.db.operations', 'ui_theme']
tmp_ret = collect_all('streamlit')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('altair')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pandas')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('sqlalchemy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('plotly')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=binaries,
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
    name='Sistema_EPM_Ratones',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\logos\\logo_ria.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Sistema_EPM_Ratones',
)
