# Plano de Ação - Limpeza do Repositório

**Data:** 18 de outubro de 2025  
**Status:** 🟢 Pronto para execução

---

## 🎯 Objetivo

Executar limpeza mínima e segura baseada na auditoria V2.

---

## ✅ Fase 1: Limpeza Imediata (Risco Zero)

### Ação 1: Remover ícone duplicado

**Arquivo:** `rc.ico` (122 KB)  
**Razão:** Duplicado exato de `assets/app.ico` (mesmo SHA-256)  
**Risco:** 🟢 Zero - existe cópia em `assets/`

```powershell
# Verificar hash antes de remover (confirmação)
Get-FileHash rc.ico -Algorithm SHA256
Get-FileHash assets\app.ico -Algorithm SHA256

# Remover duplicado
Remove-Item rc.ico -Verbose
```

**Economia:** 122 KB

---

### Ação 2: Remover backup obsoleto

**Arquivo:** `scripts/infrastructure_scripts_init.py.bak` (0 bytes)  
**Razão:** Arquivo vazio, backup obsoleto  
**Risco:** 🟢 Zero - arquivo vazio

```powershell
Remove-Item scripts\infrastructure_scripts_init.py.bak -Verbose
```

**Economia:** 0 bytes (mas remove ruído)

---

## ⚠️ Fase 2: Verificação de Assets (Opcional)

### Ação 3: Avaliar rc.png

**Arquivo:** `rc.png` (32 KB)  
**Status:** ⚠️ Comentado no código, documentado como "material promocional"  
**Risco:** 🟡 Baixo - pode ser necessário para marketing/documentação

```powershell
# Verificar referências ativas no código Python
Select-String -Path *.py -Pattern "rc\.png" -Recurse |
  Where-Object { $_.Line -notmatch "^\s*#" }

# Se não houver referências ativas, mover para quarentena
New-Item -ItemType Directory -Force -Path ajuda\_quarentena_assets
Move-Item rc.png ajuda\_quarentena_assets\ -Verbose
```

**Decisão sugerida:**
- Se usado em docs/marketing: **MANTER**
- Se não usado: **MOVER para quarentena** (pode restaurar depois)

**Economia potencial:** 32 KB

---

## 📋 Comandos Completos

### Opção A: Limpeza Mínima (Recomendada)

```powershell
# Apenas duplicados e backups vazios
Remove-Item rc.ico -Verbose
Remove-Item scripts\infrastructure_scripts_init.py.bak -Verbose
```

**Resultado:** -122 KB, 0 risco

---

### Opção B: Limpeza Completa (Com verificação)

```powershell
# 1. Remover duplicados e backups
Remove-Item rc.ico -Verbose
Remove-Item scripts\infrastructure_scripts_init.py.bak -Verbose

# 2. Verificar uso de rc.png
$rcPngRefs = Select-String -Path *.py -Pattern "rc\.png" -Recurse |
  Where-Object { $_.Line -notmatch "^\s*#" }

if ($rcPngRefs.Count -eq 0) {
    # Sem referências ativas, mover para quarentena
    New-Item -ItemType Directory -Force -Path ajuda\_quarentena_assets | Out-Null
    Move-Item rc.png ajuda\_quarentena_assets\ -Verbose
    Write-Host "✅ rc.png movido para quarentena (pode restaurar se necessário)" -ForegroundColor Green
} else {
    Write-Host "⚠️  rc.png tem referências ativas, mantido na raiz" -ForegroundColor Yellow
    $rcPngRefs
}
```

**Resultado:** -122 a -154 KB

---

## 🔄 Comandos de Verificação (Pós-Limpeza)

### Confirmar remoções

```powershell
# Verificar se rc.ico foi removido
Test-Path rc.ico  # Deve retornar False

# Verificar se assets/app.ico ainda existe
Test-Path assets\app.ico  # Deve retornar True

# Listar quarentena (se criada)
Get-ChildItem ajuda\_quarentena_assets -ErrorAction SilentlyContinue
```

