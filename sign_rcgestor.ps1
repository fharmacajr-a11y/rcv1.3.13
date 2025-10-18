# 🔐 Script de Assinatura Digital - RC-Gestor
# Assinar executável rcgestor.exe com certificado de código

param(
    [Parameter(Mandatory=$false)]
    [string]$CertPath = "",

    [Parameter(Mandatory=$false)]
    [string]$CertPassword = "",

    [Parameter(Mandatory=$false)]
    [string]$ExePath = "dist\rcgestor.exe",

    [Parameter(Mandatory=$false)]
    [string]$TimestampServer = "http://timestamp.digicert.com"
)

# CORES
$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"

Write-Host "`n🔐 RC-GESTOR - ASSINATURA DIGITAL`n" -ForegroundColor Cyan

# 1. VERIFICAR SE EXECUTÁVEL EXISTE
if (-not (Test-Path $ExePath)) {
    Write-Host "❌ ERRO: Executável não encontrado: $ExePath" -ForegroundColor $Red
    exit 1
}
Write-Host "✅ Executável encontrado: $ExePath" -ForegroundColor $Green

# 2. VERIFICAR SE SIGNTOOL ESTÁ DISPONÍVEL
$SignTool = Get-Command signtool.exe -ErrorAction SilentlyContinue
if (-not $SignTool) {
    Write-Host "❌ ERRO: SignTool.exe não encontrado!" -ForegroundColor $Red
    Write-Host "   Instale o Windows SDK: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/" -ForegroundColor $Yellow
    exit 1
}
Write-Host "✅ SignTool encontrado: $($SignTool.Source)" -ForegroundColor $Green

# 3. VERIFICAR SE CERTIFICADO FOI FORNECIDO
if ([string]::IsNullOrEmpty($CertPath)) {
    Write-Host "`n⚠️  CERTIFICADO NÃO FORNECIDO!" -ForegroundColor $Yellow
    Write-Host "   Para assinar, execute:" -ForegroundColor $Yellow
    Write-Host '   .\sign_rcgestor.ps1 -CertPath "C:\path\to\cert.pfx" -CertPassword "SUA_SENHA"' -ForegroundColor $Yellow
    Write-Host "`n   Pulando assinatura..`n" -ForegroundColor $Yellow
    exit 0
}

# 4. VERIFICAR SE CERTIFICADO EXISTE
if (-not (Test-Path $CertPath)) {
    Write-Host "❌ ERRO: Certificado não encontrado: $CertPath" -ForegroundColor $Red
    exit 1
}
Write-Host "✅ Certificado encontrado: $CertPath" -ForegroundColor $Green

# 5. ASSINAR EXECUTÁVEL
Write-Host "`n🔏 Assinando executável..." -ForegroundColor Cyan
$SignArgs = @(
    "sign",
    "/f", $CertPath,
    "/p", $CertPassword,
    "/fd", "SHA256",
    "/tr", $TimestampServer,
    "/td", "SHA256",
    "/v",
    $ExePath
)

try {
    $Result = & signtool.exe $SignArgs 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ ASSINATURA CONCLUÍDA COM SUCESSO!" -ForegroundColor $Green
        Write-Host $Result -ForegroundColor Gray
    } else {
        Write-Host "❌ ERRO AO ASSINAR:" -ForegroundColor $Red
        Write-Host $Result -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ EXCEÇÃO AO ASSINAR: $_" -ForegroundColor $Red
    exit 1
}

# 6. VERIFICAR ASSINATURA
Write-Host "`n🔍 Verificando assinatura..." -ForegroundColor Cyan
try {
    $VerifyResult = & signtool.exe verify /pa /v $ExePath 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ ASSINATURA VÁLIDA!" -ForegroundColor $Green
        Write-Host $VerifyResult -ForegroundColor Gray
    } else {
        Write-Host "⚠️  AVISO: Verificação retornou código $LASTEXITCODE" -ForegroundColor $Yellow
        Write-Host $VerifyResult -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Não foi possível verificar: $_" -ForegroundColor $Yellow
}

Write-Host "`n✅ PROCESSO CONCLUÍDO!`n" -ForegroundColor $Green
