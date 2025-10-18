# ========================================
# 🧹 Script de Limpeza Segura V3
# ========================================
# Descrição: Move duplicados para quarentena e remove lixo confirmado
# Modo: Dry-run por padrão (use -Apply para executar)
# Autor: Auditoria V3
# Data: 2025-01-18

param(
    [switch]$Apply,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

# Cores
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warning { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Error { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }
function Write-Step { param($msg) Write-Host "`n[STEP] $msg" -ForegroundColor Magenta }

# ========================================
# Configuração
# ========================================

$QuarantineDir = "ajuda\_quarentena_assets"
$FilesToQuarantine = @(
    @{ Path = "assets\app.ico"; Reason = "Duplicado byte-a-byte de rc.ico" },
    @{ Path = "rc.png"; Reason = "Comentado no código, uso incerto" }
)
$FilesToRemove = @(
    @{ Path = "scripts\infrastructure_scripts_init.py.bak"; Reason = "Backup vazio" }
)

# ========================================
# Funções Auxiliares
# ========================================

function Test-FileExists {
    param([string]$Path)
    if (Test-Path $Path) {
        return $true
    } else {
        Write-Warning "Arquivo não encontrado: $Path"
        return $false
    }
}

function Get-FileSHA256 {
    param([string]$Path)
    $hash = Get-FileHash $Path -Algorithm SHA256
    return $hash.Hash.Substring(0, 16)
}

function Show-FileInfo {
    param([string]$Path)
    if (Test-Path $Path) {
        $file = Get-Item $Path
        $size = [math]::Round($file.Length / 1KB, 2)
        Write-Info "  File: $Path -> $size KB"
    }
}

# ========================================
# Banner
# ========================================

Write-Host @"

==============================================
    Limpeza Segura V3 - RC-Gestor
    Modo: $(if ($Apply) { "APLICAR (real)" } else { "DRY-RUN (simulacao)" })
==============================================

"@ -ForegroundColor Cyan

if (-not $Apply) {
    Write-Warning "Executando em modo DRY-RUN (nenhum arquivo será movido/removido)"
    Write-Info "Use -Apply para executar as ações de verdade"
    Write-Host ""
}

# ========================================
# Passo 1: Verificar Arquivos
# ========================================

Write-Step "Verificando arquivos alvo..."

$allFilesExist = $true

Write-Info "Arquivos para quarentena:"
foreach ($file in $FilesToQuarantine) {
    if (Test-FileExists $file.Path) {
        Show-FileInfo $file.Path
        Write-Host "     Razao: $($file.Reason)" -ForegroundColor Gray
    } else {
        $allFilesExist = $false
    }
}

Write-Host ""
Write-Info "Arquivos para remover:"
foreach ($file in $FilesToRemove) {
    if (Test-FileExists $file.Path) {
        Show-FileInfo $file.Path
        Write-Host "     Razao: $($file.Reason)" -ForegroundColor Gray
    } else {
        $allFilesExist = $false
    }
}

if (-not $allFilesExist) {
    Write-Error "Alguns arquivos não foram encontrados. Abortando."
    exit 1
}

Write-Success "Todos os arquivos existem"

# ========================================
# Passo 2: Verificar Duplicados
# ========================================

Write-Step "Verificando hashes SHA-256..."

if ((Test-Path "rc.ico") -and (Test-Path "assets\app.ico")) {
    $hash1 = Get-FileSHA256 "rc.ico"
    $hash2 = Get-FileSHA256 "assets\app.ico"

    Write-Info "  rc.ico:         $hash1..."
    Write-Info "  assets\app.ico: $hash2..."

    if ($hash1 -eq $hash2) {
        Write-Success "Hashes idênticos confirmados (duplicado byte-a-byte)"
    } else {
        Write-Error "ATENÇÃO: Hashes diferentes! Arquivos NÃO são duplicados idênticos."
        Write-Warning "Abortando por segurança. Verifique manualmente."
        exit 1
    }
} else {
    Write-Warning "Não foi possível verificar hashes (arquivos ausentes)"
}

# ========================================
# Passo 3: Criar Quarentena
# ========================================

Write-Step "Preparando quarentena..."

if ($Apply) {
    if (-not (Test-Path $QuarantineDir)) {
        New-Item -ItemType Directory -Force -Path $QuarantineDir | Out-Null
        Write-Success "Pasta de quarentena criada: $QuarantineDir"
    } else {
        Write-Info "Pasta de quarentena já existe: $QuarantineDir"
    }
} else {
    Write-Info "DRY-RUN: Criaria pasta $QuarantineDir"
}

# ========================================
# Passo 4: Mover para Quarentena
# ========================================

Write-Step "Movendo arquivos para quarentena..."

foreach ($file in $FilesToQuarantine) {
    $sourcePath = $file.Path
    $destPath = Join-Path $QuarantineDir (Split-Path $sourcePath -Leaf)

    if ($Apply) {
        if (Test-Path $sourcePath) {
            Move-Item $sourcePath $destPath -Force
            Write-Success "Movido: $sourcePath -> $destPath"
        } else {
            Write-Warning "Arquivo não encontrado: $sourcePath (pulando)"
        }
    } else {
        Write-Info "DRY-RUN: Moveria $sourcePath -> $destPath"
    }
}

# ========================================
# Passo 5: Remover Lixo
# ========================================

Write-Step "Removendo arquivos de lixo..."

foreach ($file in $FilesToRemove) {
    if ($Apply) {
        if (Test-Path $file.Path) {
            Remove-Item $file.Path -Force
            Write-Success "Removido: $($file.Path)"
        } else {
            Write-Warning "Arquivo não encontrado: $($file.Path) (pulando)"
        }
    } else {
        Write-Info "DRY-RUN: Removeria $($file.Path)"
    }
}

# ========================================
# Passo 6: Relatório Final
# ========================================

Write-Step "Relatório final"

if ($Apply) {
    Write-Host ""
    Write-Success "Limpeza concluida com sucesso!"
    Write-Host ""
    Write-Info "Resumo:"
    Write-Host "  - Arquivos movidos para quarentena: $($FilesToQuarantine.Count)" -ForegroundColor Gray
    Write-Host "  - Arquivos removidos: $($FilesToRemove.Count)" -ForegroundColor Gray
    Write-Host ""
    Write-Info "Quarentena: $QuarantineDir"

    if (Test-Path $QuarantineDir) {
        Write-Host ""
        Write-Info "Conteudo da quarentena:"
        Get-ChildItem $QuarantineDir | ForEach-Object {
            $size = [math]::Round($_.Length / 1KB, 2)
            Write-Host "  - $($_.Name) ($size KB)" -ForegroundColor Gray
        }
    }

    Write-Host ""
    Write-Info "Para restaurar um arquivo:"
    Write-Host "  Move-Item ajuda\_quarentena_assets\app.ico assets\ -Force" -ForegroundColor Gray
    Write-Host "  Move-Item ajuda\_quarentena_assets\rc.png . -Force" -ForegroundColor Gray

    Write-Host ""
    Write-Info "Proximo passo: Executar smoke test"
    Write-Host "  python .\scripts\smoke_runtime.py" -ForegroundColor Gray

} else {
    Write-Host ""
    Write-Warning "DRY-RUN concluido (nenhuma alteracao foi feita)"
    Write-Host ""
    Write-Info "O que seria feito:"
    Write-Host "  - Mover $($FilesToQuarantine.Count) arquivo(s) para quarentena" -ForegroundColor Gray
    Write-Host "  - Remover $($FilesToRemove.Count) arquivo(s)" -ForegroundColor Gray
    Write-Host ""
    Write-Info "Para executar de verdade:"
    Write-Host "  .\ajuda\cleanup_v3.ps1 -Apply" -ForegroundColor Yellow
}

Write-Host ""
