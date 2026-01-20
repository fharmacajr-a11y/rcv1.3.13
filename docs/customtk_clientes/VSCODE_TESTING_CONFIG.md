# Configurações Recomendadas para VS Code Testing

**Data:** 13/01/2026  
**Status:** Recomendações para evitar painel Testing abrindo automaticamente

---

## 🎯 Problema

O painel "Testing" do VS Code pode abrir automaticamente durante o desenvolvimento, interrompendo o fluxo de trabalho. Isso acontece quando:

1. **Auto-descoberta de testes** está habilitada
2. **Auto-exibição de resultados** está ativa
3. **Salvar arquivos** dispara re-scan de testes

---

## ✅ Solução: Configurações Recomendadas

### Opção 1: Configuração no Workspace (Recomendada)

Crie ou edite `.vscode/settings.json` na raiz do projeto:

```json
{
    // ===== PYTHON TESTING =====
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "python.testing.autoTestDiscoverOnSaveEnabled": false,
    
    // ===== VS CODE TESTING UI =====
    "testing.openTesting": "neverOpen",
    "testing.automaticallyOpenPeekView": "never",
    "testing.automaticallyOpenPeekViewDuringAutoRun": false,
    
    // ===== OUTRAS CONFIGURAÇÕES ÚTEIS =====
    "python.analysis.typeCheckingMode": "basic",
    "python.analysis.autoImportCompletions": true,
    "files.watcherExclude": {
        "**/.git/objects/**": true,
        "**/.git/subtree-cache/**": true,
        "**/node_modules/**": true,
        "**/.venv/**": true,
        "**/htmlcov/**": true,
        "**/__pycache__/**": true,
        "**/.pytest_cache/**": true
    }
}
```

### Opção 2: Configuração Global do Usuário

Se preferir aplicar para todos os projetos, vá em:

**File → Preferences → Settings** (ou `Ctrl+,`)

Pesquise por:
- `testing.openTesting` → **neverOpen**
- `testing.automaticallyOpenPeekView` → **never**
- `python.testing.autoTestDiscoverOnSaveEnabled` → **false**

---

## 📋 Descrição das Configurações

### Python Testing

| Configuração | Valor | Descrição |
|-------------|-------|-----------|
| `python.testing.pytestEnabled` | `true` | Habilita pytest como framework de testes |
| `python.testing.unittestEnabled` | `false` | Desabilita unittest (evita conflito) |
| `python.testing.autoTestDiscoverOnSaveEnabled` | `false` | **CRÍTICO:** Impede re-scan ao salvar arquivos |

### VS Code Testing UI

| Configuração | Valor | Descrição |
|-------------|-------|-----------|
| `testing.openTesting` | `"neverOpen"` | **CRÍTICO:** Nunca abre painel Testing automaticamente |
| `testing.automaticallyOpenPeekView` | `"never"` | Não abre peek view de testes |
| `testing.automaticallyOpenPeekViewDuringAutoRun` | `false` | Não abre peek durante auto-run |

### File Watcher

Excluir diretórios desnecessários do watcher melhora performance:
- `.venv/` → Ambiente virtual Python
- `htmlcov/` → Relatórios de cobertura
- `__pycache__/` → Cache compilado Python
- `.pytest_cache/` → Cache do pytest

---

## 🧪 Como Executar Testes Manualmente

### Via Terminal (Recomendado)

```powershell
# Todos os testes
python -m pytest tests/ -v

# Testes do módulo Clientes
python -m pytest tests/modules/clientes/ -v

# Com relatório de skips detalhado
python -m pytest -ra --no-fold-skipped

# Com cobertura
python -m pytest --cov=src --cov-report=html
```

### Via VS Code Testing UI (Opcional)

1. Abrir painel Testing: `Ctrl+Shift+T` ou clicar no ícone de erlenmeyer
2. Clicar em "▶ Run All Tests" ou selecionar testes específicos
3. Ver resultados inline no código ou no painel

---

## 🔍 Troubleshooting

### Problema: Painel Testing ainda abre

**Solução:**
1. Verifique se `.vscode/settings.json` está na raiz do projeto (não em subdiretórios)
2. Recarregue janela do VS Code: `Ctrl+Shift+P` → "Developer: Reload Window"
3. Se persistir, configure globalmente em User Settings

### Problema: Testes não são descobertos

**Solução:**
1. Abrir Command Palette: `Ctrl+Shift+P`
2. Executar: "Python: Configure Tests"
3. Selecionar pytest
4. Selecionar diretório raiz: `tests/`
5. Verificar se `pytest.ini` existe na raiz

### Problema: pytest.ini não encontrado

**Solução:**
O arquivo `pytest.ini` deve estar na raiz do projeto com:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -ra --strict-markers --strict-config
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
```

---

## 📌 Boas Práticas

### 1. Executar Testes Localmente Antes de Commit

```powershell
# Quick smoke test
python -m pytest tests/modules/clientes/ -v

# Full test suite
python -m pytest tests/ -v
```

### 2. Não Commitar `.vscode/settings.json` se Contiver Configurações Pessoais

Adicione ao `.gitignore` se necessário:
```
.vscode/settings.json
```

Ou crie um `.vscode/settings.json.example` com configurações recomendadas.

### 3. Usar `-v` para Ver Nomes de Testes

```powershell
python -m pytest -v
```

Output:
```
tests/modules/clientes/test_clientes_toolbar_ctk_visual_polish_smoke.py::test_toolbar_ctk_imports PASSED
tests/modules/clientes/test_clientes_actionbar_ctk_smoke.py::test_actionbar_ctk_imports PASSED
```

### 4. Filtrar Testes por Nome

```powershell
# Apenas testes smoke
python -m pytest -k "smoke" -v

# Apenas testes de toolbar
python -m pytest -k "toolbar" -v

# Excluir testes lentos
python -m pytest -m "not slow" -v
```

---

## 🎓 Referências

- [VS Code Testing Documentation](https://code.visualstudio.com/docs/python/testing)
- [pytest Documentation](https://docs.pytest.org/)
- [VS Code Settings Reference](https://code.visualstudio.com/docs/getstarted/settings)

---

**Autor:** Equipe de Desenvolvimento  
**Revisão:** Pendente
