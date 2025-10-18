#!/bin/bash
# ============================================================================
# 🧹 LIMPEZA SEGURA - MOVER PARA QUARENTENA (bash)
# ============================================================================
# Script gerado automaticamente - Code Janitor
# IMPORTANTE: Este script MOVE itens para quarentena, não deleta!
# ============================================================================

set -e  # Parar em caso de erro crítico (mas ignora itens não encontrados)

# Criar pasta de quarentena com timestamp
trash="_trash_$(date +%Y%m%d_%H%M)"
echo "🗑️  Criando quarentena: $trash"
mkdir -p "$trash"

moved_count=0
skipped_count=0

# ============================================================================
# FUNÇÃO AUXILIAR: Mover item preservando estrutura de diretórios
# ============================================================================
move_to_trash() {
    local source_path="$1"

    if [ -e "$source_path" ]; then
        local target_path="$trash/$source_path"
        local target_dir=$(dirname "$target_path")

        mkdir -p "$target_dir"

        if mv "$source_path" "$target_path" 2>/dev/null; then
            echo "  ✓ Movido: $source_path"
            return 0
        else
            echo "  ⚠ Erro ao mover: $source_path"
            return 1
        fi
    fi
    return 1
}

# ============================================================================
# PARTE 1: Pastas __pycache__ (recursivas)
# ============================================================================
echo ""
echo "📦 Buscando pastas __pycache__..."

# Encontrar todas as pastas __pycache__ recursivamente
while IFS= read -r -d '' pycache_dir; do
    relative_path="${pycache_dir#./}"
    if move_to_trash "$relative_path"; then
        ((moved_count++))
    fi
done < <(find . -type d -name "__pycache__" -print0 2>/dev/null)

# ============================================================================
# PARTE 2: Caches de ferramentas
# ============================================================================
echo ""
echo "🔧 Buscando caches de ferramentas..."

cache_dirs=(
    ".ruff_cache"
    ".import_linter_cache"
)

for cache in "${cache_dirs[@]}"; do
    if move_to_trash "$cache"; then
        ((moved_count++))
    else
        ((skipped_count++))
    fi
done

# ============================================================================
# PARTE 3: Ambiente virtual (.venv)
# ============================================================================
echo ""
echo "🐍 Buscando ambiente virtual..."

if move_to_trash ".venv"; then
    ((moved_count++))
else
    ((skipped_count++))
fi

# ============================================================================
# PARTE 4: Artefatos de build
# ============================================================================
echo ""
echo "🔨 Buscando artefatos de build..."

build_dirs=("build" "dist")

for build_dir in "${build_dirs[@]}"; do
    if move_to_trash "$build_dir"; then
        ((moved_count++))
    else
        ((skipped_count++))
    fi
done

# ============================================================================
# PARTE 5: Documentação e scripts de desenvolvimento
# ============================================================================
echo ""
echo "📚 Buscando docs e scripts de desenvolvimento..."

dev_dirs=(
    "ajuda"
    "runtime_docs"
    "scripts"
    "detectors"
    "infrastructure"
)

for dir in "${dev_dirs[@]}"; do
    if move_to_trash "$dir"; then
        ((moved_count++))
    else
        ((skipped_count++))
    fi
done

# ============================================================================
# PARTE 6: Arquivos específicos
# ============================================================================
echo ""
echo "📄 Buscando arquivos específicos..."

target_files=(
    "RELATORIO_BUILD_PYINSTALLER.md"
    "RELATORIO_ONEFILE.md"
    "EXCLUSOES_SUGERIDAS.md"
    "PYINSTALLER_BUILD.md"
    "requirements.in"
    "requirements-min.in"
    "requirements-min.txt"
    ".pre-commit-config.yaml"
    ".importlinter"
)

for file in "${target_files[@]}"; do
    if move_to_trash "$file"; then
        ((moved_count++))
    else
        ((skipped_count++))
    fi
done

# ============================================================================
# RESUMO FINAL
# ============================================================================
echo ""
echo "✅ LIMPEZA CONCLUÍDA!"
echo ""
echo "📊 Resumo:"
echo "  • Itens movidos: $moved_count"
echo "  • Itens não encontrados: $skipped_count"
echo "  • Pasta de quarentena: $trash"

echo ""
echo "📋 Próximos passos:"
echo "  1. Verifique o conteúdo de '$trash'"
echo "  2. Execute os comandos de validação abaixo"
echo "  3. Se tudo estiver OK, delete: rm -rf '$trash'"
echo "  4. Se algo falhar, restaure: mv '$trash'/* . && rm -rf '$trash'"

# ============================================================================
# VALIDAÇÃO (descomente para executar automaticamente)
# ============================================================================
: <<'VALIDATION'
echo ""
echo "🔍 Validando compilação Python..."
python -m compileall . 2>&1 | grep "SyntaxError" || echo "  ✓ Sem erros de sintaxe"

echo ""
echo "🚀 Testando aplicação..."
# python app_gui.py
# (pressione Ctrl+C após verificar que abre sem erros)
VALIDATION

# ============================================================================
# COMANDO DE REVERSÃO (copie se precisar desfazer)
# ============================================================================
: <<'REVERTER'
# Para REVERTER tudo (restaurar da quarentena):
trash="_trash_YYYYMMDD_HHMM"  # Substitua pelo nome correto
mv "$trash"/* .
rm -rf "$trash"
REVERTER

echo ""
echo "✨ Concluído! Revise a pasta '$trash' antes de deletar."
