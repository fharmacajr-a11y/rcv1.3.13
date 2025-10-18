# 🧹 Plano de Limpeza V3 - Ações Seguras

**Gerado em:** 2025-01-18 07:35:00  
**Base:** ARVORE.txt + INVENTARIO.csv + CLEANUP_PLAN.md + Verificação de referências

---

## 📊 Resumo Executivo

| Métrica | Valor |
|---------|-------|
| **Arquivos analisados** | 163 |
| **Grupos duplicados** | 2 |
| **Arquivos stale (>60d)** | 0 |
| **Fora do runtime** | 68 (esperado/correto) |
| **Economia potencial** | ~122 KB (baixo impacto) |

### ✅ Boa notícia: Repositório bem mantido!
- **Zero arquivos obsoletos** (todos modificados <60 dias)
- Estrutura organizada com separação clara entre runtime/docs/tests
- Apenas 1 duplicata real (rc.ico = assets/app.ico)

---

## 🔍 Verificação de Referências

### ✅ `rc.ico` (122 KB) — **MANTER NA RAIZ**

**Status:** 🟢 **EM USO ATIVO**

**Referências encontradas:**
- `gui/main_window.py:104` → `self.iconbitmap(resource_path("rc.ico"))`
- `ui/login/login.py:37` → `ico = resource_path("rc.ico")`
- `ui/dialogs/upload_progress.py:21` → `dlg.iconbitmap(resource_path("rc.ico"))`
- `ui/forms/actions.py:159,242` → `self.iconbitmap(resource_path("rc.ico"))`
- `ui/files_browser.py:29,221` → `docs_window.iconbitmap(resource_path("rc.ico"))`
- `build/rc_gestor.spec:32,86` → Empacotado no build PyInstaller

**Conclusão:** Arquivo crítico, usado em 8+ locais. **NÃO REMOVER**.

---

### 🟡 `rc.png` (32 KB) — **CANDIDATO A QUARENTENA**

**Status:** 🟡 **COMENTADO NO CÓDIGO**

**Referências encontradas:**
- `ui/login/login.py:43` → `# self.iconphoto(True, tk.PhotoImage(file=resource_path("rc.png")))` ← **COMENTADO**
- `build/rc_gestor.spec:33` → Empacotado no build, mas **não usado em runtime**
- `config/runtime_manifest.yaml:36` → Listado como "material promocional"

**Conclusão:** Arquivo de propósito indefinido:
- **Não é usado ativamente** no código Python
- Empacotado no build mas sem referência ativa
- Pode ser logo/splash screen planejado mas não implementado

**Ação recomendada:** Mover para quarentena (pode ser restaurado se necessário).

---

### ✅ `assets/app.ico` (122 KB) — **DUPLICADO DE rc.ico**

**Status:** 🟠 **DUPLICADO BYTE-A-BYTE**

**Verificação SHA-256:**
```
rc.ico:         ebf2adcf9e7768e8...
assets/app.ico: ebf2adcf9e7768e8... ← IDÊNTICO
```

**Uso no código:**
- `rc.ico` → 8+ referências diretas
- `assets/app.ico` → 0 referências diretas

**Conclusão:** `assets/app.ico` é uma cópia de backup não utilizada.

**Ação recomendada:** Mover para quarentena (economia de 122 KB).

---

## 📋 Plano de Ações

### Categoria 1: MANTER (Arquivos Críticos)

✅ **Nenhuma ação necessária** — Todos os arquivos do runtime estão corretos.

| Arquivo | Tamanho | Razão |
|---------|---------|-------|
| `rc.ico` | 122 KB | Usado em 8+ locais (main_window, login, dialogs, forms) |
| Todos os .py runtime | ~600 KB | Código ativo em produção |

---

### Categoria 2: QUARENTENA (Verificação Manual)

🟡 **Mover para `ajuda/_quarentena_assets/`** — Arquivos de uso incerto.

