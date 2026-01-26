#!/bin/bash
# ============================================================================
# SCRIPT DE LIMPEZA E ORGANIZAÇÃO DO REPOSITÓRIO - BASH
# ============================================================================
# Data: 26/01/2026
# Propósito: Desversionar artefatos, mover documentação, organizar estrutura
# IMPORTANTE: Revise antes de executar!
# Uso: chmod +x cleanup_repo.sh && ./cleanup_repo.sh
# ============================================================================

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

write_step() { echo -e "\n${CYAN}==> $1${NC}"; }
write_success() { echo -e "    ${GREEN}✓ $1${NC}"; }
write_warning() { echo -e "    ${YELLOW}⚠ $1${NC}"; }
write_info() { echo -e "    ${GRAY}→ $1${NC}"; }
write_error() { echo -e "    ${RED}✗ $1${NC}"; }

# ============================================================================
# VERIFICAÇÕES INICIAIS
# ============================================================================

write_step "VERIFICAÇÕES INICIAIS"

# Verificar se estamos em um repositório Git
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    write_error "Não estamos em um repositório Git válido!"
    exit 1
fi
write_success "Repositório Git válido"

# Verificar mudanças pendentes
if [[ -n $(git status --porcelain) ]]; then
    write_warning "Há mudanças pendentes no repositório:"
    git status --short
    echo ""
    read -p "Deseja continuar mesmo assim? (s/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        write_info "Operação cancelada. Commit ou stash suas mudanças primeiro."
        exit 0
    fi
fi

# Verificar branch atual
current_branch=$(git branch --show-current)
write_info "Branch atual: $current_branch"

# ============================================================================
# CRIAR BRANCH DE TRABALHO
# ============================================================================

write_step "CRIAR BRANCH DE TRABALHO"

target_branch="chore/organize-repo-structure"

if git show-ref --verify --quiet refs/heads/"$target_branch"; then
    write_warning "Branch '$target_branch' já existe"
    read -p "Deseja usar ela mesmo assim? (s/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        write_info "Operação cancelada"
        exit 0
    fi
    git checkout "$target_branch"
else
    git checkout -b "$target_branch"
    write_success "Branch '$target_branch' criada e ativada"
fi

# ============================================================================
# PASSO 1: DESVERSIONAR ARTEFATOS GERADOS (git rm --cached)
# ============================================================================

write_step "PASSO 1: Desversionar artefatos gerados"

artifacts=(
    "__pycache__"
    ".mypy_cache"
    ".pytest_cache"
    ".ruff_cache"
    "htmlcov"
    "coverage"
    "diagnostics"
)

for item in "${artifacts[@]}"; do
    if [[ -e "$item" ]]; then
        if git rm -r --cached "$item" 2>/dev/null; then
            write_success "Desversionado: $item (mantido no disco)"
        else
            write_info "Já desversionado ou não versionado: $item"
        fi
    else
        write_info "Não encontrado (pulando): $item"
    fi
done

# ============================================================================
# PASSO 2: DESVERSIONAR ARQUIVOS TEMPORÁRIOS
# ============================================================================

write_step "PASSO 2: Desversionar arquivos temporários"

temp_files=(
    "audit_ctk.txt"
    "audit_ttk.txt"
    "audit_ttkbootstrap.txt"
    "baseline_ttk_inventory.txt"
    "hub_35.txt"
    "hub_final_result.txt"
    "hub_final_results.txt"
    "hub_results_v2.txt"
    "hub_results_v3.txt"
    "hub_results_v4.txt"
    "hub_results_v5.txt"
    "hub_results_v6.txt"
    "hub_stats.txt"
    "hub_test_results.txt"
)

for file in "${temp_files[@]}"; do
    if [[ -f "$file" ]]; then
        if git rm --cached "$file" 2>/dev/null; then
            write_success "Desversionado: $file (mantido no disco)"
        else
            write_info "Já desversionado ou não versionado: $file"
        fi
    else
        write_info "Não encontrado (pulando): $file"
    fi
done

# ============================================================================
# PASSO 3: CRIAR ESTRUTURA EM docs/
# ============================================================================

write_step "PASSO 3: Criar estrutura em docs/"

doc_dirs=(
    "docs/patches"
    "docs/reports/microfases"
    "docs/reports/releases"
    "docs/guides"
    "tools/migration"
    "tests/experiments"
)

for dir in "${doc_dirs[@]}"; do
    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir"
        write_success "Criado: $dir"
    else
        write_info "Já existe: $dir"
    fi
done

# ============================================================================
# PASSO 4: MOVER PATCHES
# ============================================================================

write_step "PASSO 4: Mover patches para docs/patches/"

