# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files  # retorna (src, dest) 2-tuplas

BASE = Path(SPECPATH).resolve()  # usar pasta do .spec (estavel)
SRC = BASE / "src"
sys.path.insert(0, str(SRC))

from src.version import get_version  # noqa: E402

APP_VERSION = get_version()

# ---------- datas: APENAS (src, dest) 2-tuplas aqui ----------
datas = []


def add_file(src: Path, dest: str = ".") -> None:
    if src.exists():
        datas.append((str(src), dest))


# opcionais
add_file(BASE / "rc.ico", ".")
add_file(BASE / ".env", ".")
add_file(BASE / "CHANGELOG.md", ".")
add_file(BASE / "CHANGELOG_CONSOLIDADO.md", ".")

# dados de pacotes (site-packages)
datas += collect_data_files("ttkbootstrap")
datas += collect_data_files("tzdata")
datas += collect_data_files("certifi")  # bundle CA para HTTPS

# diretorios do projeto: anexar via Tree **DEPOIS** do Analysis
ASSETS_DIR = BASE / "assets"
TEMPLATES_DIR = BASE / "templates"
RUNTIME_DOCS_DIR = None
for cand in (BASE / "runtime_docs", SRC / "runtime_docs", BASE / "assets" / "runtime_docs"):
    if cand.exists():
        RUNTIME_DOCS_DIR = cand
        break

# ---------- Analysis ----------
a = Analysis(
    ["src/app_gui.py"],
    pathex=[str(BASE), str(SRC)],
    binaries=[
        # Binarios do 7-Zip para extracao de arquivos RAR
        ("infra/bin/7zip/7z.exe", "7z"),
        ("infra/bin/7zip/7z.dll", "7z"),
    ],
    datas=datas,  # aqui so 2-tuplas
    hiddenimports=["tzdata", "tzlocal"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# ---------- anexar diretorios inteiros via Tree (TOC 3-tuplas) ----------
if "Tree" in globals():
    if ASSETS_DIR.is_dir():
        a.datas += Tree(str(ASSETS_DIR), prefix="assets")
    if TEMPLATES_DIR.is_dir():
        a.datas += Tree(str(TEMPLATES_DIR), prefix="templates")
    if RUNTIME_DOCS_DIR and RUNTIME_DOCS_DIR.is_dir():
        a.datas += Tree(str(RUNTIME_DOCS_DIR), prefix="runtime_docs")

pyz = PYZ(a.pure, a.zipped_data)

ICON = str(BASE / "rc.ico") if (BASE / "rc.ico").exists() else None
VERSION_FILE = str(BASE / "version_file.txt") if (BASE / "version_file.txt").exists() else None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=f"RC-Gestor-Clientes-{APP_VERSION}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI sem console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
    version=VERSION_FILE,
)
