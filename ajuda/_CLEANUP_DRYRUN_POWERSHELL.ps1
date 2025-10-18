# ========================================================================
# 🧹 CODE JANITOR - DRY RUN COMMANDS (PowerShell)
# ========================================================================
# IMPORTANTE: NÃO EXECUTE AINDA! Apenas REVISE e aguarde confirmação.
# ========================================================================

# Criar pasta de quarentena com timestamp
$trash = "_trash_$(Get-Date -Format yyyyMMdd_HHmm)"
Write-Host "🗑️  Criando pasta de quarentena: $trash" -ForegroundColor Yellow
New-Item -ItemType Directory -Path $trash -Force | Out-Null

# ========================================================================
# PARTE 1: CACHES (100% seguro - regeneráveis automaticamente)
# ========================================================================
Write-Host "`n📦 Movendo caches Python..." -ForegroundColor Cyan

# __pycache__ (todos os diretórios)
$pycacheDirs = @(
    "__pycache__",
    "adapters\__pycache__",
    "adapters\storage\__pycache__",
    "application\__pycache__",
    "config\__pycache__",
    "core\__pycache__",
    "core\auth\__pycache__",
    "core\db_manager\__pycache__",
    "core\logs\__pycache__",
    "core\search\__pycache__",
    "core\services\__pycache__",
    "core\session\__pycache__",
    "detectors\__pycache__",
    "gui\__pycache__",
    "infra\__pycache__",
    "infra\db\__pycache__",
    "infrastructure\__pycache__",
    "infrastructure\scripts\__pycache__",
    "scripts\__pycache__",
    "shared\__pycache__",
    "shared\config\__pycache__",
    "shared\logging\__pycache__",
    "ui\__pycache__",
    "ui\dialogs\__pycache__",
    "ui\forms\__pycache__",
    "ui\login\__pycache__",
    "ui\lixeira\__pycache__",
    "ui\subpastas\__pycache__",
    "ui\widgets\__pycache__",
    "utils\__pycache__",
    "utils\file_utils\__pycache__",
    "utils\helpers\__pycache__"
)

foreach ($dir in $pycacheDirs) {
    if (Test-Path $dir) {
        Move-Item -Path $dir -Destination "$trash\" -Force
        Write-Host "  ✓ $dir" -ForegroundColor Green
    }
}

# Outros caches
if (Test-Path ".ruff_cache") {
    Move-Item -Path ".ruff_cache" -Destination "$trash\" -Force
    Write-Host "  ✓ .ruff_cache" -ForegroundColor Green
}

if (Test-Path ".import_linter_cache") {
    Move-Item -Path ".import_linter_cache" -Destination "$trash\" -Force
    Write-Host "  ✓ .import_linter_cache" -ForegroundColor Green
}

# ========================================================================
# PARTE 2: BUILD ARTIFACTS (regeneráveis via PyInstaller)
# ========================================================================
Write-Host "`n🔨 Movendo artefatos de build..." -ForegroundColor Cyan

if (Test-Path "build") {
    Move-Item -Path "build" -Destination "$trash\" -Force
    Write-Host "  ✓ build/" -ForegroundColor Green
}

if (Test-Path "dist") {
    Move-Item -Path "dist" -Destination "$trash\" -Force
    Write-Host "  ✓ dist/" -ForegroundColor Green
}

# ========================================================================
# PARTE 3: DOCUMENTAÇÃO DE DESENVOLVIMENTO (verificar com usuário)
# ========================================================================
Write-Host "`n📚 Movendo documentação de desenvolvimento..." -ForegroundColor Cyan

if (Test-Path "ajuda") {
    Move-Item -Path "ajuda" -Destination "$trash\" -Force
    Write-Host "  ✓ ajuda/" -ForegroundColor Green
}

$devDocs = @(
    "RELATORIO_BUILD_PYINSTALLER.md",
    "RELATORIO_ONEFILE.md",
    "EXCLUSOES_SUGERIDAS.md",
    "PYINSTALLER_BUILD.md"
)

foreach ($doc in $devDocs) {
    if (Test-Path $doc) {
        Move-Item -Path $doc -Destination "$trash\" -Force
        Write-Host "  ✓ $doc" -ForegroundColor Green
    }
}

# ========================================================================
# PARTE 4: SCRIPTS DE DESENVOLVIMENTO (verificar com usuário)
# ========================================================================
Write-Host "`n🔧 Movendo scripts de desenvolvimento..." -ForegroundColor Cyan

if (Test-Path "scripts") {
    Move-Item -Path "scripts" -Destination "$trash\" -Force
    Write-Host "  ✓ scripts/" -ForegroundColor Green
}

# ========================================================================
# PARTE 5: MÓDULOS VAZIOS/REDUNDANTES (verificar com usuário)
# ========================================================================
Write-Host "`n🗂️  Movendo módulos vazios/redundantes..." -ForegroundColor Cyan

if (Test-Path "detectors") {
    Move-Item -Path "detectors" -Destination "$trash\" -Force
    Write-Host "  ✓ detectors/" -ForegroundColor Green
}

if (Test-Path "infrastructure") {
    Move-Item -Path "infrastructure" -Destination "$trash\" -Force
    Write-Host "  ✓ infrastructure/" -ForegroundColor Green
}

# ========================================================================
# RESUMO
# ========================================================================
Write-Host "`n" -NoNewline
Write-Host "✅ DRY-RUN COMPLETO!" -ForegroundColor Green -BackgroundColor Black
Write-Host "`nTodos os itens foram movidos para: $trash" -ForegroundColor Yellow
Write-Host "`n📋 Próximos passos:" -ForegroundColor Cyan
Write-Host "  1. Revise o conteúdo de '$trash'" -ForegroundColor White
Write-Host "  2. Execute: python -m compileall ." -ForegroundColor White
Write-Host "  3. Execute: python app_gui.py" -ForegroundColor White
Write-Host "  4. Se algo falhar, restaure: Move-Item '$trash\*' -Destination . -Force" -ForegroundColor White
Write-Host "  5. Se tudo funcionar, delete: Remove-Item -Recurse -Force '$trash'" -ForegroundColor White

# ========================================================================
# COMANDO DE REVERSÃO (copie se precisar desfazer)
# ========================================================================
<#
# Para REVERTER tudo (restaurar da quarentena):
$trash = "_trash_YYYYMMDD_HHMM"  # Substitua pelo nome correto
Move-Item -Path "$trash\*" -Destination . -Force -Recurse
Remove-Item -Path $trash -Force
#>