| Arquivo | Tamanho | Motivo | Segurança |
|---------|---------|--------|-----------|
| `assets/app.ico` | 122 KB | Duplicado de rc.ico | 🟢 Alta (não referenciado) |
| `rc.png` | 32 KB | Comentado no código | 🟡 Média (pode ser planejado) |

**Economia:** ~154 KB

**Comando PowerShell:**
```powershell
# Criar pasta de quarentena
New-Item -ItemType Directory -Force -Path "ajuda\_quarentena_assets"

# Mover duplicado
Move-Item "assets\app.ico" "ajuda\_quarentena_assets\" -Verbose

# Mover rc.png (uso incerto)
Move-Item "rc.png" "ajuda\_quarentena_assets\" -Verbose

# Documentar
Write-Host "✅ Quarentena criada em ajuda\_quarentena_assets\" -ForegroundColor Green
Write-Host "ℹ️  Para restaurar:" -ForegroundColor Cyan
Write-Host "   Move-Item ajuda\_quarentena_assets\app.ico assets\" -ForegroundColor Gray
Write-Host "   Move-Item ajuda\_quarentena_assets\rc.png .\" -ForegroundColor Gray
```

---

### Categoria 3: DOCUMENTAÇÃO (Mover para ajuda/)

📄 **Já está no lugar correto** — Toda documentação já está em `ajuda/` e `docs/`.

*Nenhuma ação necessária.*

---

### Categoria 4: LIXO (.bak, temporários)

🗑️ **Arquivos seguros para remover:**

| Arquivo | Tamanho | Motivo |
|---------|---------|--------|
| `scripts/infrastructure_scripts_init.py.bak` | 0 KB | Backup vazio |

**Comando:**
```powershell
Remove-Item "scripts\infrastructure_scripts_init.py.bak" -Verbose
Write-Host "✅ Arquivo .bak removido" -ForegroundColor Green
```

---

## 🚀 Roteiro de Execução

### Passo 1: Criar Quarentena (dry-run)

```powershell
# Testar se arquivos existem antes de mover
Test-Path "assets\app.ico"  # Deve retornar True
Test-Path "rc.png"          # Deve retornar True

# Visualizar hash
Get-FileHash "rc.ico" -Algorithm SHA256
Get-FileHash "assets\app.ico" -Algorithm SHA256
```

**Resultado esperado:** Hashes idênticos confirmando duplicação.

---

### Passo 2: Executar Quarentena

```powershell
# Criar pasta
New-Item -ItemType Directory -Force -Path "ajuda\_quarentena_assets"

# Mover arquivos
Move-Item "assets\app.ico" "ajuda\_quarentena_assets\" -Verbose
Move-Item "rc.png" "ajuda\_quarentena_assets\" -Verbose

# Verificar
Get-ChildItem "ajuda\_quarentena_assets"
```

**Resultado esperado:**
```
Diretório: C:\...\ajuda\_quarentena_assets

Mode    Name
----    ----
-a----  app.ico  (122,078 bytes)
-a----  rc.png   (32,502 bytes)
```

---

### Passo 3: Remover Lixo Confirmado

```powershell
Remove-Item "scripts\infrastructure_scripts_init.py.bak" -Verbose
```

---

### Passo 4: Testar Runtime

```powershell
# Smoke test completo
python .\scripts\smoke_runtime.py

# Verificar importações
python -c "from gui.main_window import MainWindow; print('✅ GUI imports OK')"

# Verificar resource_path
python -c "from utils.resource_path import resource_path; print(resource_path('rc.ico'))"
```

**Resultado esperado:** Todos os testes devem passar sem erros.

---

### Passo 5: Commit das Mudanças

```powershell
git status

# Se tudo ok, commitar
git add -A
git commit -m "chore: limpar duplicados e mover assets não usados para quarentena

- Move assets/app.ico (duplicado de rc.ico) para quarentena
- Move rc.png (uso incerto, comentado no código) para quarentena
- Remove infrastructure_scripts_init.py.bak (arquivo vazio)
- Economia: ~154 KB de duplicados
- Runtime testado: 100% funcional"
```

