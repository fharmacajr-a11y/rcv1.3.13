# Reorganização da Estrutura do Repositório

## 📊 Resumo

Esta PR realiza uma reorganização abrangente da estrutura do repositório, focando em:
- **Limpeza da raiz**: Redução de 82 → 52 itens (-37%)
- **Documentação organizada**: Movimentação para `docs/` com índice completo
- **Artefatos desversionados**: Mantidos no disco, ignorados no Git
- **Qualidade garantida**: Pre-commit 100% verde, Bandit sem issues

---

## 🎯 Mudanças Principais

### 1. Documentação Reorganizada (`docs/`)

```
docs/
├── README.md (índice completo)
├── patches/ (5 arquivos)
│   ├── ANALISE_MIGRACAO_CTK_CLIENTESV2.md
│   ├── PATCH_CLIENTESV2_DOUBLECLICK_FLASH.md
│   ├── PATCH_CLIENT_FILES_BROWSER.md
│   ├── PATCH_FIX_FILES_BROWSER_ACCESS.md
│   └── PATCH_V2_DOUBLECLICK_DETERMINISTICO.md
├── reports/
│   ├── microfases/ (4 relatórios)
│   └── releases/ (7 relatórios)
└── guides/
    └── MIGRACAO_CTK_GUIA_COMPLETO.ipynb
```

### 2. Artefatos Desversionados

**Pastas** (mantidas no disco, ignoradas no Git):
- `diagnostics/` (21 arquivos)

**Arquivos temporários** → `artifacts/local/`:
- 4 audit files (`audit_*.txt`)
- 10 hub results (`hub_*.txt`)
- 1 baseline (`baseline_ttk_inventory.txt`)
- 1 log (`lifecycle_test.log`)

### 3. Scripts Arquivados

- `fix_ctk_advanced.py` → `tools/migration/`
- `fix_ctk_padding.py` → `tools/migration/`
- `test_ctktreeview.py` → `tests/experiments/`

### 4. Ferramentas de Limpeza Arquivadas

- `cleanup_repo.ps1` (338 linhas) → `tools/repo/`
- `cleanup_repo.sh` (333 linhas) → `tools/repo/`
- `gitignore_additions.txt` (70 linhas) → `tools/repo/`
- `EXECUTION_GUIDE.md` (349 linhas) → `tools/repo/`

---

## 🔒 Qualidade e Segurança

### Bandit Security
- ✅ **0 issues** (todos tratados pontualmente)
- Removido B112 do skip global
- Tratamento pontual com `# nosec` + comentários justificativos:
  - `# nosec B112 - Fallback pattern: tenta múltiplos caminhos até encontrar módulo válido`
  - `# nosec B606 - Local path controlado (download de Supabase Storage)`
  - `# nosec B404 - Necessário para xdg-open em Linux`
  - `# nosec B603, B607 - xdg-open com path local controlado`

### Pre-commit Hooks
```
✅ 20/20 hooks PASSED
✅ Trailing whitespace
✅ End of file fixer
✅ Check added large files
✅ Check YAML/TOML/JSON syntax
✅ Check merge conflict markers
✅ Check case conflicts
✅ Mixed line endings
✅ Ruff (linter + formatter)
✅ Python syntax validation
✅ Check builtin literals
✅ Check docstring position
✅ Debug statements check
✅ Test file naming
✅ CustomTkinter SSoT policy
✅ UI/Theme policy validation
✅ Python compileall
✅ Bandit security scan
```

### Configurações Atualizadas

**.gitignore**:
- Adicionadas regras para `diagnostics/`, `artifacts/local/`
- Exceções para `tools/repo/` (versionado)
- Padrões para arquivos temporários

**ruff.toml**:
- Exclusão E402 para `**/_archived/**`

**.bandit**:
- Removido B112 do skip global
- Mantidos apenas B101 (assert) e B110 (try-except-pass)

---

## 📈 Impacto

| Métrica | Antes | Depois | Mudança |
|---------|-------|--------|---------|
| **Itens na raiz** | 82 | 52 | **-30 (-37%)** |
| **Arquivos na raiz** | 60 | 29 | **-31 (-52%)** |
| **Temporários na raiz** | 15 | **0** | **-15 (-100%)** |

---

## ✅ Como Testar

### 1. Validação de Testes
```powershell
# Rodar testes do módulo principal
pytest tests/modules/clientes_v2/ -v

# Resultado esperado: 113/113 PASSED
```

### 2. Validação de Qualidade
```powershell
# Ruff
ruff check src/ tests/
# Resultado esperado: 0 errors

# Pre-commit
pre-commit run --all-files
# Resultado esperado: 20/20 PASSED
```

### 3. Verificar Links de Documentação
- Abrir `README.md` → Link para `docs/README.md` deve funcionar
- Abrir `docs/README.md` → Todos os links relativos devem funcionar
- Links entre documentos em `docs/` devem estar corretos

### 4. Smoke Test da Aplicação
```powershell
python main.py
# Aplicação deve iniciar normalmente
```

---

## ⚠️ Limitações Conhecidas

### Testes Legacy
Alguns testes antigos em `tests/unit/modules/clientes/` falham na coleta por imports de módulos refatorados. Estes testes **não fazem parte do escopo desta PR**, que foca em reorganização estrutural.

**Testes validados:**
- ✅ `tests/modules/clientes_v2/` - 113/113 PASSED
- ⚠️ `tests/unit/modules/clientes/` - 36 erros de coleta (módulos refatorados, fora do escopo)

### Pyright
Pyright ainda reporta **61 errors e 845 warnings** relacionados a código legacy e third-party. Estes issues existem antes desta PR e **não fazem parte do escopo**. O pre-commit passou 100% (20/20 hooks).

---

## 🔍 Checklist de Revisão

- [x] Todos os arquivos versionados estão na branch
- [x] `tools/repo/` não requer `git add -f`
- [x] Pre-commit hooks 100% verdes
- [x] Bandit sem issues de segurança
- [x] Documentação organizada e links corretos
- [x] README.md atualizado com destaque para `docs/`
- [x] .gitignore configurado corretamente
- [x] Arquivos temporários movidos para `artifacts/local/`
- [x] Testes principais (clientes_v2) passando

---

## 📝 Notas Adicionais

### Stash Pendente
Há um stash guardado antes da reorganização:
```
stash@{0}: On refactor/estrutura-pdf-v1.5.35: WIP: before repo cleanup
```

Pode ser descartado após merge desta PR:
```powershell
git stash drop stash@{0}
```

### Próximos Passos (Pós-Merge)
1. Fazer merge para `refactor/estrutura-pdf-v1.5.35`
2. Rodar validação completa
3. Atualizar documentação de contribuição se necessário
4. Limpar branches antigas

---

## 🎉 Conclusão

Esta reorganização deixa o repositório mais limpo, organizado e profissional, facilitando:
- **Navegação**: Raiz com apenas essenciais
- **Manutenção**: Documentação centralizada em `docs/`
- **Onboarding**: Estrutura clara para novos colaboradores
- **CI/CD**: Pre-commit garantindo qualidade automaticamente
