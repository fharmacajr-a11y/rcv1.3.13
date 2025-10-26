# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

BASE = Path.cwd().resolve()          # <- em vez de __file__
SRC  = BASE / "src"

# ---------- montar lista de datas de forma segura ----------
datas = []

def add_data_safe(path: Path, dest="."):
    if path.exists():
        datas.append((str(path), dest))

# opcionais (só entram se existirem)
add_data_safe(BASE / "rc.ico", ".")
add_data_safe(BASE / ".env", ".")
add_data_safe(BASE / "CHANGELOG_CONSOLIDADO.md", ".")

# runtime_docs (se existir em algum lugar comum)
for candidate in [BASE / "runtime_docs", SRC / "runtime_docs", BASE / "assets" / "runtime_docs"]:
    if candidate.exists():
        add_data_safe(candidate, "runtime_docs")
        break

# libs que carregam arquivos de dados
datas += collect_data_files("ttkbootstrap")
datas += collect_data_files("tzdata")

# ---------- análise ----------
a = Analysis(
    ['src/app_gui.py'],
    pathex=[str(BASE), str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=['tzdata', 'tzlocal'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data)

ICON = str(BASE / "rc.ico") if (BASE / "rc.ico").exists() else None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='rcgestor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                   # GUI sem console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,                       # string ou None
)