---

## 🔄 Rollback (Se Necessário)

Se algo quebrar após a limpeza, restaurar arquivos:

```powershell
# Restaurar app.ico
Move-Item "ajuda\_quarentena_assets\app.ico" "assets\" -Force

# Restaurar rc.png
Move-Item "ajuda\_quarentena_assets\rc.png" "." -Force

# Verificar
Test-Path "assets\app.ico"  # Deve retornar True
Test-Path "rc.png"          # Deve retornar True
```

---

## 📊 Impacto Estimado

| Métrica | Antes | Depois | Diferença |
|---------|-------|--------|-----------|
| **Arquivos totais** | 163 | 160 | -3 (-1.8%) |
| **Tamanho repo** | ~2.5 MB | ~2.35 MB | -154 KB (-6.2%) |
| **Arquivos runtime** | 95 | 95 | 0 (sem impacto) |
| **Duplicados** | 2 grupos | 1 grupo | -1 |
| **Build PyInstaller** | Funcional | Funcional | Sem impacto |

---

## ⚠️ Avisos Importantes

### 🔴 NÃO REMOVER:
- `rc.ico` (raiz) → Usado em 8+ locais
- Qualquer arquivo em `runtime/` → Essencial para execução
- `build/rc_gestor.spec` → Necessário para builds futuros

### 🟡 VERIFICAR ANTES:
- `rc.png` → Pode ser usado em splash screen futuro
- `assets/app.ico` → Pode ser referenciado em builds antigos

### 🟢 SEGURO:
- `.bak` files vazios
- Duplicados byte-a-byte confirmados por SHA-256

---

## 📈 Próximos Passos (Opcional)

### Análise de Dead Code

Se quiser remover código morto (não obrigatório):

```powershell
# Rodar vulture (já instalado)
vulture . --min-confidence 80 --sort-by-size > ajuda\VULTURE_V3_REPORT.txt

# Analisar resultados manualmente
code ajuda\VULTURE_V3_REPORT.txt
```

**⚠️ Atenção:** Vulture pode gerar falsos positivos. **Não remover** código sem análise manual.

---

### Análise de Dependências Transitivas

Se quiser verificar dependências não usadas:

```powershell
# Rodar deptry (já instalado)
deptry . > ajuda\DEPTRY_V3_REPORT.txt

# Analisar resultados
code ajuda\DEPTRY_V3_REPORT.txt
```

---

## ✅ Checklist Final

Antes de considerar a limpeza concluída:

- [ ] **Passo 1:** Criar quarentena executado
- [ ] **Passo 2:** Mover duplicados executado
- [ ] **Passo 3:** Remover .bak executado
- [ ] **Passo 4:** Smoke test passou 100%
- [ ] **Passo 5:** Commit realizado
- [ ] **Passo 6:** Build PyInstaller testado (opcional)
- [ ] **Passo 7:** Documentação atualizada (este arquivo)

---

## 📝 Conclusão

**Status geral:** 🟢 Repositório em excelente estado

**Principais descobertas:**
- ✅ Zero arquivos obsoletos (manutenção ativa)
- ✅ Estrutura bem organizada (runtime/docs/tests separados)
- ✅ Apenas 1 duplicata real (154 KB de economia potencial)
- ✅ Código limpo e sem lixo acumulado

**Ações recomendadas:**
1. ✅ Mover duplicados para quarentena (seguro, reversível)
2. ✅ Remover .bak vazio (sem risco)
3. 🟡 Decidir sobre rc.png (baixa prioridade)

**Impacto:** Mínimo (~154 KB), mas melhora organização e remove redundância.

---

**Gerado por:** `scripts/audit_repo_v2.py` + análise manual de referências  
**Data:** 2025-01-18 07:35:00  
**Branch:** integrate/v1.0.29