patches=(
    "PATCH_V2_DOUBLECLICK_DETERMINISTICO.md"
    "PATCH_CLIENTESV2_DOUBLECLICK_FLASH.md"
    "PATCH_CLIENT_FILES_BROWSER.md"
    "PATCH_FIX_FILES_BROWSER_ACCESS.md"
    "ANALISE_MIGRACAO_CTK_CLIENTESV2.md"
)

for file in "${patches[@]}"; do
    if [[ -f "$file" ]]; then
        if git mv "$file" docs/patches/; then
            write_success "Movido: $file -> docs/patches/"
        else
            write_warning "Erro ao mover $file"
        fi
    else
        write_info "Não encontrado (pulando): $file"
    fi
done

# ============================================================================
# PASSO 5: MOVER RELATÓRIOS DE MICROFASES
# ============================================================================

write_step "PASSO 5: Mover relatórios de microfases"

microfases=(
    "RELATORIO_MICROFASE_35.md"
    "MICROFASE_36_RELATORIO_FINAL.md"
    "RELATORIO_MICROFASE_37.md"
    "RELATORIO_MIGRACAO_CTK_COMPLETA.md"
)

for file in "${microfases[@]}"; do
    if [[ -f "$file" ]]; then
        if git mv "$file" docs/reports/microfases/; then
            write_success "Movido: $file -> docs/reports/microfases/"
        else
            write_warning "Erro ao mover $file"
        fi
    else
        write_info "Não encontrado (pulando): $file"
    fi
done

# ============================================================================
# PASSO 6: MOVER RELATÓRIOS DE RELEASE
# ============================================================================

write_step "PASSO 6: Mover relatórios de release"

releases=(
    "EXECUTIVE_SUMMARY.md"
    "GATE_FINAL.md"
    "CI_GREEN_REPORT.md"
    "RELEASE_STATUS.md"
    "NEXT_STEPS.md"
    "CREATE_PR_INSTRUCTIONS.md"
    "PR_DESCRIPTION.md"
)

for file in "${releases[@]}"; do
    if [[ -f "$file" ]]; then
        if git mv "$file" docs/reports/releases/; then
            write_success "Movido: $file -> docs/reports/releases/"
        else
            write_warning "Erro ao mover $file"
        fi
    else
        write_info "Não encontrado (pulando): $file"
    fi
done

# ============================================================================
# PASSO 7: MOVER GUIAS
# ============================================================================

write_step "PASSO 7: Mover guias para docs/guides/"

guides=(
    "MIGRACAO_CTK_GUIA_COMPLETO.ipynb"
)

for file in "${guides[@]}"; do
    if [[ -f "$file" ]]; then
        if git mv "$file" docs/guides/; then
            write_success "Movido: $file -> docs/guides/"
        else
            write_warning "Erro ao mover $file"
        fi
    else
        write_info "Não encontrado (pulando): $file"
    fi
done

# ============================================================================
# PASSO 8: MOVER SCRIPTS DE MIGRAÇÃO
# ============================================================================

write_step "PASSO 8: Mover scripts de migração"

migration_scripts=(
    "fix_ctk_advanced.py"
    "fix_ctk_padding.py"
)

for file in "${migration_scripts[@]}"; do
    if [[ -f "$file" ]]; then
        if git mv "$file" tools/migration/; then
            write_success "Movido: $file -> tools/migration/"
        else
            write_warning "Erro ao mover $file"
        fi
    else
        write_info "Não encontrado (pulando): $file"
    fi
done

# ============================================================================
# PASSO 9: MOVER TESTES EXPERIMENTAIS
# ============================================================================

write_step "PASSO 9: Mover testes experimentais"

experiments=(
    "test_ctktreeview.py"
)

for file in "${experiments[@]}"; do
    if [[ -f "$file" ]]; then
        if git mv "$file" tests/experiments/; then
            write_success "Movido: $file -> tests/experiments/"
        else
            write_warning "Erro ao mover $file"
        fi
    else
        write_info "Não encontrado (pulando): $file"
    fi
done

# ============================================================================
# RESUMO
# ============================================================================

echo ""
echo -e "${YELLOW}============================================================================${NC}"
echo -e "${GREEN}✅ REORGANIZAÇÃO CONCLUÍDA${NC}"
echo -e "${YELLOW}============================================================================${NC}"
echo ""
echo -e "${CYAN}PRÓXIMOS PASSOS:${NC}"
echo "1. Criar docs/README.md com índice completo da documentação"
echo "2. Atualizar README.md na raiz (versão curta/vitrine)"
echo "3. Atualizar .gitignore com padrões adicionais"
echo "4. Corrigir links relativos nos arquivos .md movidos"
echo "5. Revisar mudanças: git status"
echo "6. Commitar: git add -A && git commit -m 'chore: reorganize repository structure'"
echo "7. VALIDAR: pytest, ruff, pyright"
echo ""
echo -e "${CYAN}Ver git status:${NC}"
git status --short
echo ""
echo -e "${YELLOW}============================================================================${NC}"
