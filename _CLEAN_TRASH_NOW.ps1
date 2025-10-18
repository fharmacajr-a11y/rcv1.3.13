# ============================================================================
# 🧹 LIMPEZA SEGURA - MOVER PARA QUARENTENA (PowerShell)
# ============================================================================
# Script gerado automaticamente - Code Janitor
# IMPORTANTE: Este script MOVE itens para quarentena, não deleta!
# ============================================================================

# Criar pasta de quarentena com timestamp
$trash = "_trash_$(Get-Date -Format yyyyMMdd_HHmm)"
Write-Host "🗑️  Criando quarentena: $trash" -ForegroundColor Yellow
New-Item -ItemType Directory -Path $trash -Force | Out-Null

$movedCount = 0
$skippedCount = 0

# ============================================================================
# FUNÇÃO AUXILIAR: Mover item preservando estrutura de diretórios
# ============================================================================
function Move-ToTrash {
    param(
        [string]$SourcePath,
        [string]$TrashRoot
    )

    if (Test-Path $SourcePath) {
        $relativePath = $SourcePath
        $targetPath = Join-Path $TrashRoot $relativePath
        $targetDir = Split-Path $targetPath -Parent

        if ($targetDir -and -not (Test-Path $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }

        try {
            Move-Item -Path $SourcePath -Destination $targetPath -Force -ErrorAction Stop
            Write-Host "  ✓ Movido: $SourcePath" -ForegroundColor Green
            return $true
        }
        catch {
            Write-Host "  ⚠ Erro ao mover: $SourcePath - $_" -ForegroundColor Red
            return $false
        }
    }
    return $false
}

# ============================================================================
# PARTE 1: Pastas __pycache__ (recursivas)
# ============================================================================
Write-Host "`n📦 Buscando pastas __pycache__..." -ForegroundColor Cyan

$pycacheDirs = Get-ChildItem -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue
foreach ($dir in $pycacheDirs) {
    if (Move-ToTrash -SourcePath $dir.FullName.Replace("$PWD\", "") -TrashRoot $trash) {
        $movedCount++
    }
}

# ============================================================================
# PARTE 2: Caches de ferramentas
# ============================================================================
Write-Host "`n🔧 Buscando caches de ferramentas..." -ForegroundColor Cyan

$cacheDirs = @(
    ".ruff_cache",
    ".import_linter_cache"
)

foreach ($cache in $cacheDirs) {
    if (Move-ToTrash -SourcePath $cache -TrashRoot $trash) {
        $movedCount++
    }
    else {
        $skippedCount++
    }
}

# ============================================================================
# PARTE 3: Ambiente virtual (.venv)
# ============================================================================
Write-Host "`n🐍 Buscando ambiente virtual..." -ForegroundColor Cyan

if (Move-ToTrash -SourcePath ".venv" -TrashRoot $trash) {
    $movedCount++
}
else {
    $skippedCount++
}

# ============================================================================
# PARTE 4: Artefatos de build
# ============================================================================
Write-Host "`n🔨 Buscando artefatos de build..." -ForegroundColor Cyan

$buildDirs = @("build", "dist")

foreach ($buildDir in $buildDirs) {
    if (Move-ToTrash -SourcePath $buildDir -TrashRoot $trash) {
        $movedCount++
    }
    else {
        $skippedCount++
    }
}

# ============================================================================
# PARTE 5: Documentação e scripts de desenvolvimento
# ============================================================================
Write-Host "`n📚 Buscando docs e scripts de desenvolvimento..." -ForegroundColor Cyan

$devDirs = @(
    "ajuda",
    "runtime_docs",
    "scripts",
    "detectors",
    "infrastructure"
)

foreach ($dir in $devDirs) {
    if (Move-ToTrash -SourcePath $dir -TrashRoot $trash) {
        $movedCount++
    }
    else {
        $skippedCount++
    }
}

# ============================================================================
# PARTE 6: Arquivos específicos
# ============================================================================
Write-Host "`n📄 Buscando arquivos específicos..." -ForegroundColor Cyan

$targetFiles = @(
    "RELATORIO_BUILD_PYINSTALLER.md",
    "RELATORIO_ONEFILE.md",
    "EXCLUSOES_SUGERIDAS.md",
    "PYINSTALLER_BUILD.md",
    "requirements.in",
    "requirements-min.in",
    "requirements-min.txt",
    ".pre-commit-config.yaml",
    ".importlinter"
)

foreach ($file in $targetFiles) {
    if (Move-ToTrash -SourcePath $file -TrashRoot $trash) {
        $movedCount++
    }
    else {
        $skippedCount++
    }
}

# ============================================================================
# RESUMO FINAL
# ============================================================================
Write-Host "`n" -NoNewline
Write-Host "✅ LIMPEZA CONCLUÍDA!" -ForegroundColor Green -BackgroundColor Black
Write-Host "`n📊 Resumo:" -ForegroundColor Cyan
Write-Host "  • Itens movidos: $movedCount" -ForegroundColor Green
Write-Host "  • Itens não encontrados: $skippedCount" -ForegroundColor Gray
Write-Host "  • Pasta de quarentena: $trash" -ForegroundColor Yellow

Write-Host "`n📋 Próximos passos:" -ForegroundColor Cyan
Write-Host "  1. Verifique o conteúdo de '$trash'" -ForegroundColor White
Write-Host "  2. Execute os comandos de validação abaixo" -ForegroundColor White
Write-Host "  3. Se tudo estiver OK, delete: Remove-Item -Recurse -Force '$trash'" -ForegroundColor White
Write-Host "  4. Se algo falhar, restaure: Move-Item -Path '$trash\*' -Destination . -Force -Recurse" -ForegroundColor White

# ============================================================================
# VALIDAÇÃO (descomente para executar automaticamente)
# ============================================================================
<#
Write-Host "`n🔍 Validando compilação Python..." -ForegroundColor Cyan
python -m compileall . 2>&1 | Select-String "SyntaxError"

Write-Host "`n🚀 Testando aplicação..." -ForegroundColor Cyan
# python .\app_gui.py
# (pressione Ctrl+C após verificar que abre sem erros)
#>

# ============================================================================
# COMANDO DE REVERSÃO (copie se precisar desfazer)
# ============================================================================
<#
# Para REVERTER tudo (restaurar da quarentena):
$trash = "_trash_YYYYMMDD_HHMM"  # Substitua pelo nome correto
Move-Item -Path "$trash\*" -Destination . -Force -Recurse
Remove-Item -Path $trash -Force -Recurse
#>

Write-Host "`n✨ Concluído! Revise a pasta '$trash' antes de deletar." -ForegroundColor Yellow
