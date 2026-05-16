# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec para Spotify Sync Manager
# Genera: dist/Spotify Sync Manager/Spotify Sync Manager.exe
#
# Para buildear: ver build.ps1

from PyInstaller.utils.hooks import collect_all, collect_submodules

# Recolectar todo lo de pywebview automáticamente
webview_datas, webview_binaries, webview_hiddenimports = collect_all('webview')

# Hidden imports de uvicorn/fastapi (carga dinámica)
uvicorn_hidden = collect_submodules('uvicorn')
anyio_hidden   = collect_submodules('anyio')

a = Analysis(
    ['gui/app.py'],
    pathex=['.'],
    binaries=webview_binaries,
    datas=[
        # Frontend construido
        ('gui/frontend/dist',   'gui/frontend/dist'),
        # Scripts de herramientas (corren como subprocess)
        ('tools',               'tools'),
        # Módulos fuente (importados dinámicamente)
        ('src',                 'src'),
        # Archivos de datos (blacklist, etc.)
        ('data',                'data'),
        # Assets del webview
        *webview_datas,
    ],
    hiddenimports=[
        'gui.backend.main',
        'gui.backend.routes.adb',
        'gui.backend.routes.compare',
        'gui.backend.routes.config',
        'gui.backend.routes.queue',
        'gui.backend.routes.scripts',
        'gui.backend.routes.spotify',
        'gui.backend.routes.youtube',
        'gui.backend.ws_runner',
        'gui.backend.models',
        'fastapi',
        'fastapi.staticfiles',
        'fastapi.middleware.cors',
        'starlette',
        'starlette.staticfiles',
        'starlette.middleware.cors',
        'multipart',
        'python_multipart',
        *uvicorn_hidden,
        *anyio_hidden,
        *webview_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'PIL'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Spotify Sync Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # sin ventana de consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    # icon='icon.ico',      # descomenta y pon la ruta a tu .ico si querés ícono
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Spotify Sync Manager',
)
