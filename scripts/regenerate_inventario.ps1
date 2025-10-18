# Regenera INVENTARIO.csv em UTF-8 sem BOM (compatível PS 5.1 e PS 7+)

$outputPath = ".\ajuda\dup-consolidacao\INVENTARIO.csv"

Write-Host "📊 Coletando arquivos..." -ForegroundColor Cyan

# Coletar dados
$data = Get-ChildItem -Recurse -Force |
    Where-Object { -not $_.PSIsContainer } |
    Select-Object FullName, Extension, Length, LastWriteTime

# Verificar versão do PowerShell
$isPowerShell7 = $PSVersionTable.PSVersion.Major -ge 7

if ($isPowerShell7) {
    # PowerShell 7+: Export-Csv já usa utf8NoBOM por padrão
    Write-Host "✅ PowerShell 7+ detectado - usando Export-Csv" -ForegroundColor Green
    $data | Export-Csv -NoTypeInformation -Path $outputPath
} else {
    # PowerShell 5.1: Usar StreamWriter para UTF-8 sem BOM
    Write-Host "⚠️  PowerShell 5.1 detectado - usando StreamWriter para UTF-8 sem BOM" -ForegroundColor Yellow

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $writer = New-Object System.IO.StreamWriter($outputPath, $false, $utf8NoBom)

    try {
        $csv = $data | ConvertTo-Csv -NoTypeInformation
        foreach ($line in $csv) {
            $writer.WriteLine($line)
        }
        Write-Host "✅ CSV gravado com UTF-8 sem BOM" -ForegroundColor Green
    } finally {
        $writer.Dispose()
    }
}

Write-Host ""
Write-Host "✅ Inventário criado: $outputPath" -ForegroundColor Green

# Verificar tamanho
$fileInfo = Get-Item $outputPath
Write-Host "📦 Tamanho: $([math]::Round($fileInfo.Length / 1KB, 2)) KB" -ForegroundColor Cyan
Write-Host "📊 Registros: $($data.Count)" -ForegroundColor Cyan
