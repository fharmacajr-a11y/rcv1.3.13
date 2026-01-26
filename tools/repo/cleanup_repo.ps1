#!/usr/bin/env pwsh
# ============================================================================
# SCRIPT DE LIMPEZA E ORGANIZAÇÃO DO REPOSITÓRIO - POWERSHELL
# ============================================================================
# Data: 26/01/2026
# Propósito: Desversionar artefatos, mover documentação, organizar estrutura
# IMPORTANTE: Revise antes de executar!
# ============================================================================

$ErrorActionPreference = "Stop"

# Cores para output
function Write-Step { param($msg) Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "    ✓ $msg" -ForegroundColor Green }
function Write-Warning { param($msg) Write-Host "    ⚠ $msg" -ForegroundColor Yellow }
function Write-Info { param($msg) Write-Host "    → $msg" -ForegroundColor Gray }

# ============================================================================
# VERIFICAÇÕES INICIAIS
# ============================================================================

Write-Step "VERIFICAÇÕES INICIAIS"

# Verificar se estamos em um repositório Git
try {
    $isGitRepo = git rev-parse --is-inside-work-tree 2>$null
    if ($isGitRepo -ne "true") {
        Write-Error "Não estamos em um repositório Git válido!"
        exit 1
    }
    Write-Success "Repositório Git válido"
} catch {
    Write-Error "Git não encontrado ou não é um repositório válido"
    exit 1
}

# Verificar mudanças pendentes
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Warning "Há mudanças pendentes no repositório:"
    Write-Host $gitStatus -ForegroundColor Yellow
    Write-Host ""
    $response = Read-Host "Deseja continuar mesmo assim? (s/N)"
    if ($response -ne 's' -and $response -ne 'S') {
        Write-Info "Operação cancelada. Commit ou stash suas mudanças primeiro."
        exit 0
    }
}

# Verificar branch atual
$currentBranch = git branch --show-current
Write-Info "Branch atual: $currentBranch"

# ============================================================================
# CRIAR BRANCH DE TRABALHO
# ============================================================================

Write-Step "CRIAR BRANCH DE TRABALHO"

$targetBranch = "chore/organize-repo-structure"
$branchExists = git branch --list $targetBranch

if ($branchExists) {
    Write-Warning "Branch '$targetBranch' já existe"
    $response = Read-Host "Deseja usar ela mesmo assim? (s/N)"
    if ($response -ne 's' -and $response -ne 'S') {
        Write-Info "Operação cancelada"
        exit 0
    }
    git checkout $targetBranch
} else {
    git checkout -b $targetBranch
    Write-Success "Branch '$targetBranch' criada e ativada"
}

# ============================================================================
# PASSO 1: DESVERSIONAR ARTEFATOS GERADOS (git rm --cached)
# ============================================================================

Write-Step "PASSO 1: Desversionar artefatos gerados"

$artifacts = @(
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "htmlcov",
    "coverage",
    "diagnostics"
)

foreach ($item in $artifacts) {
    if (Test-Path $item) {
        try {
            git rm -r --cached $item 2>$null
            Write-Success "Desversionado: $item (mantido no disco)"
        } catch {
            Write-Info "Já desversionado ou não versionado: $item"
        }
    } else {
        Write-Info "Não encontrado (pulando): $item"
    }
}

# ============================================================================
# PASSO 2: DESVERSIONAR ARQUIVOS TEMPORÁRIOS
# ============================================================================

Write-Step "PASSO 2: Desversionar arquivos temporários"

$tempFiles = @(
    "audit_ctk.txt",
    "audit_ttk.txt",
    "audit_ttkbootstrap.txt",
    "baseline_ttk_inventory.txt",
    "hub_35.txt",
    "hub_final_result.txt",
    "hub_final_results.txt",
    "hub_results_v2.txt",
    "hub_results_v3.txt",
    "hub_results_v4.txt",
    "hub_results_v5.txt",
    "hub_results_v6.txt",
    "hub_stats.txt",
    "hub_test_results.txt"
)

foreach ($file in $tempFiles) {
    if (Test-Path $file) {
        try {
            git rm --cached $file 2>$null
            Write-Success "Desversionado: $file (mantido no disco)"
        } catch {
            Write-Info "Já desversionado ou não versionado: $file"
        }
    } else {
        Write-Info "Não encontrado (pulando): $file"
    }
}

# ============================================================================
# PASSO 3: CRIAR ESTRUTURA EM docs/
# ============================================================================

Write-Step "PASSO 3: Criar estrutura em docs/"

$docDirs = @(
    "docs/patches",
    "docs/reports/microfases",
    "docs/reports/releases",
    "docs/guides",
    "tools/migration",
    "tests/experiments"
)

foreach ($dir in $docDirs) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Success "Criado: $dir"
    } else {
        Write-Info "Já existe: $dir"
    }
}

# ============================================================================
# PASSO 4: MOVER PATCHES
# ============================================================================

Write-Step "PASSO 4: Mover patches para docs/patches/"

