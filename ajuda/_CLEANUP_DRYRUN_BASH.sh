#!/bin/bash
# ========================================================================
# 🧹 CODE JANITOR - DRY RUN COMMANDS (bash/Linux/macOS)
# ========================================================================
# IMPORTANTE: NÃO EXECUTE AINDA! Apenas REVISE e aguarde confirmação.
# ========================================================================

set -e  # Parar em caso de erro

# Criar pasta de quarentena com timestamp
trash="_trash_$(date +%Y%m%d_%H%M)"
echo "🗑️  Criando pasta de quarentena: $trash"
mkdir -p "$trash"

# ========================================================================
# PARTE 1: CACHES (100% seguro - regeneráveis automaticamente)
# ========================================================================
echo ""
echo "📦 Movendo caches Python..."

# __pycache__ (todos os diretórios)
pycache_dirs=(
    "__pycache__"
    "adapters/__pycache__"
    "adapters/storage/__pycache__"
    "application/__pycache__"
    "config/__pycache__"
    "core/__pycache__"
    "core/auth/__pycache__"
    "core/db_manager/__pycache__"
    "core/logs/__pycache__"
    "core/search/__pycache__"
    "core/services/__pycache__"
    "core/session/__pycache__"
    "detectors/__pycache__"
    "gui/__pycache__"
    "infra/__pycache__"
    "infra/db/__pycache__"
    "infrastructure/__pycache__"
    "infrastructure/scripts/__pycache__"
    "scripts/__pycache__"
    "shared/__pycache__"
    "shared/config/__pycache__"
    "shared/logging/__pycache__"
    "ui/__pycache__"
    "ui/dialogs/__pycache__"
    "ui/forms/__pycache__"
    "ui/login/__pycache__"
    "ui/lixeira/__pycache__"
    "ui/subpastas/__pycache__"
    "ui/widgets/__pycache__"
    "utils/__pycache__"
    "utils/file_utils/__pycache__"
    "utils/helpers/__pycache__"
)

for dir in "${pycache_dirs[@]}"; do
    if [ -d "$dir" ]; then
        mv "$dir" "$trash/"
        echo "  ✓ $dir"
    fi
done

# Outros caches
if [ -d ".ruff_cache" ]; then
    mv ".ruff_cache" "$trash/"
    echo "  ✓ .ruff_cache"
fi

if [ -d ".import_linter_cache" ]; then
    mv ".import_linter_cache" "$trash/"
    echo "  ✓ .import_linter_cache"
fi

# ========================================================================
# PARTE 2: BUILD ARTIFACTS (regeneráveis via PyInstaller)
# ========================================================================
echo ""
echo "🔨 Movendo artefatos de build..."

if [ -d "build" ]; then
    mv "build" "$trash/"
    echo "  ✓ build/"
fi

if [ -d "dist" ]; then
    mv "dist" "$trash/"
    echo "  ✓ dist/"
fi

# ========================================================================
# PARTE 3: DOCUMENTAÇÃO DE DESENVOLVIMENTO (verificar com usuário)
# ========================================================================
echo ""
echo "📚 Movendo documentação de desenvolvimento..."

if [ -d "ajuda" ]; then
    mv "ajuda" "$trash/"
    echo "  ✓ ajuda/"
fi

dev_docs=(
    "RELATORIO_BUILD_PYINSTALLER.md"
    "RELATORIO_ONEFILE.md"
    "EXCLUSOES_SUGERIDAS.md"
    "PYINSTALLER_BUILD.md"
)

for doc in "${dev_docs[@]}"; do
    if [ -f "$doc" ]; then
        mv "$doc" "$trash/"
        echo "  ✓ $doc"
    fi
done

# ========================================================================
# PARTE 4: SCRIPTS DE DESENVOLVIMENTO (verificar com usuário)
# ========================================================================
echo ""
echo "🔧 Movendo scripts de desenvolvimento..."

if [ -d "scripts" ]; then
    mv "scripts" "$trash/"
    echo "  ✓ scripts/"
fi

# ========================================================================
# PARTE 5: MÓDULOS VAZIOS/REDUNDANTES (verificar com usuário)
# ========================================================================
echo ""
echo "🗂️  Movendo módulos vazios/redundantes..."

if [ -d "detectors" ]; then
    mv "detectors" "$trash/"
    echo "  ✓ detectors/"
fi

if [ -d "infrastructure" ]; then
    mv "infrastructure" "$trash/"
    echo "  ✓ infrastructure/"
fi

# ========================================================================
# RESUMO
# ========================================================================
echo ""
echo "✅ DRY-RUN COMPLETO!"
echo ""
echo "Todos os itens foram movidos para: $trash"
echo ""
echo "📋 Próximos passos:"
echo "  1. Revise o conteúdo de '$trash'"
echo "  2. Execute: python -m compileall ."
echo "  3. Execute: python app_gui.py"
echo "  4. Se algo falhar, restaure: mv $trash/* . && rm -rf $trash"
echo "  5. Se tudo funcionar, delete: rm -rf $trash"

# ========================================================================
# COMANDO DE REVERSÃO (copie se precisar desfazer)
# ========================================================================
: <<'REVERTER'
# Para REVERTER tudo (restaurar da quarentena):
trash="_trash_YYYYMMDD_HHMM"  # Substitua pelo nome correto
mv "$trash"/* .
rm -rf "$trash"
REVERTER
