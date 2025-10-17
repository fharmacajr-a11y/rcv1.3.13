# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file para RC-Gestor v1.0.29
===============================================

Build seguro sem incluir arquivos de ambiente (.env) no bundle.
Apenas recursos públicos (ícones, imagens) são empacotados.

Referência: https://pyinstaller.org/en/stable/spec-files.html

Build:
    pyinstaller build/rc_gestor.spec

IMPORTANTE: 
- O arquivo .env NÃO deve estar em datas=[]
- Apenas arquivos públicos (ícones, recursos estáticos) devem ser incluídos
- Segredos devem ser fornecidos via variáveis de ambiente em runtime
"""

block_cipher = None

# Caminho base do projeto (parent do diretório build)
import os
basedir = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

a = Analysis(
    [os.path.join(basedir, 'app_gui.py')],
    pathex=[basedir],
    binaries=[],
    datas=[
        # Apenas recursos públicos - SEM .env
        (os.path.join(basedir, 'rc.ico'), '.'),
        (os.path.join(basedir, 'rc.png'), '.'),
        # Adicione outros recursos públicos conforme necessário
        # ('config.yml', '.'),  # apenas se necessário e não contiver segredos
    ],
    hiddenimports=[
        'tkinter',
        'ttkbootstrap',
        'dotenv',
        'supabase',
        'httpx',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'pytest',
        'setuptools',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RC-Gestor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI application - sem console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(basedir, 'rc.ico')
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RC-Gestor'
)
