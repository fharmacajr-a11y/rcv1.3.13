# -*- mode: python ; coding: utf-8 -*-
# =============================================================================
# RC Gestor de Clientes - PyInstaller Spec File
# =============================================================================
# Arquivo de configuração para geração do executável Windows.
#
# Uso:
#   pyinstaller rcgestor.spec
#
# Saída:
#   dist/RC-Gestor-Clientes-{versão}.exe
#
# Revisado na FASE 5 (2026-01-03) - src-layout: paths atualizados para src/infra.
# =============================================================================

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files  # retorna (src, dest) 2-tuplas

# =============================================================================
# CAMINHOS BASE
# =============================================================================
BASE = Path(SPECPATH).resolve()  # usar pasta do .spec (estavel)
SRC = BASE / "src"

# FASE 5: Adicionar BASE ao sys.path para permitir "import src.*"
sys.path.insert(0, str(BASE))

# Importa versão do app para nomear o executável
from src.version import get_version  # noqa: E402

APP_VERSION = get_version()

# =============================================================================
# ARQUIVOS DE DADOS (datas)
# =============================================================================
# Apenas tuplas (src, dest) são permitidas aqui.
# Diretórios inteiros são adicionados via Tree após o Analysis.
datas = []


def add_file(src: Path, dest: str = ".") -> None:
    """Adiciona arquivo aos datas se existir."""
    if src.exists():
        datas.append((str(src), dest))


# -----------------------------------------------------------------------------
# Arquivos opcionais da raiz do projeto
# -----------------------------------------------------------------------------
add_file(BASE / "rc.ico", ".")                    # Ícone do aplicativo
# SEGURANÇA: .env NÃO deve ser empacotado (contém credenciais)
# add_file(BASE / ".env", ".")                    # REMOVIDO - P0-002: Não distribuir credenciais
add_file(BASE / "CHANGELOG.md", ".")              # Histórico de versões
add_file(BASE / "CHANGELOG_CONSOLIDADO.md", ".")  # Changelog consolidado

# -----------------------------------------------------------------------------
# Dados de pacotes Python (site-packages)
# -----------------------------------------------------------------------------
datas += collect_data_files("ttkbootstrap")  # Temas e assets do ttkbootstrap
datas += collect_data_files("tzdata")        # Dados de timezone
datas += collect_data_files("certifi")       # Certificados CA para HTTPS

# -----------------------------------------------------------------------------
# Diretórios do projeto (anexados via Tree após Analysis)
# -----------------------------------------------------------------------------
ASSETS_DIR = BASE / "assets"
TEMPLATES_DIR = BASE / "templates"
RUNTIME_DOCS_DIR = None
for cand in (BASE / "runtime_docs", SRC / "runtime_docs", BASE / "assets" / "runtime_docs"):
    if cand.exists():
        RUNTIME_DOCS_DIR = cand
        break

# =============================================================================
# ANALYSIS - Análise do código e dependências
# =============================================================================
a = Analysis(
    # Entrypoint principal do aplicativo
    ["src/core/app.py"],

    # Caminhos de busca de módulos
    pathex=[str(BASE), str(SRC)],

    # Binários externos necessários
    binaries=[
        # 7-Zip para extração de arquivos RAR/ZIP
        # FASE 5 (2026-01-03): Atualizado para src/infra após migração
        ("src/infra/bin/7zip/7z.exe", "7z"),
        ("src/infra/bin/7zip/7z.dll", "7z"),
    ],

    # Arquivos de dados (tuplas src, dest)
    datas=datas,

    # Imports ocultos não detectados automaticamente
    hiddenimports=[
        "tzdata",
        "tzlocal",
        # P1-001: Keyring backends para armazenamento seguro de tokens
        "keyring.backends.Windows",  # DPAPI no Windows
    ],

    # Configurações adicionais
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# =============================================================================
# DIRETÓRIOS VIA TREE (tuplas de 3 elementos)
# =============================================================================
# Tree gera TOC com 3-tuplas, por isso é anexado após o Analysis.
if "Tree" in globals():
    if ASSETS_DIR.is_dir():
        a.datas += Tree(str(ASSETS_DIR), prefix="assets")
    if TEMPLATES_DIR.is_dir():
        a.datas += Tree(str(TEMPLATES_DIR), prefix="templates")
    if RUNTIME_DOCS_DIR and RUNTIME_DOCS_DIR.is_dir():
        a.datas += Tree(str(RUNTIME_DOCS_DIR), prefix="runtime_docs")

# =============================================================================
# COMPILAÇÃO
# =============================================================================
pyz = PYZ(a.pure, a.zipped_data)

# Ícone e arquivo de versão do Windows
ICON = str(BASE / "rc.ico") if (BASE / "rc.ico").exists() else None
VERSION_FILE = str(BASE / "version_file.txt") if (BASE / "version_file.txt").exists() else None

# =============================================================================
# EXECUTÁVEL FINAL
# =============================================================================
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],

    # Nome do executável (inclui versão)
    name=f"RC-Gestor-Clientes-{APP_VERSION}",

    # Opções de debug
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,

    # Compressão UPX (reduz tamanho)
    upx=True,

    # Modo GUI (sem console)
    console=False,
    disable_windowed_traceback=False,

    # Configurações de plataforma
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,

    # Ícone e metadados Windows
    icon=ICON,
    version=VERSION_FILE,
)