$patches = @(
    "PATCH_V2_DOUBLECLICK_DETERMINISTICO.md",
    "PATCH_CLIENTESV2_DOUBLECLICK_FLASH.md",
    "PATCH_CLIENT_FILES_BROWSER.md",
    "PATCH_FIX_FILES_BROWSER_ACCESS.md",
    "ANALISE_MIGRACAO_CTK_CLIENTESV2.md"
)

foreach ($file in $patches) {
    if (Test-Path $file) {
        try {
            git mv $file docs/patches/
            Write-Success "Movido: $file -> docs/patches/"
        } catch {
            Write-Warning "Erro ao mover $file : $_"
        }
    } else {
        Write-Info "Não encontrado (pulando): $file"
    }
}

# ============================================================================
# PASSO 5: MOVER RELATÓRIOS DE MICROFASES
# ============================================================================

Write-Step "PASSO 5: Mover relatórios de microfases"

$microfases = @(
    "RELATORIO_MICROFASE_35.md",
    "MICROFASE_36_RELATORIO_FINAL.md",
    "RELATORIO_MICROFASE_37.md",
    "RELATORIO_MIGRACAO_CTK_COMPLETA.md"
)

foreach ($file in $microfases) {
    if (Test-Path $file) {
        try {
            git mv $file docs/reports/microfases/
            Write-Success "Movido: $file -> docs/reports/microfases/"
        } catch {
            Write-Warning "Erro ao mover $file : $_"
        }
    } else {
        Write-Info "Não encontrado (pulando): $file"
    }
}

# ============================================================================
# PASSO 6: MOVER RELATÓRIOS DE RELEASE
# ============================================================================

Write-Step "PASSO 6: Mover relatórios de release"

$releases = @(
    "EXECUTIVE_SUMMARY.md",
    "GATE_FINAL.md",
    "CI_GREEN_REPORT.md",
    "RELEASE_STATUS.md",
    "NEXT_STEPS.md",
    "CREATE_PR_INSTRUCTIONS.md",
    "PR_DESCRIPTION.md"
)

foreach ($file in $releases) {
    if (Test-Path $file) {
        try {
            git mv $file docs/reports/releases/
            Write-Success "Movido: $file -> docs/reports/releases/"
        } catch {
            Write-Warning "Erro ao mover $file : $_"
        }
    } else {
        Write-Info "Não encontrado (pulando): $file"
    }
}

# ============================================================================
# PASSO 7: MOVER GUIAS
# ============================================================================

Write-Step "PASSO 7: Mover guias para docs/guides/"

$guides = @(
    "MIGRACAO_CTK_GUIA_COMPLETO.ipynb"
)

foreach ($file in $guides) {
    if (Test-Path $file) {
        try {
            git mv $file docs/guides/
            Write-Success "Movido: $file -> docs/guides/"
        } catch {
            Write-Warning "Erro ao mover $file : $_"
        }
    } else {
        Write-Info "Não encontrado (pulando): $file"
    }
}

# ============================================================================
# PASSO 8: MOVER SCRIPTS DE MIGRAÇÃO
# ============================================================================

Write-Step "PASSO 8: Mover scripts de migração"

$migrationScripts = @(
    "fix_ctk_advanced.py",
    "fix_ctk_padding.py"
)

foreach ($file in $migrationScripts) {
    if (Test-Path $file) {
        try {
            git mv $file tools/migration/
            Write-Success "Movido: $file -> tools/migration/"
        } catch {
            Write-Warning "Erro ao mover $file : $_"
        }
    } else {
        Write-Info "Não encontrado (pulando): $file"
    }
}

# ============================================================================
# PASSO 9: MOVER TESTES EXPERIMENTAIS
# ============================================================================

Write-Step "PASSO 9: Mover testes experimentais"

$experiments = @(
    "test_ctktreeview.py"
)

foreach ($file in $experiments) {
    if (Test-Path $file) {
        try {
            git mv $file tests/experiments/
            Write-Success "Movido: $file -> tests/experiments/"
        } catch {
            Write-Warning "Erro ao mover $file : $_"
        }
    } else {
        Write-Info "Não encontrado (pulando): $file"
    }
}

# ============================================================================
# RESUMO
# ============================================================================

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Yellow
Write-Host "✅ REORGANIZAÇÃO CONCLUÍDA" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "PRÓXIMOS PASSOS:" -ForegroundColor Cyan
Write-Host "1. Criar docs/README.md com índice completo da documentação"
Write-Host "2. Atualizar README.md na raiz (versão curta/vitrine)"
Write-Host "3. Atualizar .gitignore com padrões adicionais"
Write-Host "4. Corrigir links relativos nos arquivos .md movidos"
Write-Host "5. Revisar mudanças: git status"
Write-Host "6. Commitar: git add -A && git commit -m 'chore: reorganize repository structure'"
Write-Host "7. VALIDAR: pytest, ruff, pyright"
Write-Host ""
Write-Host "Ver git status:" -ForegroundColor Cyan
git status --short
Write-Host ""
Write-Host "============================================================================" -ForegroundColor Yellow