### Executar nova auditoria

```powershell
# Re-executar auditoria para confirmar limpeza
python .\scripts\audit_repo_v2.py --stale-days 60 --top 80

# Comparar resultados
Get-Content ajuda\CLEANUP_PLAN.md | Select-String "Duplicados"
```

---

## 📊 Resultado Esperado

### Antes da Limpeza
```
Arquivos: 163
Duplicados: 2 grupos
Tamanho: ~0.9 MB
```

### Depois da Limpeza (Opção A)
```
Arquivos: 161
Duplicados: 1 grupo (apenas vazios)
Tamanho: ~0.78 MB
Economia: 122 KB (13.5%)
```

### Depois da Limpeza (Opção B)
```
Arquivos: 160
Duplicados: 1 grupo (apenas vazios)
Tamanho: ~0.75 MB
Economia: 154 KB (17.1%)
```

---

## ⚠️ Notas Importantes

### Sobre rc.png

**Encontrado em:**
- ✅ `ui/login/login.py` - **COMENTADO** (linha 43)
- ✅ `scripts/healthcheck.py` - Verificação de bundle
- ✅ Documentação - Referenciado como "material promocional"

**Status atual:**
- Código não usa ativamente (linha comentada)
- Pode ser usado para marketing/docs
- Está no manifesto como "material promocional"

**Recomendação:**
1. Se projeto precisa de logo PNG para docs/marketing → **MANTER**
2. Se não precisa → **MOVER para quarentena**
3. Não delete diretamente (use quarentena primeiro)

---

### Sobre Duplicados Vazios

**Arquivos:**
- `docs/.gitkeep` - ✅ **MANTER** (propósito: manter pasta vazia no git)
- `utils/__init__.py` - ✅ **MANTER** (necessário para Python packages)
- `scripts/infrastructure_scripts_init.py.bak` - ❌ **REMOVER** (backup obsoleto)

---

## 🎓 Referências dos Comandos

- [Remove-Item](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/remove-item)
- [Get-FileHash](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/get-filehash)
- [Select-String](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/select-string)
- [Test-Path](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/test-path)

---

## ✅ Checklist de Execução

### Pré-Limpeza
- [ ] Ler auditoria completa (`ajuda/CLEANUP_PLAN.md`)
- [ ] Confirmar backups/git commitados
- [ ] Decidir sobre rc.png (manter ou quarentena)

### Execução
- [ ] Executar comandos da Fase 1
- [ ] (Opcional) Executar comandos da Fase 2
- [ ] Verificar remoções com Test-Path

### Pós-Limpeza
- [ ] Re-executar auditoria V2
- [ ] Confirmar redução de duplicados
- [ ] Testar smoke test: `python scripts\smoke_runtime.py`
- [ ] Commit das mudanças

---

## 🚀 Execução Rápida

**Para limpeza mínima segura (recomendada):**

```powershell
# Copie e cole este bloco completo
Write-Host "🧹 Iniciando limpeza..." -ForegroundColor Cyan

# Remover duplicado do ícone
if (Test-Path rc.ico) {
    Remove-Item rc.ico -Verbose
    Write-Host "✅ rc.ico removido" -ForegroundColor Green
}

# Remover backup vazio
if (Test-Path scripts\infrastructure_scripts_init.py.bak) {
    Remove-Item scripts\infrastructure_scripts_init.py.bak -Verbose
    Write-Host "✅ Backup obsoleto removido" -ForegroundColor Green
}

Write-Host ""
Write-Host "✅ Limpeza concluída!" -ForegroundColor Green
Write-Host "📊 Economia: ~122 KB" -ForegroundColor Cyan
Write-Host ""
Write-Host "🔄 Re-executar auditoria:" -ForegroundColor Yellow
Write-Host "  python .\scripts\audit_repo_v2.py --stale-days 60 --top 80"
```

---

**Última atualização:** 18 de outubro de 2025  
**Versão:** v1.0.33  
**Branch:** integrate/v1.0.29
