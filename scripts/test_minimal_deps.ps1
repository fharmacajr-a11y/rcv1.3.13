# Test Runtime with Minimal Dependencies
# =======================================
# Script para testar o runtime com as dependências mínimas

Write-Host "🧪 RC-Gestor - Teste de Dependências Mínimas" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Verificar se já existe .venv-min
if (Test-Path ".venv-min") {
    Write-Host "⚠️  Ambiente .venv-min já existe." -ForegroundColor Yellow
    $response = Read-Host "Deseja recriá-lo? (s/N)"
    if ($response -eq "s" -or $response -eq "S") {
        Write-Host "🗑️  Removendo .venv-min existente..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force .venv-min
    } else {
        Write-Host "✅ Usando ambiente existente" -ForegroundColor Green
        . .\.venv-min\Scripts\Activate.ps1
        Write-Host ""
        Write-Host "📦 Pacotes instalados:" -ForegroundColor Cyan
        pip list
        exit 0
    }
}

# Criar novo ambiente
Write-Host "📦 Criando novo ambiente virtual (.venv-min)..." -ForegroundColor Cyan
py -3.13 -m venv .venv-min

if (-not $?) {
    Write-Host "❌ Erro ao criar ambiente virtual" -ForegroundColor Red
    exit 1
}

# Ativar ambiente
Write-Host "🔌 Ativando ambiente..." -ForegroundColor Cyan
. .\.venv-min\Scripts\Activate.ps1

# Verificar se requirements-min.txt existe
if (-not (Test-Path "requirements-min.txt")) {
    Write-Host "❌ Arquivo requirements-min.txt não encontrado!" -ForegroundColor Red
    Write-Host "Execute primeiro: pip-compile requirements-min.in --output-file requirements-min.txt" -ForegroundColor Yellow
    exit 1
}

# Instalar dependências
Write-Host "📥 Instalando dependências mínimas..." -ForegroundColor Cyan
pip install --upgrade pip
pip install -r requirements-min.txt

if (-not $?) {
    Write-Host "❌ Erro ao instalar dependências" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Ambiente preparado com sucesso!" -ForegroundColor Green
Write-Host ""

# Mostrar pacotes instalados
Write-Host "📦 Pacotes instalados:" -ForegroundColor Cyan
pip list | Select-String -Pattern "^Package" -Context 0,999

Write-Host ""
Write-Host "🎯 Próximos passos:" -ForegroundColor Yellow
Write-Host "  1. cd runtime" -ForegroundColor White
Write-Host "  2. python app_gui.py" -ForegroundColor White
Write-Host ""
Write-Host "📋 Checklist de testes:" -ForegroundColor Yellow
Write-Host "  [ ] Login com credenciais válidas" -ForegroundColor White
Write-Host "  [ ] Navegação entre telas" -ForegroundColor White
Write-Host "  [ ] Listagem de clientes" -ForegroundColor White
Write-Host "  [ ] Upload de arquivo PDF" -ForegroundColor White
Write-Host "  [ ] Visualização de PDF" -ForegroundColor White
Write-Host "  [ ] Detecção de CNPJ (OCR)" -ForegroundColor White
Write-Host "  [ ] Busca/filtros" -ForegroundColor White
Write-Host "  [ ] Lixeira (soft delete)" -ForegroundColor White
Write-Host "  [ ] Healthcheck de conectividade" -ForegroundColor White
Write-Host "  [ ] Logout" -ForegroundColor White
Write-Host ""
